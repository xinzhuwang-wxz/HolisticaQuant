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
from pydantic import BaseModel
from loguru import logger

from holisticaquant.agents.utils.base_agent import BaseAgent
from holisticaquant.agents.utils.agent_states import AgentState
from holisticaquant.agents.utils.schemas import PlanSchema
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
        return ["query", "tickers", "plan"]

    def _get_state_input_keys(self) -> list[str]:
        return ["query"]

    def _get_state_output_keys(self) -> list[str]:
        return ["tickers", "plan"]
    
    def _get_structured_output_schema(self) -> Optional[Type[BaseModel]]:
        """返回结构化输出Schema"""
        return PlanSchema
    
    def _get_system_message(self) -> str:
        """获取系统提示词"""
        return (
            "你是金融分析规划助手。从用户查询中提取股票代码和时间范围。\n\n"
            "流程：\n"
            "1. 查询含6位数字代码 → 直接提取\n"
            "2. 查询含公司名称 → 基于知识库推测股票代码（如：海陆重工→002255，中国石油→601857）\n"
            "3. 查询含方向 → 返回空tickers列表（让data_analyst使用被动工具）\n\n"
            "输出：tickers（6位数字列表，最多5支）、time_range（last_7d/last_30d/last_90d）\n"
            "注意：如果无法确定股票代码，tickers可以为空列表[]"
        )

    def _get_user_input(self, state: AgentState, memory_context: str = "") -> str:
        """获取用户输入"""
        query = state["query"]
        
        # 检查是否包含股票代码格式（6位数字）
        ticker_pattern = r'\b\d{6}\b'
        has_ticker_code = bool(re.search(ticker_pattern, query))
        
        if has_ticker_code:
            return f"用户查询：{query}\n\n查询含股票代码，直接提取6位数字代码和时间范围。"
        else:
            return f"用户查询：{query}\n\n基于知识库推测股票代码（如：海陆重工→002255，中国石油→601857）。如果无法确定，tickers返回空列表[]。"
    
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
            
            # 如果所有tickers都被过滤掉了，直接报错（不使用默认值）
            if not cleaned_tickers:
                error_msg = (
                    f"plan_analyst: ⚠️ 所有tickers都不是有效的股票代码格式，tickers列表已为空！\n"
                    f"  - 原始tickers: {plan_dict.get('tickers', [])}\n"
                    f"  - 用户查询: {state.get('query', 'N/A')}\n"
                    f"  - 结构化数据: {structured_data}\n"
                    f"这可能导致后续数据收集失败。请检查LLM是否正确提取了股票代码。"
                )
                logger.error(error_msg)
                raise ValueError("plan_analyst: 无法提取有效的股票代码。请检查用户查询是否包含股票代码或公司名称，以及LLM是否正确提取。")
        else:
            # 确保tickers字段存在
            plan_dict["tickers"] = []
            
            # 如果tickers字段不存在或为空，直接报错（不使用默认值）
            # 注意：方向性查询（如"推荐近期科技板块的股票"）可能允许tickers为空
            # 但为了严格检查，如果查询明确提到股票或公司名，tickers应该不为空
            query = state.get("query", "")
            if query and any(keyword in query for keyword in ["股票", "代码", "公司", "股份", "投资", "分析"]):
                error_msg = (
                    f"plan_analyst: tickers列表为空，但查询似乎要求提取股票代码！\n"
                    f"  - 用户查询: {query}\n"
                    f"  - 结构化数据: {structured_data}\n"
                    f"请检查LLM是否正确提取了股票代码。"
                )
                logger.error(error_msg)
                raise ValueError("plan_analyst: 无法提取股票代码，但查询要求提取股票代码。请检查LLM是否正确提取。")
        
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
            f"股票: {plan_dict['tickers']}, "
            f"时间范围: {plan_dict['time_range']}"
        )
        
        if self.debug:
            logger.info(f"plan_analyst: 计划生成成功 - {output_summary}")

        return {
            "tickers": plan_dict["tickers"],  # 顶层维护tickers
            "plan": plan_dict,  # plan字典也保留tickers（向后兼容）
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
