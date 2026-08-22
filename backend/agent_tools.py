# -*- coding: utf-8 -*-
"""Agent-callable delivery-risk analysis for Data Studio."""

from __future__ import annotations

import json
from typing import Any

try:
    from .risk_engine import analyze_orders
except ImportError:
    from risk_engine import analyze_orders


class RiskToolInputError(ValueError):
    """Raised when an Agent passes an unsupported query result shape."""


def parse_order_payload(orders_json: str) -> list[dict[str, Any]]:
    """Accept Data Core query output, a record list, or a plain order list."""
    try:
        payload = json.loads(orders_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RiskToolInputError("orders_json 必须是有效 JSON") from exc

    if isinstance(payload, dict) and "records" in payload:
        payload = payload["records"]
    elif isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise RiskToolInputError("订单数据必须是数组或 Data Core 查询结果")
    if len(payload) > 1000:
        raise RiskToolInputError("单次最多分析1000条订单")

    orders: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise RiskToolInputError("每条订单必须是对象")
        data = item.get("data", item)
        if not isinstance(data, dict):
            raise RiskToolInputError("订单 data 必须是对象")
        order = dict(data)
        # Provenance must survive analysis so every Agent conclusion can be
        # traced back to the exact persistent Data Core record.
        order["record_id"] = item.get("record_id", data.get("record_id"))
        order["source_type"] = item.get("source_type", data.get("source_type"))
        if not order["record_id"] or order["source_type"] not in {"real", "simulated"}:
            raise RiskToolInputError("每条订单必须包含 Data Core record_id 和 source_type")
        orders.append(order)
    return orders


def analyze_order_delivery_risk(
    orders_json: str,
    top_n: int = 20,
    include_green: bool = False,
) -> Any:
    """Analyze delivery risk for orders returned by Data Core.

    First call query_enterprise_orders, then pass its JSON result to this
    tool. It returns red/yellow/green counts plus evidence-backed reasons.
    """
    from agentscope.message import TextBlock, ToolResultState
    from agentscope.tool import ToolChunk

    try:
        orders = parse_order_payload(orders_json)
        analysis = analyze_orders(orders)
        results = analysis["results"]
        if not include_green:
            results = [item for item in results if item["level"] != "green"]
        capped = max(1, min(int(top_n), 100))
        for result, order in zip(analysis["results"], orders):
            result.update({"record_id": order["record_id"], "source_type": order["source_type"]})
        payload = {
            "summary": analysis["summary"],
            "returned": min(len(results), capped),
            "risk_orders": results[:capped],
            "method": "rule-based-explainable-v1",
        }
        return ToolChunk(
            state=ToolResultState.SUCCESS,
            content=[TextBlock(type="text", text=json.dumps(payload, ensure_ascii=False))],
        )
    except (RiskToolInputError, TypeError, ValueError) as exc:
        return ToolChunk(
            state=ToolResultState.ERROR,
            content=[TextBlock(type="text", text=f"交付风险分析失败：{exc}")],
        )
