from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from holisticaquant.config.config import get_config
from holisticaquant.graph import HolisticaGraph
from holisticaquant.memory.scenario_repository import (
    get_learning_topics,
    get_research_templates,
    load_scenario_library,
)
from holisticaquant.utils.llm_factory import create_llm


class QueryRequest(BaseModel):
    """统一查询入参"""

    query: str = Field(..., min_length=1, description="用户输入的查询或任务描述")
    provider: Optional[str] = Field(
        default=None,
        description="可选的 LLM 提供商覆盖（默认使用配置中的优先级）",
    )
    scenario_override: Optional[str] = Field(
        default=None,
        pattern=r"^(learning_workshop|research_lab|assistant)$",
        description="可选的场景覆盖，通常保持 None 由系统自动判定",
    )
    return_trace: bool = Field(False, description="是否返回完整 trace 信息（调试用途）")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="可选上下文，未提供时将自动注入 trigger_time",
    )


class QueryResponse(BaseModel):
    """统一查询出参"""

    scenario_type: str = Field(..., description="最终判定的核心场景类型")
    plan: Optional[Dict[str, Any]] = Field(None, description="规划阶段的结构化结果")
    tickers: List[str] = Field(default_factory=list, description="识别出的股票代码列表")
    plan_target_id: Optional[str] = Field(None, description="计划阶段选取的目标 ID")
    report: str = Field(..., description="最终 Markdown 报告或回答")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="辅助元数据（学习卡片、问答摘要等）")
    segments: Dict[str, Any] = Field(
        default_factory=dict,
        description="按模块拆分的结构化段落，便于前端逐块展示",
    )
    trace: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="可选的 trace 信息，仅当 return_trace=true 时返回",
    )


def build_application() -> FastAPI:
    app = FastAPI(title="HolisticaQuant API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup() -> None:  # pragma: no cover - FastAPI 生命周期
        config = get_config().config
        provider_override = config.get("llm", {}).get("provider")
        app.state.config = config
        app.state.provider_override = provider_override
        app.state.llm = create_llm(provider=provider_override, config=config)
        app.state.graph = HolisticaGraph(llm=app.state.llm, config=config)

    @app.get("/api/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/scenarios")
    async def list_scenarios() -> Dict[str, Any]:
        try:
            return load_scenario_library()
        except Exception as exc:  # pragma: no cover - 配置异常
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/scenarios/learning")
    async def list_learning_topics() -> Dict[str, Any]:
        return {"topics": get_learning_topics()}

    @app.get("/api/scenarios/research")
    async def list_research_templates() -> Dict[str, Any]:
        return {"templates": get_research_templates()}

    @app.post("/api/query", response_model=QueryResponse)
    async def run_query(payload: QueryRequest) -> QueryResponse:
        graph: HolisticaGraph = getattr(app.state, "graph", None)
        if graph is None:  # pragma: no cover - 理论不会出现
            raise HTTPException(status_code=503, detail="Graph not initialized")

        context = payload.context.copy() if payload.context else {}
        context.setdefault("trigger_time", datetime.now().strftime("%Y-%m-%d %H:00:00"))

        try:
            state = await graph.run_async(query=payload.query, context=context)
        except Exception as exc:  # pragma: no cover - 运行期异常
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        # 可选场景覆盖（多用于调试或灰度控制）
        if payload.scenario_override:
            state["scenario_type"] = payload.scenario_override

        metadata = jsonable_encoder(state.get("metadata", {}) or {})
        scenario_type = state.get("scenario_type", "assistant")
        plan = jsonable_encoder(state.get("plan") or {}) or None
        tickers = jsonable_encoder(state.get("tickers", []) or [])
        plan_target_id = state.get("plan_target_id")
        report = state.get("report") or ""

        segments: Dict[str, Any] = {
            "learning_workshop": metadata.get("learning_workshop"),
            "assistant_answer": metadata.get("assistant_answer"),
            "data_analysis": state.get("data_analysis"),
            "strategy": state.get("strategy"),
            "data_sufficiency": state.get("data_sufficiency"),
        }

        segments = {k: jsonable_encoder(v) for k, v in segments.items() if v}
        trace = jsonable_encoder(state.get("trace")) if payload.return_trace else None

        return QueryResponse(
            scenario_type=scenario_type,
            plan=plan,
            tickers=tickers,
            plan_target_id=plan_target_id,
            report=report,
            metadata=metadata,
            segments=segments,
            trace=trace,
        )

    return app


app = build_application()
