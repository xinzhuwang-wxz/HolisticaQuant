from typing import List, Callable, Dict
from pydantic import BaseModel
from .generay_tool_base import GeneralToolBase
from datetime import datetime
from holisticaquant.dataflows.utils.general_tool_utils import (
    search_api,
    clean_search_result
)


class SearchTool(GeneralToolBase):
    """
    搜索工具
    
    用于在互联网上搜索信息
    """
    name: str = "web_search"
    description: str = "搜索工具，用于在互联网上搜索信息"

    async def execute(self, query: str):
        """执行搜索工具
        
        这个方法会：
        1. 调用搜索API
        2. 解析API返回的数据
        3. 提取相关信息
        4. 返回结构化数据
        
        Args:
            query: 搜索查询字符串
            
        Returns:
            包含搜索结果的结构化数据
        """
        # 调用搜索API（search_api是同步函数，但返回结果很快）
        result = search_api(query)
        
        # 清理和格式化结果
        cleaned_result = clean_search_result(result)

        return {
            "tool_name": self.name,
            "query": query,
            "results": cleaned_result,
            "count": len(cleaned_result),
            "timestamp": datetime.now().isoformat()
        }