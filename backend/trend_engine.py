# -*- coding: utf-8 -*-
"""Deterministic KPI trend analysis for order data."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import sqrt
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


def analyze_order_trends(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate orders by month and calculate simple explainable trends."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid_dates = 0
    for order in orders:
        parsed = _day(order.get("order_date"))
        if parsed:
            groups[parsed.strftime("%Y-%m")].append(order)
        else:
            invalid_dates += 1

    series = []
    for period in sorted(groups):
        rows = groups[period]
        total = len(rows)
        average_progress = round(sum(max(0, min(100, _number(row.get("progress")))) for row in rows) / total, 1)
        delayed = sum(_number(row.get("production_delay_days")) > 0 for row in rows)
        series.append({
            "period": period,
            "order_count": total,
            "average_progress": average_progress,
            "delay_rate": round(100 * delayed / total, 1),
        })

    values = [item["order_count"] for item in series]
    slope = 0.0
    if len(values) >= 2:
        xs = list(range(len(values)))
        x_mean = sum(xs) / len(xs)
        y_mean = sum(values) / len(values)
        denominator = sum((x - x_mean) ** 2 for x in xs)
        slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values)) / denominator if denominator else 0.0

    anomalies = []
    if len(values) >= 3:
        mean = sum(values) / len(values)
        deviation = sqrt(sum((value - mean) ** 2 for value in values) / len(values))
        if deviation:
            anomalies = [item["period"] for item in series if abs(item["order_count"] - mean) >= 1.5 * deviation]

    direction = "上升" if slope > 0.5 else "下降" if slope < -0.5 else "平稳"
    return {
        "summary": {
            "periods": len(series),
            "valid_orders": sum(values),
            "invalid_date_records": invalid_dates,
            "order_count_slope": round(slope, 2),
            "direction": direction,
            "anomaly_periods": anomalies,
            "method": "按月聚合 + 最小二乘线性趋势 + 1.5倍标准差异常识别",
        },
        "series": series,
    }
