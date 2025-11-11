"""
Strategy Analyst Agent - 策略分析师

职责：
1. 基于前面的报告（plan、data_analysis）生成最终投资报告
2. 分析整体市场趋势，生成超额回报策略
3. 管理与市场走势相关的风险
4. 提供投资建议与风险管理
"""

from typing import Dict, Any, Optional, Type
import json
import re
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from holisticaquant.agents.utils.base_agent import BaseAgent
from holisticaquant.agents.utils.agent_states import AgentState
from holisticaquant.agents.utils.schemas import StrategySchema
from holisticaquant.agents.utils.agent_tools import web_search
# strategy_analyst可以使用web_search工具获取最新市场信息，补充策略分析


class StrategyAnalyst(BaseAgent):
    """策略分析师Agent"""
    
    def __init__(self, llm, config=None, reasoning_engine=None):
        """
        初始化策略分析师
        
        Args:
            llm: LangChain LLM实例
            config: 配置字典（可选）
            reasoning_engine: 金融推理引擎（可选，用于Agentic RAG）
        """
        # strategy_analyst可以使用web_search工具获取最新市场信息，补充策略分析
        # 主要基于data_analysis报告生成策略，web_search用于获取最新市场动态或行业趋势
        tools = [web_search]
        
        super().__init__(
            name="strategy_analyst",
            llm=llm,
            tools=tools,
            config=config
        )
    
        self.reasoning_engine = reasoning_engine
        self.rag_enabled = config and config.get("agentic_rag", {}).get("enabled", False) if config else False
        
        # 记录Agentic RAG状态（INFO级别，确保可见）
        if self.rag_enabled:
            if self.reasoning_engine:
                logger.info(f"strategy_analyst: Agentic RAG已启用，推理引擎已初始化")
            else:
                logger.warning(f"strategy_analyst: Agentic RAG配置已启用，但推理引擎未初始化！")
        else:
            logger.info(f"strategy_analyst: Agentic RAG未启用")
    
    def _get_state_keys_to_monitor(self) -> list[str]:
        return ["plan", "data_analysis", "strategy", "report"]

    def _get_state_input_keys(self) -> list[str]:
        return ["query", "plan", "data_analysis", "strategy"]

    def _get_state_output_keys(self) -> list[str]:
        return ["strategy", "report"]
    
    def _get_structured_output_schema(self) -> Optional[Type[BaseModel]]:
        """返回结构化输出Schema"""
        return StrategySchema
    
    def _needs_text_report(self) -> bool:
        """需要生成文本报告"""
        return True
    
    def _get_system_message(self) -> str:
        """获取系统提示词"""
        return (
            "你是投资策略分析师。基于data_analysis报告生成投资策略报告。\n\n"
            "**可用工具（仅限以下1个）**：\n"
            "1. web_search - 网络搜索工具，用于补充最新市场动态或行业趋势\n\n"
            "**严格禁止**：\n"
            "- **禁止调用任何被动数据收集工具**：如get_stock_fundamental、get_stock_market_data、get_market_data、get_sina_news等。这些工具是data_analyst使用的，你不需要调用。只能调用web_search工具。\n"
            "- **禁止调用任何未列出的工具**：只使用web_search工具。如果尝试调用其他工具会报错。\n\n"
            "**报告长度要求**：\n"
            "- 策略报告总长度控制在1000-1500字以内\n"
            "- 宏观市场分析：250-350字\n"
            "- 微观个股分析：300-400字\n"
            "- 风险分析：200-300字\n"
            "- 投资建议：100-150字（JSON格式）\n"
            "- 执行建议：150-200字\n\n"
            "**报告结构（5部分）**：\n"
            "1. 宏观市场分析（市场走势、情绪、宏观环境）\n"
            "2. 微观个股分析（基本面、技术面、公司财务状况）\n"
            "3. 风险分析（市场风险、个股风险、风险控制措施）\n"
            "4. 投资建议（JSON格式：recommendation、confidence、target_price等）\n"
            "5. 执行建议（策略要点、监控指标、跟踪建议）\n\n"
            "**要求**：\n"
            "- 主要基于data_analysis报告生成策略，不要尝试重新收集数据\n"
            "- 如需补充最新市场动态，可使用web_search工具\n"
            "- 引用data_analysis中的具体数据\n"
            "- 报告末尾输出JSON格式投资建议"
        )
    
    def _get_user_input(self, state: AgentState, memory_context: str = "") -> str:
        """获取用户输入"""
        plan = state["plan"]
        data_analysis = state["data_analysis"]
        query = state["query"]
        metadata = state.get("metadata", {})
        data_analysis_summary = metadata.get("data_analysis_summary", {})
        tool_summaries = data_analysis_summary.get("tools", []) if data_analysis_summary else []
        tool_summary_text = ""
        if tool_summaries:
            tool_lines = []
            for item in tool_summaries[:5]:
                name = item.get("name")
                latest = item.get("latest_summary")
                if name and latest:
                    tool_lines.append(f"- {name}：{latest}")
            if tool_lines:
                tool_summary_text = "\n\n数据收集摘要：\n" + "\n".join(tool_lines)
        
        # 检索相关历史洞见（如果启用Agentic RAG）
        insights_context = ""
        if self.rag_enabled and self.reasoning_engine:
            logger.info("策略分析：开始检索相关历史洞见...")
            try:
                relevant_insights = self.reasoning_engine.search_relevant_insights(query, plan, top_k=5)
                insights_context = self.reasoning_engine.format_insights_context(relevant_insights)
                
                # 打印使用的历史洞见详细信息（INFO级别）
                if relevant_insights:
                    logger.info(f"策略分析：检索到 {len(relevant_insights)} 个相关历史洞见")
                    for i, insight in enumerate(relevant_insights[:3], 1):  # 只显示前3个
                        logger.info(f"  历史洞见{i}: [{insight.insight_type}] {insight.content[:100]}...")
                    if len(relevant_insights) > 3:
                        logger.info(f"  ...还有 {len(relevant_insights) - 3} 个历史洞见")
                else:
                    logger.info("策略分析：未检索到相关历史洞见（首次运行或查询不匹配）")
            except Exception as e:
                logger.error(f"策略分析：检索历史洞见失败: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        elif self.rag_enabled and not self.reasoning_engine:
            logger.warning("策略分析：Agentic RAG已启用，但推理引擎未初始化，跳过洞见检索")
        
        base_input = f"""请基于以下信息生成最终的投资策略报告。

用户查询：
{query}

数据收集计划：
{json.dumps(plan, ensure_ascii=False, indent=2)}

数据分析报告：
{data_analysis}"""

        if tool_summary_text:
            base_input += tool_summary_text
        
        # 如果有历史洞见，添加到上下文中
        if insights_context:
            base_input += f"\n\n{insights_context}\n"
            base_input += "\n**注意**：上述历史洞见仅供参考，请结合当前数据分析报告做出判断。\n"
        
        base_input += """
生成投资策略报告（5部分）：

1. 宏观市场分析：基于data_analysis分析市场走势、情绪、宏观环境（引用具体数据）
2. 微观个股分析：基于data_analysis分析基本面、技术面、公司财务状况（引用具体数据）
3. 风险分析：市场风险、个股风险、风险控制措施（止损、仓位、监控）
4. 投资建议：JSON格式 {recommendation, confidence, target_price, position_suggestion, time_horizon, rationale, entry_conditions, exit_conditions}
5. 执行建议：策略要点、监控指标、跟踪建议

**重要**：
- 此agent只使用web_search工具，不要尝试调用其他工具（如get_stock_fundamental、get_stock_market_data等）
- 如需补充最新市场动态，可使用web_search工具（可选）
- 主要基于data_analysis报告生成策略，不要尝试重新收集数据

报告末尾单独输出JSON格式投资建议。
"""
        
        return base_input
    
    def _get_continue_prompt(self) -> str:
        """获取继续处理的提示词"""
        return "请基于前面的数据分析报告生成最终的投资策略报告。"
    
    def _validate_state(self, state: AgentState):
        """验证状态"""
        if "plan" not in state:
            raise ValueError("strategy_analyst: state必须包含plan字段")
        if "data_analysis" not in state:
            raise ValueError("strategy_analyst: state必须包含data_analysis字段")
        
        plan = state["plan"]
        data_analysis = state["data_analysis"]
        
        if not plan:
            raise ValueError("strategy_analyst: plan为空")
        if not data_analysis:
            raise ValueError("strategy_analyst: data_analysis为空")
    
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
            logger.warning("strategy_analyst: 结构化数据为None，使用占位值")
            structured_data = StrategySchema(
                recommendation="analyze",
                confidence=0.0,
                target_price=None,
                position_suggestion=None,
                time_horizon="中期",
                rationale="结构化输出失败，无法生成投资建议。可能原因：token限制或LLM响应格式错误。",
                entry_conditions=["等待进一步分析"],
                exit_conditions=["等待进一步分析"]
            )
        
        # 使用structured output获取结构化数据
        if not isinstance(structured_data, StrategySchema):
            error_msg = f"strategy_analyst: 结构化数据类型错误，期望StrategySchema，实际: {type(structured_data)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 转换为字典
        strategy_recommendation = structured_data.model_dump()
        
        # 提取文本报告（如果为空，尝试使用结构化数据或工具结果摘要）
        if text_content is None or not text_content.strip():
            # 如果工具调用成功，使用工具结果摘要生成临时报告
            if tool_results:
                tool_summaries = []
                for tool_name, tool_result in tool_results.items():
                    summary_length = min(300, len(tool_result))
                    summary = tool_result[:summary_length]
                    if len(tool_result) > summary_length:
                        summary += f"\n...（已截断，完整结果共 {len(tool_result)} 字符）"
                    tool_summaries.append(f"**{tool_name}**:\n{summary}")
                strategy_report = "## 策略分析概览\n\n" + "\n\n".join(tool_summaries)
                # 如果有结构化数据，添加投资建议
                if structured_data:
                    strategy_dict = structured_data.model_dump()
                    if strategy_dict.get("recommendation"):
                        strategy_report += f"\n\n## 投资建议\n\n建议: {strategy_dict.get('recommendation')}"
                        if strategy_dict.get("confidence") is not None:
                            strategy_report += f"\n置信度: {strategy_dict.get('confidence'):.0%}"
                warning_msg = (
                    f"strategy_analyst: 文本报告为空，但工具调用已成功，使用工具结果摘要作为临时报告\n"
                    f"  - 工具调用结果数量: {len(tool_results)}\n"
                    f"  - 工具调用结果: {list(tool_results.keys())}\n"
                )
                logger.warning(warning_msg)
            elif structured_data:
                # 如果有结构化数据但无文本报告，基于结构化数据生成报告
                strategy_dict = structured_data.model_dump()
                strategy_report = f"## 投资建议\n\n建议: {strategy_dict.get('recommendation', 'analyze')}"
                if strategy_dict.get("confidence") is not None:
                    strategy_report += f"\n置信度: {strategy_dict.get('confidence'):.0%}"
                if strategy_dict.get("target_price"):
                    strategy_report += f"\n目标价: {strategy_dict.get('target_price')}"
                logger.warning("strategy_analyst: 文本报告为空，但结构化数据可用，基于结构化数据生成报告")
            else:
                # 如果都没有，记录警告但不抛出异常
                warning_msg = (
                    f"strategy_analyst: 文本报告为空且无工具调用结果或结构化数据\n"
                    f"  - text_content: {text_content}\n"
                    f"  - plan: {state.get('plan', {})}\n"
                    f"  - data_analysis: {state.get('data_analysis', 'N/A')[:200] if state.get('data_analysis') else 'N/A'}\n"
                )
                logger.warning(warning_msg)
                # 生成最小化占位内容
                strategy_report = "策略分析完成，但未能生成详细策略报告。"
        else:
            strategy_report = text_content.strip()
        metadata = state.setdefault("metadata", {})
        tool_outputs_by_agent = (
            metadata.get("tool_outputs", {}).get(self.name, {}) if metadata else {}
        )
        # 移除"市场补充信息"部分，不再将web_search的原始结果添加到报告中
        # tool_insight_lines 保留用于metadata中的tools字段，但不添加到报告正文
        
        if self.debug:
            logger.debug(f"strategy_analyst: 文本报告长度: {len(strategy_report)}")
            logger.debug(f"strategy_analyst: 文本报告前200字符: {strategy_report[:200]}")
        
        # 生成最终报告
        query = state["query"]
        plan = state["plan"]
        data_analysis = state["data_analysis"]
        final_report = _generate_final_report(
            query=query,
            state=state,
            plan=plan,
            data_analysis=data_analysis,
            strategy_report=strategy_report,
            strategy_recommendation=strategy_recommendation,
        )
        
        # 保存新洞见（如果启用Agentic RAG）
        if self.rag_enabled and self.reasoning_engine:
            logger.info("策略分析：开始保存新洞见...")
            try:
                result = self.reasoning_engine.reason_with_strategy_agent(
                    query=query,
                    plan=plan,
                    data_analysis=data_analysis,
                    strategy=strategy_recommendation,
                    report=strategy_report
                )
                # 打印洞见统计信息（INFO级别，确保可见）
                logger.info(f"Agentic RAG: 洞见保存完成")
                if result.get("extracted_insights"):
                    logger.info(f"Agentic RAG: 本次策略生成已保存 {len(result['extracted_insights'])} 个新洞见")
                    # 打印每个洞见的详细信息
                    for i, insight_dict in enumerate(result['extracted_insights'], 1):
                        logger.info(f"  新洞见{i}: [{insight_dict.get('insight_type', 'unknown')}] {insight_dict.get('content', '')[:150]}...")
                        if insight_dict.get('metadata', {}).get('tickers'):
                            logger.info(f"    相关股票: {insight_dict['metadata']['tickers']}")
                        if insight_dict.get('metadata', {}).get('confidence'):
                            logger.info(f"    置信度: {insight_dict['metadata']['confidence']:.2f}")
                else:
                    logger.info(f"Agentic RAG: 本次策略生成未提取到新洞见")
                if result.get("insight_count") is not None:
                    logger.info(f"Agentic RAG: 当前总洞见数: {result['insight_count']}")
            except Exception as e:
                logger.error(f"Agentic RAG: 保存洞见失败: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        elif self.rag_enabled and not self.reasoning_engine:
            logger.warning("策略分析：Agentic RAG已启用，但推理引擎未初始化，跳过洞见保存")
        
        # 输出摘要
        output_summary = (
            f"建议: {strategy_recommendation['recommendation']}, "
            f"置信度: {strategy_recommendation['confidence']}"
        )
        
        if self.debug:
            logger.info(f"strategy_analyst: 策略生成完成 - {output_summary}")
        
        strategy_highlights: list[str] = []
        for raw_line in strategy_report.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith(("###", "##")):
                strategy_highlights.append(stripped.lstrip("#").strip())
            elif stripped.startswith(("*", "-", "•")):
                strategy_highlights.append(stripped.lstrip("*-• ").strip())
            elif stripped.startswith(("建议", "结论", "风险")):
                strategy_highlights.append(stripped)
            if len(strategy_highlights) >= 6:
                break

        metadata["strategy_summary"] = {
            "updated_at": datetime.now().isoformat(),
            "recommendation": strategy_recommendation.get("recommendation"),
            "confidence": strategy_recommendation.get("confidence"),
            "target_price": strategy_recommendation.get("target_price"),
            "position_suggestion": strategy_recommendation.get("position_suggestion"),
            "time_horizon": strategy_recommendation.get("time_horizon"),
            "entry_conditions": strategy_recommendation.get("entry_conditions", []),
            "exit_conditions": strategy_recommendation.get("exit_conditions", []),
            "rationale": strategy_recommendation.get("rationale"),
            "report_preview": strategy_report[:400],
            "highlights": strategy_highlights,
            "full_report": strategy_report,
            "tools": [
                {
                    "name": tool_name,
                    "latest_summary": entries[-1].get("summary") if entries else "",
                    "call_count": len(entries),
                }
                for tool_name, entries in tool_outputs_by_agent.items()
            ],
        }

        # 实时推送"策略洞见"和"策略完成"事件
        progress_queue = None
        try:
            progress_queue = state.get("context", {}).get("_progress_queue")
        except Exception:
            progress_queue = None

        if progress_queue:
            try:
                # 推送"策略洞见"事件（策略报告预览）
                strategy_preview = strategy_report[:400]
                if strategy_preview:
                    readable_preview = strategy_preview.replace("###", "").replace("**", "")
                    progress_queue.put_nowait({
                        "type": "timeline",
                        "title": "策略洞见",
                        "content": readable_preview,
                    })

                # 推送"策略完成"事件（投资建议摘要）
                summary_parts = []
                recommendation = strategy_recommendation.get("recommendation")
                if recommendation:
                    rec_map = {"buy": "买入", "sell": "卖出", "hold": "持有", "analyze": "分析"}
                    rec_display = rec_map.get(str(recommendation).lower(), recommendation)
                    summary_parts.append(f"建议：{rec_display}")

                target_price = strategy_recommendation.get("target_price")
                if target_price:
                    summary_parts.append(f"目标价：{target_price}")

                confidence = strategy_recommendation.get("confidence")
                if confidence is not None:
                    try:
                        if isinstance(confidence, (int, float)):
                            summary_parts.append(f"置信度：{confidence:.0%}")
                        else:
                            summary_parts.append(f"置信度：{confidence}")
                    except Exception:
                        summary_parts.append(f"置信度：{confidence}")

                position_suggestion = strategy_recommendation.get("position_suggestion")
                if position_suggestion:
                    summary_parts.append(f"仓位：{position_suggestion}")

                time_horizon = strategy_recommendation.get("time_horizon")
                if time_horizon:
                    summary_parts.append(f"周期：{time_horizon}")

                entry_conditions = strategy_recommendation.get("entry_conditions", [])
                if entry_conditions and isinstance(entry_conditions, list) and len(entry_conditions) > 0:
                    entry_str = "；".join(entry_conditions[:2])
                    if len(entry_conditions) > 2:
                        entry_str += f"等{len(entry_conditions)}项"
                    summary_parts.append(f"入场：{entry_str}")

                exit_conditions = strategy_recommendation.get("exit_conditions", [])
                if exit_conditions and isinstance(exit_conditions, list) and len(exit_conditions) > 0:
                    exit_str = "；".join(exit_conditions[:2])
                    if len(exit_conditions) > 2:
                        exit_str += f"等{len(exit_conditions)}项"
                    summary_parts.append(f"出场：{exit_str}")

                if summary_parts:
                    summary = "｜".join(summary_parts)
                    # 确定标题
                    title = "策略完成"
                    try:
                        template_type = metadata.get("template_type")
                        cta_label = metadata.get("cta_label")
                        if cta_label:
                            title = f"{cta_label}完成"
                        elif template_type == "valuation":
                            title = "估值策略完成"
                        elif template_type == "industry":
                            title = "行业策略完成"
                        elif template_type == "risk":
                            title = "风险评估完成"
                    except Exception:
                        pass

                    progress_queue.put_nowait({
                        "type": "timeline",
                        "title": title,
                        "content": summary,
                    })
            except Exception as exc:
                if self.debug:
                    logger.warning(f"strategy_analyst: 推送策略进度失败: {exc}")
        
        return {
            "strategy": strategy_recommendation,
            "report": final_report,
            "output_summary": output_summary,
        }


def _generate_final_report(
    query: str,
    state: Dict[str, Any],
    plan: Dict[str, Any],
    data_analysis: str,
    strategy_report: str,
    strategy_recommendation: Dict[str, Any],
) -> str:
    """
    生成最终的投资报告（Markdown格式）
    
    注意：strategy_report本身已经是一个完整的投资策略报告（包含标题、宏观、微观、风险、建议等），
    这里只添加必要的元数据（查询、计划概览、数据分析摘要），不重复添加投资建议部分。
    """
    def _markdown_to_plain(text: str) -> str:
        lines: list[str] = []
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                lines.append("")
                continue

            heading_match = re.match(r"^(#{1,6})\s*(.+)$", stripped)
            if heading_match:
                content = heading_match.group(2).strip()
                lines.append(f"【{content}】")
                continue

            if stripped.startswith(("- ", "* ")):
                lines.append(f"• {stripped[2:].strip()}")
                continue

            lines.append(stripped)
        # 移除首尾空行
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    _ = data_analysis  # 保留参数以兼容调用方，实际展示由前端处理
    plain_strategy = _markdown_to_plain(strategy_report)
    conclusion_segments: list[str] = []

    recommendation = strategy_recommendation.get("recommendation")
    if recommendation:
        # 转换recommendation为中文
        rec_map = {"buy": "买入", "sell": "卖出", "hold": "持有", "analyze": "分析"}
        rec_display = rec_map.get(recommendation.lower(), recommendation)
        conclusion_segments.append(f"建议：{rec_display}")

    confidence = strategy_recommendation.get("confidence")
    if confidence is not None:
        try:
            if isinstance(confidence, (int, float)):
                conclusion_segments.append(f"置信度：{confidence:.0%}")
            else:
                conclusion_segments.append(f"置信度：{confidence}")
        except Exception:
            conclusion_segments.append(f"置信度：{confidence}")

    target_price = strategy_recommendation.get("target_price")
    if target_price:
        conclusion_segments.append(f"目标价：{target_price}")

    position_suggestion = strategy_recommendation.get("position_suggestion")
    if position_suggestion:
        conclusion_segments.append(f"仓位建议：{position_suggestion}")

    time_horizon = strategy_recommendation.get("time_horizon")
    if time_horizon:
        conclusion_segments.append(f"持有周期：{time_horizon}")

    # 添加更多字段
    entry_conditions = strategy_recommendation.get("entry_conditions")
    if entry_conditions and isinstance(entry_conditions, list) and len(entry_conditions) > 0:
        entry_str = "；".join(entry_conditions[:3])  # 最多显示3个
        if len(entry_conditions) > 3:
            entry_str += f"等{len(entry_conditions)}项"
        conclusion_segments.append(f"入场条件：{entry_str}")

    exit_conditions = strategy_recommendation.get("exit_conditions")
    if exit_conditions and isinstance(exit_conditions, list) and len(exit_conditions) > 0:
        exit_str = "；".join(exit_conditions[:3])  # 最多显示3个
        if len(exit_conditions) > 3:
            exit_str += f"等{len(exit_conditions)}项"
        conclusion_segments.append(f"出场条件：{exit_str}")

    # 构建扩展的投资结论
    conclusion_lines = []
    
    # 第一行：核心建议摘要（确保包含所有关键字段）
    # 重新构建摘要，确保所有字段都显示
    summary_parts = []
    if recommendation:
        rec_map = {"buy": "买入", "sell": "卖出", "hold": "持有", "analyze": "分析"}
        rec_display = rec_map.get(str(recommendation).lower(), recommendation)
        summary_parts.append(f"建议：{rec_display}")
    
    if confidence is not None:
        try:
            if isinstance(confidence, (int, float)):
                summary_parts.append(f"置信度：{confidence:.0%}")
            else:
                summary_parts.append(f"置信度：{confidence}")
        except Exception:
            summary_parts.append(f"置信度：{confidence}")
    
    if target_price:
        summary_parts.append(f"目标价：{target_price}")
    
    if position_suggestion:
        summary_parts.append(f"仓位：{position_suggestion}")
    
    if time_horizon:
        summary_parts.append(f"周期：{time_horizon}")
    
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
    
    summary_line = " | ".join(summary_parts) if summary_parts else "建议：请参考策略详情"
    conclusion_lines.append(summary_line)
    
    # 添加策略理由（完整显示，不截断）
    rationale = strategy_recommendation.get("rationale")
    if rationale and len(rationale) > 0:
        conclusion_lines.append("")  # 空行分隔
        conclusion_lines.append("【策略理由】")
        conclusion_lines.append(rationale)
    
    # 从strategy_report中提取执行建议部分
    execution_suggestions = []
    if strategy_report:
        # 使用文件顶部导入的re模块
        # 尝试提取执行建议部分（可能包含策略要点、监控指标、跟踪建议）
        execution_patterns = [
            r"##\s*(?:5\.\s*)?执行建议[\s\S]*?(?=##|$)",
            r"执行建议[\s\S]*?(?=##|$)",
            r"策略要点[\s\S]*?(?=##|监控指标|跟踪建议|$)",
            r"监控指标[\s\S]*?(?=##|跟踪建议|$)",
            r"跟踪建议[\s\S]*?(?=##|$)",
        ]
        
        for pattern in execution_patterns:
            match = re.search(pattern, strategy_report, re.IGNORECASE | re.DOTALL)
            if match:
                execution_text = match.group(0).strip()
                # 清理markdown格式，提取纯文本
                execution_text = re.sub(r"^#+\s*", "", execution_text, flags=re.MULTILINE)
                execution_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", execution_text)
                execution_text = execution_text.strip()
                if execution_text and len(execution_text) > 20:  # 确保有实际内容
                    execution_suggestions.append(execution_text)
                    break  # 找到第一个匹配的就够了
    
    # 如果没有找到执行建议，尝试从报告中提取关键信息
    if not execution_suggestions and strategy_report:
        key_phrases = ["策略要点", "监控指标", "跟踪建议", "建仓", "加仓", "止损", "止盈", "分批", "仓位"]
        found_sections = []
        for phrase in key_phrases:
            # 更宽松的匹配，匹配包含关键词的段落（前后各10行）
            pattern = rf"(?:^|\n).*{phrase}.*(?:\n.*){{0,10}}"
            match = re.search(pattern, strategy_report, re.IGNORECASE | re.MULTILINE)
            if match:
                section = match.group(0).strip()
                # 清理格式
                section = re.sub(r"^#+\s*", "", section, flags=re.MULTILINE)
                section = re.sub(r"\*\*([^*]+)\*\*", r"\1", section)
                if len(section) > 30 and len(section) < 500:  # 确保长度合理
                    found_sections.append(section)
                    if len(found_sections) >= 2:  # 最多取2个
                        break
        
        if found_sections:
            execution_suggestions.extend(found_sections[:2])
    
    # 如果还是没有找到，使用结构化数据中的entry_conditions和exit_conditions构建执行建议
    if not execution_suggestions:
        execution_parts = []
        entry_conditions = strategy_recommendation.get("entry_conditions", [])
        exit_conditions = strategy_recommendation.get("exit_conditions", [])
        position_suggestion = strategy_recommendation.get("position_suggestion")
        time_horizon = strategy_recommendation.get("time_horizon")
        
        if entry_conditions and isinstance(entry_conditions, list) and len(entry_conditions) > 0:
            execution_parts.append("入场条件：" + "；".join(entry_conditions))
        
        if exit_conditions and isinstance(exit_conditions, list) and len(exit_conditions) > 0:
            execution_parts.append("出场条件：" + "；".join(exit_conditions))
        
        if position_suggestion:
            execution_parts.append(f"仓位建议：{position_suggestion}")
        
        if time_horizon:
            execution_parts.append(f"持有周期：{time_horizon}")
        
        if execution_parts:
            execution_suggestions.append("\n".join(execution_parts))
    
    # 如果有执行建议，添加到投资结论中
    if execution_suggestions:
        conclusion_lines.append("")  # 空行分隔
        conclusion_lines.append("【执行建议】")
        # 只取第一个执行建议，避免重复
        execution_text = execution_suggestions[0]
        # 如果太长，截断到800字符（放宽限制）
        if len(execution_text) > 800:
            execution_text = execution_text[:800].rstrip() + "..."
        conclusion_lines.append(execution_text)

    conclusion_content = "\n".join(conclusion_lines)

    # 构建最终报告
    report_sections = []
    
    # 保留查询信息供前端展示
    if query:
        report_sections.append(f"【用户需求】\n{query.strip()}")
    
    # 添加投资结论（包含建议摘要、策略理由、执行建议）
    if conclusion_content.strip():
        report_sections.append(f"【投资结论】\n{conclusion_content}")
    
    # 添加策略详情
    report_sections.append(f"【策略详情】\n{plain_strategy or '（当前暂无可用的策略详情）'}")
    
    # 添加生成时间
    report_sections.append(f"【生成时间】\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n\n".join(report_sections).strip()


def create_strategy_analyst(llm, config=None, reasoning_engine=None):
    """
    创建策略分析师Agent
    
    Args:
        llm: LangChain LLM实例
        config: 配置字典（可选）
        reasoning_engine: 金融推理引擎（可选，用于Agentic RAG）
    
    Returns:
        LangGraph节点函数
    """
    agent = StrategyAnalyst(llm, config, reasoning_engine)
    return agent.create_node()
