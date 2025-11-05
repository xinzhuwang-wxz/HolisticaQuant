"""
图构建模块

负责构建LangGraph工作流图
"""

from langgraph.graph import StateGraph, END
from typing import Callable

from holisticaquant.agents import AgentState
from holisticaquant.graph.conditional_logic import should_collect_more_data


def build_mvp_graph(
    plan_analyst_node: Callable,
    data_analyst_node: Callable,
    strategy_analyst_node: Callable
):
    """
    构建MVP工作流图
    
    流程：
    plan_analyst -> data_analyst -> (条件判断) -> data_analyst (循环) 或 strategy_analyst -> END
    
    条件边：
    - 如果数据不足且未达最大迭代次数，返回 data_analyst 继续收集
    - 如果数据充足或已达最大迭代次数，继续到 strategy_analyst
    
    Args:
        plan_analyst_node: plan_analyst节点函数
        data_analyst_node: data_analyst节点函数
        strategy_analyst_node: strategy_analyst节点函数
        
    Returns:
        编译后的图
    """
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("plan_analyst", plan_analyst_node)
    workflow.add_node("data_analyst", data_analyst_node)
    workflow.add_node("strategy_analyst", strategy_analyst_node)
    
    # 定义流程
    workflow.set_entry_point("plan_analyst")
    workflow.add_edge("plan_analyst", "data_analyst")
    
    # 添加条件边：data_analyst 后判断是否需要继续收集
    workflow.add_conditional_edges(
        "data_analyst",
        should_collect_more_data,
        {
            "collect_more": "data_analyst",  # 数据不足，继续收集
            "continue": "strategy_analyst",  # 数据充足，继续策略
        }
    )
    
    workflow.add_edge("strategy_analyst", END)
    
    return workflow.compile()

