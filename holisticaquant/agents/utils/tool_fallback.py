"""
工具降级辅助函数

用于检查工具失败率并建议降级
"""

from typing import Dict, Any, Optional
from loguru import logger


def get_failing_tools(state: Dict[str, Any], failure_threshold: int = 3) -> list:
    """
    获取失败率高的工具列表
    
    Args:
        state: AgentState
        failure_threshold: 失败次数阈值（默认3次）
        
    Returns:
        失败工具名称列表
    """
    if not state.get("metadata") or "tool_stats" not in state["metadata"]:
        return []
    
    tool_stats = state["metadata"]["tool_stats"]
    failing_tools = []
    
    for tool_name, stats in tool_stats.items():
        failure_count = stats.get("failure_count", 0)
        success_count = stats.get("success_count", 0)
        total_count = failure_count + success_count
        
        # 如果失败次数超过阈值，或者失败率超过50%
        if failure_count >= failure_threshold or (total_count > 0 and failure_count / total_count > 0.5):
            failing_tools.append(tool_name)
            logger.warning(
                f"工具 {tool_name} 失败率高: "
                f"失败 {failure_count} 次，成功 {success_count} 次，总调用 {total_count} 次"
            )
    
    return failing_tools


def get_tool_suggestion_message(failing_tools: list) -> str:
    """
    生成工具降级建议消息
    
    Args:
        failing_tools: 失败工具列表
        
    Returns:
        建议消息字符串
    """
    if not failing_tools:
        return ""
    
    # 数据源降级映射
    fallback_map = {
        "get_sina_news": "get_thx_news",
        "get_thx_news": "get_sina_news",
        "get_market_data": "web_search",  # 市场数据失败时可用搜索补充
        "get_hot_money": "web_search",
        "get_stock_fundamental": "web_search",
        "get_stock_market_data": "web_search",
    }
    
    suggestions = []
    for tool in failing_tools:
        if tool in fallback_map:
            fallback = fallback_map[tool]
            suggestions.append(f"- {tool} 失败率高，建议使用 {fallback} 替代")
        else:
            suggestions.append(f"- {tool} 失败率高，建议检查工具配置或使用其他数据源")
    
    if suggestions:
        return (
            "\n**工具状态提醒**：\n" +
            "\n".join(suggestions) +
            "\n"
        )
    
    return ""
