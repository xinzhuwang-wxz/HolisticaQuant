from typing import List, Callable, Dict
from pydantic import BaseModel


class GeneralToolBase(BaseModel):
    """
    通用工具基类
    """
    name: str
    description: str
    parameters: Dict

    async def execute(self, **kwargs):
        """执行工具的异步方法"""
        raise NotImplementedError

