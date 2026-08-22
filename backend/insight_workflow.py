# -*- coding: utf-8 -*-
"""Durable review workflow for Data Studio analytical artifacts."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InsightWorkflowStore:
    """Persist derived artifacts without copying or mutating Data Core records."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.getenv("DATA_STUDIO_DB")
        self.path = Path(configured) if configured else Path.home() / ".zhiyun-data-studio" / "insights.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path))
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS insight_projects (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS insight_runs (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES insight_projects(id),
                    kind TEXT NOT NULL, status TEXT NOT NULL, trace_id TEXT NOT NULL,
                    started_at TEXT NOT NULL, finished_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS insight_artifacts (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES insight_projects(id),
                    run_id TEXT NOT NULL REFERENCES insight_runs(id), kind TEXT NOT NULL, name TEXT NOT NULL,
                    content_json TEXT NOT NULL, source_refs_json TEXT NOT NULL, version INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS insight_reviews (
                    id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL REFERENCES insight_artifacts(id),
                    action TEXT NOT NULL, reviewer TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL
                );
            """)

    @staticmethod
    def _normalize_refs(source_refs: list[dict[str, Any]]) -> list[dict[str, str]]:
        normalized = []
        for item in source_refs:
            record_id = str(item.get("record_id") or "").strip()
            source_type = str(item.get("source_type") or "").strip()
            if not record_id or source_type not in {"real", "simulated"}:
                raise ValueError("每个来源必须包含 Data Core record_id 和 real/simulated source_type")
            normalized.append({"record_id": record_id, "source_type": source_type})
        if not normalized:
            raise ValueError("分析工件至少需要一个可追溯 Data Core 来源")
        return normalized

    def create_artifact(self, kind: str, name: str, content: dict[str, Any],
                        source_refs: list[dict[str, Any]], title: str | None = None) -> dict[str, Any]:
        if kind not in {"delivery_risk", "department_fusion", "daily_brief", "kpi_trend"}:
            raise ValueError("不支持的分析工件类型")
        if not name.strip() or not isinstance(content, dict):
            raise ValueError("工件名称和内容不能为空")
        refs = self._normalize_refs(source_refs)
        project_id, run_id, artifact_id, now = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), _now()
        trace_id = str(uuid.uuid4())
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO insight_projects VALUES (?,?,?,?,?)", (
                project_id, title or name.strip(), "pending_review", now, now))
            db.execute("INSERT INTO insight_runs VALUES (?,?,?,?,?,?,?)", (
                run_id, project_id, kind, "completed", trace_id, now, now))
            db.execute("INSERT INTO insight_artifacts VALUES (?,?,?,?,?,?,?,?,?)", (
                artifact_id, project_id, run_id, kind, name.strip(), json.dumps(content, ensure_ascii=False),
                json.dumps(refs, ensure_ascii=False), 1, now))
        return self.get_artifact(artifact_id)

    def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        with closing(self._connect()) as db, db:
            row = db.execute("""
                SELECT a.*, p.title AS project_title, p.status AS project_status, r.trace_id, r.status AS run_status
                FROM insight_artifacts a JOIN insight_projects p ON p.id=a.project_id
                JOIN insight_runs r ON r.id=a.run_id WHERE a.id=?
            """, (artifact_id,)).fetchone()
            if not row:
                raise KeyError(artifact_id)
            result = dict(row)
            result["content"] = json.loads(result.pop("content_json"))
            result["source_refs"] = json.loads(result.pop("source_refs_json"))
            result["reviews"] = [dict(item) for item in db.execute(
                "SELECT * FROM insight_reviews WHERE artifact_id=? ORDER BY created_at", (artifact_id,))]
            return result

    def review(self, artifact_id: str, action: str, reviewer: str, note: str | None = None) -> dict[str, Any]:
        if action not in {"accept", "revoke"}:
            raise ValueError("审阅动作必须是 accept 或 revoke")
        if not reviewer.strip():
            raise ValueError("审阅人不能为空")
        artifact = self.get_artifact(artifact_id)
        now = _now()
        status = "accepted" if action == "accept" else "pending_review"
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO insight_reviews VALUES (?,?,?,?,?,?)", (
                str(uuid.uuid4()), artifact_id, action, reviewer.strip(), note, now))
            db.execute("UPDATE insight_projects SET status=?, updated_at=? WHERE id=?", (
                status, now, artifact["project_id"]))
        return self.get_artifact(artifact_id)

    def export(self, artifact_id: str) -> tuple[str, str]:
        artifact = self.get_artifact(artifact_id)
        if artifact["project_status"] != "accepted":
            raise ValueError("只有已接受的分析工件可以导出")
        return json.dumps(artifact, ensure_ascii=False, indent=2), "application/json"
