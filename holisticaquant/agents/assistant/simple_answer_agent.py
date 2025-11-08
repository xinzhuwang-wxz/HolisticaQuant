"""
SimpleAnswerAgent

应对“AI 智能陪伴”场景，聚焦于即时问答，输出带有数据支撑和后续建议的结构化回答。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type
from loguru import logger
from pydantic import BaseModel

from holisticaquant.agents.utils.base_agent import BaseAgent
from holisticaquant.agents.utils.agent_states import AgentState
from holisticaquant.agents.utils.schemas import AssistantAnswerSchema


class SimpleAnswerAgent(BaseAgent):
    """智能陪伴问答 Agent"""

    def __init__(self, llm, config=None):
        super().__init__(
            name="simple_answer_agent",
            llm=llm,
            tools=[],
            config=config,
        )

    def _get_state_keys_to_monitor(self):
        return ["query", "scenario_type", "plan_target_id"]

    def _get_state_input_keys(self):
        return ["query", "plan", "metadata"]

    def _get_state_output_keys(self):
        return ["report", "metadata"]

    def _get_structured_output_schema(self) -> Optional[Type[BaseModel]]:
        return AssistantAnswerSchema

    def _get_system_message(self) -> str:
        return (
            "你是AI智能陪伴导师，回答用户的问题并提供数据、逻辑与来源。"
            "必须输出AssistantAnswerSchema定义的JSON，禁止输出额外文本。"
        )

    def _get_user_input(self, state: AgentState, memory_context: str = "") -> str:
        query = state["query"]
        plan = state.get("plan", {})
        data_summary = state.get("metadata", {}).get("data_analysis_summary", {})
        strategy_summary = state.get("metadata", {}).get("strategy_summary", {})

        payload = {
            "query": query,
            "plan": plan,
            "data_analysis_summary": data_summary,
            "strategy_summary": strategy_summary,
        }

        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)

        return (
            f"请基于以下上下文回答用户问题，输出AssistantAnswerSchema格式的JSON：\n"
            f"{payload_text}\n\n"
            "要求：\n"
            "1. answer 需直接回应用户问题。\n"
            "2. supporting_points 至少列出两条带有数据或逻辑说明的要点。\n"
            "3. recommended_next_actions 给出可执行建议。\n"
            "4. data_sources 列出引用的数据来源，如“新浪财经 2025-04-01 行情”。\n"
            "如缺乏真实数据，请明确说明并提供合理的替代建议。"
        )

    def _get_continue_prompt(self) -> str:
        return "请继续输出AssistantAnswerSchema格式的JSON。"

    def _validate_state(self, state: AgentState):
        if state.get("scenario_type") != "assistant":
            raise ValueError("simple_answer_agent: 仅在 assistant 场景下调用。")

    def _process_result(
        self,
        state: AgentState,
        structured_data: Optional[BaseModel],
        text_content: Optional[str],
        tool_results: Dict[str, str],
    ) -> Dict[str, Any]:
        if structured_data is None:
            raise ValueError("simple_answer_agent: 未获得结构化输出。")

        if not isinstance(structured_data, AssistantAnswerSchema):
            raise ValueError("simple_answer_agent: 结构化输出类型错误。")

        data = structured_data.model_dump()
        if self.debug:
            logger.debug("simple_answer_agent: 结构化输出 %s", data)

        report_lines = [
            "# AI 智能陪伴回答",
            f"## 场景\n{data['scenario_context']}",
            "## 回答",
            data["answer"],
            "\n## 支撑要点",
        ]
        for point in data.get("supporting_points", []):
            report_lines.append(f"- {point}")

        if data.get("recommended_next_actions"):
            report_lines.append("\n## 推荐的下一步行动")
            for action in data["recommended_next_actions"]:
                report_lines.append(f"- {action}")

        if data.get("data_sources"):
            report_lines.append("\n## 数据来源")
            for source in data["data_sources"]:
                report_lines.append(f"- {source}")

        report = "\n".join(report_lines).strip()

        metadata = state.setdefault("metadata", {})
        metadata["assistant_answer"] = data

        output_summary = f"assistant 回答: {data['answer'][:60]}..."

        return {
            "report": report,
            "metadata": metadata,
            "output_summary": output_summary,
        }


def create_simple_answer_agent(llm, config=None):
    agent = SimpleAnswerAgent(llm, config)
    return agent.create_node()

