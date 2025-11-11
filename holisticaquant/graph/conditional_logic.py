"""
条件逻辑模块

定义图的条件边判断函数
"""

from typing import Literal

from holisticaquant.agents import AgentState


def should_collect_more_data(state: AgentState) -> Literal["collect_more", "continue"]:
    """
    判断是否需要继续收集数据（优化版：智能提前退出）
    
    条件：
    - 提前退出条件1：已调用足够工具（≥min_tools）且置信度≥阈值
    - 提前退出条件2：已收集到关键数据源（基本面或市场数据）且置信度≥0.5
    - 提前退出条件3：LLM判断数据已充足
    - 兜底：如果数据不充足且未达到最大迭代次数，继续收集
    
    Args:
        state: 当前状态
        
    Returns:
        "collect_more": 需要继续收集数据，返回 data_analyst
        "continue": 数据充足，继续到 strategy_analyst
    """
    # 检查必需字段
    if "data_sufficiency" not in state:
        raise ValueError("state必须包含data_sufficiency字段")
    if "collection_iteration" not in state:
        raise ValueError("state必须包含collection_iteration字段")
    if "max_collection_iterations" not in state:
        raise ValueError("state必须包含max_collection_iterations字段")
    
    data_sufficiency = state["data_sufficiency"]
    collection_iteration = state["collection_iteration"]
    max_iterations = state["max_collection_iterations"]
    
    # 检查data_sufficiency必需字段
    if "sufficient" not in data_sufficiency:
        raise ValueError("data_sufficiency必须包含sufficient字段")
    
    # 获取配置（从metadata中读取）
    metadata = state.get("metadata", {})
    config = metadata.get("config", {})
    agents_config = config.get("agents", {})
    data_suff_config = agents_config.get("data_sufficiency", {})
    min_confidence = data_suff_config.get("min_confidence", 0.6)
    min_tools = data_suff_config.get("min_tools_called", 2)
    early_stop = data_suff_config.get("early_stop", True)
    
    # 提前退出条件3：LLM判断数据已充足（最高优先级）
    if data_sufficiency.get("sufficient", False):
        return "continue"
    
    # 如果提前退出功能未启用，使用原有逻辑
    if not early_stop:
        if collection_iteration < max_iterations:
            return "collect_more"
        return "continue"
    
    # 检查已收集的数据
    collected_data = state.get("collected_data", {})
    tools_called_count = len(collected_data)
    confidence = data_sufficiency.get("confidence", 0.0)
    
    # 提前退出条件1：已调用足够工具且置信度达标
    if tools_called_count >= min_tools and confidence >= min_confidence:
        return "continue"
    
    # 提前退出条件2：已收集到关键数据源（基本面或市场数据）且置信度≥0.5
    if tools_called_count >= 1:
        key_tools = ["get_stock_fundamental", "get_stock_market_data", "get_market_data"]
        collected_tool_names = set(collected_data.keys())
        if any(tool in collected_tool_names for tool in key_tools):
            # 如果已收集到关键数据，且置信度不太低，可以提前退出
            if confidence >= 0.5:
                return "continue"
    
    # 兜底逻辑：如果数据不充足且未达到最大迭代次数，继续收集
    if collection_iteration < max_iterations:
        return "collect_more"
    
    return "continue"


def determine_scenario_route(state: AgentState) -> Literal[
    "learning_workshop", "research_lab", "assistant"
]:
    """
    根据plan_analyst识别的场景类型决定路由。
    默认回退到assistant，避免流程中断。
    """
    scenario_type = state.get("scenario_type") or "assistant"
    if scenario_type not in {"learning_workshop", "research_lab", "assistant"}:
        return "assistant"
    return scenario_type

