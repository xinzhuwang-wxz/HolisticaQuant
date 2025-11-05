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
            "- **禁止调用任何数据收集工具**：如get_stock_fundamental、get_stock_market_data、get_market_data、get_sina_news等。这些工具是data_analyst使用的，你不需要调用。\n"
            "- **禁止调用任何未列出的工具**：只使用web_search工具。如果尝试调用其他工具会报错。\n\n"
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
        
        # 提取文本报告（如果为空，直接报错，不使用默认值）
        if text_content is None or not text_content.strip():
            error_msg = (
                f"strategy_analyst: 文本报告为空！\n"
                f"  - text_content: {text_content}\n"
                f"  - 工具调用结果数量: {len(tool_results) if tool_results else 0}\n"
                f"  - 工具调用结果: {list(tool_results.keys()) if tool_results else []}\n"
                f"  - 结构化数据: {structured_data}\n"
                f"  - plan: {state.get('plan', {})}\n"
                f"  - data_analysis: {state.get('data_analysis', 'N/A')[:200] if state.get('data_analysis') else 'N/A'}\n"
            )
            logger.error(error_msg)
            raise ValueError("strategy_analyst: 文本报告生成失败，LLM返回空内容。请检查工具调用结果和LLM配置。")
        
        strategy_report = text_content.strip()
        
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
    # 构建报告头部（元数据）
    report = f"""# 投资策略报告

## 用户查询
{query}

---

## 执行计划概览
- **关注股票**：{', '.join(state.get('tickers', []) or plan.get('tickers', []) or ['无'])}
- **时间范围**：{plan.get('time_range', 'last_30d')}
- **需求意图**：{plan.get('intent', '投资分析')}
- **数据源**：{', '.join(plan.get('data_sources', [])) if plan.get('data_sources') else '未指定'}
- **重点关注**：{', '.join(plan.get('focus_areas', [])) if plan.get('focus_areas') else '未指定'}

--------------------------------

## 数据分析摘要

{data_analysis}


--------------------------------

## 投资策略分析

{strategy_report}

--------------------------------

*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    return report


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
