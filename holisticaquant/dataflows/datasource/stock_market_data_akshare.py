"""
股票市场数据源（主动工具）

根据股票代码主动查询市场数据，包括：
- 实时行情数据
- K线数据（日K、周K等）
- 历史价格数据
- 成交量、成交额等
"""
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from .data_source_base import DataSourceBase
from ..utils.akshare_utils import akshare_cached, HAS_AKSHARE
from ..utils.date_utils import get_previous_trading_date


class StockMarketDataAkshare(DataSourceBase):
    """
    股票市场数据源（基于 akshare，主动查询工具）
    
    根据股票代码获取市场数据：
    - 实时行情
    - K线数据（日K、周K等）
    - 历史价格
    - 成交量、成交额
    """
    
    def __init__(self,
                 max_size_kb: Optional[float] = 512.0,
                 max_time_range_days: Optional[int] = 30,
                 max_records: Optional[int] = 500,
                 use_cache: bool = False):
        """
        Args:
            max_size_kb: 最大数据大小（KB）
            max_time_range_days: 最大时间范围（天数）
            max_records: 最大记录数
            use_cache: 是否使用缓存，默认 False（主动工具通常需要最新数据）
        """
        super().__init__("stock_market_data_akshare", max_size_kb=max_size_kb,
                        max_time_range_days=max_time_range_days,
                        max_records=max_records, use_cache=use_cache)
    
    def _normalize_ticker(self, ticker: str) -> str:
        """
        标准化股票代码（支持多种格式）
        
        Args:
            ticker: 股票代码，可能是 "000001", "000001.SZ", "sh000001" 等
            
        Returns:
            标准化的股票代码（用于 akshare）
        """
        ticker = ticker.upper().strip()
        # 移除 .SH, .SZ 等后缀
        if '.' in ticker:
            ticker = ticker.split('.')[0]
        
        # 如果已经有市场前缀（SH/SZ/BJ），先提取纯数字部分
        if ticker.startswith(('SH', 'SZ', 'BJ')):
            ticker_digits = ticker[2:]  # 移除前缀
            if ticker_digits.isdigit() and len(ticker_digits) == 6:
                # 返回小写前缀格式（akshare使用小写）
                return f"{ticker[:2].lower()}{ticker_digits}"
        
        # 如果是 6 位数字，添加市场前缀
        if ticker.isdigit() and len(ticker) == 6:
            if ticker.startswith(('00', '30')):  # 深市
                return f"sz{ticker}"
            elif ticker.startswith(('60', '68')):  # 沪市
                return f"sh{ticker}"
            elif ticker.startswith(('43', '83', '87')):  # 北交所
                return f"bj{ticker}"
        
        return ticker.lower() if ticker else ticker
    
    def get_realtime_quote(self, ticker: str) -> dict:
        """
        获取实时行情数据
        
        Args:
            ticker: 股票代码（标准化后）
            
        Returns:
            实时行情数据字典
        """
        try:
            if not HAS_AKSHARE:
                return {}
            
            ticker_code = ticker.replace('sh', '').replace('sz', '').replace('bj', '')
            
            # 方法1：尝试使用实时行情数据（已禁用，因为经常失败）
            # try:
            #     df = self._run_akshare(
            #         func_name="stock_zh_a_spot_em",
            #         func_kwargs={},
            #         verbose=False
            #     )
            #     
            #     if not df.empty and '代码' in df.columns:
            #         stock_df = df[df['代码'] == ticker_code]
            #         if not stock_df.empty:
            #             row = stock_df.iloc[0].to_dict()
            #             
            #             quote = {
            #                 'code': row.get('代码', ticker_code),
            #                 'name': row.get('名称', 'N/A'),
            #                 'latest_price': row.get('最新价', 'N/A'),
            #                 'change_amount': row.get('涨跌额', 'N/A'),
            #                 'change_rate': row.get('涨跌幅', 'N/A'),
            #                 'volume': row.get('成交量', 'N/A'),
            #                 'turnover': row.get('成交额', 'N/A'),
            #                 'high': row.get('最高', 'N/A'),
            #                 'low': row.get('最低', 'N/A'),
            #                 'open': row.get('今开', 'N/A'),
            #                 'pre_close': row.get('昨收', 'N/A'),
            #                 'turnover_rate': row.get('换手率', 'N/A'),
            #                 'pe_ratio': row.get('市盈率', 'N/A'),
            #                 'total_mv': row.get('总市值', 'N/A'),
            #                 'flow_mv': row.get('流通市值', 'N/A'),
            #             }
            #             
            #             return quote
            # except Exception as e:
            #     logger.debug(f"方法1失败（stock_zh_a_spot_em）: {e}")
            
            # 方法2：尝试使用另一个实时行情函数（已禁用，因为经常失败）
            # try:
            #     df = self._run_akshare(
            #         func_name="stock_zh_a_spot",
            #         func_kwargs={},
            #         verbose=False
            #     )
            #     
            #     if not df.empty:
            #         # 查找可能的列名
            #         code_col = None
            #         for col in ['代码', 'code', 'symbol', '股票代码']:
            #             if col in df.columns:
            #                 code_col = col
            #                 break
            #         
            #         if code_col:
            #             stock_df = df[df[code_col] == ticker_code]
            #             if not stock_df.empty:
            #                 row = stock_df.iloc[0].to_dict()
            #                 
            #                 # 尝试提取字段（根据实际返回格式调整）
            #                 quote = {
            #                     'code': row.get(code_col, ticker_code),
            #                     'name': row.get('名称', row.get('name', ticker_code)),
            #                     'latest_price': row.get('最新价', row.get('price', 'N/A')),
            #                     'change_amount': row.get('涨跌额', row.get('change', 'N/A')),
            #                     'change_rate': row.get('涨跌幅', row.get('change_percent', 'N/A')),
            #                     'volume': row.get('成交量', row.get('volume', 'N/A')),
            #                     'turnover': row.get('成交额', row.get('turnover', 'N/A')),
            #                     'high': row.get('最高', row.get('high', 'N/A')),
            #                     'low': row.get('最低', row.get('low', 'N/A')),
            #                     'open': row.get('今开', row.get('open', 'N/A')),
            #                     'pre_close': row.get('昨收', row.get('pre_close', 'N/A')),
            #                     'turnover_rate': row.get('换手率', 'N/A'),
            #                     'pe_ratio': row.get('市盈率', 'N/A'),
            #                     'total_mv': row.get('总市值', 'N/A'),
            #                     'flow_mv': row.get('流通市值', 'N/A'),
            #                 }
            #                 
            #                 return quote
            # except Exception as e:
            #     logger.debug(f"方法2失败（stock_zh_a_spot）: {e}")
            
            # 方法3：从历史数据获取最近行情（更稳定，但可能不是最新的）
            try:
                # 获取股票的历史数据（最近30天）
                # 注意：stock_zh_a_hist 需要不带市场前缀的代码（如 '000001' 而不是 'sz000001'）
                df = self._run_akshare(
                    func_name="stock_zh_a_hist",
                    func_kwargs={"symbol": ticker_code, "period": "daily", "adjust": ""},
                    verbose=False
                )
                
                if not df.empty:
                    # 取最近一条数据作为"实时"行情
                    latest = df.iloc[-1].to_dict()
                    
                    # 计算涨跌额和涨跌幅
                    change_amount = 0
                    change_rate = 0
                    if len(df) > 1:
                        prev_close = df.iloc[-2].get('收盘', latest.get('收盘', 0))
                        if isinstance(latest.get('收盘', 0), (int, float)) and isinstance(prev_close, (int, float)):
                            change_amount = latest.get('收盘', 0) - prev_close
                            change_rate = (change_amount / prev_close * 100) if prev_close != 0 else 0
                    
                    quote = {
                        'code': ticker_code,
                        'name': ticker_code,  # 历史数据中没有名称
                        'latest_price': latest.get('收盘', 'N/A'),
                        'change_amount': change_amount,
                        'change_rate': change_rate,
                        'volume': latest.get('成交量', 'N/A'),
                        'turnover': latest.get('成交额', 'N/A'),
                        'high': latest.get('最高', 'N/A'),
                        'low': latest.get('最低', 'N/A'),
                        'open': latest.get('开盘', 'N/A'),
                        'pre_close': prev_close if len(df) > 1 else latest.get('收盘', 'N/A'),
                        'turnover_rate': 'N/A',  # 历史数据中没有
                        'pe_ratio': 'N/A',  # 历史数据中没有
                        'total_mv': 'N/A',  # 历史数据中没有
                        'flow_mv': 'N/A',  # 历史数据中没有
                    }
                    
                    return quote
            except Exception as e:
                logger.debug(f"方法3失败（stock_zh_a_hist）: {e}")
            
            # 方法4：尝试使用分钟数据获取最新信息（备用方案）
            try:
                df = self._run_akshare(
                    func_name="stock_zh_a_hist_min_em",
                    func_kwargs={"symbol": ticker_code, "period": "1", "adjust": ""},
                    verbose=False
                )
                
                if not df.empty:
                    latest = df.iloc[-1].to_dict()
                    
                    change_amount = 0
                    change_rate = 0
                    if len(df) > 1:
                        prev_close = df.iloc[-2].get('收盘', latest.get('收盘', 0))
                        if isinstance(latest.get('收盘', 0), (int, float)) and isinstance(prev_close, (int, float)):
                            change_amount = latest.get('收盘', 0) - prev_close
                            change_rate = (change_amount / prev_close * 100) if prev_close != 0 else 0
                    
                    quote = {
                        'code': ticker_code,
                        'name': ticker_code,
                        'latest_price': latest.get('收盘', 'N/A'),
                        'change_amount': change_amount,
                        'change_rate': change_rate,
                        'volume': 'N/A',
                        'turnover': 'N/A',
                        'high': latest.get('最高', 'N/A'),
                        'low': latest.get('最低', 'N/A'),
                        'open': latest.get('开盘', 'N/A'),
                        'pre_close': prev_close if len(df) > 1 else latest.get('收盘', 'N/A'),
                        'turnover_rate': 'N/A',
                        'pe_ratio': 'N/A',
                        'total_mv': 'N/A',
                        'flow_mv': 'N/A',
                    }
                    
                    return quote
            except Exception as e:
                logger.debug(f"方法4失败（stock_zh_a_hist_min_em）: {e}")
            
            # 如果都失败，返回空字典
            return {}
            
        except Exception as e:
            logger.warning(f"获取实时行情失败 {ticker}: {e}")
            return {}
    
    def get_kline_data(self, ticker: str, period: str = "daily", count: int = 30) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            ticker: 股票代码（标准化后）
            period: K线周期，可选 "daily"（日K）、"weekly"（周K）、"monthly"（月K）
            count: 获取的数据条数，默认 30 条
            
        Returns:
            K线数据 DataFrame
        """
        try:
            if not HAS_AKSHARE:
                return pd.DataFrame()
            
            # 根据周期选择不同的函数
            period_map = {
                "daily": "stock_zh_a_hist",
                "weekly": "stock_zh_a_hist",
                "monthly": "stock_zh_a_hist",
            }
            
            func_name = period_map.get(period, "stock_zh_a_hist")
            
            try:
                # 获取历史数据
                # 注意：stock_zh_a_hist 需要不带市场前缀的代码
                ticker_code = ticker.replace('sh', '').replace('sz', '').replace('bj', '')
                df = self._run_akshare(
                    func_name=func_name,
                    func_kwargs={
                        "symbol": ticker_code,
                        "period": period if period != "daily" else "daily",
                        "adjust": "",
                    },
                    verbose=False
                )
                
                if df.empty:
                    return pd.DataFrame()
                
                # 取最近 count 条
                df = df.tail(count)
                return df
            except Exception as e:
                logger.warning(f"获取K线数据失败: {e}")
                return pd.DataFrame()
        except Exception as e:
            logger.warning(f"获取K线数据失败 {ticker}: {e}")
            return pd.DataFrame()
    
    async def get_data(self, trigger_time: str, ticker: str, **query_params) -> pd.DataFrame:
        """
        实现基类的抽象方法，获取数据（主动查询）
        
        Args:
            trigger_time: 触发时间字符串，格式 'YYYY-MM-DD HH:MM:SS'
            ticker: 股票代码（主动查询参数，必需）
            **query_params: 额外的查询参数
            
        Returns:
            DataFrame with columns ['title', 'content', 'pub_time', 'url']
        """
        try:
            if not HAS_AKSHARE:
                logger.error("akshare 未安装")
                return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
            
            ticker_normalized = self._normalize_ticker(ticker)
            trade_date = get_previous_trading_date(trigger_time)
            
            logger.info(f"获取 {ticker_normalized} 的市场数据")
            
            all_records = []
            
            # 1. 实时行情数据
            try:
                quote = self.get_realtime_quote(ticker_normalized)
                if quote and quote.get('code'):
                    quote_content = f"股票代码: {quote.get('code', ticker_normalized)}\n"
                    quote_content += f"股票名称: {quote.get('name', 'N/A')}\n"
                    quote_content += f"查询时间: {trigger_time}\n"
                    quote_content += f"交易日期: {trade_date}\n\n"
                    quote_content += "实时行情:\n"
                    quote_content += f"最新价: {quote.get('latest_price', 'N/A')}\n"
                    quote_content += f"涨跌额: {quote.get('change_amount', 'N/A')}\n"
                    quote_content += f"涨跌幅: {quote.get('change_rate', 'N/A')}%\n"
                    quote_content += f"今开: {quote.get('open', 'N/A')}\n"
                    quote_content += f"最高: {quote.get('high', 'N/A')}\n"
                    quote_content += f"最低: {quote.get('low', 'N/A')}\n"
                    quote_content += f"昨收: {quote.get('pre_close', 'N/A')}\n"
                    quote_content += f"成交量: {quote.get('volume', 'N/A')}\n"
                    quote_content += f"成交额: {quote.get('turnover', 'N/A')}\n"
                    quote_content += f"换手率: {quote.get('turnover_rate', 'N/A')}%\n"
                    quote_content += f"市盈率: {quote.get('pe_ratio', 'N/A')}\n"
                    quote_content += f"总市值: {quote.get('total_mv', 'N/A')}\n"
                    quote_content += f"流通市值: {quote.get('flow_mv', 'N/A')}\n"
                    
                    all_records.append({
                        "title": f"{quote.get('name', ticker_normalized)}({quote.get('code', ticker_normalized)}) 实时行情",
                        "content": quote_content,
                        "pub_time": trigger_time,
                        "url": f"akshare://stock/quote/{quote.get('code', ticker_normalized)}/{trade_date}"
                    })
            except Exception as e:
                logger.warning(f"获取实时行情失败: {e}")
            
            # 2. K线数据（最近30天）
            try:
                kline_df = self.get_kline_data(ticker_normalized, period="daily", count=30)
                if not kline_df.empty:
                    kline_content = f"股票代码: {ticker_normalized}\n"
                    kline_content += f"查询时间: {trigger_time}\n"
                    kline_content += f"交易日期: {trade_date}\n\n"
                    kline_content += f"最近30天日K线数据:\n\n"
                    
                    # 格式化最近5天的数据
                    recent_kline = kline_df.tail(5)
                    for idx, row in recent_kline.iterrows():
                        date = row.get('日期', 'N/A')
                        open_price = row.get('开盘', 'N/A')
                        close_price = row.get('收盘', 'N/A')
                        high_price = row.get('最高', 'N/A')
                        low_price = row.get('最低', 'N/A')
                        volume = row.get('成交量', 'N/A')
                        turnover = row.get('成交额', 'N/A')
                        
                        kline_content += f"{date}: 开盘={open_price}, 收盘={close_price}, "
                        kline_content += f"最高={high_price}, 最低={low_price}, "
                        kline_content += f"成交量={volume}, 成交额={turnover}\n"
                    
                    kline_content += f"\n（共 {len(kline_df)} 条K线数据，仅显示最近5天）\n"
                    
                    all_records.append({
                        "title": f"{ticker_normalized} K线数据",
                        "content": kline_content,
                        "pub_time": trigger_time,
                        "url": f"akshare://stock/kline/{ticker_normalized}/{trade_date}"
                    })
            except Exception as e:
                logger.warning(f"获取K线数据失败: {e}")
            
            if not all_records:
                logger.warning(f"未能获取 {ticker_normalized} 的市场数据")
                return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
            
            df = pd.DataFrame(all_records)
            logger.info(f"成功获取 {ticker_normalized} 市场数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)


if __name__ == "__main__":
    # 测试代码
    import asyncio
    stock_market = StockMarketDataAkshare(use_cache=False)
    trigger_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = asyncio.run(stock_market.fetch_data_async(trigger_time, ticker="000001"))
    print(f"获取到 {len(df)} 条记录")
    if not df.empty:
        print("\n内容预览:")
        for idx, row in df.iterrows():
            print(f"\n=== {row['title']} ===")
            print(row['content'][:300] + "...")

