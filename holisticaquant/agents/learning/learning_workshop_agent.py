"""
LearningWorkshopAgent

负责处理“场景化学习工坊”场景：根据预定义的知识点与场景配置，
将任务拆解为可执行步骤，并生成带有数据点与验证逻辑的指导说明。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type
from loguru import logger
from pydantic import BaseModel

from holisticaquant.agents.utils.base_agent import BaseAgent
from holisticaquant.agents.utils.agent_states import AgentState
from holisticaquant.agents.utils.schemas import LearningWorkshopSchema
from holisticaquant.memory.scenario_repository import get_learning_topic_by_id, get_learning_topics


class LearningWorkshopAgent(BaseAgent):
    """场景化学习工坊 Agent"""

    def __init__(self, llm, config=None):
        super().__init__(
            name="learning_workshop_agent",
            llm=llm,
            tools=[],
            config=config,
        )

    def _get_state_keys_to_monitor(self):
        return ["query", "plan_target_id", "scenario_type"]

    def _get_state_input_keys(self):
        return ["query", "plan", "plan_target_id"]

    def _get_state_output_keys(self):
        return ["report", "metadata"]

    def _get_structured_output_schema(self) -> Optional[Type[BaseModel]]:
        return LearningWorkshopSchema

    def _get_system_message(self) -> str:
        return (
            "你是场景化学习教练，根据提供的知识点配置与用户需求，输出结构化学习指导。\n"
            "必须使用LearningWorkshopSchema定义的JSON格式返回，禁止输出多余文本。"
        )

    def _get_user_input(self, state: AgentState, memory_context: str = "") -> str:
        query = state["query"]
        target_id = state.get("plan_target_id")
        plan = state.get("plan", {})
        topic = None

        if target_id:
            topic = get_learning_topic_by_id(target_id)

        if topic is None:
            # 回退到第一个可用主题
            topics = get_learning_topics()
            if not topics:
                raise ValueError("learning_workshop_agent: 未找到可用的学习场景配置。")
            topic = topics[0]
            if self.debug:
                logger.warning(
                    "learning_workshop_agent: 未找到plan_target_id匹配的主题，回退到默认主题 %s",
                    topic.get("id"),
                )

        topic_json = json.dumps(topic, ensure_ascii=False, indent=2)
        plan_json = json.dumps(plan, ensure_ascii=False, indent=2) if plan else "{}"

        return (
            f"用户查询：{query}\n\n"
            f"规划信息：{plan_json}\n\n"
            "请基于以下学习场景配置生成LearningWorkshopSchema格式的JSON：\n"
            f"{topic_json}\n\n"
            "要求：\n"
            "1. learning_objectives、task_steps 等列表至少包含2项。\n"
            "2. calculator_inputs 需结合配置提供的数值，描述清晰。\n"
            "3. validation_logic 要引用原始数据来源或参考数据。\n"
            "4. ai_guidance 给出下一步学习建议。\n"
            "输出时请仅返回JSON，不要额外说明。"
        )

    def _get_continue_prompt(self) -> str:
        return "请继续生成LearningWorkshopSchema格式的JSON。"

    def _validate_state(self, state: AgentState):
        if state.get("scenario_type") != "learning_workshop":
            raise ValueError("learning_workshop_agent: 仅在 learning_workshop 场景下调用。")

    def _process_result(
        self,
        state: AgentState,
        structured_data: Optional[BaseModel],
        text_content: Optional[str],
        tool_results: Dict[str, str],
    ) -> Dict[str, Any]:
        if structured_data is None:
            raise ValueError("learning_workshop_agent: 未获得结构化输出。")

        if not isinstance(structured_data, LearningWorkshopSchema):
            raise ValueError("learning_workshop_agent: 结构化输出类型错误。")

        data = structured_data.model_dump()
        if self.debug:
            logger.debug("learning_workshop_agent: 结构化输出 %s", data)

        def _as_bullets(items: list[str]) -> str:
            return "\n".join(f"• {item}" for item in items) if items else "（暂无）"

        report_sections = [
            f"【知识点】\n{data['knowledge_point']}",
            f"【学习目标】\n{_as_bullets(data.get('learning_objectives', []))}",
            f"【场景概要】\n{data['scenario_summary']}",
            f"【关键数据】\n{_as_bullets(data.get('key_data_points', []))}",
            f"【微型任务步骤】\n{_as_bullets(data.get('task_steps', []))}",
            f"【计算器输入】\n{_as_bullets(data.get('calculator_inputs', []))}",
            f"【预期结果】\n{data['expected_result']}",
            f"【验证逻辑】\n{data['validation_logic']}",
            f"【AI 指导】\n{data['ai_guidance']}",
        ]

        report = "\n\n".join(section.strip() for section in report_sections if section).strip()

        metadata = state.setdefault("metadata", {})
        metadata["learning_workshop"] = {
            "scenario_id": data["scenario_id"],
            "knowledge_point": data["knowledge_point"],
            "learning_objectives": data.get("learning_objectives", []),
        }

        # 实时推送学习工坊事件
        progress_queue = None
        try:
            progress_queue = state.get("context", {}).get("_progress_queue")
        except Exception:
            progress_queue = None

        if progress_queue:
            try:
                # 推送"知识点"事件
                knowledge_point = data.get("knowledge_point", "")
                if knowledge_point:
                    progress_queue.put_nowait({
                        "type": "timeline",
                        "title": "知识点",
                        "content": knowledge_point,
                    })

                # 推送"学习目标"事件
                learning_objectives = data.get("learning_objectives", [])
                if learning_objectives:
                    progress_queue.put_nowait({
                        "type": "timeline",
                        "title": "学习目标",
                        "content": _as_bullets(learning_objectives),
                    })

                # 推送"任务步骤"事件
                task_steps = data.get("task_steps", [])
                if task_steps:
                    progress_queue.put_nowait({
                        "type": "timeline",
                        "title": "任务步骤",
                        "content": _as_bullets(task_steps),
                    })

                # 推送"验证逻辑"事件
                validation_logic = data.get("validation_logic", "")
                if validation_logic:
                    progress_queue.put_nowait({
                        "type": "timeline",
                        "title": "验证逻辑",
                        "content": validation_logic,
                    })

                # 推送"AI 指导"事件
                ai_guidance = data.get("ai_guidance", "")
                if ai_guidance:
                    progress_queue.put_nowait({
                        "type": "timeline",
                        "title": "AI 指导",
                        "content": ai_guidance,
                    })
            except Exception as exc:
                if self.debug:
                    logger.warning(f"learning_workshop_agent: 推送进度事件失败: {exc}")

        output_summary = f"学习场景: {data['scenario_id']} - {data['knowledge_point']}"

        return {
            "report": report,
            "metadata": metadata,
            "output_summary": output_summary,
        }


def create_learning_workshop_agent(llm, config=None):
    agent = LearningWorkshopAgent(llm, config)
    return agent.create_node()

