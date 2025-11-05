"""
Agent结构化输出Schema定义

使用Pydantic模型定义各个agent的结构化输出格式，确保类型安全和解析鲁棒性
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class PlanSchema(BaseModel):
    """PlanAnalyst的结构化输出（简化版）"""
    
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

