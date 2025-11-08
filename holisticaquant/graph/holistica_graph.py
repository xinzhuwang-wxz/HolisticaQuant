"""
HolisticaGraph - 主图构建

基于LangGraph构建的agent工作流：
plan_analyst -> data_analyst -> strategy_analyst
"""

from typing import Dict, Any, Optional
from langchain_core.language_models import BaseChatModel
from loguru import logger

from holisticaquant.agents import (
    AgentState,
    create_empty_state,
    create_plan_analyst,
    create_data_analyst,
    create_strategy_analyst,
)
from holisticaquant.graph.build_graph import build_mvp_graph
from holisticaquant.agents.utils.debug_formatter import (
    snapshot_state,
    format_state_snapshot,
)


class HolisticaGraph:
    """
    HolisticaGraph - 主工作流图
    
    流程：
    1. plan_analyst: 分析用户查询，制定数据收集计划
    2. data_analyst: 根据计划收集数据并生成分析报告
    3. strategy_analyst: 基于分析报告生成投资策略和建议
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化图
        
        Args:
            llm: LangChain LLM实例
            config: 配置字典（可选）
        """
        self.llm = llm
        self.config = config or {}
        self.debug = self.config.get("debug", False)
        
        # 初始化推理引擎（如果启用Agentic RAG）
        reasoning_engine = None
        rag_config = self.config.get("agentic_rag", {})
        if rag_config.get("enabled", False):
            try:
                from holisticaquant.memory import FinancialReasoningEngine
                reasoning_engine = FinancialReasoningEngine(llm=llm, config=config)
                # 记录详细配置信息（INFO级别）
                logger.info(f"HolisticaGraph: Agentic RAG已启用")
                logger.info(f"  - max_insights: {rag_config.get('max_insights', 100)}")
                logger.info(f"  - forget_days: {rag_config.get('forget_days', 90)}")
                logger.info(f"  - extract_insights: {rag_config.get('extract_insights', True)}")
            except Exception as e:
                logger.error(f"HolisticaGraph: 初始化推理引擎失败: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        else:
            logger.info("HolisticaGraph: Agentic RAG未启用")
        
        # 创建agents
        plan_analyst_node = create_plan_analyst(llm, config)
        data_analyst_node = create_data_analyst(llm, config)
        strategy_analyst_node = create_strategy_analyst(llm, config, reasoning_engine)
        
        # 构建图
        self.graph = build_mvp_graph(
            plan_analyst_node,
            data_analyst_node,
            strategy_analyst_node
        )
    
    async def run_async(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        异步执行完整工作流
        
        Args:
            query: 用户查询
            context: 上下文信息（必须包含 trigger_time）
            
        Returns:
            最终状态
        """
        if context is None:
            from datetime import datetime
            context = {
                "trigger_time": datetime.now().strftime('%Y-%m-%d %H:00:00'),
            }
        
        # 创建初始状态
        initial_state = create_empty_state(query=query, context=context, config=self.config)
        
        # 执行图
        final_state = await self.graph.ainvoke(initial_state)
        
        if self.debug:
            logger.info(f"HolisticaGraph: 执行完成")
            if "plan" in final_state and "intent" in final_state["plan"]:
                logger.info(f"  - 计划: {final_state['plan']['intent']}")
            if "strategy" in final_state and "recommendation" in final_state["strategy"]:
                logger.info(f"  - 策略建议: {final_state['strategy']['recommendation']}")
            metadata = final_state.get("metadata", {})
            if metadata.get("tool_outputs"):
                logger.info(f"  - 工具调用统计: { {agent: {tool: len(entries) for tool, entries in tools.items()} for agent, tools in metadata['tool_outputs'].items()} }")
            if metadata.get("data_analysis_summary"):
                logger.info(f"  - 数据分析摘要可用")
            if metadata.get("strategy_summary"):
                logger.info(f"  - 策略摘要可用")
            summary_keys = [
                "plan",
                "collected_data",
                "data_sufficiency",
                "data_analysis",
                "strategy",
                "report",
                "errors",
                "trace",
            ]
            snapshot = snapshot_state(final_state, summary_keys)
            if snapshot:
                logger.info(format_state_snapshot("holistica_graph", "最终状态", snapshot))
        
        return final_state
    
    def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        同步执行完整工作流
        
        Args:
            query: 用户查询
            context: 上下文信息（必须包含 trigger_time）
            
        Returns:
            最终状态
        """
        import asyncio
        return asyncio.run(self.run_async(query, context))
    
    def get_report(self, state: AgentState) -> str:
        """
        获取最终报告
        
        Args:
            state: 最终状态
            
        Returns:
            Markdown格式的报告
        """
        if "report" not in state:
            raise ValueError("state必须包含report字段")
        return state["report"]

