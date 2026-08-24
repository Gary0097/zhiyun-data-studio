# -*- coding: utf-8 -*-
"""Data Studio file parsing and explainable analysis endpoints."""

from __future__ import annotations

import sys
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from qwenpaw.plugins.api import PluginApi

try:
    from .agent_tools import analyze_order_delivery_risk
    from .brief_engine import generate_order_daily_brief
    from .fusion_engine import analyze_department_metrics
    from .risk_engine import analyze_orders
    from .order_contract import OrderContractError, build_agent_context, normalize_order_response
    from .trend_engine import analyze_order_trends
    from .table_parser import parse_table
    from .insight_workflow import InsightWorkflowStore
except ImportError:
    backend_dir = str(Path(__file__).resolve().parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from agent_tools import analyze_order_delivery_risk
    from brief_engine import generate_order_daily_brief
    from fusion_engine import analyze_department_metrics
    from risk_engine import analyze_orders
    from order_contract import OrderContractError, build_agent_context, normalize_order_response
    from trend_engine import analyze_order_trends
    from table_parser import parse_table
    from insight_workflow import InsightWorkflowStore

router = APIRouter()
MAX_UPLOAD = 20 * 1024 * 1024
PLUGIN_VERSION = "0.9.2"


def _insights() -> InsightWorkflowStore:
    try:
        return InsightWorkflowStore()
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(status_code=503, detail=f"分析工件存储不可用：{exc}") from exc


class RiskRequest(BaseModel):
    orders: list[dict[str, Any]] = Field(max_length=5000)


class FusionRequest(BaseModel):
    records: list[dict[str, Any]] = Field(max_length=10000)
    mapping: dict[str, str]


class DataCoreOrdersRequest(BaseModel):
    payload: Any


class AgentContextRequest(BaseModel):
    order: dict[str, Any]


class ArtifactRequest(BaseModel):
    kind: str
    name: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    content: dict[str, Any]
    source_refs: list[dict[str, Any]] = Field(min_length=1, max_length=5000)


class ArtifactReviewRequest(BaseModel):
    action: str
    reviewer: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=2000)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "available", "version": PLUGIN_VERSION, "data_core_required": True}


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


@router.post("/orders/normalize")
async def normalize_orders(request: DataCoreOrdersRequest) -> dict[str, Any]:
    """Validate the public Data Core orders query contract for the UI."""
    try:
        return normalize_order_response(request.payload)
    except OrderContractError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/agent/context")
async def agent_context(request: AgentContextRequest) -> dict[str, Any]:
    """Return a provenance-preserving context object for the host Agent."""
    try:
        return build_agent_context(request.order)
    except OrderContractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/trends/analyze")
async def trend_analysis(request: RiskRequest) -> dict[str, Any]:
    return analyze_order_trends(request.orders)


@router.post("/brief/daily")
async def daily_brief(request: RiskRequest) -> dict[str, Any]:
    return generate_order_daily_brief(request.orders)


@router.post("/fusion/analyze")
async def fusion_analysis(request: FusionRequest) -> dict[str, Any]:
    try:
        return analyze_department_metrics(request.records, request.mapping)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/artifacts")
async def create_artifact(request: ArtifactRequest) -> dict[str, Any]:
    try:
        return _insights().create_artifact(request.kind, request.name, request.content,
                                           request.source_refs, request.title)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail=f"分析工件存储不可用：{exc}") from exc


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str) -> dict[str, Any]:
    try:
        return _insights().get_artifact(artifact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="分析工件不存在") from exc


@router.post("/artifacts/{artifact_id}/reviews")
async def review_artifact(artifact_id: str, request: ArtifactReviewRequest) -> dict[str, Any]:
    try:
        return _insights().review(artifact_id, request.action, request.reviewer, request.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="分析工件不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/artifacts/{artifact_id}/export")
async def export_artifact(artifact_id: str) -> Response:
    try:
        content, media_type = _insights().export(artifact_id)
        return Response(content=content, media_type=media_type,
                        headers={"Content-Disposition": 'attachment; filename="data-studio-artifact.json"'})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="分析工件不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def analyze_order_kpi_trends(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze monthly order count, progress and production delay trends."""
    return analyze_order_trends(orders)


def create_order_daily_brief(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a one-page order management brief with risks and trend insights."""
    return generate_order_daily_brief(orders)


def analyze_cross_department_metrics(records: list[dict[str, Any]], mapping: dict[str, str]) -> dict[str, Any]:
    """Calculate configurable department output, labor, cost and loss indicators."""
    return analyze_department_metrics(records, mapping)


class DataStudioPlugin:
    """Register Data Studio helpers inside the QwenPaw process."""

    def register(self, api: PluginApi) -> None:
        api.register_http_router(router, prefix="/zhiyun-data-studio", tags=["zhiyun-data-studio"])
        api.register_tool(
            tool_name="analyze_order_delivery_risk",
            tool_func=analyze_order_delivery_risk,
            description="分析 Data Core 查询出的订单交付风险，返回红黄绿统计、风险分数和可解释原因。",
            icon="⚠️",
            tool_type="internal",
        )
        api.register_tool(
            tool_name="analyze_cross_department_metrics",
            tool_func=analyze_cross_department_metrics,
            description="根据用户指定的部门、产量、工时、人数、成本和损耗字段，生成部门级人效、单位成本和损耗率指标。",
            icon="🏭",
            tool_type="internal",
        )
        api.register_tool(
            tool_name="create_order_daily_brief",
            tool_func=create_order_daily_brief,
            description="根据订单数据生成一页式每日管理简报，包含交付风险、逾期、临期、数据质量和趋势结论，并明确数据覆盖范围。",
            icon="📰",
            tool_type="internal",
        )
        api.register_tool(
            tool_name="analyze_order_kpi_trends",
            tool_func=analyze_order_kpi_trends,
            description="按月分析订单量、平均进度和生产延误率，返回上升/下降/平稳趋势与异常月份。",
            icon="📈",
            tool_type="internal",
        )


plugin = DataStudioPlugin()
