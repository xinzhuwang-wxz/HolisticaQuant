from typing import List, Callable, Dict
from pydantic import BaseModel
from .generay_tool_base import GeneralToolBase
from datetime import datetime
from holisticaquant.dataflows.utils.general_tool_utils import (
    is_safe_query,
    format_results
)
from loguru import logger


class DatabaseTool(GeneralToolBase):
    """数据库查询工具
    
    这个工具可以查询内部数据库，获取结构化数据。
    注意：需要配置数据库连接才能使用。
    """
    name: str = "db_query"
    description: str = "查询数据库"
    
    def __init__(self, db_connection=None, **kwargs):
        """初始化数据库工具
        
        Args:
            db_connection: 数据库连接对象（可选）
        """
        super().__init__(**kwargs)
        self.db_connection = db_connection
    
    async def execute(self, sql: str):
        """安全地执行 SQL 查询
        
        Args:
            sql: SQL查询语句（仅支持SELECT）
            
        Returns:
            格式化的查询结果
        """
        # 验证 SQL 安全性
        if not is_safe_query(sql):
            raise ValueError("Unsafe SQL query detected")
        
        # 执行查询
        if self.db_connection is None:
            logger.warning("数据库连接未配置，返回占位结果")
            return format_results("数据库连接未配置，请先配置数据库连接")
        
        try:
            # 假设数据库连接对象有execute方法
            # 实际使用时需要根据具体的数据库连接库调整
            if hasattr(self.db_connection, 'execute'):
                results = await self.db_connection.execute(sql)
            else:
                # 如果是同步连接，使用同步执行
                results = self.db_connection.execute(sql)
        
        # 格式化结果
            return format_results(results)
        except Exception as e:
            logger.error(f"数据库查询失败: {e}")
            raise ValueError(f"数据库查询失败: {e}")