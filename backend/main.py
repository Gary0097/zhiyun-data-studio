# -*- coding: utf-8 -*-
"""Data Studio file parsing and explainable analysis endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from qwenpaw.plugins.api import PluginApi

try:
    from .risk_engine import analyze_orders
    from .table_parser import parse_table
except ImportError:
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


plugin = DataStudioPlugin()
