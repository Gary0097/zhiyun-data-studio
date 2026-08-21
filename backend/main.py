# -*- coding: utf-8 -*-
"""Data Studio file parsing and explainable analysis endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from qwenpaw.plugins.api import PluginApi

try:
    from .agent_tools import analyze_order_delivery_risk
    from .risk_engine import analyze_orders
    from .table_parser import parse_table
except ImportError:
    backend_dir = str(Path(__file__).resolve().parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from agent_tools import analyze_order_delivery_risk
    from risk_engine import analyze_orders
    from table_parser import parse_table

router = APIRouter()
MAX_UPLOAD = 20 * 1024 * 1024


class RiskRequest(BaseModel):
    orders: list[dict[str, Any]] = Field(max_length=5000)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "available", "data_core_required": True}


@router.post("/parse")
async def parse_upload(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="文件不能超过20MB")
    try:
        return parse_table(file.filename or "upload", content)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/risk/analyze")
async def risk_analysis(request: RiskRequest) -> dict[str, Any]:
    return analyze_orders(request.orders)


class DataStudioPlugin:
    """Register Data Studio helpers inside the QwenPaw process."""

    def register(self, api: PluginApi) -> None:
        api.register_http_router(router, prefix="/zhiyun-data-studio", tags=["zhiyun-data-studio"])
        api.register_tool(
            tool_name="analyze_order_delivery_risk",
            tool_func=analyze_order_delivery_risk,
            description="分析 Data Core 查询出的订单交付风险，返回红黄绿统计、风险分数和可解释原因。",
            icon="⚠️",
            tool_type="filesystem",
        )


plugin = DataStudioPlugin()
