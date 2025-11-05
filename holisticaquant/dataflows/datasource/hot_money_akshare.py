"""
基于 akshare 的资金流数据源

整合涨跌停、龙虎榜、游资等资金流市场数据
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


class HotMoneyAkshare(DataSourceBase):
    """
    资金流数据源（基于 akshare）
    
    获取涨跌停、龙虎榜、概念板块、游资营业部等数据
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
        super().__init__("hot_money_akshare", max_size_kb=max_size_kb,
                        max_time_range_days=max_time_range_days,
                        max_records=max_records, use_cache=use_cache)

    def get_zt_data(self, trade_date: str) -> pd.DataFrame:
        """
        获取涨停股票数据
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            涨停股票 DataFrame
        """
        try:
            df = self._run_akshare(
                func_name="stock_zt_pool_em",
                func_kwargs={"date": trade_date},
                verbose=False
            )
            
            if df.empty:
                logger.warning(f"{trade_date} 无涨停数据")
                return pd.DataFrame()
            
            logger.info(f"获取 {trade_date} 涨停数据成功，{len(df)} 条记录")
            return df
            
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
                logger.error(f"获取涨停数据失败: {error_msg}")
            else:
                logger.warning(f"获取涨停数据失败（{error_type}）: {error_msg}")
            return pd.DataFrame()

    def get_dt_data(self, trade_date: str) -> pd.DataFrame:
        """
        获取跌停股票数据
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            跌停股票 DataFrame
        """
        try:
            df = self._run_akshare(
                func_name="stock_zt_pool_dtgc_em",
                func_kwargs={"date": trade_date},
                verbose=False
            )
            
            if df.empty:
                logger.warning(f"{trade_date} 无跌停数据")
                return pd.DataFrame()
            
            logger.info(f"获取 {trade_date} 跌停数据成功，{len(df)} 条记录")
            return df
            
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
                logger.error(f"获取跌停数据失败: {error_msg}")
            else:
                logger.warning(f"获取跌停数据失败（{error_type}）: {error_msg}")
            return pd.DataFrame()

    def get_lhb_data(self, trade_date: str) -> pd.DataFrame:
        """
        获取龙虎榜数据（近10天）
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            龙虎榜数据 DataFrame
        """
        try:
            # 计算10天前的日期
            end_date = trade_date
            start_date_obj = datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=10)
            start_date = start_date_obj.strftime('%Y%m%d')
            
            df = self._run_akshare(
                func_name="stock_lhb_detail_em",
                func_kwargs={"start_date": start_date, "end_date": end_date},
                verbose=False
            )
            
            if df.empty:
                logger.warning(f"{start_date}到{end_date} 无龙虎榜数据")
                return pd.DataFrame()
            
            logger.info(f"获取 {start_date}到{end_date} 龙虎榜数据成功，{len(df)} 条记录")
            return df
            
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
                logger.error(f"获取龙虎榜数据失败: {error_msg}")
            else:
                logger.warning(f"获取龙虎榜数据失败（{error_type}）: {error_msg}")
            return pd.DataFrame()

    def get_lhb_jg_data(self, trade_date: str) -> pd.DataFrame:
        """
        获取龙虎榜机构明细数据（近10天）
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            龙虎榜机构数据 DataFrame
        """
        try:
            # 计算10天前的日期
            end_date = trade_date
            start_date_obj = datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=10)
            start_date = start_date_obj.strftime('%Y%m%d')
            
            df = self._run_akshare(
                func_name="stock_lhb_jgmmtj_em",
                func_kwargs={"start_date": start_date, "end_date": end_date},
                verbose=False
            )
            
            if df.empty:
                logger.warning(f"{start_date}到{end_date} 无龙虎榜机构数据")
                return pd.DataFrame()
            
            logger.info(f"获取 {start_date}到{end_date} 龙虎榜机构数据成功，{len(df)} 条记录")
            return df
            
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
                logger.error(f"获取龙虎榜机构数据失败: {error_msg}")
            else:
                logger.warning(f"获取龙虎榜机构数据失败（{error_type}）: {error_msg}")
            return pd.DataFrame()

    def get_concept_data(self) -> pd.DataFrame:
        """
        获取概念板块资金流数据
        
        Returns:
            概念板块数据 DataFrame
        """
        try:
            df = self._run_akshare(
                func_name="stock_board_concept_name_em",
                func_kwargs={},
                verbose=False
            )
            
            if df.empty:
                logger.warning("无概念板块数据")
                return pd.DataFrame()
            
            logger.info(f"获取概念板块数据成功，{len(df)} 条记录")
            return df
            
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
                logger.error(f"获取概念板块数据失败: {error_msg}")
            else:
                logger.warning(f"获取概念板块数据失败（{error_type}）: {error_msg}")
            return pd.DataFrame()

    def get_yyb_data(self) -> pd.DataFrame:
        """
        获取游资营业部资金数据
        
        Returns:
            游资营业部数据 DataFrame
        """
        try:
            df = self._run_akshare(
                func_name="stock_lh_yyb_capital",
                func_kwargs={},
                verbose=False
            )
            
            if df.empty:
                logger.warning("无游资营业部数据")
                return pd.DataFrame()
            
            logger.info(f"获取游资营业部数据成功，{len(df)} 条记录")
            return df
            
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
                logger.error(f"获取游资营业部数据失败: {error_msg}")
            else:
                logger.warning(f"获取游资营业部数据失败（{error_type}）: {error_msg}")
            return pd.DataFrame()

    def format_fund_flow_summary(self, trade_date: str) -> str:
        """
        格式化资金流数据摘要（不含LLM总结）
        
        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            
        Returns:
            格式化的资金流数据摘要文本
        """
        try:
            # 获取各类数据
            zt_data = self.get_zt_data(trade_date)
            dt_data = self.get_dt_data(trade_date)
            lhb_data = self.get_lhb_data(trade_date)
            lhb_jg_data = self.get_lhb_jg_data(trade_date)
            concept_data = self.get_concept_data()
            yyb_data = self.get_yyb_data()
            
            sections = [f"## {trade_date} 资金流数据摘要\n"]
            
            # 一、涨跌停情况
            if not zt_data.empty or not dt_data.empty:
                sections.append("### 一、涨跌停情况\n")
                
                if not zt_data.empty:
                    zt_count = len(zt_data)
                    # 连板股统计
                    if '连板数' in zt_data.columns:
                        lianbao_stats = zt_data['连板数'].value_counts().sort_index(ascending=False)
                        sections.append(f"**涨停股票**: 共{zt_count}只")
                        sections.append(f"**连板分布**: {dict(lianbao_stats)}")
                        top_zt = zt_data.head(5)
                        sections.append("**主要涨停股票**:")
                        for _, row in top_zt.iterrows():
                            sections.append(
                                f"- {row.get('名称', 'N/A')}({row.get('代码', 'N/A')}): "
                                f"{row.get('涨跌幅', 0):.2f}%, "
                                f"连板{row.get('连板数', 0)}天, "
                                f"炸板{row.get('炸板次数', 0)}次"
                            )
                
                if not dt_data.empty:
                    dt_count = len(dt_data)
                    sections.append(f"**跌停股票**: 共{dt_count}只")
                    if dt_count <= 5:
                        for _, row in dt_data.iterrows():
                            sections.append(
                                f"- {row.get('名称', 'N/A')}({row.get('代码', 'N/A')}): "
                                f"{row.get('涨跌幅', 0):.2f}%, "
                                f"连续跌停{row.get('连续跌停', 0)}天"
                            )
                sections.append("")  # 空行
            
            # 二、龙虎榜活跃度
            if not lhb_data.empty:
                sections.append("### 二、龙虎榜活跃度\n")
                
                lhb_count = len(lhb_data)
                # 按上榜日期统计最近几天的数据
                recent_lhb = lhb_data[lhb_data.get('上榜日', '') == trade_date] if '上榜日' in lhb_data.columns else lhb_data
                recent_count = len(recent_lhb)
                
                sections.append(f"**龙虎榜上榜股票**: 近10天共{lhb_count}只，{trade_date}当日{recent_count}只")
                
                if not recent_lhb.empty and recent_count <= 10:
                    sections.append("**当日主要龙虎榜股票**:")
                    for _, row in recent_lhb.head(5).iterrows():
                        net_buy = row.get('龙虎榜净买额', 0)
                        net_buy_str = f"{net_buy/10000:.0f}万" if abs(net_buy) < 100000000 else f"{net_buy/100000000:.2f}亿"
                        sections.append(
                            f"- {row.get('名称', 'N/A')}({row.get('代码', 'N/A')}): "
                            f"{row.get('涨跌幅', 0):.2f}%, "
                            f"净买额{net_buy_str}"
                        )
                sections.append("")  # 空行
            
            # 三、机构参与情况
            if not lhb_jg_data.empty:
                sections.append("### 三、机构参与情况\n")
                
                jg_count = len(lhb_jg_data)
                total_net_buy = lhb_jg_data['机构买入净额'].sum() if '机构买入净额' in lhb_jg_data.columns else 0
                
                sections.append(f"**机构参与股票**: {jg_count}只")
                sections.append(f"**机构净买入**: {total_net_buy/100000000:.2f}亿元")
                
                top_jg = lhb_jg_data.head(3)
                if not top_jg.empty:
                    sections.append("**主要机构参与股票**:")
                    for _, row in top_jg.iterrows():
                        net_buy = row.get('机构买入净额', 0)
                        sections.append(
                            f"- {row.get('名称', 'N/A')}: "
                            f"机构净买额{net_buy/10000:.0f}万元"
                        )
                sections.append("")  # 空行
            
            # 四、概念板块热度
            if not concept_data.empty:
                sections.append("### 四、概念板块热度\n")
                
                top_concepts = concept_data.head(5)
                sections.append("**热门概念板块**:")
                for _, row in top_concepts.iterrows():
                    up_count = row.get('上涨家数', 0)
                    down_count = row.get('下跌家数', 0)
                    total_count = up_count + down_count
                    up_ratio = (up_count / total_count * 100) if total_count > 0 else 0
                    sections.append(
                        f"- {row.get('板块名称', 'N/A')}: "
                        f"{row.get('涨跌幅', 0):.2f}%, "
                        f"上涨率{up_ratio:.0f}%({up_count}/{total_count})"
                    )
                sections.append("")  # 空行
            
            # 五、游资营业部活跃度
            if not yyb_data.empty:
                sections.append("### 五、游资营业部活跃度\n")
                
                yyb_count = len(yyb_data)
                sections.append(f"**活跃游资营业部**: {yyb_count}家")
                
                top_yyb = yyb_data.head(3)
                if not top_yyb.empty:
                    sections.append("**主要活跃营业部**:")
                    for _, row in top_yyb.iterrows():
                        yyb_name = row.get('营业部名称', 'N/A')
                        sections.append(
                            f"- {yyb_name}: "
                            f"今日操作{row.get('今日最高操作', 0)}次, "
                            f"最高金额{row.get('今日最高金额', 0)}"
                        )
            
            return "\n".join(sections)
            
        except Exception as e:
            logger.error(f"格式化资金流数据摘要失败: {e}")
            return f"格式化资金流数据摘要失败: {str(e)}"

    async def get_data(self, trigger_time: str, **query_params) -> pd.DataFrame:
        """
        实现基类的抽象方法，获取数据
        
        将各类数据拆分成多条记录，每条记录对应一个实体（如一只股票、一个板块等）
        
        Args:
            trigger_time: 触发时间字符串，格式 'YYYY-MM-DD HH:MM:SS'
            
        Returns:
            DataFrame with columns ['title', 'content', 'pub_time', 'url']
        """
        try:
            # 获取上一个交易日
            trade_date = get_previous_trading_date(trigger_time)
            logger.info(f"获取 {trade_date} 的资金流数据（trigger_time: {trigger_time}）")
            
            all_records = []
            
            # 1. 涨停股票 - 每条股票一条记录
            zt_data = self.get_zt_data(trade_date)
            if not zt_data.empty:
                for _, row in zt_data.iterrows():
                    try:
                        stock_name = row.get('名称', 'N/A')
                        stock_code = row.get('代码', 'N/A')
                        change_rate = row.get('涨跌幅', 0)
                        lianbao = row.get('连板数', 0)
                        zaban = row.get('炸板次数', 0)
                        latest_price = row.get('最新价', 0)
                        
                        content = f"股票代码: {stock_code}\n"
                        content += f"股票名称: {stock_name}\n"
                        content += f"最新价: {latest_price:.2f}\n"
                        content += f"涨跌幅: {change_rate:.2f}%\n"
                        content += f"连板数: {lianbao}天\n"
                        content += f"炸板次数: {zaban}次\n"
                        if '封单金额' in row:
                            content += f"封单金额: {row.get('封单金额', 0):.0f}万元\n"
                        
                        all_records.append({
                            "title": f"{trade_date} 涨停股票: {stock_name}({stock_code})",
                            "content": content,
                            "pub_time": trigger_time,
                            "url": f"akshare://stock/zt/{stock_code}/{trade_date}"
                        })
                    except Exception as e:
                        logger.warning(f"处理涨停股票数据失败: {e}")
                        continue
            
            # 2. 跌停股票 - 每条股票一条记录
            dt_data = self.get_dt_data(trade_date)
            if not dt_data.empty:
                for _, row in dt_data.iterrows():
                    try:
                        stock_name = row.get('名称', 'N/A')
                        stock_code = row.get('代码', 'N/A')
                        change_rate = row.get('涨跌幅', 0)
                        lianxu_dt = row.get('连续跌停', 0)
                        latest_price = row.get('最新价', 0)
                        
                        content = f"股票代码: {stock_code}\n"
                        content += f"股票名称: {stock_name}\n"
                        content += f"最新价: {latest_price:.2f}\n"
                        content += f"涨跌幅: {change_rate:.2f}%\n"
                        content += f"连续跌停: {lianxu_dt}天\n"
                        
                        all_records.append({
                            "title": f"{trade_date} 跌停股票: {stock_name}({stock_code})",
                            "content": content,
                            "pub_time": trigger_time,
                            "url": f"akshare://stock/dt/{stock_code}/{trade_date}"
                        })
                    except Exception as e:
                        logger.warning(f"处理跌停股票数据失败: {e}")
                        continue
            
            # 3. 龙虎榜股票 - 每条股票一条记录（只取当日数据）
            lhb_data = self.get_lhb_data(trade_date)
            if not lhb_data.empty:
                # 筛选当日数据
                if '上榜日' in lhb_data.columns:
                    today_lhb = lhb_data[lhb_data['上榜日'] == trade_date]
                else:
                    today_lhb = lhb_data.head(20)  # 如果没有日期列，取前20条
                
                for _, row in today_lhb.iterrows():
                    try:
                        stock_name = row.get('名称', 'N/A')
                        stock_code = row.get('代码', 'N/A')
                        change_rate = row.get('涨跌幅', 0)
                        net_buy = row.get('龙虎榜净买额', 0)
                        net_buy_str = f"{net_buy/10000:.0f}万" if abs(net_buy) < 100000000 else f"{net_buy/100000000:.2f}亿"
                        
                        content = f"股票代码: {stock_code}\n"
                        content += f"股票名称: {stock_name}\n"
                        content += f"涨跌幅: {change_rate:.2f}%\n"
                        content += f"龙虎榜净买额: {net_buy_str}\n"
                        if '买入额' in row:
                            buy_amount = row.get('买入额', 0)
                            content += f"买入额: {buy_amount/10000:.0f}万元\n"
                        if '卖出额' in row:
                            sell_amount = row.get('卖出额', 0)
                            content += f"卖出额: {sell_amount/10000:.0f}万元\n"
                        
                        all_records.append({
                            "title": f"{trade_date} 龙虎榜: {stock_name}({stock_code})",
                            "content": content,
                            "pub_time": trigger_time,
                            "url": f"akshare://stock/lhb/{stock_code}/{trade_date}"
                        })
                    except Exception as e:
                        logger.warning(f"处理龙虎榜数据失败: {e}")
                        continue
            
            # 4. 概念板块 - 每个板块一条记录（取前20个）
            concept_data = self.get_concept_data()
            if not concept_data.empty:
                top_concepts = concept_data.head(20)
                for _, row in top_concepts.iterrows():
                    try:
                        concept_name = row.get('板块名称', 'N/A')
                        change_rate = row.get('涨跌幅', 0)
                        up_count = row.get('上涨家数', 0)
                        down_count = row.get('下跌家数', 0)
                        total_count = up_count + down_count
                        up_ratio = (up_count / total_count * 100) if total_count > 0 else 0
                        
                        content = f"板块名称: {concept_name}\n"
                        content += f"涨跌幅: {change_rate:.2f}%\n"
                        content += f"上涨家数: {up_count}\n"
                        content += f"下跌家数: {down_count}\n"
                        content += f"上涨率: {up_ratio:.0f}%\n"
                        if '总市值' in row:
                            market_cap = row.get('总市值', 0) / 100000000
                            content += f"总市值: {market_cap:.0f}亿元\n"
                        
                        all_records.append({
                            "title": f"{trade_date} 概念板块: {concept_name}",
                            "content": content,
                            "pub_time": trigger_time,
                            "url": f"akshare://concept/{concept_name}/{trade_date}"
                        })
                    except Exception as e:
                        logger.warning(f"处理概念板块数据失败: {e}")
                        continue
            
            # 5. 机构参与股票 - 每条股票一条记录（取前10个）
            lhb_jg_data = self.get_lhb_jg_data(trade_date)
            if not lhb_jg_data.empty:
                top_jg = lhb_jg_data.head(10)
                for _, row in top_jg.iterrows():
                    try:
                        stock_name = row.get('名称', 'N/A')
                        stock_code = row.get('代码', 'N/A')
                        net_buy = row.get('机构买入净额', 0)
                        net_buy_str = f"{net_buy/10000:.0f}万元" if abs(net_buy) < 100000000 else f"{net_buy/100000000:.2f}亿元"
                        
                        content = f"股票代码: {stock_code}\n"
                        content += f"股票名称: {stock_name}\n"
                        content += f"机构买入净额: {net_buy_str}\n"
                        
                        all_records.append({
                            "title": f"{trade_date} 机构参与: {stock_name}({stock_code})",
                            "content": content,
                            "pub_time": trigger_time,
                            "url": f"akshare://stock/jg/{stock_code}/{trade_date}"
                        })
                    except Exception as e:
                        logger.warning(f"处理机构参与数据失败: {e}")
                        continue
            
            # 如果没有数据，至少返回一条汇总记录
            if not all_records:
                summary = self.format_fund_flow_summary(trade_date)
                all_records.append({
                    "title": f"{trade_date}:资金流数据汇总",
                    "content": summary,
                    "pub_time": trigger_time,
                    "url": f"akshare://fund_flow_summary/{trade_date}"
                })
            
            df = pd.DataFrame(all_records)
            logger.info(f"成功获取资金流数据: {trade_date}，共 {len(df)} 条记录")
            return df
                
        except Exception as e:
            logger.error(f"获取资金流数据失败: {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)


if __name__ == "__main__":
    # 测试代码
    hot_money = HotMoneyAkshare()
    trigger_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = asyncio.run(hot_money.fetch_data_async(trigger_time))
    print(f"获取到 {len(df)} 条记录")
    if not df.empty:
        print("\n内容预览:")
        print(df['content'].values[0][:500])

