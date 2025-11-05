"""
股票基本面数据源（主动工具）

根据股票代码主动查询基本面数据，包括：
- 基本信息（公司名称、行业、市值等）
- 财务指标（PE、PB、ROE等）
- 业绩数据（营收、利润等）
"""
import pandas as pd
import asyncio
from datetime import datetime
from typing import Optional
from loguru import logger

from .data_source_base import DataSourceBase
from ..utils.akshare_utils import akshare_cached, HAS_AKSHARE
from ..utils.date_utils import get_previous_trading_date


class StockFundamentalAkshare(DataSourceBase):
    """
    股票基本面数据源（基于 akshare，主动查询工具）
    
    根据股票代码获取基本面数据：
    - 基本信息（公司名称、行业、市值等）
    - 财务指标（PE、PB、ROE等）
    - 业绩数据（营收、利润等）
    """
    
    def __init__(self,
                 max_size_kb: Optional[float] = 512.0,
                 max_time_range_days: Optional[int] = 7,
                 max_records: Optional[int] = 500,
                 use_cache: bool = False):
        """
        Args:
            max_size_kb: 最大数据大小（KB）
            max_time_range_days: 最大时间范围（天数）
            max_records: 最大记录数
            use_cache: 是否使用缓存，默认 False（主动工具通常需要最新数据）
        """
        super().__init__("stock_fundamental_akshare", max_size_kb=max_size_kb,
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
    
    def get_stock_info(self, ticker: str) -> pd.DataFrame:
        """
        获取股票基本信息
        
        Args:
            ticker: 股票代码（标准化后）
            
        Returns:
            包含股票基本信息的 DataFrame
        """
        try:
            if not HAS_AKSHARE:
                return pd.DataFrame()
            
            # 提取股票代码（移除市场前缀）
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
            #         # 查找指定股票
            #         stock_df = df[df['代码'] == ticker_code]
            #         if not stock_df.empty:
            #             return stock_df
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
            #         # stock_zh_a_spot 返回的格式可能不同，需要查找股票
            #         # 检查可能的列名
            #         code_col = None
            #         for col in ['代码', 'code', 'symbol', '股票代码']:
            #             if col in df.columns:
            #                 code_col = col
            #                 break
            #         
            #         if code_col:
            #             # 查找指定股票
            #             stock_df = df[df[code_col] == ticker_code]
            #             if not stock_df.empty:
            #                 return stock_df
            # except Exception as e:
            #     logger.debug(f"方法2失败（stock_zh_a_spot）: {e}")
            
            # 方法3：尝试使用历史数据获取基本信息（更稳定）
            try:
                # 获取股票的历史数据，从中提取基本信息
                # 注意：stock_zh_a_hist 需要不带市场前缀的代码（如 '000001' 而不是 'sz000001'）
                df = self._run_akshare(
                    func_name="stock_zh_a_hist",
                    func_kwargs={"symbol": ticker_code, "period": "daily", "adjust": ""},
                    verbose=False
                )
                
                if not df.empty:
                    # 从历史数据构建基本信息（取最近一条）
                    latest = df.iloc[-1]
                    
                    # 构建一个包含基本信息的 DataFrame
                    info_dict = {
                        '代码': ticker_code,
                        '名称': ticker_code,  # 历史数据中没有名称，需要单独获取
                        '最新价': latest.get('收盘', 'N/A'),
                        '昨收': latest.get('收盘', 'N/A'),
                        '今开': latest.get('开盘', 'N/A'),
                        '最高': latest.get('最高', 'N/A'),
                        '最低': latest.get('最低', 'N/A'),
                        '成交量': latest.get('成交量', 'N/A'),
                        '成交额': latest.get('成交额', 'N/A'),
                    }
                    
                    # 计算涨跌额和涨跌幅（如果有前一条数据）
                    if len(df) > 1:
                        prev_close = df.iloc[-2].get('收盘', latest.get('收盘', 0))
                        if isinstance(latest.get('收盘', 0), (int, float)) and isinstance(prev_close, (int, float)):
                            change_amount = latest.get('收盘', 0) - prev_close
                            change_rate = (change_amount / prev_close * 100) if prev_close != 0 else 0
                            info_dict['涨跌额'] = change_amount
                            info_dict['涨跌幅'] = change_rate
                    
                    # 返回单行 DataFrame
                    info_df = pd.DataFrame([info_dict])
                    return info_df
            except Exception as e:
                logger.debug(f"方法3失败（stock_zh_a_hist）: {e}")
            
            # 方法4：尝试使用分钟数据获取最新信息（备用方案）
            try:
                # 获取分钟数据，取最新的作为基本信息
                df = self._run_akshare(
                    func_name="stock_zh_a_hist_min_em",
                    func_kwargs={"symbol": ticker_code, "period": "1", "adjust": ""},
                    verbose=False
                )
                
                if not df.empty:
                    # 从分钟数据取最新一条
                    latest = df.iloc[-1]
                    
                    # 构建基本信息
                    info_dict = {
                        '代码': ticker_code,
                        '名称': ticker_code,
                        '最新价': latest.get('收盘', 'N/A'),
                        '昨收': latest.get('收盘', 'N/A'),
                        '今开': latest.get('开盘', 'N/A'),
                        '最高': latest.get('最高', 'N/A'),
                        '最低': latest.get('最低', 'N/A'),
                        '成交量': 'N/A',  # 分钟数据可能没有
                        '成交额': 'N/A',
                    }
                    
                    # 计算涨跌额和涨跌幅（如果有前一条数据）
                    if len(df) > 1:
                        prev_close = df.iloc[-2].get('收盘', latest.get('收盘', 0))
                        if isinstance(latest.get('收盘', 0), (int, float)) and isinstance(prev_close, (int, float)):
                            change_amount = latest.get('收盘', 0) - prev_close
                            change_rate = (change_amount / prev_close * 100) if prev_close != 0 else 0
                            info_dict['涨跌额'] = change_amount
                            info_dict['涨跌幅'] = change_rate
                    
                    info_df = pd.DataFrame([info_dict])
                    return info_df
            except Exception as e:
                logger.debug(f"方法4失败（stock_zh_a_hist_min_em）: {e}")
            
            # 如果都失败，返回空 DataFrame
            logger.warning(f"未能获取股票 {ticker_code} 的基本信息（所有方法都失败）")
            return pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"获取股票信息失败 {ticker}: {e}")
            return pd.DataFrame()
    
    def get_financial_indicators(self, ticker: str, trade_date: str, stock_info_df: pd.DataFrame) -> dict:
        """
        获取财务指标（从实时行情数据中提取）
        
        Args:
            ticker: 股票代码（标准化后）
            trade_date: 交易日期
            stock_info_df: 股票基本信息 DataFrame（从实时行情获取）
            
        Returns:
            财务指标字典
        """
        try:
            if stock_info_df.empty:
                return {}
            
            row = stock_info_df.iloc[0].to_dict()
            
            # 从实时行情数据中提取财务指标
            indicators = {
                'pe_ratio': row.get('市盈率', row.get('市盈率-动态', 'N/A')),
                'pb_ratio': row.get('市净率', 'N/A'),
                'total_mv': row.get('总市值', 'N/A'),
                'flow_mv': row.get('流通市值', 'N/A'),
                'turnover_rate': row.get('换手率', 'N/A'),
                'volume_ratio': row.get('量比', 'N/A'),
            }
            
            return indicators
        except Exception as e:
            logger.warning(f"提取财务指标失败: {e}")
            return {}
    
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
            
            logger.info(f"获取 {ticker_normalized} 的基本面数据")
            
            all_records = []
            
            # 1. 基本信息（从实时行情获取）
            stock_info_df = self.get_stock_info(ticker_normalized)
            
            if not stock_info_df.empty:
                try:
                    row = stock_info_df.iloc[0].to_dict()
                    
                    # 格式化基本信息为结构化文本
                    info_content = f"股票代码: {row.get('代码', ticker_normalized)}\n"
                    info_content += f"股票名称: {row.get('名称', 'N/A')}\n"
                    info_content += f"查询时间: {trigger_time}\n"
                    info_content += f"交易日期: {trade_date}\n\n"
                    info_content += "基本信息:\n"
                    info_content += f"最新价: {row.get('最新价', 'N/A')}\n"
                    info_content += f"涨跌额: {row.get('涨跌额', 'N/A')}\n"
                    info_content += f"涨跌幅: {row.get('涨跌幅', 'N/A')}%\n"
                    info_content += f"今开: {row.get('今开', 'N/A')}\n"
                    info_content += f"最高: {row.get('最高', 'N/A')}\n"
                    info_content += f"最低: {row.get('最低', 'N/A')}\n"
                    info_content += f"昨收: {row.get('昨收', 'N/A')}\n"
                    info_content += f"成交量: {row.get('成交量', 'N/A')}\n"
                    info_content += f"成交额: {row.get('成交额', 'N/A')}\n"
                    
                    all_records.append({
                        "title": f"{row.get('名称', ticker_normalized)}({row.get('代码', ticker_normalized)}) 基本信息",
                        "content": info_content,
                        "pub_time": trigger_time,
                        "url": f"akshare://stock/info/{row.get('代码', ticker_normalized)}/{trade_date}"
                    })
                    
                    # 2. 财务指标（从实时行情数据中提取）
                    try:
                        financial_indicators = self.get_financial_indicators(ticker_normalized, trade_date, stock_info_df)
                        if financial_indicators:
                            finance_content = f"股票代码: {row.get('代码', ticker_normalized)}\n"
                            finance_content += f"股票名称: {row.get('名称', 'N/A')}\n"
                            finance_content += f"交易日期: {trade_date}\n"
                            finance_content += f"查询时间: {trigger_time}\n\n"
                            finance_content += "财务指标:\n"
                            finance_content += f"市盈率(PE): {financial_indicators.get('pe_ratio', 'N/A')}\n"
                            finance_content += f"市净率(PB): {financial_indicators.get('pb_ratio', 'N/A')}\n"
                            finance_content += f"总市值: {financial_indicators.get('total_mv', 'N/A')}\n"
                            finance_content += f"流通市值: {financial_indicators.get('flow_mv', 'N/A')}\n"
                            finance_content += f"换手率: {financial_indicators.get('turnover_rate', 'N/A')}%\n"
                            finance_content += f"量比: {financial_indicators.get('volume_ratio', 'N/A')}\n"
                            
                            all_records.append({
                                "title": f"{row.get('名称', ticker_normalized)}({row.get('代码', ticker_normalized)}) 财务指标",
                                "content": finance_content,
                                "pub_time": trigger_time,
                                "url": f"akshare://stock/financial/{row.get('代码', ticker_normalized)}/{trade_date}"
                            })
                    except Exception as e:
                        logger.warning(f"提取财务指标失败: {e}")
                        
                except Exception as e:
                    logger.warning(f"处理基本信息失败: {e}")
            else:
                logger.warning(f"未获取到股票 {ticker_normalized} 的基本信息")
            
            if not all_records:
                logger.warning(f"未能获取 {ticker_normalized} 的基本面数据")
                return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
            
            df = pd.DataFrame(all_records)
            logger.info(f"成功获取 {ticker_normalized} 基本面数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取基本面数据失败: {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)


if __name__ == "__main__":
    # 测试代码
    import asyncio
    stock_fundamental = StockFundamentalAkshare(use_cache=False)
    trigger_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = asyncio.run(stock_fundamental.fetch_data_async(trigger_time, ticker="000001"))
    print(f"获取到 {len(df)} 条记录")
    if not df.empty:
        print("\n内容预览:")
        for idx, row in df.iterrows():
            print(f"\n=== {row['title']} ===")
            print(row['content'][:300] + "...")

