"""
基于 akshare 的市场数据源

整合K线数据、板块资金流向等，生成市场分析
注意：此版本不包含 LLM 总结，只返回格式化的数据文本
"""
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from .data_source_base import DataSourceBase
from ..utils.akshare_utils import akshare_cached
from ..utils.date_utils import get_previous_trading_date


class MarketDataAkshare(DataSourceBase):
    """
    市场数据源（基于 akshare）
    
    获取三大指数K线数据、当日数据、板块资金流向等
    """
    
    def __init__(self, 
                 max_size_kb: Optional[float] = 512.0,
                 max_time_range_days: Optional[int] = 7,
                 max_records: Optional[int] = 500,
                 use_cache: bool = True):
        """
        Args:
            max_size_kb: 最大数据大小（KB）
            max_time_range_days: 最大时间范围（天数）
            max_records: 最大记录数
            use_cache: 是否使用缓存，False 表示每次都获取最新数据（适合LLM调用），默认 True
        """
        super().__init__("market_data_akshare", max_size_kb=max_size_kb,
                        max_time_range_days=max_time_range_days,
                        max_records=max_records, use_cache=use_cache)
        
    def get_kline_data(self, trade_date: str) -> dict:
        """
        获取三大指数的K线数据
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            包含三大指数K线数据的字典
        """
        try:
            indices = {
                "000001.SH": {"symbol": "sh000001", "name": "上证指数"},
                "399006.SZ": {"symbol": "sz399006", "name": "创业板指"},
                "000688.SH": {"symbol": "sh000688", "name": "科创50"}
            }
            
            kline_data = {}
            
            for stock_code, info in indices.items():
                try:
                    # 获取指数历史数据
                    df = self._run_akshare(
                        func_name="stock_zh_index_daily",
                        func_kwargs={"symbol": info["symbol"]},
                        verbose=False
                    )
                    
                    if df.empty:
                        logger.warning(f"{info['name']} 数据为空")
                        continue
                    
                    # 转换日期格式并筛选最近90天的数据
                    df['date'] = pd.to_datetime(df['date'])
                    target_date = datetime.strptime(trade_date, '%Y%m%d')
                    
                    filtered_df = df[df['date'] <= target_date].tail(90)
                    
                    if filtered_df.empty:
                        logger.warning(f"{info['name']} 无{trade_date}之前的数据")
                        continue
                    
                    # 转换为所需格式
                    data_list = []
                    for _, row in filtered_df.iterrows():
                        data_list.append({
                            'trade_date': row['date'].strftime('%Y%m%d'),
                            'open_price': float(row['open']),
                            'high_price': float(row['high']),
                            'low_price': float(row['low']),
                            'close_price': float(row['close']),
                            'trade_lots': int(row['volume'])
                        })
                    
                    kline_data[stock_code] = {
                        'name': info['name'],
                        'data': data_list
                    }
                    
                    logger.info(f"获取 {info['name']} K线数据成功，{len(data_list)} 条记录")
                    
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e) if str(e) else f"{error_type}异常（无详细信息）"
                    # 如果错误信息为空或None，使用异常类型
                    if not error_msg or error_msg == "None":
                        error_msg = f"{error_type}异常"
                    # 检查是否是真正的 ImportError（akshare未安装）
                    is_import_error = isinstance(e, ImportError) or (
                        hasattr(e, '__cause__') and e.__cause__ and isinstance(e.__cause__, ImportError)
                    )
                    # 检查错误信息是否包含"未安装"
                    has_install_msg = "未安装" in error_msg or "not installed" in error_msg.lower()
                    
                    if is_import_error and ("akshare" in error_msg.lower() or has_install_msg):
                        logger.error(f"获取 {info['name']} K线数据失败: {error_msg}")
                    else:
                        logger.warning(f"获取 {info['name']} K线数据失败（{error_type}）: {error_msg}")
                    continue
            
            return kline_data
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else f"{error_type}异常"
            # 检查是否是真正的 ImportError（akshare未安装）
            is_import_error = isinstance(e, ImportError) or (
                hasattr(e, '__cause__') and e.__cause__ and isinstance(e.__cause__, ImportError)
            )
            # 检查错误信息是否包含"未安装"
            has_install_msg = "未安装" in error_msg or "not installed" in error_msg.lower()
            
            if is_import_error and ("akshare" in error_msg.lower() or has_install_msg):
                logger.error(f"获取K线数据失败: {error_msg}")
            else:
                logger.warning(f"获取K线数据失败（{error_type}）: {error_msg}")
            return {}
    
    def get_current_day_data(self, trade_date: str) -> dict:
        """
        获取三大指数当日收盘数据
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            包含三大指数当日数据的字典
        """
        try:
            indices = {
                "000001.SH": {"symbol": "sh000001", "name": "上证指数"},
                "399006.SZ": {"symbol": "sz399006", "name": "创业板指"},
                "000688.SH": {"symbol": "sh000688", "name": "科创50"}
            }
            
            current_day_data = {}
            
            for stock_code, info in indices.items():
                try:
                    # 获取指数历史数据
                    df = self._run_akshare(
                        func_name="stock_zh_index_daily",
                        func_kwargs={"symbol": info["symbol"]},
                        verbose=False
                    )
                    
                    if df.empty:
                        logger.warning(f"{info['name']} 数据为空")
                        continue
                    
                    # 转换日期格式并查找指定日期的数据
                    df['date'] = pd.to_datetime(df['date'])
                    target_date = datetime.strptime(trade_date, '%Y%m%d')
                    
                    # 查找指定日期的数据
                    target_row = df[df['date'] == target_date]
                    
                    if target_row.empty:
                        # 如果没有当日数据，取最近的一条数据
                        target_row = df[df['date'] <= target_date].tail(1)
                        if target_row.empty:
                            logger.warning(f"{info['name']} 无{trade_date}的数据")
                            continue
                    
                    row = target_row.iloc[0]
                    
                    # 计算涨跌幅（需要前一天的数据）
                    prev_row = df[df['date'] < row['date']].tail(1)
                    if not prev_row.empty:
                        prev_close = float(prev_row.iloc[0]['close'])
                        price_change = float(row['close']) - prev_close
                        price_change_rate = price_change / prev_close
                    else:
                        price_change = 0.0
                        price_change_rate = 0.0
                    
                    current_day_data[stock_code] = {
                        'name': info['name'],
                        'open_price': float(row['open']),
                        'high_price': float(row['high']),
                        'low_price': float(row['low']),
                        'close_price': float(row['close']),
                        'price_change': price_change,
                        'price_change_rate': price_change_rate,
                        'trade_amount': float(row['volume']) * float(row['close']),  # 估算成交额
                        'trade_lots': int(row['volume'])
                    }
                    
                    logger.info(f"获取 {info['name']} 当日数据成功")
                    
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e) if str(e) else f"{error_type}异常（无详细信息）"
                    # 如果错误信息为空或None，使用异常类型
                    if not error_msg or error_msg == "None":
                        error_msg = f"{error_type}异常"
                    # 检查是否是真正的 ImportError（akshare未安装）
                    is_import_error = isinstance(e, ImportError) or (
                        hasattr(e, '__cause__') and e.__cause__ and isinstance(e.__cause__, ImportError)
                    )
                    # 检查错误信息是否包含"未安装"
                    has_install_msg = "未安装" in error_msg or "not installed" in error_msg.lower()
                    
                    if is_import_error and ("akshare" in error_msg.lower() or has_install_msg):
                        logger.error(f"获取 {info['name']} 当日数据失败: {error_msg}")
                    else:
                        logger.warning(f"获取 {info['name']} 当日数据失败（{error_type}）: {error_msg}")
                    continue
            
            return current_day_data
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else f"{error_type}异常"
            # 检查是否是真正的 ImportError（akshare未安装）
            is_import_error = isinstance(e, ImportError) or (
                hasattr(e, '__cause__') and e.__cause__ and isinstance(e.__cause__, ImportError)
            )
            # 检查错误信息是否包含"未安装"
            has_install_msg = "未安装" in error_msg or "not installed" in error_msg.lower()
            
            if is_import_error and ("akshare" in error_msg.lower() or has_install_msg):
                logger.error(f"获取当日数据失败: {error_msg}")
            else:
                logger.warning(f"获取当日数据失败（{error_type}）: {error_msg}")
            return {}
    
    def get_sector_summary(self, trade_date: str) -> str:
        """
        获取板块资金流向摘要
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            板块资金流向摘要文本
        """
        try:
            # 获取板块资金流向数据
            df = self._run_akshare(
                func_name="stock_board_industry_name_em",
                func_kwargs={},
                verbose=False
            )
            
            if df.empty:
                return "无板块资金流向数据"
            
            summary_lines = [f"{trade_date} 板块资金流向情况（东方财富数据）：\n"]
            
            # 取前10个板块
            top_sectors = df.head(10)
            
            for _, row in top_sectors.iterrows():
                try:
                    sector_name = row['板块名称']
                    latest_price = row['最新价']
                    change_amount = row['涨跌额']
                    change_rate = row['涨跌幅']
                    market_cap = row['总市值'] / 100000000  # 转换为亿元
                    turnover_rate = row['换手率']
                    up_count = row['上涨家数']
                    down_count = row['下跌家数']
                    leading_stock = row['领涨股票']
                    leading_change = row['领涨股票-涨跌幅']
                    
                    change_sign = "+" if change_amount >= 0 else ""
                    rate_sign = "+" if change_rate >= 0 else ""
                    
                    summary_lines.append(
                        f"**{sector_name}**: 最新价 {latest_price:.2f}, "
                        f"涨跌 {change_sign}{change_amount:.2f} ({rate_sign}{change_rate:.2f}%), "
                        f"总市值 {market_cap:.0f}亿, 换手率 {turnover_rate:.2f}%, "
                        f"上涨 {up_count} 下跌 {down_count}, 领涨股 {leading_stock} ({leading_change:+.2f}%)"
                    )
                except Exception as e:
                    logger.warning(f"处理板块数据行失败: {e}")
                    continue
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else f"{error_type}异常"
            # 检查是否是真正的 ImportError（akshare未安装）
            is_import_error = isinstance(e, ImportError) or (
                hasattr(e, '__cause__') and e.__cause__ and isinstance(e.__cause__, ImportError)
            )
            # 检查错误信息是否包含"未安装"
            has_install_msg = "未安装" in error_msg or "not installed" in error_msg.lower()
            
            if is_import_error and ("akshare" in error_msg.lower() or has_install_msg):
                logger.error(f"获取板块资金流向失败: {error_msg}")
            else:
                logger.warning(f"获取板块资金流向失败（{error_type}）: {error_msg}")
            return f"获取板块资金流向失败: {error_msg}"
    
    def format_market_summary(self, trade_date: str) -> str:
        """
        格式化市场数据摘要（不含LLM总结）
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            格式化的市场数据摘要文本
        """
        try:
            # 获取当日数据
            current_day_data = self.get_current_day_data(trade_date)
            
            # 获取板块资金流向
            sector_summary = self.get_sector_summary(trade_date)
            
            # 获取K线数据（用于统计）
            kline_data = self.get_kline_data(trade_date)
            
            sections = [f"## {trade_date} 市场数据摘要\n"]
            
            # 一、三大指数当日收盘情况
            if current_day_data:
                sections.append("### 一、三大指数当日收盘情况\n")
                for stock_code, data in current_day_data.items():
                    change_sign = "+" if data['price_change'] >= 0 else ""
                    rate_sign = "+" if data['price_change_rate'] >= 0 else ""
                    
                    desc = f"**{data['name']}** (代码: {stock_code})\n"
                    desc += f"- 收盘价: {data['close_price']:.2f}点\n"
                    desc += f"- 开盘价: {data['open_price']:.2f}点\n"
                    desc += f"- 最高价: {data['high_price']:.2f}点\n"
                    desc += f"- 最低价: {data['low_price']:.2f}点\n"
                    desc += f"- 涨跌幅: {change_sign}{data['price_change']:.2f}点 ({rate_sign}{data['price_change_rate']*100:.2f}%)\n"
                    desc += f"- 成交额: {data['trade_amount']/100000000:.1f}亿元\n"
                    desc += f"- 成交量: {data['trade_lots']/10000:.0f}万手\n"
                    sections.append(desc)
            else:
                sections.append("### 一、三大指数当日收盘情况\n无数据\n")
            
            # 二、板块资金流向
            sections.append("\n### 二、板块资金流向\n")
            sections.append(sector_summary)
            
            # 三、K线数据统计
            if kline_data:
                sections.append("\n### 三、K线数据统计\n")
                for stock_code, stock_info in kline_data.items():
                    data_list = stock_info['data']
                    if data_list:
                        latest = data_list[-1]
                        sections.append(
                            f"**{stock_info['name']}**: "
                            f"最新收盘 {latest['close_price']:.2f}点, "
                            f"最近90天数据 {len(data_list)} 条"
                        )
            
            return "\n".join(sections)
            
        except Exception as e:
            logger.error(f"格式化市场数据摘要失败: {e}")
            return f"格式化市场数据摘要失败: {str(e)}"
    
    async def get_data(self, trigger_time: str, **query_params) -> pd.DataFrame:
        """
        实现基类的抽象方法，获取数据
        
        将各类数据拆分成多条记录，每条记录对应一个实体（如一个指数、一个板块等）
        
        Args:
            trigger_time: 触发时间字符串，格式 'YYYY-MM-DD HH:MM:SS'
            
        Returns:
            DataFrame with columns ['title', 'content', 'pub_time', 'url']
        """
        try:
            # 获取上一个交易日
            trade_date = get_previous_trading_date(trigger_time)
            logger.info(f"获取 {trade_date} 的市场数据")
            
            all_records = []
            
            # 1. 三大指数 - 每条指数一条记录
            current_day_data = self.get_current_day_data(trade_date)
            if current_day_data:
                for stock_code, data in current_day_data.items():
                    try:
                        change_sign = "+" if data['price_change'] >= 0 else ""
                        rate_sign = "+" if data['price_change_rate'] >= 0 else ""
                        
                        content = f"指数代码: {stock_code}\n"
                        content += f"指数名称: {data['name']}\n"
                        content += f"收盘价: {data['close_price']:.2f}点\n"
                        content += f"开盘价: {data['open_price']:.2f}点\n"
                        content += f"最高价: {data['high_price']:.2f}点\n"
                        content += f"最低价: {data['low_price']:.2f}点\n"
                        content += f"涨跌: {change_sign}{data['price_change']:.2f}点\n"
                        content += f"涨跌幅: {rate_sign}{data['price_change_rate']*100:.2f}%\n"
                        content += f"成交额: {data['trade_amount']/100000000:.1f}亿元\n"
                        content += f"成交量: {data['trade_lots']/10000:.0f}万手\n"
                        
                        all_records.append({
                            "title": f"{trade_date} 指数数据: {data['name']}({stock_code})",
                            "content": content,
                            "pub_time": trigger_time,
                            "url": f"akshare://index/{stock_code}/{trade_date}"
                        })
                    except Exception as e:
                        logger.warning(f"处理指数数据失败: {e}")
                        continue
            
            # 2. 板块资金流向 - 每个板块一条记录（取前20个）
            try:
                sector_df = self._run_akshare(
                    func_name="stock_board_industry_name_em",
                    func_kwargs={},
                    verbose=False
                )
                
                if not sector_df.empty:
                    top_sectors = sector_df.head(20)
                    for _, row in top_sectors.iterrows():
                        try:
                            sector_name = row.get('板块名称', 'N/A')
                            latest_price = row.get('最新价', 0)
                            change_amount = row.get('涨跌额', 0)
                            change_rate = row.get('涨跌幅', 0)
                            market_cap = row.get('总市值', 0) / 100000000  # 转换为亿元
                            turnover_rate = row.get('换手率', 0)
                            up_count = row.get('上涨家数', 0)
                            down_count = row.get('下跌家数', 0)
                            leading_stock = row.get('领涨股票', 'N/A')
                            leading_change = row.get('领涨股票-涨跌幅', 0)
                            
                            change_sign = "+" if change_amount >= 0 else ""
                            rate_sign = "+" if change_rate >= 0 else ""
                            
                            content = f"板块名称: {sector_name}\n"
                            content += f"最新价: {latest_price:.2f}\n"
                            content += f"涨跌: {change_sign}{change_amount:.2f}\n"
                            content += f"涨跌幅: {rate_sign}{change_rate:.2f}%\n"
                            content += f"总市值: {market_cap:.0f}亿元\n"
                            content += f"换手率: {turnover_rate:.2f}%\n"
                            content += f"上涨家数: {up_count}\n"
                            content += f"下跌家数: {down_count}\n"
                            content += f"领涨股票: {leading_stock} ({leading_change:+.2f}%)\n"
                            
                            all_records.append({
                                "title": f"{trade_date} 板块资金流向: {sector_name}",
                                "content": content,
                                "pub_time": trigger_time,
                                "url": f"akshare://sector/{sector_name}/{trade_date}"
                            })
                        except Exception as e:
                            logger.warning(f"处理板块数据失败: {e}")
                            continue
            except Exception as e:
                logger.warning(f"获取板块资金流向失败: {e}")
            
            # 如果没有数据，至少返回一条汇总记录
            if not all_records:
                summary = self.format_market_summary(trade_date)
                all_records.append({
                    "title": f"{trade_date}:市场宏观数据汇总",
                    "content": summary,
                    "pub_time": trigger_time,
                    "url": f"akshare://market_summary/{trade_date}"
                })
            
            df = pd.DataFrame(all_records)
            logger.info(f"成功获取市场数据: {trade_date}，共 {len(df)} 条记录")
            return df
                
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)


if __name__ == "__main__":
    # 测试代码
    market_data = MarketDataAkshare()
    trigger_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = asyncio.run(market_data.fetch_data_async(trigger_time))
    print(f"获取到 {len(df)} 条记录")
    if not df.empty:
        print("\n内容预览:")
        print(df['content'].values[0][:500])

