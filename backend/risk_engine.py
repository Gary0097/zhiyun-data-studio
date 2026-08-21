# -*- coding: utf-8 -*-
"""Explainable delivery-risk scoring for order records."""

from __future__ import annotations

from datetime import date
from typing import Any


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


COMPLETED_STATUSES = {"已完成", "已交付", "完成", "closed", "completed", "delivered"}
LOGISTICS_STATUSES = {"待发货", "运输中", "已发货", "shipping", "in_transit"}


def _integer(value: Any) -> int:
    try:
        return max(0, int(float(value or 0)))
    except (TypeError, ValueError):
        return 0


def score_order(order: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Score one order and return evidence-backed risk reasons."""
    now = today or date.today()
    score = 0
    reasons: list[str] = []
    promised = _day(order.get("promised_date"))
    logistics = _day(order.get("last_logistics_update"))
    status = str(order.get("status", "")).strip()
    status_key = status.casefold()
    completed = status_key in COMPLETED_STATUSES
    progress = min(100.0, max(0.0, _number(order.get("progress"))))
    production_delay = _integer(order.get("production_delay_days"))
    data_quality_issues: list[str] = []
    if not order.get("order_no"):
        data_quality_issues.append("缺少订单编号")
    if not promised:
        data_quality_issues.append("缺少或无法识别承诺交期")
    if not status:
        data_quality_issues.append("缺少订单状态")

    if promised and not completed:
        remaining = (promised - now).days
        if remaining < 0:
            points = min(70, 20 + abs(remaining) * 4)
            score += points
            reasons.append(f"已超过承诺交期{abs(remaining)}天")
        elif remaining <= 3 and progress < 90:
            score += 30
            reasons.append(f"距交期仅{remaining}天，当前进度{progress:g}%")

    if production_delay:
        points = min(35, production_delay * 5)
        score += points
        reasons.append(f"生产延误{production_delay}天")

    if logistics and status_key in LOGISTICS_STATUSES:
        stale = (now - logistics).days
        if stale >= 3:
            score += min(30, stale * 4)
            reasons.append(f"物流{stale}天未更新")

    if status == "生产中" and progress < 30:
        score += 10
        reasons.append("生产进度低于30%")

    score = min(100, score)
    level = "red" if score >= 60 else "yellow" if score >= 30 else "green"
    if not reasons:
        reasons.append("暂未发现明显交付风险信号")
    return {
        "order_no": order.get("order_no"),
        "customer_name": order.get("customer_name"),
        "status": status,
        "promised_date": order.get("promised_date"),
        "progress": progress,
        "score": score,
        "level": level,
        "reasons": reasons,
        "data_quality_issues": data_quality_issues,
    }


def analyze_orders(orders: list[dict[str, Any]], today: date | None = None) -> dict[str, Any]:
    """Score and summarize an order collection."""
    results = [score_order(order, today) for order in orders]
    results.sort(key=lambda item: (-item["score"], str(item.get("order_no") or "")))
    overdue = 0
    due_soon = 0
    quality_issues = 0
    status_distribution: dict[str, int] = {}
    for order, result in zip(orders, results, strict=False):
        promised = _day(order.get("promised_date"))
        status = str(order.get("status", "")).strip()
        status_distribution[status or "未填写"] = status_distribution.get(status or "未填写", 0) + 1
        if promised and status.casefold() not in COMPLETED_STATUSES:
            remaining = (promised - (today or date.today())).days
            overdue += remaining < 0
            due_soon += 0 <= remaining <= 3
        quality_issues += len(result["data_quality_issues"])
    total = len(results)
    summary = {
        "total": total,
        "red": sum(item["level"] == "red" for item in results),
        "yellow": sum(item["level"] == "yellow" for item in results),
        "green": sum(item["level"] == "green" for item in results),
        "risk_rate": round(100 * sum(item["level"] != "green" for item in results) / total, 1) if total else 0.0,
        "average_progress": round(sum(item["progress"] for item in results) / total, 1) if total else 0.0,
        "overdue": overdue,
        "due_within_3_days": due_soon,
        "data_quality_issues": quality_issues,
    }
    return {"summary": summary, "status_distribution": status_distribution, "results": results}
