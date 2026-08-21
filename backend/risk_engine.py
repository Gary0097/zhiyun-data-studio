# -*- coding: utf-8 -*-
"""Explainable delivery-risk scoring for order records."""

from __future__ import annotations

from datetime import date
from typing import Any


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def score_order(order: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Score one order and return evidence-backed risk reasons."""
    now = today or date.today()
    score = 0
    reasons: list[str] = []
    promised = _day(order.get("promised_date"))
    logistics = _day(order.get("last_logistics_update"))
    status = str(order.get("status", ""))
    progress = float(order.get("progress") or 0)
    production_delay = max(0, int(order.get("production_delay_days") or 0))

    if promised and status != "已完成":
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

    if logistics and status in {"待发货", "运输中"}:
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
        "score": score,
        "level": level,
        "reasons": reasons,
    }


def analyze_orders(orders: list[dict[str, Any]], today: date | None = None) -> dict[str, Any]:
    """Score and summarize an order collection."""
    results = [score_order(order, today) for order in orders]
    results.sort(key=lambda item: (-item["score"], str(item.get("order_no") or "")))
    summary = {
        "total": len(results),
        "red": sum(item["level"] == "red" for item in results),
        "yellow": sum(item["level"] == "yellow" for item in results),
        "green": sum(item["level"] == "green" for item in results),
    }
    return {"summary": summary, "results": results}
