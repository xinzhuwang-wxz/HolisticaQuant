from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

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


def _markdown_to_readable(text: str) -> str:
    if not text:
        return ""

    lines: List[str] = []
    for raw in str(text).splitlines():
        stripped = raw.strip()
        if not stripped:
            lines.append("")
            continue
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
            lines.append(stripped)
            continue
        if stripped.startswith(("- ", "* ", "• ")):
            lines.append(f"• {stripped[2:].strip()}")
            continue
        lines.append(stripped)

    cleaned: List[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if previous_blank:
                continue
            previous_blank = True
            cleaned.append("")
        else:
            previous_blank = False
            cleaned.append(line)

    return "\n".join(cleaned).strip()


async def _execute_query(graph: HolisticaGraph, payload: QueryRequest) -> QueryResponse:
    if graph is None:
        raise RuntimeError("Graph not initialized")

    context = payload.context.copy() if payload.context else {}
    context.setdefault("trigger_time", datetime.now().strftime("%Y-%m-%d %H:00:00"))

    state = await graph.run_async(query=payload.query, context=context)

    if payload.scenario_override:
        state["scenario_type"] = payload.scenario_override

    metadata = jsonable_encoder(state.get("metadata", {}) or {})
    if isinstance(metadata, dict) and payload.context:
        template_type = payload.context.get("template_type")
        if template_type and "template_type" not in metadata:
            metadata["template_type"] = template_type
        cta_label = payload.context.get("cta_label")
        if cta_label and "cta_label" not in metadata:
            metadata["cta_label"] = cta_label

    scenario_type = state.get("scenario_type", "assistant")
    plan = jsonable_encoder(state.get("plan") or {}) or None
    tickers = jsonable_encoder(state.get("tickers", []) or [])
    plan_target_id = state.get("plan_target_id")
    report = state.get("report") or ""

    data_summary = metadata.get("data_analysis_summary") if isinstance(metadata, dict) else {}
    strategy_summary = metadata.get("strategy_summary") if isinstance(metadata, dict) else {}

    final_report_source = state.get("report") or report
    if scenario_type == "research_lab" and isinstance(strategy_summary, dict):
        final_report_source = strategy_summary.get("full_report") or final_report_source

    readable_report = _markdown_to_readable(final_report_source)
    if not readable_report:
        readable_report = _markdown_to_readable(report)

    segments: Dict[str, Any] = {}
    learning_block = metadata.get("learning_workshop") if isinstance(metadata, dict) else None
    if learning_block:
        segments["learning_workshop"] = learning_block

    assistant_answer = metadata.get("assistant_answer") if isinstance(metadata, dict) else None
    if assistant_answer:
        if isinstance(assistant_answer, dict):
            assistant_copy = assistant_answer.copy()
            for field in ("answer", "analysis", "draft"):
                if isinstance(assistant_copy.get(field), str):
                    assistant_copy[field] = _markdown_to_readable(assistant_copy[field])
            segments["assistant_answer"] = assistant_copy
        else:
            segments["assistant_answer"] = assistant_answer

    if isinstance(data_summary, dict) and data_summary:
        data_full_report = data_summary.get("full_report") or state.get("data_analysis")
        if data_full_report:
            segments["data_analysis"] = _markdown_to_readable(data_full_report)
        if data_summary.get("highlights"):
            segments["data_highlights"] = data_summary.get("highlights")
        if data_summary.get("tools"):
            segments["data_tools"] = data_summary.get("tools")
    elif state.get("data_analysis"):
        segments["data_analysis"] = _markdown_to_readable(state.get("data_analysis"))

    if isinstance(strategy_summary, dict) and strategy_summary:
        strategy_copy = strategy_summary.copy()
        if isinstance(strategy_copy.get("full_report"), str):
            strategy_copy["full_report"] = _markdown_to_readable(strategy_copy["full_report"])
        segments["strategy"] = strategy_copy

    if state.get("strategy"):
        segments["strategy_structured"] = state.get("strategy")

    if state.get("data_sufficiency"):
        segments["data_sufficiency"] = state.get("data_sufficiency")

    segments = {k: jsonable_encoder(v) for k, v in segments.items() if v}
    trace = jsonable_encoder(state.get("trace")) if payload.return_trace else None

    return QueryResponse(
        scenario_type=scenario_type,
        plan=plan,
        tickers=tickers,
        plan_target_id=plan_target_id,
        report=readable_report,
        metadata=metadata,
        segments=segments,
        trace=trace,
    )


def _extract_report_sections(report: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    current_key: Optional[str] = None
    buffer: List[str] = []

    for raw_line in report.splitlines():
        line = raw_line.strip()
        if not line and not buffer:
            continue
        if line.startswith("【") and "】" in line:
            if current_key is not None:
                sections[current_key] = "\n".join(buffer).strip()
            buffer = []
            closing_index = line.find("】")
            current_key = line[1:closing_index]
            remainder = line[closing_index + 1 :].strip()
            if remainder:
                buffer.append(remainder)
            continue
        if current_key is not None:
            buffer.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(buffer).strip()

    return sections


def _format_highlights(highlights: List[str]) -> str:
    lines = [f"• {item.strip()}" for item in highlights if isinstance(item, str) and item.strip()]
    return "\n".join(lines)


def _build_learning_timeline_events(response: QueryResponse) -> List[Dict[str, str]]:
    events: List[Dict[str, str]] = []
    metadata = response.metadata if isinstance(response.metadata, dict) else {}

    if response.scenario_type == "research_lab":
        plan = response.plan if isinstance(response.plan, dict) else {}
        plan_summary = plan.get("intent") or plan.get("summary")
        if plan_summary:
            events.append({"type": "timeline", "title": "规划完成", "content": str(plan_summary)})

        data_summary = metadata.get("data_analysis_summary") if isinstance(metadata, dict) else None
        if isinstance(data_summary, dict) and data_summary:
            # 移除"数据收集"事件的构建，流式输出时不再输出工具原始内容
            # collected = data_summary.get("tools")
            # if isinstance(collected, list) and collected:
            #     lines = []
            #     for item in collected:
            #         name = item.get("name")
            #         summary = item.get("latest_summary")
            #         if name and summary:
            #             readable = _markdown_to_readable(str(summary))
            #             max_len = 240
            #             if len(readable) > max_len:
            #                 readable = readable[: max_len - 1].rstrip() + "…"
            #             lines.append(f"• {name}：{readable}")
            #     if lines:
            #         events.append({
            #             "type": "timeline",
            #             "title": "数据收集",
            #             "content": "\n".join(lines),
            #         })
            preview = data_summary.get("analysis_preview") or data_summary.get("full_report")
            if preview:
                readable_preview = _markdown_to_readable(str(preview))
                events.append({
                    "type": "timeline",
                    "title": "数据分析",
                    "content": readable_preview,
                })

        strategy_summary = metadata.get("strategy_summary") if isinstance(metadata, dict) else None
        if isinstance(strategy_summary, dict) and strategy_summary:
            preview = strategy_summary.get("report_preview") or strategy_summary.get("full_report")
            if preview:
                readable_preview = _markdown_to_readable(str(preview))
                events.append({
                    "type": "timeline",
                    "title": "策略洞见",
                    "content": readable_preview,
                })
            recommendation = strategy_summary.get("recommendation")
            target_price = strategy_summary.get("target_price")
            confidence = strategy_summary.get("confidence")
            position_suggestion = strategy_summary.get("position_suggestion")
            time_horizon = strategy_summary.get("time_horizon")
            entry_conditions = strategy_summary.get("entry_conditions")
            exit_conditions = strategy_summary.get("exit_conditions")
            
            if recommendation or target_price or confidence:
                summary_parts = []
                # 转换recommendation为中文
                if recommendation:
                    rec_map = {"buy": "买入", "sell": "卖出", "hold": "持有", "analyze": "分析"}
                    rec_display = rec_map.get(str(recommendation).lower(), recommendation)
                    summary_parts.append(f"建议：{rec_display}")
                
                if target_price:
                    summary_parts.append(f"目标价：{target_price}")
                
                if confidence is not None:
                    try:
                        if isinstance(confidence, (int, float)):
                            summary_parts.append(f"置信度：{confidence:.0%}")
                        else:
                            summary_parts.append(f"置信度：{confidence}")
                    except Exception:
                        summary_parts.append(f"置信度：{confidence}")
                
                if position_suggestion:
                    summary_parts.append(f"仓位：{position_suggestion}")
                
                if time_horizon:
                    summary_parts.append(f"周期：{time_horizon}")
                
                # 添加入场和出场条件（如果存在）
                if entry_conditions and isinstance(entry_conditions, list) and len(entry_conditions) > 0:
                    entry_str = "；".join(entry_conditions[:2])  # 最多显示2个
                    if len(entry_conditions) > 2:
                        entry_str += f"等{len(entry_conditions)}项"
                    summary_parts.append(f"入场：{entry_str}")
                
                if exit_conditions and isinstance(exit_conditions, list) and len(exit_conditions) > 0:
                    exit_str = "；".join(exit_conditions[:2])  # 最多显示2个
                    if len(exit_conditions) > 2:
                        exit_str += f"等{len(exit_conditions)}项"
                    summary_parts.append(f"出场：{exit_str}")
                
                summary = "｜".join([part for part in summary_parts if part])
                if summary:
                    title = "策略完成"
                    try:
                        template_type = response.metadata.get("template_type") if isinstance(response.metadata, dict) else None
                        cta_label = response.metadata.get("cta_label") if isinstance(response.metadata, dict) else None
                        if cta_label:
                            title = f"{cta_label}完成"
                        elif template_type == "valuation":
                            title = "估值策略完成"
                        elif template_type == "industry":
                            title = "行业策略完成"
                        elif template_type == "risk":
                            title = "风险评估完成"
                    except Exception:
                        title = "策略完成"
                    events.append({
                        "type": "timeline",
                        "title": title,
                        "content": summary,
                    })

        return events

    # learning_workshop 场景的最终事件构建
    if response.scenario_type == "learning_workshop":
        learning_meta = metadata.get("learning_workshop") if isinstance(metadata, dict) else None
        if isinstance(learning_meta, dict):
            knowledge_point = learning_meta.get("knowledge_point")
            if knowledge_point:
                events.append({"type": "timeline", "title": "知识点", "content": str(knowledge_point)})

        plan = response.plan if isinstance(response.plan, dict) else {}
        if plan:
            plan_summary = plan.get("intent") or plan.get("summary")
            if plan_summary:
                events.append({"type": "timeline", "title": "规划完成", "content": str(plan_summary)})

        sections = _extract_report_sections(response.report or "")
        section_mapping = (
            ("学习目标", "学习目标"),
            ("微型任务步骤", "任务步骤"),
            ("验证逻辑", "验证逻辑"),
            ("AI 指导", "AI 指导"),
        )

        for key, title in section_mapping:
            content = sections.get(key)
            if content:
                events.append({"type": "timeline", "title": title, "content": content})

    # assistant 场景：不构建最终事件，因为已经实时推送了所有内容
    # 避免流式输出和最终结果混在一起
    if response.scenario_type == "assistant":
        return events

    return events


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

        try:
            return await _execute_query(graph, payload)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.websocket("/api/query/stream")
    async def stream_query(websocket: WebSocket) -> None:
        await websocket.accept()
        graph: HolisticaGraph = getattr(app.state, "graph", None)
        if graph is None:
            await websocket.send_json({"type": "error", "message": "Graph not initialized"})
            await websocket.close()
            return

        try:
            raw_message = await websocket.receive_text()
        except WebSocketDisconnect:
            return
        except Exception as exc:  # pragma: no cover - 输入异常
            await websocket.send_json({"type": "error", "message": f"无法读取请求：{exc}"})
            await websocket.close()
            return

        try:
            payload = QueryRequest.model_validate_json(raw_message)
        except ValidationError as exc:
            await websocket.send_json({"type": "error", "message": f"请求参数无效: {exc.errors()}"})
            await websocket.close()
            return

        progress_queue: asyncio.Queue | None = asyncio.Queue()
        progress_titles_streamed: Dict[str, int] = {}
        final_content_ready = asyncio.Event()  # 标记最终内容是否已准备好

        async def forward_progress() -> None:
            if progress_queue is None:
                return
            while True:
                # 如果最终内容已准备好，停止流式输出
                if final_content_ready.is_set():
                    # 清空队列中剩余的事件（因为最终内容已经准备好了）
                    while not progress_queue.empty():
                        try:
                            progress_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    break
                
                try:
                    # 使用超时等待，以便能够检查 final_content_ready 状态
                    item = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    if item is None:
                        break
                    title = str(item.get("title", ""))
                    progress_titles_streamed[title] = progress_titles_streamed.get(title, 0) + 1
                    await websocket.send_json(item)
                except asyncio.TimeoutError:
                    # 超时后继续检查 final_content_ready
                    continue

        forward_task = asyncio.create_task(forward_progress())

        try:
            context_with_queue = payload.context.copy() if payload.context else {}
            if progress_queue is not None:
                context_with_queue["_progress_queue"] = progress_queue
            payload = payload.model_copy(update={"context": context_with_queue})

            await websocket.send_json({"type": "status", "message": "已接收任务，正在调度 AI 工作流……"})
            response = await _execute_query(graph, payload)
            
            # 最终内容已准备好，立即停止流式输出
            final_content_ready.set()
        except WebSocketDisconnect:
            return
        except Exception as exc:  # pragma: no cover - 执行异常
            final_content_ready.set()  # 即使出错也要停止流式输出
            await websocket.send_json({"type": "error", "message": str(exc)})
            await websocket.close()
            return
        finally:
            # 停止流式输出
            if progress_queue is not None:
                progress_queue.put_nowait(None)
            # 等待流式输出任务完成（最多等待1秒）
            try:
                await asyncio.wait_for(forward_task, timeout=1.0)
            except asyncio.TimeoutError:
                forward_task.cancel()
                try:
                    await forward_task
                except asyncio.CancelledError:
                    pass

        try:
            for event in _build_learning_timeline_events(response):
                title = str(event.get("title", ""))
                # 如果已经实时推送过，跳过（避免重复）
                # 检查 progress_titles_streamed 中是否已经存在该标题（支持动态标题如"行业快照完成"）
                if progress_titles_streamed.get(title):
                    continue
                await websocket.send_json(event)
            await websocket.send_json({"type": "final", "payload": jsonable_encoder(response)})
        except WebSocketDisconnect:
            return
        finally:
            await websocket.close()

    return app


app = build_application()
