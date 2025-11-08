"""
Agent结构化输出Schema定义

使用Pydantic模型定义各个agent的结构化输出格式，确保类型安全和解析鲁棒性
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class PlanSchema(BaseModel):
    """PlanAnalyst的结构化输出（简化版）"""
    
    scenario_type: Literal["learning_workshop", "research_lab", "assistant"] = Field(
        default="research_lab",
        description="场景类型：learning_workshop（场景化学习工坊）、research_lab（全流程投研实验室）、assistant（AI 智能陪伴问答）"
    )
    target_id: Optional[str] = Field(
        default=None,
        description="针对特定场景的目标ID，例如学习工坊的知识点ID或投研实验室的模板ID"
    )
    tickers: List[str] = Field(
        default_factory=list,
        description="股票代码列表（6位数字）。从用户查询中提取或通过web_search搜索获得。"
    )
    time_range: Literal["last_7d", "last_30d", "last_90d"] = Field(
        default="last_30d",
        description="时间范围。从用户查询中推断，或使用默认值last_30d。"
    )
    
    # 向后兼容字段（可选，有默认值）
    intent: Optional[str] = Field(
        default="投资分析",
        description="需求意图（用于向后兼容，默认'投资分析'）"
    )
    data_sources: Optional[List[Literal["market", "fundamental", "news", "hot_money"]]] = Field(
        default_factory=lambda: ["market", "fundamental", "news"],
        description="数据源列表（用于向后兼容，默认['market', 'fundamental', 'news']）"
    )
    focus_areas: Optional[List[str]] = Field(
        default_factory=lambda: ["基本面", "技术面"],
        description="重点关注领域（用于向后兼容，默认['基本面', '技术面']）"
    )
    priority: Optional[Literal["high", "medium", "low"]] = Field(
        default=None,
        description="优先级（可选，用于向后兼容）"
    )
    estimated_complexity: Optional[Literal["simple", "complex"]] = Field(
        default=None,
        description="预估复杂度（可选，用于向后兼容）"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "scenario_type": "research_lab",
                "target_id": "tesla_equity_valuation_2025",
                "tickers": ["601857"],
                "time_range": "last_30d"
            }
        }


class DataSufficiencySchema(BaseModel):
    """DataAnalyst的数据充分性评估结构化输出"""
    
    sufficient: bool = Field(description="数据是否充足")
    missing_data: List[str] = Field(
        default_factory=list,
        description="缺失的数据类型列表"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="数据充分性置信度，范围0.0-1.0"
    )
    reason: str = Field(
        description="数据充分性评估的详细说明"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "sufficient": True,
                "missing_data": [],
                "confidence": 0.8,
                "reason": "已收集到足够的数据进行分析"
            }
        }


class StrategySchema(BaseModel):
    """StrategyAnalyst的投资建议结构化输出"""
    
    recommendation: Literal["buy", "sell", "hold", "analyze"] = Field(
        description="投资建议"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="置信度，范围0.0-1.0"
    )
    target_price: Optional[str] = Field(
        default=None,
        description="目标价位（如有）"
    )
    position_suggestion: Optional[str] = Field(
        default=None,
        description="仓位建议（如适用）"
    )
    time_horizon: Literal["短期", "中期", "长期"] = Field(
        description="时间周期"
    )
    rationale: str = Field(
        description="详细策略理由"
    )
    entry_conditions: List[str] = Field(
        default_factory=list,
        description="入场条件列表"
    )
    exit_conditions: List[str] = Field(
        default_factory=list,
        description="出场条件列表"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "recommendation": "buy",
                "confidence": 0.75,
                "target_price": "10.5元",
                "position_suggestion": "总资金的15%",
                "time_horizon": "短期",
                "rationale": "基于技术面和基本面分析，建议买入",
                "entry_conditions": ["股价回调至10.0元附近", "成交量温和放大"],
                "exit_conditions": ["股价跌破9.5元止损位", "成交量突然放大但股价滞涨"]
            }
        }


class LearningWorkshopSchema(BaseModel):
    """LearningWorkshopAgent的结构化输出"""
    
    scenario_id: str = Field(description="学习场景ID，对应配置库中的唯一标识")
    knowledge_point: str = Field(description="当前学习的知识点名称")
    learning_objectives: List[str] = Field(
        description="本次学习的核心目标",
        default_factory=list
    )
    scenario_summary: str = Field(description="场景背景与关键说明")
    key_data_points: List[str] = Field(
        description="场景中需要关注的关键数据点摘要",
        default_factory=list
    )
    task_steps: List[str] = Field(
        description="完成任务所需的步骤（逐步指导）",
        default_factory=list
    )
    calculator_inputs: List[str] = Field(
        description="需要在内置计算器中输入的参数说明",
        default_factory=list
    )
    expected_result: str = Field(description="任务预期结果或答案")
    validation_logic: str = Field(description="验证结论的逻辑说明，包含数据来源")
    ai_guidance: str = Field(description="AI 陪伴式总结与下一步建议")
    
    class Config:
        json_schema_extra = {
            "example": {
                "scenario_id": "blockchain_cbdc",
                "knowledge_point": "区块链支付 / CBDC",
                "learning_objectives": [
                    "理解CBDC试点的目标与范围",
                    "学会用收入增长率衡量数字化业务提升"
                ],
                "scenario_summary": "2025年中国央行在重点城市推动CBDC试点，聚焦跨境支付效率。",
                "key_data_points": [
                    "试点城市：上海、深圳、雄安等11城",
                    "用户规模：超过1亿规模用户开通CBDC钱包"
                ],
                "task_steps": [
                    "阅读CBDC试点核心数据",
                    "在计算器输入试点前后收入数据",
                    "计算并解释增长率"
                ],
                "calculator_inputs": [
                    "试点前收入：10亿元",
                    "试点后收入：12亿元"
                ],
                "expected_result": "数字化业务收入增长率 = (12-10)/10 = 20%",
                "validation_logic": "结合2025Q1财报披露的数据，说明收入增长与CBDC提升体验的关系。",
                "ai_guidance": "增长率合理，下一步可讨论支付效率与客户留存指标。"
            }
        }


class AssistantAnswerSchema(BaseModel):
    """SimpleAnswerAgent的结构化输出"""
    
    scenario_context: str = Field(description="当前问题所处的场景说明")
    answer: str = Field(description="给用户的直接回答")
    supporting_points: List[str] = Field(
        description="支持回答的关键数据或逻辑",
        default_factory=list
    )
    recommended_next_actions: List[str] = Field(
        description="建议用户进行的后续动作",
        default_factory=list
    )
    data_sources: List[str] = Field(
        description="引用的数据来源或参考信息",
        default_factory=list
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "scenario_context": "全流程投研实验室 - 特斯拉估值作业",
                "answer": "特斯拉当前PE约为20，属于行业偏高区间。",
                "supporting_points": [
                    "当前股价约200美元，每股收益约10美元 → PE=20",
                    "行业平均PE约15 → 高于行业均值"
                ],
                "recommended_next_actions": [
                    "结合PEG指标评估成长性：PEG≈0.8",
                    "跟踪销量增长是否符合25%的预期"
                ],
                "data_sources": [
                    "新浪财经 2025-04-01 行情",
                    "行业PE均值：内部资料（彭博行业研究 2025Q1）"
                ]
            }
        }

