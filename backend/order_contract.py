# -*- coding: utf-8 -*-
"""Contract helpers for persistent orders returned by AI-OS Data Core."""

from __future__ import annotations

from typing import Any


ORDER_FIELDS = (
    "order_no", "customer_name", "product_name", "quantity",
    "promised_date", "status", "progress",
)
VALID_SOURCE_TYPES = {"real", "simulated"}


class OrderContractError(ValueError):
    """Raised when Data Core returns an unsupported response shape."""


def normalize_order_response(payload: Any) -> dict[str, Any]:
    """Normalize ``GET /zhiyun-data-core/orders`` without inventing values."""
    if isinstance(payload, list):
        raw_records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("orders"), list):
        raw_records = payload["orders"]
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        raw_records = payload["records"]
    else:
        raise OrderContractError("Data Core 订单响应必须包含 orders 或 records 数组")

    orders: list[dict[str, Any]] = []
    for index, record in enumerate(raw_records):
        if not isinstance(record, dict):
            raise OrderContractError(f"第 {index + 1} 条订单不是对象")
        data = record.get("data", record)
        if not isinstance(data, dict):
            raise OrderContractError(f"第 {index + 1} 条订单 data 不是对象")
        order = {field: data.get(field) for field in ORDER_FIELDS}
        order.update({
            "record_id": record.get("record_id", data.get("record_id")),
            "source_type": record.get("source_type", data.get("source_type")),
            "source_name": record.get("source_name", data.get("source_name")),
        })
        order["missing_fields"] = [field for field in ORDER_FIELDS if data.get(field) in (None, "")]
        orders.append(order)
    return {"orders": orders, "total": len(orders)}


def build_agent_context(order: dict[str, Any]) -> dict[str, Any]:
    """Build auditable app context for one persisted Data Core record."""
    record_id = order.get("record_id") or order.get("__record_id")
    source_type = order.get("source_type") or order.get("__source_type")
    if not record_id:
        raise OrderContractError("订单缺少 Data Core record_id，不能加入 Agent 上下文")
    if source_type not in VALID_SOURCE_TYPES:
        raise OrderContractError("订单缺少有效的 Data Core source_type")
    return {
        "type": "data-core-order",
        "entity": "orders",
        "record_id": str(record_id),
        "source_type": source_type,
        "order_no": order.get("order_no"),
        "label": f"订单 {order.get('order_no') or record_id}",
    }
