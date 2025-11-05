"""
akshare 工具函数

提供 akshare 数据获取的缓存功能
"""
import json
import hashlib
import pickle
from pathlib import Path
from datetime import datetime
from ...config.config import PROJECT_ROOT

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    ak = None


DEFAULT_AKSHARE_CACHE_DIR = Path(PROJECT_ROOT) / "holisticaquant" / "dataflows" / "datasource" / "data_cache" / "akshare"


class CachedAksharePro:
    """带缓存的 akshare 数据获取器"""
    
    def __init__(self, cache_dir=None, use_cache: bool = True):
        if not cache_dir:
            self.cache_dir = DEFAULT_AKSHARE_CACHE_DIR
        else:
            self.cache_dir = Path(cache_dir)
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache

    def run(self, func_name: str, func_kwargs: dict, verbose: bool = False, use_cache: bool = None):
        """
        运行 akshare 函数并缓存结果
        
        Args:
            func_name: akshare 函数名
            func_kwargs: 函数参数字典
            verbose: 是否打印详细信息
            use_cache: 是否使用缓存，None 表示使用实例的 use_cache 设置
            
        Returns:
            函数返回的 DataFrame 或其他结果
        """
        if not HAS_AKSHARE:
            raise ImportError("akshare 未安装，请运行: pip install akshare")
        
        # 确定是否使用缓存
        should_use_cache = use_cache if use_cache is not None else self.use_cache
        
        if not should_use_cache:
            # 如果禁用缓存，直接调用 akshare 函数，不缓存
            func_kwargs_dict = func_kwargs
            try:
                result = getattr(ak, func_name)(**func_kwargs_dict)
                return result
            except AttributeError:
                raise AttributeError(f"akshare函数 {func_name} 不存在，可能是akshare版本不兼容")
            except Exception as e:
                # 保留原始异常类型，但添加更详细的错误信息
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else f"{error_type}异常（无详细信息）"
                # 如果错误信息为空或None，使用异常类型
                if not error_msg or error_msg == "None":
                    error_msg = f"{error_type}异常"
                raise type(e)(f"akshare调用失败: {error_msg}") from e
        
        func_kwargs_str = json.dumps(func_kwargs, sort_keys=True)
        return self.run_with_cache(func_name, func_kwargs_str, verbose)

    def run_with_cache(self, func_name: str, func_kwargs: str, verbose: bool = False):
        """
        运行 akshare 函数并缓存结果（内部方法）
        
        Args:
            func_name: akshare 函数名
            func_kwargs: 函数参数的 JSON 字符串
            verbose: 是否打印详细信息
            
        Returns:
            函数返回的 DataFrame 或其他结果
        """
        if not HAS_AKSHARE:
            raise ImportError("akshare 未安装，请运行: pip install akshare")
        
        func_kwargs_dict = json.loads(func_kwargs)
        args_hash = hashlib.md5(str(func_kwargs_dict).encode()).hexdigest()
        trigger_time = datetime.now().strftime("%Y%m%d%H")
        args_hash = f"{args_hash}_{trigger_time}"
        
        func_cache_dir = self.cache_dir / func_name
        if not func_cache_dir.exists():
            func_cache_dir.mkdir(parents=True, exist_ok=True)
        
        func_cache_file = func_cache_dir / f"{args_hash}.pkl"
        
        if func_cache_file.exists():
            if verbose:
                print(f"从缓存加载: {func_cache_file}")
            with open(func_cache_file, "rb") as f:
                return pickle.load(f)
        else:
            if verbose:
                print(f"缓存未命中 {func_name}, 参数: {func_kwargs_dict}")
            
            try:
                result = getattr(ak, func_name)(**func_kwargs_dict)
            except AttributeError:
                raise AttributeError(f"akshare函数 {func_name} 不存在，可能是akshare版本不兼容")
            except Exception as e:
                # 保留原始异常类型，但添加更详细的错误信息
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else f"{error_type}异常（无详细信息）"
                # 如果错误信息为空或None，使用异常类型
                if not error_msg or error_msg == "None":
                    error_msg = f"{error_type}异常"
                raise type(e)(f"akshare调用失败: {error_msg}") from e
            
            if verbose:
                print(f"保存结果到: {func_cache_file}")
            with open(func_cache_file, "wb") as f:
                pickle.dump(result, f)
            
            return result


# 全局实例（默认启用缓存）
akshare_cached = CachedAksharePro(use_cache=True)

if __name__ == "__main__":
    if HAS_AKSHARE:
        # 测试代码
        stock_sse_summary_df = akshare_cached.run(
            func_name="stock_sse_summary", 
            func_kwargs={},
            verbose=True
        )
        print(stock_sse_summary_df)
    else:
        print("akshare 未安装，请运行: pip install akshare")

