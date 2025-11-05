"""
Agent工具模块

将 holisticaquant/dataflows/datasource 中的数据源封装成 LangChain @tool 工具

数据源分类：
- 被动工具：自动获取排行榜数据（不需要查询参数）
  - get_sina_news: 获取新浪财经新闻
  - get_thx_news: 获取同花顺新闻
  - get_market_data: 获取市场数据（指数、板块资金流）
  - get_hot_money: 获取热门资金流数据（涨停、跌停、龙虎榜等）

- 主动工具：根据查询参数获取特定数据（需要 ticker 参数）
  - get_stock_fundamental: 获取股票基本面数据
  - get_stock_market_data: 获取股票市场数据（实时行情、K线）

- 通用工具
  - calculator: 执行数学计算
  - web_search: 网络搜索
  - db_query: 数据库查询（需要配置数据库连接）

"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from loguru import logger
import pandas as pd
import json

# 导入数据源
from holisticaquant.dataflows.datasource import (
    SinaNewsCrawl,
    ThxNewsCrawl,
    MarketDataAkshare,
    HotMoneyAkshare,
    StockFundamentalAkshare,
    StockMarketDataAkshare,
    HAS_AKSHARE_SOURCES,
    HAS_AKSHARE_ACTIVE_SOURCES,
)

# 导入通用工具
from holisticaquant.dataflows.general import (
    CalculatorTool,
    SearchTool,
    DatabaseTool,
)

# 工具配置常量（默认值，会被配置覆盖）
USE_CACHE = False  # 默认不使用缓存，获取最新数据
MAX_RECORDS = 50   # 每个工具返回的最大记录数

def _get_tool_config() -> Dict[str, Any]:
    """从配置读取工具配置"""
    try:
        from holisticaquant.config.config import get_config
        config = get_config().config
        return config.get("tools", {})
    except Exception:
        return {}

def _get_max_records() -> int:
    """从配置读取最大记录数"""
    tool_config = _get_tool_config()
    return tool_config.get("max_records", MAX_RECORDS)

def _get_sina_news_config() -> Dict[str, Any]:
    """从配置读取新浪新闻配置"""
    tool_config = _get_tool_config()
    sina_config = tool_config.get("news", {}).get("sina", {})
    return {
        "enabled": sina_config.get("enabled", True),
        "end_page": sina_config.get("end_page", 3),
    }

def _get_thx_news_config() -> Dict[str, Any]:
    """从配置读取同花顺新闻配置"""
    tool_config = _get_tool_config()
    thx_config = tool_config.get("news", {}).get("thx", {})
    return {
        "enabled": thx_config.get("enabled", True),
        "max_pages": thx_config.get("max_pages", 2),
    }


def _format_dataframe_for_llm(df: pd.DataFrame, max_records: int = None) -> str:
    """
    将DataFrame格式化为LLM可读的字符串
    
    Args:
        df: 数据源返回的DataFrame
        max_records: 最大记录数
        
    Returns:
        格式化的字符串
    """
    if df.empty:
        return "未获取到数据"
    
    max_records = max_records or _get_max_records()
    
    # 限制记录数
    df_display = df.head(max_records)
    
    # 格式化输出
    lines = [f"共获取 {len(df)} 条记录（显示前 {len(df_display)} 条）：\n"]
    
    for idx, row in df_display.iterrows():
        lines.append(f"\n【记录 {idx + 1}】")
        lines.append(f"标题: {row.get('title', 'N/A')}")
        lines.append(f"发布时间: {row.get('pub_time', 'N/A')}")
        content = str(row.get('content', 'N/A'))
        # 限制content长度
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"内容: {content}")
        url = row.get('url', 'N/A')
        if url and url != 'N/A':
            lines.append(f"链接: {url}")
    
    return "\n".join(lines)


# 优化：使用线程本地存储的事件循环，减少创建开销
_thread_local_loop = None

def _run_async(coro):
    """
    在同步环境中运行异步函数（优化版本）
    
    优化策略：
    1. 优先使用线程本地事件循环，避免重复创建
    2. 如果没有运行中的事件循环，创建线程本地循环
    3. 如果已有事件循环，使用 nest_asyncio 或新线程
    
    Args:
        coro: 协程对象
        
    Returns:
        协程的返回值
    """
    import threading
    
    try:
        # 尝试获取运行中的事件循环
        loop = asyncio.get_running_loop()
        # 如果已经在事件循环中运行，需要使用 nest_asyncio 或新线程
        try:
            import nest_asyncio
            # nest_asyncio 只需应用一次（会自动检查）
            nest_asyncio.apply(loop)
            return loop.run_until_complete(coro)
        except (ImportError, AttributeError):
            # 如果没有 nest_asyncio 或方法不存在，在新线程中运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=300)  # 5分钟超时
    except RuntimeError:
        # 如果没有运行中的事件循环，使用线程本地循环（如果可用）
        thread_id = threading.current_thread().ident
        global _thread_local_loop
        
        # 每个线程使用自己的事件循环，避免线程安全问题
        try:
            return asyncio.run(coro)
        except RuntimeError:
            # 如果当前线程已有事件循环但未运行，创建新线程
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=300)


def _get_trigger_time(trigger_time: Optional[str] = None) -> str:
    """
    获取触发时间字符串
    
    Args:
        trigger_time: 指定的触发时间，None则使用当前时间
        
    Returns:
        格式化的时间字符串 'YYYY-MM-DD HH:MM:SS'
    """
    if trigger_time:
        return trigger_time
    return datetime.now().strftime('%Y-%m-%d %H:00:00')


# ==================== 被动工具 ====================

@tool
def get_sina_news(trigger_time: Optional[str] = None) -> str:
    """
    获取新浪财经新闻数据
    
    这是被动工具，会自动获取最新的财经新闻排行榜数据。
    
    Args:
        trigger_time: 触发时间（格式：'YYYY-MM-DD HH:MM:SS'），默认为当前时间
        
    Returns:
        格式化的新闻数据字符串，包含标题、内容、发布时间等信息
    """
    try:
        sina_config = _get_sina_news_config()
        if not sina_config["enabled"]:
            return "新浪新闻工具已禁用"
        
        trigger_time_str = _get_trigger_time(trigger_time)
        source = SinaNewsCrawl(
            start_page=1,
            end_page=sina_config["end_page"],
            use_cache=USE_CACHE,
            max_records=_get_max_records()
        )
        
        # 运行异步方法
        df = _run_async(source.fetch_data_async(trigger_time_str))
        
        return _format_dataframe_for_llm(df)
    except Exception as e:
        error_msg = f"获取新浪新闻失败: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def get_thx_news(trigger_time: Optional[str] = None) -> str:
    """
    获取同花顺新闻数据
    
    这是被动工具，会自动获取最新的同花顺财经新闻排行榜数据。
    
    Args:
        trigger_time: 触发时间（格式：'YYYY-MM-DD HH:MM:SS'），默认为当前时间
        
    Returns:
        格式化的新闻数据字符串，包含标题、内容、发布时间等信息
    """
    try:
        thx_config = _get_thx_news_config()
        if not thx_config["enabled"]:
            return "同花顺新闻工具已禁用"
        
        trigger_time_str = _get_trigger_time(trigger_time)
        source = ThxNewsCrawl(
            use_cache=USE_CACHE,
            max_records=_get_max_records(),
            max_pages=thx_config["max_pages"]
        )
        
        df = _run_async(source.fetch_data_async(trigger_time_str))
        
        return _format_dataframe_for_llm(df)
    except Exception as e:
        error_msg = f"获取同花顺新闻失败: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def get_market_data(trigger_time: Optional[str] = None) -> str:
    """
    获取市场数据（指数K线、板块资金流等）
    
    这是被动工具，会自动获取最新的市场数据，包括：
    - 三大指数（上证、深证、创业板）的K线数据
    - 板块资金流向数据（前20名）
    - 市场整体概况
    
    Args:
        trigger_time: 触发时间（格式：'YYYY-MM-DD HH:MM:SS'），默认为当前时间
        
    Returns:
        格式化的市场数据字符串
    """
    if not HAS_AKSHARE_SOURCES:
        return "错误: akshare 未安装，无法获取市场数据"
    
    try:
        trigger_time_str = _get_trigger_time(trigger_time)
        source = MarketDataAkshare(
            use_cache=USE_CACHE,
            max_records=_get_max_records()
        )
        
        df = _run_async(source.fetch_data_async(trigger_time_str))
        
        return _format_dataframe_for_llm(df)
    except Exception as e:
        error_msg = f"获取市场数据失败: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def get_hot_money(trigger_time: Optional[str] = None) -> str:
    """
    获取热门资金流数据（涨停、跌停、龙虎榜、概念板块等）
    
    这是被动工具，会自动获取最新的热门资金流数据，包括：
    - 涨停股票列表
    - 跌停股票列表
    - 龙虎榜股票数据
    - 概念板块资金流向
    - 机构参与股票数据
    
    Args:
        trigger_time: 触发时间（格式：'YYYY-MM-DD HH:MM:SS'），默认为当前时间
        
    Returns:
        格式化的热门资金流数据字符串
    """
    if not HAS_AKSHARE_SOURCES:
        return "错误: akshare 未安装，无法获取热门资金流数据"
    
    try:
        trigger_time_str = _get_trigger_time(trigger_time)
        source = HotMoneyAkshare(
            use_cache=USE_CACHE,
            max_records=_get_max_records()
        )
        
        df = _run_async(source.fetch_data_async(trigger_time_str))
        
        return _format_dataframe_for_llm(df)
    except Exception as e:
        error_msg = f"获取热门资金流数据失败: {e}"
        logger.error(error_msg)
        return error_msg


# ==================== 主动工具 ====================

@tool
def get_stock_fundamental(ticker: str, trigger_time: Optional[str] = None) -> str:
    """
    获取股票基本面数据
    
    这是主动工具，需要提供股票代码（ticker）参数。
    获取指定股票的基本面数据，包括：
    - 股票基本信息（代码、名称、市值、市盈率等）
    - 财务指标（营收、净利润、ROE等）
    
    Args:
        ticker: 股票代码（如：'000001'、'600000'、'sz000001'等，支持多种格式）
        trigger_time: 触发时间（格式：'YYYY-MM-DD HH:MM:SS'），默认为当前时间
        
    Returns:
        格式化的股票基本面数据字符串
    """
    if not HAS_AKSHARE_ACTIVE_SOURCES:
        return "错误: akshare 未安装，无法获取股票基本面数据"
    
    if not ticker:
        return "错误: 必须提供股票代码（ticker）参数"
    
    try:
        trigger_time_str = _get_trigger_time(trigger_time)
        source = StockFundamentalAkshare(
            use_cache=USE_CACHE
        )
        
        df = _run_async(source.fetch_data_async(trigger_time_str, ticker=ticker))
        
        return _format_dataframe_for_llm(df)
    except Exception as e:
        error_msg = f"获取股票基本面数据失败（ticker={ticker}）: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def get_stock_market_data(ticker: str, trigger_time: Optional[str] = None) -> str:
    """
    获取股票市场数据（实时行情、K线等）
    
    这是主动工具，需要提供股票代码（ticker）参数。
    获取指定股票的市场数据，包括：
    - 实时行情（价格、涨跌幅、成交量等）
    - K线数据（开高低收、成交量）
    
    Args:
        ticker: 股票代码（如：'000001'、'600000'、'sz000001'等，支持多种格式）
        trigger_time: 触发时间（格式：'YYYY-MM-DD HH:MM:SS'），默认为当前时间
        
    Returns:
        格式化的股票市场数据字符串
    """
    if not HAS_AKSHARE_ACTIVE_SOURCES:
        return "错误: akshare 未安装，无法获取股票市场数据"
    
    if not ticker:
        return "错误: 必须提供股票代码（ticker）参数"
    
    try:
        trigger_time_str = _get_trigger_time(trigger_time)
        source = StockMarketDataAkshare(
            use_cache=USE_CACHE
        )
        
        df = _run_async(source.fetch_data_async(trigger_time_str, ticker=ticker))
        
        return _format_dataframe_for_llm(df)
    except Exception as e:
        error_msg = f"获取股票市场数据失败（ticker={ticker}）: {e}"
        logger.error(error_msg)
        return error_msg


# ==================== 通用工具 ====================

@tool
def calculator(expression: str) -> str:
    """
    执行数学计算工具
    
    安全地计算数学表达式，支持基本运算（加减乘除、幂运算）。
    使用AST（抽象语法树）来安全地计算表达式，避免执行任意代码。
    
    Args:
        expression: 数学表达式字符串（如 "2 + 3 * 4"、"10 / 2"、"2 ** 3"）
        
    Returns:
        计算结果字符串，如果出错则返回错误信息
    """
    try:
        calc_tool = CalculatorTool(
            name="calculator",
            description="执行数学计算",
            parameters={}
        )
        
        # 运行异步方法
        result = _run_async(calc_tool.execute(expression))
        
        # 格式化返回结果
        if isinstance(result, dict):
            if "error" in result:
                return f"计算错误: {result['error']}\n表达式: {result.get('expression', '')}"
            elif "result" in result:
                return f"计算结果: {result['result']}\n表达式: {result.get('expression', '')}"
        
        return str(result)
    except Exception as e:
        error_msg = f"计算工具执行失败: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def web_search(query: str) -> str:
    """
    网络搜索工具
    
    在互联网上搜索信息，返回相关的搜索结果。
    
    Args:
        query: 搜索查询字符串
        
    Returns:
        格式化的搜索结果字符串，包含标题、链接、摘要等信息
    """
    try:
        search_tool = SearchTool(
            name="web_search",
            description="网络搜索",
            parameters={}
        )
        
        # 运行异步方法
        result = _run_async(search_tool.execute(query))
        
        # 格式化返回结果
        if isinstance(result, dict):
            results = result.get("results", [])
            if not results:
                return f"未找到与 '{query}' 相关的搜索结果"
            
            lines = [f"搜索查询: {query}\n找到 {len(results)} 条结果:\n"]
            for i, item in enumerate(results, 1):
                lines.append(f"\n【结果 {i}】")
                lines.append(f"标题: {item.get('title', 'N/A')}")
                lines.append(f"链接: {item.get('url', 'N/A')}")
                snippet = item.get('snippet', '')
                if snippet:
                    lines.append(f"摘要: {snippet}")
            
            return "\n".join(lines)
        
        return str(result)
    except Exception as e:
        error_msg = f"搜索工具执行失败: {e}"
        logger.error(error_msg)
        return error_msg


@tool
def db_query(sql: str) -> str:
    """
    数据库查询工具
    
    安全地执行SQL查询（仅支持SELECT语句）。
    注意：此工具需要预先配置数据库连接才能使用。
    如果没有配置数据库连接，将返回提示信息。
    
    Args:
        sql: SQL查询语句（仅支持SELECT语句，如 "SELECT * FROM table_name LIMIT 10"）
        
    Returns:
        格式化的查询结果字符串，如果出错则返回错误信息
    """
    try:
        # 创建数据库工具（不提供db_connection，会在工具内部处理）
        db_tool = DatabaseTool(
            name="db_query",
            description="数据库查询",
            parameters={}
        )
        
        # 运行异步方法
        result = _run_async(db_tool.execute(sql))
        
        # 格式化返回结果
        if isinstance(result, str):
            return result
        
        return str(result)
    except Exception as e:
        error_msg = f"数据库查询失败: {e}"
        logger.error(error_msg)
        return error_msg


# 导出所有工具
__all__ = [
    # 被动工具
    "get_sina_news",
    "get_thx_news",
    "get_market_data",
    "get_hot_money",
    # 主动工具
    "get_stock_fundamental",
    "get_stock_market_data",
    # 通用工具
    "calculator",
    "web_search",
    "db_query",
]
