import pandas as pd
import asyncio
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from ...config.config import PROJECT_ROOT


class DataSourceBase(ABC):
    """
    数据源基类，所有数据源都应该继承此类
    
    统一返回格式：DataFrame with columns ['title', 'content', 'pub_time', 'url']
    - title: 标题
    - content: 内容（纯文本，已去除HTML标签）
    - pub_time: 发布时间，格式 'YYYY-MM-DD HH:MM:SS'
    - url: 源链接
    
    限制选项：
    - max_size_kb: 最大数据大小（KB），None 表示无限制，默认 1024 KB (1MB)
    - max_time_range_days: 最大时间范围（天数），从 trigger_time 往前算，None 表示无限制，默认 7 天
    - max_records: 最大记录数，None 表示无限制，默认 1000 条
    """
    
    # 必需的数据列
    REQUIRED_COLUMNS = ['title', 'content', 'pub_time', 'url']
    
    def __init__(self, name: str, max_size_kb: Optional[float] = 512.0, 
                 max_time_range_days: Optional[int] = 7, max_records: Optional[int] = 500,
                 use_cache: bool = False):
        """
        初始化数据源
        
        Args:
            name: 数据源名称
            max_size_kb: 最大数据大小（KB），None 表示无限制，默认 512 KB
            max_time_range_days: 最大时间范围（天数），从 trigger_time 往前算，None 表示无限制，默认 7 天
            max_records: 最大记录数，None 表示无限制，默认 500 条
            use_cache: 是否使用缓存，False 表示每次都获取最新数据（适合LLM调用），默认 False
                      当 use_cache=False 时，会同时禁用 DataSourceBase 和 akshare_cached 的缓存
        """
        self.name = name
        self.max_size_kb = max_size_kb
        self.max_time_range_days = max_time_range_days
        self.max_records = max_records
        self.use_cache = use_cache
        self.data_cache_dir = Path(PROJECT_ROOT) / "holisticaquant" / "dataflows" / "datasource" / "data_cache" / self.name
        if not self.data_cache_dir.exists():
            self.data_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _run_akshare(self, func_name: str, func_kwargs: dict, verbose: bool = False):
        """
        统一调用 akshare_cached.run() 的辅助方法，自动传递 use_cache 参数
        
        Args:
            func_name: akshare 函数名
            func_kwargs: 函数参数字典
            verbose: 是否打印详细信息
            
        Returns:
            akshare 函数返回的结果
        """
        from ..utils.akshare_utils import akshare_cached
        return akshare_cached.run(
            func_name=func_name,
            func_kwargs=func_kwargs,
            verbose=verbose,
            use_cache=self.use_cache
        )

    def get_data_cached(self, trigger_time: str) -> Optional[pd.DataFrame]:
        """
        从缓存中获取数据
        
        Args:
            trigger_time: 触发时间字符串，格式 'YYYY-MM-DD HH:MM:SS'
            
        Returns:
            DataFrame 或 None（如果缓存不存在）
        """
        cache_file_name = trigger_time.replace(" ", "_").replace(":", "-")
        cache_file = self.data_cache_dir / f"{cache_file_name}.pkl"
        if cache_file.exists():
            try:
                df = pd.read_pickle(cache_file)
                # 确保 pub_time 是字符串格式
                if not df.empty and 'pub_time' in df.columns:
                    if df['pub_time'].dtype == 'datetime64[ns]':
                        df['pub_time'] = df['pub_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    elif df['pub_time'].dtype != 'object':
                        df['pub_time'] = df['pub_time'].astype(str)
                return df
            except Exception as e:
                print(f"读取缓存文件失败: {e}")
                return None
        return None

    def save_data_cached(self, trigger_time: str, data: pd.DataFrame):
        """
        保存数据到缓存
        
        Args:
            trigger_time: 触发时间字符串
            data: 要保存的 DataFrame
        """
        if data.empty:
            return
        cache_file_name = trigger_time.replace(" ", "_").replace(":", "-")
        cache_file = self.data_cache_dir / f"{cache_file_name}.pkl"
        try:
            data.to_pickle(cache_file)
        except Exception as e:
            print(f"保存缓存文件失败: {e}")

    def _calculate_dataframe_size_kb(self, df: pd.DataFrame) -> float:
        """
        计算 DataFrame 的内存大小（KB）
        
        Args:
            df: DataFrame
            
        Returns:
            大小（KB）
        """
        if df.empty:
            return 0.0
        # 使用 memory_usage 计算大小（字节），然后转换为 KB
        size_bytes = df.memory_usage(deep=True).sum()
        # 字符串列需要额外计算，使用近似值
        for col in df.columns:
            if df[col].dtype == 'object':
                # 估算字符串列的实际大小
                string_sizes = df[col].astype(str).str.len() * 4  # UTF-8 每个字符约4字节
                size_bytes += string_sizes.sum()
        return size_bytes / 1024.0
    
    def _trim_content_to_fit_size(self, df: pd.DataFrame, target_size_kb: float) -> pd.DataFrame:
        """
        通过截断内容字段来减小 DataFrame 大小
        
        Args:
            df: DataFrame
            target_size_kb: 目标大小（KB）
            
        Returns:
            调整后的 DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        current_size = self._calculate_dataframe_size_kb(df)
        
        if current_size <= target_size_kb:
            return df
        
        # 计算需要减少的比例
        reduction_factor = target_size_kb / current_size * 0.9  # 留10%余量
        
        # 按比例截断 content 字段
        if 'content' in df.columns:
            df['content'] = df['content'].astype(str).apply(
                lambda x: x[:int(len(x) * reduction_factor)] if x else ""
            )
        
        return df
    
    def normalize_dataframe(self, df: pd.DataFrame, trigger_time: Optional[str] = None) -> pd.DataFrame:
        """
        标准化 DataFrame 格式，确保包含所有必需列，并统一格式
        应用限制：时间范围、数据大小、记录数
        
        Args:
            df: 原始 DataFrame
            trigger_time: 触发时间字符串，用于时间范围筛选
            
        Returns:
            标准化后的 DataFrame
        """
        if df.empty:
            # 返回空的 DataFrame，但包含所有必需列
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        
        # 确保所有必需列都存在，缺失的用空字符串填充
        for col in self.REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        
        # 只保留必需的列
        df = df[self.REQUIRED_COLUMNS].copy()
        
        # 统一数据类型和格式
        df['title'] = df['title'].astype(str).fillna("")
        df['content'] = df['content'].astype(str).fillna("")
        df['url'] = df['url'].astype(str).fillna("")
        
        # 处理 pub_time：确保是字符串格式 'YYYY-MM-DD HH:MM:SS'
        if 'pub_time' in df.columns:
            # 如果是 datetime 类型，转换为字符串
            if pd.api.types.is_datetime64_any_dtype(df['pub_time']):
                df['pub_time'] = df['pub_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # 如果是字符串或其他类型，确保是字符串
                df['pub_time'] = df['pub_time'].astype(str).fillna("")
        
        # 去除重复行（基于 url，但如果 url 为空则基于 title+content）
        if 'url' in df.columns:
            # 如果 url 不为空，基于 url 去重
            if df['url'].notna().any() and (df['url'] != '').any():
                df = df.drop_duplicates(subset=['url'], keep='first').reset_index(drop=True)
            else:
                # 如果 url 都为空，基于 title+content 去重
                df = df.drop_duplicates(subset=['title', 'content'], keep='first').reset_index(drop=True)
        
        # 应用时间范围限制
        if trigger_time and self.max_time_range_days is not None and 'pub_time' in df.columns:
            try:
                end_dt = pd.to_datetime(trigger_time, errors='coerce')
                if not pd.isna(end_dt):
                    start_dt = end_dt - timedelta(days=self.max_time_range_days)
                    df['pub_time_dt'] = pd.to_datetime(df['pub_time'], errors='coerce')
                    # 允许 pub_time <= end_dt（包含等于，这样可以保留实时生成的数据）
                    mask = df['pub_time_dt'].notna() & (df['pub_time_dt'] >= start_dt) & (df['pub_time_dt'] <= end_dt)
                    df = df.loc[mask].reset_index(drop=True)
                    df = df.drop(columns=['pub_time_dt'], errors='ignore')
                    # 重新格式化时间
                    if 'pub_time' in df.columns:
                        df['pub_time'] = pd.to_datetime(df['pub_time'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
                        df['pub_time'] = df['pub_time'].fillna("")
            except Exception as e:
                print(f"时间范围筛选失败: {e}")
        
        # 应用记录数限制（优先保留最新的记录）
        if self.max_records is not None and len(df) > self.max_records:
            # 按时间排序，保留最新的记录
            if 'pub_time' in df.columns:
                try:
                    df['_sort_time'] = pd.to_datetime(df['pub_time'], errors='coerce')
                    df = df.sort_values('_sort_time', ascending=False, na_position='last')
                    df = df.drop(columns=['_sort_time'], errors='ignore')
                except Exception:
                    pass
            df = df.head(self.max_records).reset_index(drop=True)
        
        # 应用数据大小限制
        if self.max_size_kb is not None:
            current_size = self._calculate_dataframe_size_kb(df)
            if current_size > self.max_size_kb:
                # 首先尝试截断内容
                df = self._trim_content_to_fit_size(df, self.max_size_kb)
                current_size = self._calculate_dataframe_size_kb(df)
                
                # 如果还是太大，进一步减少记录数
                if current_size > self.max_size_kb:
                    # 计算需要的记录数（按比例）
                    target_records = int(len(df) * self.max_size_kb / current_size * 0.9)
                    if target_records > 0:
                        df = df.head(target_records).reset_index(drop=True)
        
        return df


    @abstractmethod
    def get_data(self, trigger_time: str, **query_params) -> pd.DataFrame:
        """
        子类必须实现此方法，从数据源获取原始数据
        
        Args:
            trigger_time: 触发时间字符串，格式 'YYYY-MM-DD HH:MM:SS'
            **query_params: 额外的查询参数（如 ticker、company_name 等，用于主动工具）
            
        Returns:
            DataFrame，应包含 ['title', 'content', 'pub_time', 'url'] 列
            如果子类实现是异步的，可以定义为 async 方法
        """
        pass
    
    def fetch_data(self, trigger_time: str, use_cache: Optional[bool] = None, **query_params) -> pd.DataFrame:
        """
        统一的获取数据接口（同步版本），自动处理缓存，支持查询参数
        
        Args:
            trigger_time: 触发时间字符串
            use_cache: 是否使用缓存，None 表示使用实例的 use_cache 设置
            **query_params: 额外的查询参数（如 ticker 等）
            
        Returns:
            标准化后的 DataFrame（已应用所有限制）
        """
        # 确定是否使用缓存
        should_use_cache = use_cache if use_cache is not None else self.use_cache
        
        # 生成缓存键（包含查询参数）
        cache_key = trigger_time
        if query_params:
            import json
            params_str = json.dumps(query_params, sort_keys=True)
            cache_key = f"{trigger_time}_{params_str}"
        
        # 如果启用缓存，先尝试从缓存获取
        if should_use_cache:
            cached_data = self.get_data_cached(cache_key)
            if cached_data is not None:
                return self.normalize_dataframe(cached_data, trigger_time)
        
        # 如果没有缓存或禁用缓存，调用子类实现的 get_data 方法
        try:
            data = self.get_data(trigger_time, **query_params)
            # 标准化数据并应用限制
            normalized_data = self.normalize_dataframe(data, trigger_time)
            # 如果启用缓存，保存到缓存
            if should_use_cache and not normalized_data.empty:
                self.save_data_cached(cache_key, normalized_data)
            return normalized_data
        except Exception as e:
            print(f"获取数据失败 [{self.name}]: {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
    
    async def fetch_data_async(self, trigger_time: str, use_cache: Optional[bool] = None, **query_params) -> pd.DataFrame:
        """
        统一的获取数据接口（异步版本），自动处理缓存，支持查询参数
        
        Args:
            trigger_time: 触发时间字符串
            use_cache: 是否使用缓存，None 表示使用实例的 use_cache 设置
            **query_params: 额外的查询参数（如 ticker 等）
            
        Returns:
            标准化后的 DataFrame（已应用所有限制）
        """
        # 确定是否使用缓存
        should_use_cache = use_cache if use_cache is not None else self.use_cache
        
        # 生成缓存键（包含查询参数）
        cache_key = trigger_time
        if query_params:
            import json
            params_str = json.dumps(query_params, sort_keys=True)
            cache_key = f"{trigger_time}_{params_str}"
        
        # 如果启用缓存，先尝试从缓存获取
        if should_use_cache:
            cached_data = self.get_data_cached(cache_key)
            if cached_data is not None:
                return self.normalize_dataframe(cached_data, trigger_time)
        
        # 如果没有缓存或禁用缓存，调用子类实现的 get_data 方法
        try:
            # 检查是否有异步实现
            if asyncio.iscoroutinefunction(self.get_data):
                data = await self.get_data(trigger_time, **query_params)
            else:
                # 如果没有异步实现，在后台线程中运行同步版本
                data = await asyncio.to_thread(self.get_data, trigger_time, **query_params)
            
            # 标准化数据并应用限制
            normalized_data = self.normalize_dataframe(data, trigger_time)
            # 如果启用缓存，保存到缓存
            if should_use_cache and not normalized_data.empty:
                self.save_data_cached(cache_key, normalized_data)
            return normalized_data
        except Exception as e:
            print(f"获取数据失败 [{self.name}]: {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    
    # Test the class
    # 注意：这是一个抽象类，不能直接实例化
    print("DataSourceBase 是一个抽象基类，需要子类实现 get_data 方法")
