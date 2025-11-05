"""
Agent State 定义

统一的状态管理，确保所有agent使用相同的state结构
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from datetime import datetime


class AgentState(TypedDict):
    """
    统一的Agent状态结构
    
    所有agent都读取和更新这个state，确保数据流的一致性
    """
    
    # === 输入层 ===
    query: str  # 用户查询
    context: Dict[str, Any]  # 上下文信息（trigger_time, user_id等）
    
    # === planTeam 输出 ===
    tickers: Annotated[List[str], "股票代码列表（6位数字），由plan_analyst提取并维护"]
    plan: Annotated[Dict[str, Any], "plan_analyst输出的数据收集计划，包含time_range、intent、data_sources、focus_areas等字段"]
    
    # === dataTeam 输出 ===
    collected_data: Annotated[Dict[str, str], "data_analyst收集的数据，键为工具名称，值为工具返回的字符串结果"]
    data_analysis: Annotated[str, "data_analyst生成的分析报告（Markdown格式）"]
    data_sufficiency: Annotated[Dict[str, Any], "数据充分性评估，包含sufficient(bool)、missing_data(list)、confidence(float)、reason(str)等字段"]
    collection_iteration: Annotated[int, "数据收集迭代次数"]
    max_collection_iterations: Annotated[int, "最大收集迭代次数"]
    
    # === strategyTeam 输出 ===
    strategy: Annotated[Dict[str, Any], "strategy_analyst输出的投资建议，包含recommendation、confidence、target_price、position_suggestion、time_horizon、rationale、entry_conditions、exit_conditions等字段"]
    report: Annotated[str, "最终投资报告（Markdown格式）"]
    
    # === 通用字段 ===
    messages: Annotated[List[Any], "LangChain消息历史"]
    trace: Annotated[List[Dict[str, Any]], "思维链追踪，每个元素包含step、agent、action、output、error、timestamp等字段"]
    errors: Annotated[List[str], "错误列表"]
    metadata: Annotated[Dict[str, Any], "额外元数据"]


def create_empty_state(query: str, context: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> AgentState:
    """
    创建空状态
    
    Args:
        query: 用户查询（必需）
        context: 上下文信息（必需，至少包含 trigger_time）
        config: 配置字典（可选，用于读取默认值）
        
    Returns:
        初始化的AgentState
    """
    if not query:
        raise ValueError("query不能为空")
    if not context:
        raise ValueError("context不能为空")
    if "trigger_time" not in context:
        raise ValueError("context必须包含 trigger_time")
    
    # 从配置读取默认值
    if config is None:
        from holisticaquant.config.config import get_config
        config = get_config().config
    
    max_collection_iterations = config.get("agents", {}).get("max_collection_iterations", 1)
    
    return {
        "query": query,
        "context": context,
        "tickers": [],  # 股票代码列表，由plan_analyst维护
        "plan": {},
        "collected_data": {},
        "data_analysis": "",
        "data_sufficiency": {"sufficient": False, "missing_data": [], "confidence": 0.0, "reason": ""},
        "collection_iteration": 0,
        "max_collection_iterations": max_collection_iterations,
        "strategy": {},
        "report": "",
        "messages": [],
        "trace": [],
        "errors": [],
        "metadata": {},
    }


def update_trace(
    state: AgentState,
    step: str,
    agent: str,
    action: str,
    output: Optional[str] = None,
    error: Optional[str] = None
):
    """
    更新追踪信息
    
    Args:
        state: 状态字典
        step: 步骤名称（plan/data_analysis/strategy）
        agent: agent名称
        action: 执行的操作
        output: 输出摘要（可选）
        error: 错误信息（可选）
    """
    if "trace" not in state:
        raise ValueError("state必须包含trace字段")
    
    trace_entry: Dict[str, Any] = {
        "step": step,
        "agent": agent,
        "action": action,
        "timestamp": datetime.now().isoformat(),
    }
    
    if output:
        trace_entry["output"] = output[:1000]  # 限制长度
    if error:
        trace_entry["error"] = error
    
    state["trace"].append(trace_entry)


def add_error(state: AgentState, error: str):
    """
    添加错误到状态
    
    Args:
        state: 状态字典
        error: 错误信息
    """
    if "errors" not in state:
        raise ValueError("state必须包含errors字段")
    state["errors"].append(error)

