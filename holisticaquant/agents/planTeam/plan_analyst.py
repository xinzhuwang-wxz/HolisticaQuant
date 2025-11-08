"""
Plan Analyst Agent - 规划分析师（简化版）

职责：
1. 分析用户查询
2. 提取股票代码（从查询中直接提取或基于知识库推测）
3. 推断时间范围
4. 返回简化的计划（只包含tickers和time_range）

工具：
- 无工具：直接基于LLM知识库推测股票代码
"""

from typing import Dict, Any, Optional, Type
import re
import json
from pydantic import BaseModel
from loguru import logger

from holisticaquant.agents.utils.base_agent import BaseAgent
from holisticaquant.agents.utils.agent_states import AgentState
from holisticaquant.agents.utils.schemas import PlanSchema
from holisticaquant.memory.scenario_repository import (
    get_learning_topic_summaries,
    get_research_template_summaries,
)
# plan_analyst简化版：不使用工具，直接基于LLM知识库推测股票代码


class PlanAnalyst(BaseAgent):
    """规划分析师Agent"""
    
    def __init__(self, llm, config=None):
        # plan_analyst简化版：不使用工具，直接基于LLM知识库推测股票代码
        tools = []  # 不使用任何工具

        super().__init__(
            name="plan_analyst",
            llm=llm,
            tools=tools,
            config=config
        )
    
    def _get_state_keys_to_monitor(self) -> list[str]:
        return ["query", "tickers", "plan", "scenario_type", "plan_target_id"]

    def _get_state_input_keys(self) -> list[str]:
        return ["query"]

    def _get_state_output_keys(self) -> list[str]:
        return ["tickers", "plan", "scenario_type", "plan_target_id"]
    
    def _get_structured_output_schema(self) -> Optional[Type[BaseModel]]:
        """返回结构化输出Schema"""
        return PlanSchema
    
    def _get_system_message(self) -> str:
        """获取系统提示词"""
        return (
            "你是HolisticaQuant的场景规划助手，负责判别用户需求所属的核心场景，并给出初步计划。\n\n"
            "可选场景：\n"
            "1. learning_workshop（场景化学习工坊）：用户想通过“知识点+场景+任务”学习某个主题，例如“区块链支付”“CBDC”。\n"
            "2. research_lab（全流程投研实验室）：用户要完成估值、行业分析、投研报告等，需要走 plan→data→strategy 流程。\n"
            "3. assistant（AI 智能陪伴）：用户只想快速得到解释或问答，不需要完整流程。\n\n"
            "输出要求：\n"
            "- scenario_type：从上述三类中选择一个。\n"
            "- target_id：若选择learning_workshop，则提供最匹配的知识点ID；若选择research_lab，则提供最匹配的模板ID；assistant时为null。\n"
            "- tickers：仅在research_lab场景需要时填写6位股票代码列表（最多5个），其他场景可为空。\n"
            "- time_range/intent/data_sources/focus_areas 按以往规范返回。\n\n"
            "如果用户提到具体经济数据练习、课程作业或投研报告，则倾向于research_lab；\n"
            "如果用户明确要学知识点、做实验任务，倾向于learning_workshop；\n"
            "如果只是问问题或需要解释，选择assistant。"
        )

    def _get_user_input(self, state: AgentState, memory_context: str = "") -> str:
        """获取用户输入"""
        query = state["query"]
        learning_topics = get_learning_topic_summaries()
        research_templates = get_research_template_summaries()
        
        # 检查是否包含股票代码格式（6位数字）
        ticker_pattern = r'\b\d{6}\b'
        has_ticker_code = bool(re.search(ticker_pattern, query))

        learning_text = (
            json.dumps(learning_topics, ensure_ascii=False, indent=2)
            if learning_topics
            else "[]"
        )
        research_text = (
            json.dumps(research_templates, ensure_ascii=False, indent=2)
            if research_templates
            else "[]"
        )
        
        instruction = (
            f"用户查询：{query}\n\n"
            f"可选学习工坊场景（learning_workshop）：\n{learning_text}\n\n"
            f"可选投研模板（research_lab）：\n{research_text}\n\n"
            "请完成以下任务：\n"
            "1. 判断用户查询最匹配的 scenario_type（learning_workshop / research_lab / assistant）。\n"
            "2. 如果选择 learning_workshop，则挑选最相关的知识点ID作为 target_id；"
            " 若无匹配则 target_id 为 null。\n"
            "3. 如果选择 research_lab，则挑选最相关的模板ID作为 target_id，并尽量提供相关股票代码列表；"
            " 若用户未给出股票代码，可根据常识推测（如“特斯拉”→无A股代码，tickers为空）。\n"
            "4. 如果选择 assistant，则 target_id 为 null，tickers 也可为空。\n"
            "5. time_range 根据查询推断（默认 last_30d）。\n"
        )
        
        if has_ticker_code:
            instruction += (
                "\n提示：查询中已包含股票代码，请在 tickers 中直接提取 6 位数字代码。"
            )
        else:
            instruction += (
                "\n提示：如果查询提到具体公司但无代码，可尝试推断A股代码；若无法确定，tickers留空。"
            )
        
        return instruction
    
    def _get_continue_prompt(self) -> str:
        """获取继续处理的提示词"""
        return "请继续提取股票代码和时间范围。"
    
    def _validate_state(self, state: AgentState):
        """验证状态"""
        if "query" not in state:
            raise ValueError("plan_analyst: state必须包含query字段")
        
        query = state["query"]
        if not query:
            raise ValueError("plan_analyst: query为空")
    
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
            logger.warning("plan_analyst: 结构化数据为None，使用占位值")
            structured_data = PlanSchema(
                tickers=[],
                time_range="last_30d"
            )
        
        # 使用structured output获取结构化数据
        if not isinstance(structured_data, PlanSchema):
            error_msg = f"plan_analyst: 结构化数据类型错误，期望PlanSchema，实际: {type(structured_data)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 转换为字典
        plan_dict = structured_data.model_dump()
        scenario_type = plan_dict.get("scenario_type", "assistant") or "assistant"
        target_id = plan_dict.get("target_id")
        
        # 验证并清理tickers：确保是股票代码格式（6位数字），不是公司名称
        if plan_dict.get("tickers"):
            cleaned_tickers = []
            for ticker in plan_dict["tickers"]:
                # 跳过空字符串和None
                if not ticker or (isinstance(ticker, str) and not ticker.strip()):
                    continue
                
                # 检查是否是股票代码格式（6位数字，或带.SH/.SZ后缀）
                ticker_str = str(ticker).strip()
                # 移除可能的后缀（如.SH, .SZ, .HK等）
                if '.' in ticker_str:
                    ticker_str = ticker_str.split('.')[0]
                
                # 检查是否是纯数字（股票代码格式）
                if ticker_str.isdigit() and len(ticker_str) == 6:
                    cleaned_tickers.append(ticker_str)
                else:
                    # 如果不是股票代码格式，记录警告
                    logger.warning(
                        f"plan_analyst: 检测到非股票代码格式的ticker: '{ticker}'，已跳过。"
                        f"请确保tickers列表中的是股票代码（6位数字），不是公司名称。"
                    )
                    if self.debug:
                        logger.debug(f"plan_analyst: 非股票代码格式的ticker详情: {ticker} (类型: {type(ticker)})")
            
            plan_dict["tickers"] = cleaned_tickers
            
            # 如果所有tickers都被过滤掉了，在research_lab场景下需要报错
            if scenario_type == "research_lab" and not cleaned_tickers:
                logger.warning(
                    "plan_analyst: research_lab 场景下未能提取有效股票代码，将允许空列表（后续可能需要被动数据源或模板填充）。"
                )
        else:
            # 确保tickers字段存在
            plan_dict["tickers"] = []
            
            if scenario_type == "research_lab":
                query_text = state.get("query", "")
                if query_text and any(keyword in query_text for keyword in ["股票", "代码", "公司", "股份", "投资", "分析"]):
                    logger.warning(
                        "plan_analyst: research_lab 场景下未提取到股票代码，后续数据收集可能依赖被动工具或模板数据。"
                    )
        
        # 确保time_range字段存在
        if "time_range" not in plan_dict or not plan_dict["time_range"]:
            plan_dict["time_range"] = "last_30d"
            logger.info("plan_analyst: time_range未设置，使用默认值last_30d")
        
        # 限制股票数量：最多5支股票
        if plan_dict.get("tickers") and len(plan_dict["tickers"]) > 5:
            original_count = len(plan_dict["tickers"])
            plan_dict["tickers"] = plan_dict["tickers"][:5]
            logger.warning(
                f"plan_analyst: 计划中包含 {original_count} 支股票，已截断为前5支: {plan_dict['tickers']}。"
            )
        
        # Schema已定义默认值（intent, data_sources, focus_areas），model_dump()会自动填充，无需手动设置
        
        # 输出摘要
        output_summary = (
            f"场景: {scenario_type}, "
            f"目标: {target_id or '无'}, "
            f"股票: {plan_dict['tickers']}, "
            f"时间范围: {plan_dict['time_range']}"
        )
        
        if self.debug:
            logger.info(f"plan_analyst: 计划生成成功 - {output_summary}")

        return {
            "tickers": plan_dict["tickers"],  # 顶层维护tickers
            "plan": plan_dict,  # plan字典也保留tickers（向后兼容）
            "scenario_type": scenario_type,
            "plan_target_id": target_id,
            "output_summary": output_summary,
        }


def create_plan_analyst(llm, config=None):
    """
    创建规划分析师Agent
    
    Args:
        llm: LangChain LLM实例
        config: 配置字典（可选）
    
    Returns:
        LangGraph节点函数
    """
    agent = PlanAnalyst(llm, config)
    return agent.create_node()
