# -*- coding: utf-8 -*-
"""One-page daily management brief generated from auditable order data."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

try:
    from .risk_engine import analyze_orders
    from .trend_engine import analyze_order_trends
except ImportError:
    from risk_engine import analyze_orders
    from trend_engine import analyze_order_trends


def generate_order_daily_brief(orders: list[dict[str, Any]], today: date | None = None) -> dict[str, Any]:
    """Generate a deterministic order-domain brief without inventing missing domains."""
    current = today or date.today()
    risks = analyze_orders(orders, current)
    trends = analyze_order_trends(orders)
    summary = risks["summary"]
    insights: list[dict[str, str]] = []
    if summary["red"]:
        insights.append({"level": "critical", "text": f"{summary['red']}笔订单为高风险，建议优先核查交期、生产延误和物流状态。"})
    if summary["overdue"]:
        insights.append({"level": "critical", "text": f"{summary['overdue']}笔未完成订单已超过承诺交期。"})
    if summary["due_within_3_days"]:
        insights.append({"level": "warning", "text": f"{summary['due_within_3_days']}笔订单将在3天内到期。"})
    if summary["data_quality_issues"]:
        insights.append({"level": "warning", "text": f"发现{summary['data_quality_issues']}个关键字段质量问题，风险结论可能不完整。"})
    direction = trends["summary"]["direction"]
    if trends["summary"]["periods"] >= 2:
        insights.append({"level": "info", "text": f"月度订单量趋势为{direction}，月均变化{trends['summary']['order_count_slope']}笔。"})
    if not insights:
        insights.append({"level": "normal", "text": "当前订单数据未发现明显交付异常。"})

    top_risks = [item for item in risks["results"] if item["level"] != "green"][:10]
    return {
        "brief_date": current.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_scope": ["orders"],
        "missing_domains": ["production", "finance", "after_sales"],
        "summary": summary,
        "trend_summary": trends["summary"],
        "insights": insights,
        "top_risks": top_risks,
        "disclaimer": "当前简报仅覆盖订单域；生产、财务和售后数据接入后才能形成完整企业日报。",
    }
