from typing import List, Callable, Dict
from pydantic import BaseModel
from .generay_tool_base import GeneralToolBase
from datetime import datetime
import ast
import operator
from holisticaquant.dataflows.utils.general_tool_utils import eval_expr


class CalculatorTool(GeneralToolBase):
    """计算工具
    
    用于执行数学计算，这在处理数据分析类问题时很有用。
    """
    name: str = "calculator"
    description: str = "执行数学计算，支持基本运算和科学计算"
    
    async def execute(self, expression: str):
        """安全地计算数学表达式
        
        使用 AST（抽象语法树）来安全地计算表达式，
        避免执行任意代码的安全风险。
        
        Args:
            expression: 数学表达式字符串（如 "2 + 3 * 4"）
            
        Returns:
            包含计算结果或错误的字典
        """
        # 定义允许的操作符
        allowed_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow
        }
        
        # 安全地解析和计算表达式
        try:
            tree = ast.parse(expression, mode='eval')
            result = eval_expr(tree.body, allowed_ops)
            return {"result": result, "expression": expression}
        except Exception as e:
            return {"error": str(e), "expression": expression}