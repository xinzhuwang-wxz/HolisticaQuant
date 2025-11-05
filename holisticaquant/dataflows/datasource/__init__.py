"""
数据源模块

提供统一的数据源接口，所有数据源都返回相同格式：
DataFrame with columns ['title', 'content', 'pub_time', 'url']

数据源分类：
- 被动工具：自动获取排行榜数据（SinaNewsCrawl, ThxNewsCrawl, MarketDataAkshare, HotMoneyAkshare）
- 主动工具：根据查询参数获取特定数据（StockFundamentalAkshare, StockMarketDataAkshare）
"""

from .data_source_base import DataSourceBase
from .sina_news_crawl import SinaNewsCrawl
from .thx_news_crawl import ThxNewsCrawl

# 完整版数据源（基于 akshare）- 被动工具
try:
    from .market_data_akshare import MarketDataAkshare
    from .hot_money_akshare import HotMoneyAkshare
    HAS_AKSHARE_SOURCES = True
except ImportError:
    # 如果 akshare 未安装，这些数据源不可用
    HAS_AKSHARE_SOURCES = False
    MarketDataAkshare = None
    HotMoneyAkshare = None

# 主动工具数据源（基于 akshare）- 需要查询参数（如 ticker）
try:
    from .stock_fundamental_akshare import StockFundamentalAkshare
    from .stock_market_data_akshare import StockMarketDataAkshare
    HAS_AKSHARE_ACTIVE_SOURCES = True
except ImportError:
    HAS_AKSHARE_ACTIVE_SOURCES = False
    StockFundamentalAkshare = None
    StockMarketDataAkshare = None

__all__ = [
    # 基类
    'DataSourceBase',
    
    # 被动工具（自动获取排行榜数据）
    'SinaNewsCrawl',
    'ThxNewsCrawl',
    'MarketDataAkshare',
    'HotMoneyAkshare',
    
    # 主动工具（需要查询参数）
    'StockFundamentalAkshare',
    'StockMarketDataAkshare',
    
    # 标志
    'HAS_AKSHARE_SOURCES',
    'HAS_AKSHARE_ACTIVE_SOURCES',
]

