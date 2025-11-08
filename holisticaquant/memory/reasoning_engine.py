"""
金融推理引擎 - Agentic RAG for Financial Insights

这个推理引擎专门用于金融场景，能够：
1. 从策略智能体的输出中提取金融洞见
2. 维护金融洞见作为记忆
3. 利用历史洞见改进策略生成
"""

from typing import Dict, Any, List, Optional, Set, Iterable, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from .mini_vector_store import MiniVectorStore


class FinancialInsight:
    """金融洞见数据结构"""
    
    def __init__(
        self,
        insight_type: str,  # market_trend, stock_pattern, risk_factor, strategy_pattern
        content: str,
        metadata: Dict[str, Any],
        timestamp: Optional[str] = None,
        vector_id: Optional[int] = None,
    ):
        self.insight_type = insight_type
        self.content = content
        self.metadata = metadata
        self.timestamp = timestamp or datetime.now().isoformat()
        self.relevance_score = 0.0  # 相关性分数，用于检索排序
        self.usage_count = 0  # 使用次数，用于评估洞见价值
        self.last_accessed: Optional[str] = None  # 最后访问时间
        self.vector_id = vector_id
    
    def update_access(self):
        """更新最后访问时间"""
        self.last_accessed = datetime.now().isoformat()
        self.usage_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "insight_type": self.insight_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "relevance_score": self.relevance_score,
            "usage_count": self.usage_count,
            "last_accessed": self.last_accessed,
            "vector_id": self.vector_id,
        }


class FinancialInsightMemory:
    """金融洞见记忆系统（轻量实现）
    
    维护金融洞见的存储和检索，不使用矢量库
    实现遗忘机制：基于时间、使用次数、总数限制
    """
    
    def __init__(
        self,
        max_insights: int = 100,
        forget_days: int = 90,
        use_vector_store: bool = False,
        vector_db_path: Optional[Path] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        初始化记忆系统
        
        Args:
            max_insights: 最大保存洞见数量（默认100）
            forget_days: 遗忘天数（默认90天）
        """
        self._insights: List[FinancialInsight] = []
        self._max_insights = max_insights
        self._forget_days = forget_days
        # 关键词索引：{ticker: [insight_ids], intent: [insight_ids]}
        self._keyword_index: Dict[str, Set[int]] = {}
        self._id_map: Dict[int, FinancialInsight] = {}
        self.vector_store: Optional[MiniVectorStore] = None
        self.use_vector_store = use_vector_store and vector_db_path is not None

        if self.use_vector_store:
            try:
                self.vector_store = MiniVectorStore(
                    db_path=vector_db_path, model_name=embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
                )
                self._load_from_vector_store()
            except Exception as e:
                logger.warning(f"Agentic RAG: 初始化向量存储失败，将回退到关键词检索。原因: {e}")
                self.vector_store = None
                self.use_vector_store = False
    
    def add_insight(self, insight: FinancialInsight):
        """添加金融洞见"""
        self._insights.append(insight)
        vector_id = None
        if self.vector_store:
            try:
                vector_id = self.vector_store.add(
                    insight_type=insight.insight_type,
                    content=insight.content,
                    metadata=insight.metadata,
                    timestamp=insight.timestamp,
                )
            except Exception as e:
                logger.warning(f"Agentic RAG: 写入向量存储失败，将继续使用内存列表。原因: {e}")
                vector_id = None
        if vector_id is not None:
            insight.vector_id = vector_id
            self._id_map[vector_id] = insight
        
        # 更新关键词索引
        self._update_keyword_index(insight, len(self._insights) - 1)
        
        # 执行遗忘机制
        self._apply_forgetting()
        
        logger.debug(f"添加金融洞见: {insight.insight_type} - {insight.content[:50]}...")
    
    def _update_keyword_index(self, insight: FinancialInsight, index: int):
        """更新关键词索引"""
        # 索引tickers
        tickers = insight.metadata.get("tickers", [])
        for ticker in tickers:
            if ticker not in self._keyword_index:
                self._keyword_index[ticker] = set()
            self._keyword_index[ticker].add(index)
        
        # 索引intent（如果有）
        intent = insight.metadata.get("source_intent", "")
        if intent:
            if intent not in self._keyword_index:
                self._keyword_index[intent] = set()
            self._keyword_index[intent].add(index)
    
    def _apply_forgetting(self):
        """应用遗忘机制"""
        # 1. 基于时间的遗忘：删除超过N天的旧洞见
        self.forget_old_insights(self._forget_days)
        
        # 2. 基于总数的限制：保留使用次数最多的
        self.prune_by_limit(self._max_insights)
    
    def forget_old_insights(self, days: int = 90):
        """删除超过N天的旧洞见"""
        if not self._insights:
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        # 删除旧洞见
        before_count = len(self._insights)
        removed: List[FinancialInsight] = []
        self._insights, removed = self._split_insights(lambda ins: ins.timestamp > cutoff_iso)
        self._remove_from_vector_store(removed)
        
        # 重建索引
        self._rebuild_index()
        
        if before_count > len(self._insights):
            logger.debug(f"遗忘机制：删除了 {before_count - len(self._insights)} 条超过 {days} 天的旧洞见")
    
    def prune_by_limit(self, max_count: int = 100):
        """限制总数，保留使用次数最多的"""
        if len(self._insights) <= max_count:
            return
        
        before_count = len(self._insights)
        
        # 按使用次数和最后访问时间排序
        self._insights.sort(
            key=lambda x: (
                x.usage_count,
                datetime.fromisoformat(x.last_accessed) if x.last_accessed else datetime.min,
                datetime.fromisoformat(x.timestamp)
            ),
            reverse=True
        )
        
        # 保留top N
        kept = self._insights[:max_count]
        removed = self._insights[max_count:]
        self._insights = kept
        self._remove_from_vector_store(removed)
        
        # 重建索引
        self._rebuild_index()
        
        if before_count > len(self._insights):
            logger.debug(f"限制机制：删除了 {before_count - len(self._insights)} 条洞见，保留使用次数最多的 {max_count} 条")
    
    def _rebuild_index(self):
        """重建关键词索引"""
        self._keyword_index.clear()
        self._id_map.clear()
        for idx, insight in enumerate(self._insights):
            self._update_keyword_index(insight, idx)
            if insight.vector_id is not None:
                self._id_map[insight.vector_id] = insight
    
    def search_insights(
        self,
        query: str,
        tickers: Optional[List[str]] = None,
        intent: Optional[str] = None,
        insight_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[FinancialInsight]:
        """搜索相关金融洞见（轻量实现，使用关键词匹配）
        
        Args:
            query: 搜索查询
            tickers: 股票代码列表（可选，用于精确匹配）
            intent: 意图（可选，用于精确匹配）
            insight_type: 洞见类型过滤（可选）
            top_k: 返回数量
            
        Returns:
            相关金融洞见列表
        """
        if self.vector_store:
            try:
                vector_results = self.vector_store.similarity_search(
                    query, top_k=top_k, insight_type=insight_type
                )
                matched_insights: List[FinancialInsight] = []
                for vector_id, v_type, content, metadata, timestamp, score in vector_results:
                    insight = self._id_map.get(vector_id)
                    if insight is None:
                        insight = FinancialInsight(
                            insight_type=v_type,
                            content=content,
                            metadata=metadata,
                            timestamp=timestamp,
                            vector_id=vector_id,
                        )
                        self._insights.append(insight)
                        self._update_keyword_index(insight, len(self._insights) - 1)
                        self._id_map[vector_id] = insight
                    insight.relevance_score = score
                    insight.update_access()
                    matched_insights.append(insight)
                if matched_insights:
                    return matched_insights[:top_k]
            except Exception as e:
                logger.warning(f"Agentic RAG: 向量检索失败，回退到关键词匹配。原因: {e}")

        matched: List[FinancialInsight] = []
        matched_indices = set()
        
        # 优先匹配：如果有tickers，先通过索引查找
        if tickers:
            for ticker in tickers:
                if ticker in self._keyword_index:
                    for idx in self._keyword_index[ticker]:
                        if idx < len(self._insights):
                            matched_indices.add(idx)
        
        # 优先匹配：如果有intent，通过索引查找
        if intent and intent in self._keyword_index:
            for idx in self._keyword_index[intent]:
                if idx < len(self._insights):
                    matched_indices.add(idx)
        
        # 关键词匹配：在所有洞见中搜索
        query_words = set(query.lower().split())
        
        for idx, insight in enumerate(self._insights):
            if insight_type and insight.insight_type != insight_type:
                continue
            
            # 计算相关性分数
            score = 0.0
            
            # 精确匹配加分（tickers/intent）
            if idx in matched_indices:
                score += 2.0
            
            # 关键词匹配
            content_words = set(insight.content.lower().split())
            match_count = len(query_words & content_words)
            if match_count > 0:
                score += match_count / len(query_words) if query_words else 0
            
            # 使用次数加分
            score += insight.usage_count * 0.1
            
            if score > 0:
                insight.relevance_score = score
                insight.update_access()  # 更新访问时间
                matched.append(insight)
        
        # 按相关性排序，返回top_k
        matched.sort(key=lambda x: (x.relevance_score, x.usage_count), reverse=True)
        return matched[:top_k]
    
    def get_all_insights(self) -> List[FinancialInsight]:
        """获取所有金融洞见"""
        return self._insights.copy()

    def _split_insights(self, predicate) -> Tuple[List[FinancialInsight], List[FinancialInsight]]:
        kept: List[FinancialInsight] = []
        removed: List[FinancialInsight] = []
        for insight in self._insights:
            if predicate(insight):
                kept.append(insight)
            else:
                removed.append(insight)
        return kept, removed

    def _remove_from_vector_store(self, removed: Iterable[FinancialInsight]):
        if not removed:
            return
        if self.vector_store:
            ids = [ins.vector_id for ins in removed if ins.vector_id is not None]
            if ids:
                try:
                    self.vector_store.delete_ids(ids)
                except Exception as e:
                    logger.warning(f"Agentic RAG: 删除向量数据失败: {e}")
            for vector_id in ids:
                if vector_id is not None:
                    self._id_map.pop(vector_id, None)

    def _load_from_vector_store(self):
        if not self.vector_store:
            return
        try:
            entries = self.vector_store.fetch_all()
            for vector_id, insight_type, content, metadata, timestamp in entries:
                insight = FinancialInsight(
                    insight_type=insight_type,
                    content=content,
                    metadata=metadata,
                    timestamp=timestamp,
                    vector_id=vector_id,
                )
                self._insights.append(insight)
            self._rebuild_index()
            logger.info(f"Agentic RAG: 向量存储加载 {len(self._insights)} 条历史洞见")
        except Exception as e:
            logger.warning(f"Agentic RAG: 加载向量存储失败，将回退到内存列表。原因: {e}")
            self.vector_store = None
            self.use_vector_store = False


class FinancialReasoningEngine:
    """金融推理引擎
    
    专门用于金融场景的Agentic RAG推理引擎。
    能够从策略智能体的输出中提取金融洞见，并维护这些洞见作为记忆。
    """
    
    def __init__(self, llm: BaseChatModel, config: Optional[Dict[str, Any]] = None):
        """
        初始化金融推理引擎
        
        Args:
            llm: 大语言模型，用于执行推理
            config: 配置字典（可选）
        """
        self.llm = llm
        self.config = config or {}
        rag_config = self.config.get("agentic_rag", {})
        vector_cfg = rag_config.get("vector_store", {}) if isinstance(rag_config.get("vector_store", {}), dict) else {}
        vector_enabled = vector_cfg.get("enabled", False)
        vector_db_path = vector_cfg.get("db_path")
        embedding_model = vector_cfg.get("model")

        if vector_enabled and vector_db_path:
            project_root = Path(self.config.get("project_root", "."))
            vector_db_path = Path(vector_db_path)
            if not vector_db_path.is_absolute():
                vector_db_path = project_root / vector_db_path
        else:
            vector_db_path = None

        self.memory = FinancialInsightMemory(
            max_insights=rag_config.get("max_insights", 100),
            forget_days=rag_config.get("forget_days", 90),
            use_vector_store=vector_enabled and vector_db_path is not None,
            vector_db_path=vector_db_path,
            embedding_model=embedding_model,
        )
        self.debug = self.config.get("debug", False)
        self.extract_enabled = rag_config.get("extract_insights", True)
    
    def extract_insights(
        self,
        query: str,
        plan: Dict[str, Any],
        data_analysis: str,
        strategy: Dict[str, Any],
        report: str
    ) -> List[FinancialInsight]:
        """从策略智能体的输出中提取金融洞见（轻量prompt）
        
        Args:
            query: 用户查询
            plan: 数据收集计划
            data_analysis: 数据分析报告
            strategy: 投资策略建议
            report: 最终报告
            
        Returns:
            提取的金融洞见列表
        """
        insights = []
        
        # 轻量化prompt：减少token使用
        # 注意：JSON示例中的花括号需要转义，避免被format()解析
        prompt = ChatPromptTemplate.from_messages([
            ("system", """提取金融洞见。类型：market_trend/stock_pattern/risk_factor/strategy_pattern。
**重要**：必须输出JSON数组格式，不要有任何其他文本、思考过程或标记。
输出格式：[{{"insight_type": "类型", "content": "1-2句话", "tickers": ["代码"], "market_condition": "环境", "confidence": 0.0-1.0}}]"""),
            ("user", """查询：{query}
意图：{intent}
股票：{tickers}
策略建议：{recommendation}（置信度：{confidence}）
策略理由：{rationale}
策略报告摘要：{strategy_summary}
数据摘要：{data_summary}

**要求**：从策略报告中提取1-3个关键金融洞见，重点关注：
- 市场趋势洞察（市场整体走势、趋势强度、持续性等）
- 股票模式识别（特定股票的表现模式、资金流向等）
- 风险因素（市场风险、个股风险、技术风险等）
- 策略模式（成功的策略模式、执行要点等）

直接输出JSON数组格式，不要有任何其他文本。格式：[{{"insight_type": "...", "content": "...", "tickers": [...], "market_condition": "...", "confidence": 0.0-1.0}}]""")
        ])
        
        try:
            data_summary = data_analysis[:200] if data_analysis else ""  # 减少到200字符
            # 从策略报告中提取关键信息（优先使用报告摘要）
            strategy_summary = ""
            if report:
                # 提取策略报告的关键部分（市场趋势、策略建议、风险管理等）
                import re
                # 提取市场趋势分析部分
                trend_match = re.search(r'##\s*(?:1\.\s*)?市场趋势分析[\s\S]*?##\s*(?:2\.\s*)?', report, re.IGNORECASE)
                if trend_match:
                    strategy_summary += trend_match.group(0)[:300] + "\n\n"
                # 提取策略建议部分
                strategy_match = re.search(r'##\s*(?:2\.\s*)?(?:超额回报)?策略[\s\S]*?##\s*(?:3\.\s*)?', report, re.IGNORECASE)
                if strategy_match:
                    strategy_summary += strategy_match.group(0)[:300] + "\n\n"
                # 如果没有找到特定部分，使用报告的开头部分
                if not strategy_summary:
                    strategy_summary = report[:500]
            else:
                # 如果没有完整报告，使用策略建议的摘要
                strategy_summary = f"建议: {strategy.get('recommendation', '')}, 理由: {strategy.get('rationale', '')[:200]}"
            
            response = self.llm.invoke(
                prompt.format_messages(
                    query=query,
                    intent=plan.get("intent", ""),
                    tickers=plan.get("tickers", []),
                    recommendation=strategy.get("recommendation", ""),
                    confidence=strategy.get("confidence", 0.0),
                    rationale=strategy.get("rationale", "")[:200],  # 减少到200字符
                    strategy_summary=strategy_summary[:500],  # 策略报告摘要，最多500字符
                    data_summary=data_summary
                )
            )
            
            # 解析LLM返回的JSON
            import json
            import re
            
            # 获取响应内容
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # 记录LLM原始响应（DEBUG级别，用于调试）
            if self.debug:
                logger.debug(f"Agentic RAG: LLM原始响应: {response_content[:500]}")
            
            # 清理思考过程标记（像plan_analyst那样）
            cleaned_response = response_content
            thinking_patterns = [
                r'<thinking>.*?</thinking>',
                r'</?thinking>',
                r'<reasoning>.*?</reasoning>',
                r'</?reasoning>',
                r'</?redacted_reasoning>',
                r'</?think>',
                r'<thought>.*?</thought>',
                r'</?thought>',
            ]
            for pattern in thinking_patterns:
                cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.DOTALL | re.IGNORECASE)
            
            # 尝试提取JSON数组（支持多种格式）
            json_match = None
            insights_data = None
            json_patterns = [
                r'\[[\s\S]*?\]',  # 标准JSON数组
                r'```(?:json)?\s*(\[[\s\S]*?\])[\s\S]*?```',  # 代码块中的JSON数组
                r'```(?:json)?\s*(\{[\s\S]*?\})[\s\S]*?```',  # 代码块中的单个JSON对象（转换为数组）
            ]
            
            for pattern in json_patterns:
                json_match = re.search(pattern, cleaned_response, re.MULTILINE | re.DOTALL)
                if json_match:
                    # 如果有group(1)，使用group(1)，否则使用group()
                    json_str = json_match.group(1) if json_match.lastindex else json_match.group()
                    # 清理可能的markdown代码块标记
                    json_str = re.sub(r'^```(?:json)?\s*\n?', '', json_str, flags=re.MULTILINE)
                    json_str = re.sub(r'\n?```\s*$', '', json_str, flags=re.MULTILINE)
                    json_str = json_str.strip()
                    
                    try:
                        # 尝试解析JSON
                        insights_data = json.loads(json_str)
                        # 如果是单个对象，转换为数组
                        if isinstance(insights_data, dict):
                            insights_data = [insights_data]
                        break
                    except json.JSONDecodeError as e:
                        if self.debug:
                            logger.debug(f"Agentic RAG: JSON解析失败 - {e}, 尝试的JSON字符串: {json_str[:200]}")
                        json_match = None
                        insights_data = None
                        continue
            
            if json_match and insights_data:
                # 处理提取的洞见数据
                for insight_data in insights_data:
                    if not isinstance(insight_data, dict):
                        logger.warning(f"Agentic RAG: 跳过无效的洞见数据（不是字典）: {insight_data}")
                        continue
                    
                    content = insight_data.get("content", "").strip()
                    if not content:
                        logger.warning(f"Agentic RAG: 跳过内容为空的洞见: {insight_data}")
                        continue
                    
                    insight = FinancialInsight(
                        insight_type=insight_data.get("insight_type", "strategy_pattern"),
                        content=content,
                        metadata={
                            "tickers": insight_data.get("tickers", []),
                            "market_condition": insight_data.get("market_condition", ""),
                            "confidence": insight_data.get("confidence", 0.0),
                            "source_query": query,
                            "source_intent": plan.get("intent", ""),
                            "source_strategy": strategy.get("recommendation", ""),
                        },
                        timestamp=datetime.now().isoformat()
                    )
                    insights.append(insight)
                    self.memory.add_insight(insight)
                    
                    # 记录每个提取的洞见（INFO级别）
                    logger.info(f"Agentic RAG: 提取洞见 - [{insight.insight_type}] {insight.content[:100]}...")
                    if insight.metadata.get("tickers"):
                        logger.info(f"  - 相关股票: {insight.metadata['tickers']}")
                    if insight.metadata.get("confidence"):
                        logger.info(f"  - 置信度: {insight.metadata['confidence']:.2f}")
            else:
                # 没有找到JSON数组
                logger.warning(f"Agentic RAG: 无法从LLM响应中提取JSON数组")
                logger.warning(f"  - 清理后的响应前500字符: {cleaned_response[:500]}")
                if self.debug:
                    logger.debug(f"  - 完整响应: {response_content}")
            
            # 总是记录提取结果（INFO级别）
            if insights:
                logger.info(f"Agentic RAG: 成功提取了 {len(insights)} 个金融洞见")
            else:
                logger.warning("Agentic RAG: 未提取到洞见（LLM返回为空、格式不正确或内容为空）")
                if self.debug:
                    logger.debug(f"  - 原始响应: {response_content}")
                    logger.debug(f"  - 清理后响应: {cleaned_response[:500]}")
                
        except RuntimeError as e:
            # 捕获事件循环关闭相关的错误
            if "cannot schedule new futures after shutdown" in str(e) or "Event loop is closed" in str(e):
                logger.warning("Agentic RAG: 事件循环已关闭，跳过洞见提取（这是正常的，当主程序退出时会发生）")
            else:
                logger.error(f"Agentic RAG: 提取金融洞见运行时错误: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            logger.error(f"Agentic RAG: 提取金融洞见失败: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
        
        return insights
    
    def search_relevant_insights(
        self,
        query: str,
        plan: Dict[str, Any],
        top_k: int = 5
    ) -> List[FinancialInsight]:
        """检索相关历史洞见
        
        Args:
            query: 用户查询
            plan: 数据收集计划
            top_k: 返回数量
            
        Returns:
            相关历史洞见列表
        """
        tickers = plan.get("tickers", [])
        intent = plan.get("intent", "")
        
        # 记录检索参数（INFO级别，确保可见）
        logger.info(f"Agentic RAG: 开始检索历史洞见 - 查询: '{query[:50]}...', tickers: {tickers}, intent: '{intent}'")
        
        # 检查当前记忆中的洞见总数
        total_insights = len(self.memory.get_all_insights())
        logger.info(f"Agentic RAG: 当前记忆中共有 {total_insights} 个历史洞见")
        
        relevant_insights = self.memory.search_insights(
            query=query,
            tickers=tickers,
            intent=intent,
            top_k=top_k
        )
        
        # 记录检索结果
        if relevant_insights:
            logger.info(f"Agentic RAG: 检索到 {len(relevant_insights)} 个相关历史洞见")
            for i, insight in enumerate(relevant_insights, 1):
                logger.info(f"  匹配洞见{i}: [{insight.insight_type}] {insight.content[:100]}...")
                if insight.metadata.get("tickers"):
                    logger.info(f"    相关股票: {insight.metadata['tickers']}")
                logger.info(f"    相关性分数: {insight.relevance_score:.2f}, 使用次数: {insight.usage_count}")
        else:
            logger.info(f"Agentic RAG: 未检索到相关历史洞见（查询关键词: '{query}', tickers: {tickers}, intent: '{intent}'）")
        
        return relevant_insights
    
    def format_insights_context(self, insights: List[FinancialInsight]) -> str:
        """格式化历史洞见为上下文字符串
        
        Args:
            insights: 历史洞见列表
            
        Returns:
            格式化的上下文字符串
        """
        if not insights:
            return ""
        
        context_lines = ["## 相关历史洞见\n"]
        for i, insight in enumerate(insights, 1):
            tickers_str = ", ".join(insight.metadata.get("tickers", []))
            market_condition = insight.metadata.get("market_condition", "")
            confidence = insight.metadata.get("confidence", 0.0)
            
            context_lines.append(
                f"{i}. [{insight.insight_type}] {insight.content}"
            )
            if tickers_str:
                context_lines.append(f"   股票：{tickers_str}")
            if market_condition:
                context_lines.append(f"   市场环境：{market_condition}")
            context_lines.append(f"   置信度：{confidence:.2f}")
            context_lines.append("")
        
        return "\n".join(context_lines)
    
    def reason_with_strategy_agent(
        self,
        query: str,
        plan: Dict[str, Any],
        data_analysis: str,
        strategy: Dict[str, Any],
        report: str
    ) -> Dict[str, Any]:
        """与策略智能体结合进行推理（轻量版本）
        
        主要功能：
        1. 提取金融洞见（如果启用）
        2. 检索相关的历史洞见
        
        注意：不再进行策略增强（减少API调用），让策略分析自己决定如何使用历史洞见
        
        Args:
            query: 用户查询
            plan: 数据收集计划
            data_analysis: 数据分析报告
            strategy: 策略智能体生成的策略
            report: 最终报告
        
        Returns:
            包含提取洞见和历史洞见的字典
        """
        # 记录方法调用（INFO级别，确保可见）
        logger.info(f"Agentic RAG: 开始处理策略分析结果（查询: {query[:50]}...）")
        
        insights = []
        
        # 步骤1：提取当前策略的金融洞见（如果启用）
        if self.extract_enabled:
            logger.info("Agentic RAG: 开始提取金融洞见...")
            insights = self.extract_insights(
                query=query,
                plan=plan,
                data_analysis=data_analysis,
                strategy=strategy,
                report=report
            )
            logger.info(f"Agentic RAG: 洞见提取完成，提取了 {len(insights)} 个洞见")
        else:
            logger.info("Agentic RAG: 洞见提取功能已禁用（extract_enabled=false）")
        
        # 步骤2：检索相关的历史洞见
        logger.info("Agentic RAG: 开始检索相关历史洞见...")
        relevant_insights = self.search_relevant_insights(query, plan, top_k=5)
        
        # 打印历史洞见信息（INFO级别）
        if relevant_insights:
            logger.info(f"Agentic RAG: 检索到 {len(relevant_insights)} 个相关历史洞见")
            for i, insight in enumerate(relevant_insights[:3], 1):  # 显示前3个
                logger.info(f"  历史洞见{i}: [{insight.insight_type}] {insight.content[:100]}...")
            if len(relevant_insights) > 3:
                logger.info(f"  ...还有 {len(relevant_insights) - 3} 个历史洞见")
        else:
            logger.info("Agentic RAG: 未检索到相关历史洞见（首次运行或查询不匹配）")
            
        # 打印新生成的洞见信息（INFO级别）
        if self.extract_enabled:
            if insights:
                logger.info(f"Agentic RAG: 本次策略生成后转化成了 {len(insights)} 个新洞见")
                for i, insight in enumerate(insights, 1):
                    logger.info(f"  新洞见{i}: [{insight.insight_type}] {insight.content[:150]}...")
                    if insight.metadata.get("tickers"):
                        logger.info(f"    相关股票: {insight.metadata['tickers']}")
                    if insight.metadata.get("confidence"):
                        logger.info(f"    置信度: {insight.metadata['confidence']:.2f}")
            else:
                logger.info("Agentic RAG: 本次策略生成未提取到新洞见（可能策略内容无新洞察）")
        
        total_insights = len(self.memory.get_all_insights())
        logger.info(f"Agentic RAG: 处理完成，当前总洞见数: {total_insights}")
        
        return {
            "extracted_insights": [insight.to_dict() for insight in insights],
            "relevant_insights": [insight.to_dict() for insight in relevant_insights],
            "insights_context": self.format_insights_context(relevant_insights),
            "insight_count": total_insights,
        }
    
    def get_insights_summary(self) -> Dict[str, Any]:
        """获取洞见统计摘要"""
        all_insights = self.memory.get_all_insights()
        
        type_counts = {}
        for insight in all_insights:
            type_counts[insight.insight_type] = type_counts.get(insight.insight_type, 0) + 1
        
        return {
            "total_insights": len(all_insights),
            "by_type": type_counts,
            "most_used": sorted(
                all_insights,
                key=lambda x: x.usage_count,
                reverse=True
            )[:5],
        }