"""
条件逻辑模块

定义图的条件边判断函数
"""

from typing import Literal

from holisticaquant.agents import AgentState


def should_collect_more_data(state: AgentState) -> Literal["collect_more", "continue"]:
    """
    判断是否需要继续收集数据
    
    条件：
    - 如果数据不充足且未达到最大迭代次数 → 返回 "collect_more"（继续收集）
    - 如果数据充足或已达最大迭代次数 → 返回 "continue"（继续到策略分析）
    
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
    
    # 如果数据不充足且未达到最大迭代次数，继续收集
    if not data_sufficiency["sufficient"] and collection_iteration < max_iterations:
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

