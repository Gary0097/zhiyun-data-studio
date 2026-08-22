# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path

from backend.insight_workflow import InsightWorkflowStore


class InsightWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "insights.db"
        self.store = InsightWorkflowStore(self.database)
        self.refs = [{"record_id": "rec-real-1", "source_type": "real"}]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_project_run_artifact_trace_and_sources_are_persisted(self) -> None:
        artifact = self.store.create_artifact("daily_brief", "订单日报", {"summary": {"total": 1}}, self.refs)
        self.assertEqual(artifact["project_status"], "pending_review")
        self.assertEqual(artifact["run_status"], "completed")
        self.assertTrue(artifact["trace_id"])
        self.assertEqual(artifact["source_refs"], self.refs)
        reopened = InsightWorkflowStore(self.database).get_artifact(artifact["id"])
        self.assertEqual(reopened["content"]["summary"]["total"], 1)

    def test_review_revoke_and_export_gate(self) -> None:
        artifact = self.store.create_artifact("kpi_trend", "趋势", {"series": []}, self.refs)
        with self.assertRaisesRegex(ValueError, "已接受"):
            self.store.export(artifact["id"])
        accepted = self.store.review(artifact["id"], "accept", "王审核", "数据已复核")
        self.assertEqual(accepted["project_status"], "accepted")
        content, media = self.store.export(artifact["id"])
        self.assertEqual(media, "application/json")
        self.assertEqual(json.loads(content)["reviews"][-1]["reviewer"], "王审核")
        revoked = self.store.review(artifact["id"], "revoke", "王审核")
        self.assertEqual(revoked["project_status"], "pending_review")

    def test_invalid_or_missing_data_core_provenance_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "record_id"):
            self.store.create_artifact("daily_brief", "日报", {}, [{"source_type": "real"}])
        with self.assertRaisesRegex(ValueError, "来源"):
            self.store.create_artifact("daily_brief", "日报", {}, [])

    def test_database_can_be_removed_after_use_on_windows(self) -> None:
        self.store.create_artifact("delivery_risk", "风险", {"red": 1}, self.refs)
        self.database.unlink()
        self.assertFalse(self.database.exists())


if __name__ == "__main__":
    unittest.main()
