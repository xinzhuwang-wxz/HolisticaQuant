"""
Data Analyst Agent - 数据分析师

职责：
1. 根据计划收集数据（使用工具）
2. 分析收集的数据（宏观+微观）
3. 生成详细的数据分析报告（有数据支撑）
"""

import asyncio
from typing import Dict, Any, Optional, Type, List
import json
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from holisticaquant.agents.utils.base_agent import BaseAgent
from holisticaquant.agents.utils.agent_states import AgentState
from holisticaquant.agents.utils.schemas import DataSufficiencySchema
from holisticaquant.agents.utils.tool_fallback import get_failing_tools, get_tool_suggestion_message
from holisticaquant.agents.utils.agent_tools import (
    get_stock_fundamental,      # 主动工具：需要股票代码
    get_stock_market_data,      # 主动工具：需要股票代码
    get_market_data,            # 被动工具：市场数据（指数、板块资金流）- 用于市场背景分析
    get_sina_news,              # 被动工具：新浪财经新闻 - 用于获取相关新闻（简化：移除thx_news）
    calculator,                 # 通用工具：数学计算
)


class DataAnalyst(BaseAgent):
    """数据分析师Agent"""
    
    def __init__(self, llm, config=None):
        # data_analyst负责收集数据，包括主动工具（需要股票代码）和被动工具（市场背景数据）
        # 简化：只保留一个新闻源（sina），移除thx以降低失败率
        tools = [
            get_stock_fundamental,   # 主动工具：股票基本面数据（需要ticker）
            get_stock_market_data,   # 主动工具：股票市场数据（需要ticker）
            get_market_data,         # 被动工具：市场数据（指数、板块资金流）- 用于市场背景分析
            get_sina_news,           # 被动工具：新浪财经新闻 - 用于获取相关新闻（简化：移除thx_news）
            calculator,              # 通用工具：数学计算
        ]
        
        super().__init__(
            name="data_analyst",
            llm=llm,
            tools=tools,
            config=config
        )
    
    def _get_state_keys_to_monitor(self) -> list[str]:
        return [
            "plan",
            "collected_data",
            "data_analysis",
            "data_sufficiency",
            "collection_iteration",
            "metadata",
        ]

    def _get_state_input_keys(self) -> list[str]:
        return ["query", "plan", "collected_data", "collection_iteration", "data_sufficiency"]

    def _get_state_output_keys(self) -> list[str]:
        return ["collected_data", "data_analysis", "data_sufficiency", "collection_iteration"]
    
    def _get_structured_output_schema(self) -> Optional[Type[BaseModel]]:
        """返回结构化输出Schema"""
        return DataSufficiencySchema
    
    def _needs_text_report(self) -> bool:
        """需要生成文本报告"""
        return True
    
    def _get_system_message(self) -> str:
        """获取系统提示词"""
        return (
            "你是金融数据分析师。根据计划收集数据并生成分析报告。\n\n"
            "可用工具（仅限以下5个）：\n"
            "1. get_stock_fundamental(ticker) - 主动工具，需ticker\n"
            "2. get_stock_market_data(ticker) - 主动工具，需ticker\n"
            "3. get_market_data() - 被动工具，市场数据\n"
            "4. get_sina_news() - 被动工具，新闻\n"
            "5. calculator(expression) - 计算工具\n\n"
            "**严格禁止**：\n"
            "- **禁止调用web_search**：此agent没有web_search工具，不要尝试调用。如果尝试调用会报错。\n"
            "- **禁止调用任何未列出的工具**：只使用上述5个工具。\n\n"
            "策略：有tickers→优先主动工具；无tickers→使用被动工具。\n\n"
            "报告：宏观分析、微观分析、数据支撑结论。输出数据充分性评估JSON。"
        )
    
    def _get_user_input(self, state: AgentState, memory_context: str = "") -> str:
        """获取用户输入"""
        plan = state["plan"]
        query = state["query"]
        if "collection_iteration" not in state:
            collection_iteration = 0
        else:
            collection_iteration = state["collection_iteration"]
        
        if "collected_data" not in state:
            existing_data = {}
        else:
            existing_data = state["collected_data"]
        
        import json
        iteration_info = ""
        if collection_iteration > 0:
            iteration_info = f"\n\n这是第 {collection_iteration + 1} 次数据收集迭代。"
            if existing_data:
                iteration_info += f"\n已收集的数据源：{list(existing_data.keys())}"
        
        # 检查失败的工具并生成降级建议
        tool_suggestion_msg = ""
        if collection_iteration > 0 and state.get("metadata", {}).get("tool_stats"):
            failing_tools = get_failing_tools(state, failure_threshold=2)
            if failing_tools:
                tool_suggestion_msg = get_tool_suggestion_message(failing_tools)
                if self.debug:
                    logger.info(f"data_analyst: 检测到失败工具: {failing_tools}")
        
        return f"""计划：{json.dumps(plan, ensure_ascii=False, indent=2)}{iteration_info}{tool_suggestion_msg}

执行：1)根据plan收集数据 2)分析（宏观+微观）3)生成报告（数据概览、宏观分析、微观分析、结论、关键发现）4)评估数据充分性（输出JSON）。

**重要**：此agent没有web_search工具，不要尝试调用web_search。只使用以下工具：get_stock_fundamental, get_stock_market_data, get_market_data, get_sina_news, calculator。
"""
    
    def _get_continue_prompt(self) -> str:
        """获取继续处理的提示词"""
        return (
            "请基于收集的数据继续分析或生成详细的分析报告（宏观+微观+数据支撑）。"
        )
    
    def _validate_state(self, state: AgentState):
        """验证状态"""
        if "plan" not in state:
            raise ValueError("data_analyst: state必须包含plan字段")
        
        plan = state["plan"]
        if not plan:
            raise ValueError("data_analyst: plan为空")
    
    def _process_result(
        self, 
        state: AgentState, 
        structured_data: Optional[BaseModel],
        text_content: Optional[str],
        tool_results: Dict[str, str]
    ) -> Dict[str, Any]:
        """处理结果"""
        # 如果structured_data为None，创建占位值
        if structured_data is None:
            logger.warning("data_analyst: 结构化数据为None，使用占位值")
            structured_data = DataSufficiencySchema(
                sufficient=False,
                missing_data=["结构化输出失败"],
                confidence=0.0,
                reason="结构化输出失败，无法评估数据充分性。可能原因：token限制或LLM响应格式错误。"
            )
        
        # 使用structured output获取结构化数据
        if not isinstance(structured_data, DataSufficiencySchema):
            error_msg = f"data_analyst: 结构化数据类型错误，期望DataSufficiencySchema，实际: {type(structured_data)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 转换为字典
        data_sufficiency = structured_data.model_dump()
        
        # 提取文本报告（如果为空，直接报错，不使用默认值）
        if text_content is None or not text_content.strip():
            error_msg = (
                f"data_analyst: 文本报告为空！\n"
                f"  - text_content: {text_content}\n"
                f"  - 工具调用结果数量: {len(tool_results) if tool_results else 0}\n"
                f"  - 工具调用结果: {list(tool_results.keys()) if tool_results else []}\n"
                f"  - 结构化数据: {structured_data}\n"
            )
            logger.error(error_msg)
            raise ValueError("data_analyst: 文本报告生成失败，LLM返回空内容。请检查工具调用结果和LLM配置。")
        
        analysis_report = text_content.strip()
        
        if self.debug:
            logger.debug(f"data_analyst: 文本报告长度: {len(analysis_report)}")
            logger.debug(f"data_analyst: 文本报告前200字符: {analysis_report[:200]}")
        
        # 整理工具摘要 -> collected_data（结构化）
        metadata = state.setdefault("metadata", {})
        tool_outputs_by_agent = (
            metadata.get("tool_outputs", {}).get(self.name, {}) if metadata else {}
        )
        collected_data_struct: Dict[str, List[Dict[str, Any]]] = {}
        tool_summary_lines: List[str] = []
        for tool_name, entries in tool_outputs_by_agent.items():
            sanitized_entries = []
            for entry in entries:
                sanitized_entries.append({
                    "timestamp": entry.get("timestamp"),
                    "arguments": entry.get("arguments"),
                    "summary": entry.get("summary"),
                })
            if sanitized_entries:
                collected_data_struct[tool_name] = sanitized_entries
                latest_summary = sanitized_entries[-1].get("summary", "")
                if latest_summary:
                    tool_summary_lines.append(f"- **{tool_name}**：{latest_summary}")
        # 如本轮执行工具但未能写入metadata（极少数异常），退回本次结果
        if not collected_data_struct and tool_results:
            for tool_name, result in tool_results.items():
                collected_data_struct[tool_name] = [{
                    "timestamp": datetime.now().isoformat(),
                    "arguments": {},
                    "summary": result,
                }]
                tool_summary_lines.append(f"- **{tool_name}**：{result}")

        # 若存在进度队列，推送实时事件
        progress_queue = None
        try:
            progress_queue = state.get("context", {}).get("_progress_queue")
        except Exception:
            progress_queue = None

        if tool_summary_lines and progress_queue:
            try:
                summary_plain = []
                for line in tool_summary_lines:
                    plain = line.replace("- **", "• ").replace("**：", "：").replace("**", "")
                    summary_plain.append(plain)
                progress_queue.put_nowait(
                    {
                        "type": "timeline",
                        "title": "数据收集",
                        "content": "\n".join(summary_plain),
                    }
                )
            except Exception as exc:
                if self.debug:
                    logger.warning(f"data_analyst: 推送数据收集进度失败: {exc}")

        # 将工具摘要附加到分析报告（避免重复添加）
        if tool_summary_lines and "### 数据收集概览" not in analysis_report:
            tool_section = "\n\n### 数据收集概览\n" + "\n".join(tool_summary_lines)
            analysis_report = analysis_report.rstrip() + tool_section

        # 生成供前端消费的汇总信息
        highlight_candidates = []
        for raw_line in analysis_report.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith(("###", "##")):
                highlight_candidates.append(stripped.lstrip("#").strip())
            elif stripped.startswith(("*", "-", "•")):
                highlight_candidates.append(stripped.lstrip("*-• ").strip())
            if len(highlight_candidates) >= 6:
                break

        metadata["data_analysis_summary"] = {
            "updated_at": datetime.now().isoformat(),
            "tools": [
                {
                    "name": tool_name,
                    "latest_summary": entries[-1].get("summary") if entries else "",
                    "call_count": len(entries),
                }
                for tool_name, entries in collected_data_struct.items()
            ],
            "analysis_preview": analysis_report[:400],
            "highlights": highlight_candidates,
            "full_report": analysis_report,
        }

        if progress_queue:
            try:
                analysis_excerpt = analysis_report.strip()
                if analysis_excerpt:
                    analysis_excerpt = analysis_excerpt.replace("###", "").replace("**", "")
                    max_len = 420
                    if len(analysis_excerpt) > max_len:
                        analysis_excerpt = analysis_excerpt[: max_len - 1].rstrip() + "…"
                    progress_queue.put_nowait(
                        {
                            "type": "timeline",
                            "title": "数据分析",
                            "content": analysis_excerpt,
                        }
                    )
            except Exception as exc:
                if self.debug:
                    logger.warning(f"data_analyst: 推送数据分析进度失败: {exc}")
        
        # 更新迭代次数
        if "collection_iteration" not in state:
            raise ValueError("state必须包含collection_iteration字段")
        if "max_collection_iterations" not in state:
            raise ValueError("state必须包含max_collection_iterations字段")
        
        collection_iteration = state["collection_iteration"] + 1
        max_iterations = state["max_collection_iterations"]
        
        # 如果已达最大迭代次数，强制认为数据充足
        if collection_iteration >= max_iterations:
            data_sufficiency["sufficient"] = True
            data_sufficiency["reason"] = f"已达最大迭代次数（{max_iterations}），停止收集"
            if self.debug:
                logger.info(f"data_analyst: 已达最大迭代次数，停止收集")
        
        # 输出摘要
        output_summary = (
            f"收集了{len(tool_results)}个数据源，迭代{collection_iteration}次，"
            f"数据充足: {data_sufficiency['sufficient']}"
        )
        
        if self.debug:
            logger.info(f"data_analyst: 数据收集完成 - {len(tool_results)}个数据源，迭代{collection_iteration}次")
            logger.info(f"data_analyst: 数据充分性 - {data_sufficiency['sufficient']}, 置信度: {data_sufficiency['confidence']}")
        
        return {
            "collected_data": collected_data_struct,
            "data_analysis": analysis_report,
            "data_sufficiency": data_sufficiency,
            "collection_iteration": collection_iteration,
            "output_summary": output_summary,
        }
    

def create_data_analyst(llm, config=None):
    """
    创建数据分析师Agent
    
    Args:
        llm: LangChain LLM实例
        config: 配置字典（可选）
    
    Returns:
        LangGraph节点函数
    """
    agent = DataAnalyst(llm, config)
    return agent.create_node()
