"""
通用工具函数模块

提供数据库、计算、搜索等通用工具函数的实现
"""

import warnings
# 全局抑制duckduckgo_search包重命名警告
warnings.filterwarnings("ignore", message=".*renamed.*", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*", category=RuntimeWarning)

import re
import ast
import operator
from typing import Any, Dict, List, Optional
import pandas as pd
from loguru import logger


# ==================== 数据库工具函数 ====================

def is_safe_query(sql: str) -> bool:
    """
    SQL安全验证函数
    
    检查SQL查询是否安全：
    - 只允许SELECT语句
    - 禁止危险操作（DROP、DELETE、UPDATE、INSERT等）
    - 检查SQL注入风险
    
    Args:
        sql: SQL查询字符串
        
    Returns:
        如果是安全查询返回True，否则返回False
    """
    if not sql or not isinstance(sql, str):
        return False
    
    # 转换为大写进行检查
    sql_upper = sql.upper().strip()
    
    # 检查是否包含危险关键词
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 
        'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE', 'CALL'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            logger.warning(f"检测到危险SQL关键词: {keyword}")
            return False
    
    # 只允许SELECT语句
    if not sql_upper.startswith('SELECT'):
        logger.warning("SQL查询必须以SELECT开头")
        return False
    
    # 检查是否有SQL注入风险（注释、分号等）
    injection_patterns = [
        r'--',  # SQL注释
        r'/\*.*?\*/',  # 多行注释
        r';',  # 多个语句分隔符
        r'UNION.*SELECT',  # UNION注入
        r'OR.*=.*',  # OR注入
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE | re.DOTALL):
            logger.warning(f"检测到可能的SQL注入模式: {pattern}")
            return False
    
    return True


def format_results(results: Any) -> str:
    """
    格式化数据库查询结果
    
    将查询结果转换为字符串格式，支持多种数据类型
    
    Args:
        results: 查询结果（可以是DataFrame、列表、字典等）
        
    Returns:
        格式化后的字符串
    """
    if results is None:
        return "查询结果为空"
    
    # DataFrame格式
    if isinstance(results, pd.DataFrame):
        if results.empty:
            return "查询结果为空"
        
        # 限制显示行数
        max_rows = 50
        display_df = results.head(max_rows)
        
        lines = [f"查询结果（共 {len(results)} 行，显示前 {len(display_df)} 行）：\n"]
        lines.append(display_df.to_string())
        
        if len(results) > max_rows:
            lines.append(f"\n... 还有 {len(results) - max_rows} 行未显示")
        
        return "\n".join(lines)
    
    # 列表格式
    if isinstance(results, list):
        if not results:
            return "查询结果为空"
        
        lines = [f"查询结果（共 {len(results)} 条）：\n"]
        for i, item in enumerate(results[:50], 1):
            if isinstance(item, dict):
                lines.append(f"\n【记录 {i}】")
                for key, value in item.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append(f"{i}. {item}")
        
        if len(results) > 50:
            lines.append(f"\n... 还有 {len(results) - 50} 条未显示")
        
        return "\n".join(lines)
    
    # 字典格式
    if isinstance(results, dict):
        lines = ["查询结果：\n"]
        for key, value in results.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    # 其他类型，直接转换为字符串
    return str(results)


# ==================== 计算工具函数 ====================

def eval_expr(node: ast.AST, allowed_ops: Dict[type, Any]) -> Any:
    """
    AST表达式求值函数
    
    安全地计算AST节点，只允许使用allowed_ops中定义的操作符
    
    Args:
        node: AST节点
        allowed_ops: 允许的操作符字典，格式为 {ast.Add: operator.add, ...}
        
    Returns:
        计算结果
        
    Raises:
        ValueError: 如果遇到不允许的操作或节点类型
    """
    # 数字常量
    if isinstance(node, ast.Constant):
        return node.value
    
    # 支持旧版本的ast.Num（Python < 3.8）
    if isinstance(node, ast.Num):
        return node.n
    
    # 二元运算
    if isinstance(node, ast.BinOp):
        left = eval_expr(node.left, allowed_ops)
        right = eval_expr(node.right, allowed_ops)
        
        # 检查操作符是否允许
        op_type = type(node.op)
        if op_type not in allowed_ops:
            raise ValueError(f"不允许的操作符: {op_type.__name__}")
        
        op_func = allowed_ops[op_type]
        return op_func(left, right)
    
    # 一元运算（正负号）
    if isinstance(node, ast.UnaryOp):
        operand = eval_expr(node.operand, allowed_ops)
        
        if isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
        else:
            raise ValueError(f"不允许的一元操作符: {type(node.op).__name__}")
    
    # 变量名（不允许）
    if isinstance(node, ast.Name):
        raise ValueError(f"不允许使用变量: {node.id}")
    
    # 函数调用（不允许）
    if isinstance(node, ast.Call):
        raise ValueError("不允许函数调用")
    
    # 其他类型不允许
    raise ValueError(f"不允许的AST节点类型: {type(node).__name__}")


# ==================== 搜索工具函数 ====================

def search_api(query: str) -> Dict[str, Any]:
    """
    搜索API调用函数
    
    调用搜索API获取搜索结果
    
    Args:
        query: 搜索查询字符串
        
    Returns:
        搜索结果字典，包含原始API响应
    """
    try:
        # 尝试使用ddgs（duckduckgo-search已重命名为ddgs）
        # 警告已在模块级别抑制
        try:
            # 优先尝试新包名ddgs
            try:
                # 在导入时抑制警告
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=RuntimeWarning)
                    from ddgs import DDGS
            except ImportError:
                # 向后兼容：尝试旧包名duckduckgo_search
                # 在导入时抑制警告
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=RuntimeWarning)
                    from duckduckgo_search import DDGS
                    logger.debug("使用旧包名duckduckgo_search，建议升级到ddgs: pip install ddgs")
            
            results = []
            try:
                # 在实例化DDGS时也抑制警告
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=RuntimeWarning)
                    with DDGS() as ddgs_instance:
                        search_results = ddgs_instance.text(query, max_results=10)
                        
                        # ddgs.text()返回生成器，需要检查是否为空
                        if search_results is None:
                            logger.debug(f"搜索API返回None，查询: {query}（可能是网络问题或API限制）")
                            return {
                                'status': 'no_results',
                                'query': query,
                                'results': [],
                                'count': 0,
                                'message': '搜索API暂时不可用，可能是网络问题或API限制'
                            }
                        
                        # 尝试迭代生成器获取结果
                        try:
                            for result in search_results:
                                if result:  # 确保result不为None
                                    results.append({
                                        'title': result.get('title', ''),
                                        'url': result.get('href', ''),
                                        'snippet': result.get('body', '')
                                    })
                        except StopIteration:
                            # 生成器为空，这是正常的
                            pass
                        except Exception as iter_error:
                            # 迭代时出错，可能是网络问题或API限制
                            logger.debug(f"搜索迭代失败: {str(iter_error)}，查询: {query}")
                            # 如果已经有部分结果，返回部分结果；否则返回空结果
                            if not results:
                                return {
                                    'status': 'no_results',
                                    'query': query,
                                    'results': [],
                                    'count': 0,
                                    'message': f'搜索迭代失败: {str(iter_error)}'
                                }
                
                if not results:
                    logger.debug(f"搜索未返回结果，查询: {query}")
                    return {
                        'status': 'no_results',
                        'query': query,
                        'results': [],
                        'count': 0,
                        'message': '搜索未找到相关结果'
                    }
                
                return {
                    'status': 'success',
                    'query': query,
                    'results': results,
                    'count': len(results)
                }
            except Exception as api_error:
                # 搜索失败不影响主流程，使用DEBUG级别
                # 捕获详细的异常信息以便调试
                error_msg = str(api_error)
                error_type = type(api_error).__name__
                logger.debug(f"搜索API调用失败 [{error_type}]: {error_msg}，查询: {query}")
                
                # 分析常见错误原因
                if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                    reason = '网络超时'
                elif 'rate limit' in error_msg.lower() or '429' in error_msg:
                    reason = 'API速率限制'
                elif 'connection' in error_msg.lower() or 'network' in error_msg.lower():
                    reason = '网络连接问题'
                elif 'none' in error_msg.lower() or 'null' in error_msg.lower():
                    reason = 'API返回空结果'
                else:
                    reason = '未知错误'
                
                return {
                    'status': 'no_results',
                    'query': query,
                    'results': [],
                    'count': 0,
                    'message': f'搜索暂时不可用（{reason}）'
                }
        except ImportError:
            logger.warning("ddgs或duckduckgo-search未安装，使用占位实现")
            # 占位实现
            return {
                'status': 'placeholder',
                'query': query,
                'results': [],
                'count': 0,
                'message': '搜索功能需要安装ddgs: pip install ddgs（或pip install duckduckgo-search作为向后兼容）'
            }
    except Exception as e:
        logger.error(f"搜索API调用失败: {e}")
        return {
            'status': 'error',
            'query': query,
            'results': [],
            'count': 0,
            'error': str(e)
        }


def clean_search_result(result: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    清理搜索结果
    
    提取标题、链接、摘要等关键信息，格式化为结构化数据
    
    Args:
        result: 搜索API返回的原始结果
        
    Returns:
        清理后的搜索结果列表，每个元素包含title、url、snippet字段
    """
    if not result or result.get('status') != 'success':
        return []
    
    cleaned_results = []
    raw_results = result.get('results', [])
    
    for item in raw_results:
        cleaned_item = {
            'title': item.get('title', '无标题'),
            'url': item.get('url', ''),
            'snippet': item.get('snippet', '')[:200]  # 限制摘要长度
        }
        cleaned_results.append(cleaned_item)
    
    return cleaned_results
