"""
配置管理模块

支持环境变量覆盖和动态配置更新
支持多个LLM提供商（豆包、chatgpt、claude、deepseek等）
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


class GlobalConfig:
    """
    全局配置管理器
    
    特性：
    - 支持环境变量覆盖
    - 支持动态配置更新
    - 支持配置继承和合并
    - LLM提供商优先级：豆包 > chatgpt > claude > deepseek
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self._config = self._load_default_config()
        
        # 加载配置文件（如果存在）
        if config_file and Path(config_file).exists():
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                self._config = self._deep_merge(self._config, file_config)
        
        # 环境变量覆盖
        self._apply_env_overrides()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            # LLM配置（优先级：豆包 > chatgpt > claude > deepseek）
            "llm": {
                "provider": "doubao",  # 默认使用豆包
                "providers": {
                    # 豆包（字节跳动）
                    "doubao": {
                        "enabled": True,
                        "priority": 1,
                        "base_url": os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
                        "api_key": os.getenv("DOUBAO_API_KEY") or os.getenv("BUILTIN_DOUBAO_API_KEY"),
                        "model": os.getenv("DOUBAO_MODEL", "doubao-pro-4k"),
                    },
                    # ChatGPT (OpenAI)
                    "chatgpt": {
                        "enabled": True,
                        "priority": 2,
                        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                        "api_key": os.getenv("OPENAI_API_KEY") or os.getenv("BUILTIN_OPENAI_API_KEY"),
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    },
                    # Claude (Anthropic)
                    "claude": {
                        "enabled": True,
                        "priority": 3,
                        "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
                        "api_key": os.getenv("ANTHROPIC_API_KEY") or os.getenv("BUILTIN_ANTHROPIC_API_KEY"),
                        "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                    },
                    # DeepSeek
                    "deepseek": {
                        "enabled": True,
                        "priority": 4,
                        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                        "api_key": os.getenv("DEEPSEEK_API_KEY") or os.getenv("BUILTIN_DEEPSEEK_API_KEY"),
                        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                    },
                },
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
                "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4000")),
            },
            
            # 数据源配置（供应商无关）
            "data_vendors": {
                "market": {
                    "primary": os.getenv("MARKET_VENDOR_PRIMARY", "akshare"),
                    "fallback": os.getenv("MARKET_VENDOR_FALLBACK", "yfinance").split(",") if os.getenv("MARKET_VENDOR_FALLBACK") else [],
                    "enabled": True,
                },
                "fundamental": {
                    "primary": os.getenv("FUNDAMENTAL_VENDOR_PRIMARY", "akshare"),
                    "fallback": os.getenv("FUNDAMENTAL_VENDOR_FALLBACK", "yfinance").split(",") if os.getenv("FUNDAMENTAL_VENDOR_FALLBACK") else [],
                    "enabled": True,
                },
                "news": {
                    "primary": os.getenv("NEWS_VENDOR_PRIMARY", "sina"),
                    "fallback": os.getenv("NEWS_VENDOR_FALLBACK", "thx").split(",") if os.getenv("NEWS_VENDOR_FALLBACK") else [],
                    "enabled": True,
                },
                "use_cache": os.getenv("USE_CACHE", "false").lower() == "true",
            },
            
            # Agent配置
            "agents": {
                "max_iterations": int(os.getenv("MAX_ITERATIONS", "3")),
                "max_collection_iterations": int(os.getenv("MAX_COLLECTION_ITERATIONS", "1")),
                "reflection": {
                    "enabled": os.getenv("REFLECTION_ENABLED", "true").lower() == "true",
                    "quality_threshold": float(os.getenv("QUALITY_THRESHOLD", "0.6")),
                    "max_retries": int(os.getenv("MAX_RETRIES", "1")),
                },
                "data_sufficiency": {
                    "min_confidence": float(os.getenv("DATA_SUFFICIENCY_MIN_CONFIDENCE", "0.6")),
                    "min_tools_called": int(os.getenv("DATA_SUFFICIENCY_MIN_TOOLS", "2")),
                    "early_stop": os.getenv("DATA_SUFFICIENCY_EARLY_STOP", "true").lower() == "true",
                },
            },
            
            # 工具路由配置
            "tools": {
                "routing": {
                    "enabled": True,
                },
                "max_result_length": int(os.getenv("TOOL_MAX_RESULT_LENGTH", "3000")),
                "max_records": int(os.getenv("TOOL_MAX_RECORDS", "50")),
                "news": {
                    "sina": {
                        "enabled": os.getenv("TOOL_SINA_NEWS_ENABLED", "true").lower() == "true",
                        "end_page": int(os.getenv("TOOL_SINA_NEWS_END_PAGE", "3")),
                    },
                    "thx": {
                        "enabled": os.getenv("TOOL_THX_NEWS_ENABLED", "true").lower() == "true",
                        "max_pages": int(os.getenv("TOOL_THX_NEWS_MAX_PAGES", "2")),
                    },
                },
            },
            
            # Agentic RAG配置
            "agentic_rag": {
                "enabled": os.getenv("AGENTIC_RAG_ENABLED", "false").lower() == "true",
                "max_insights": int(os.getenv("AGENTIC_RAG_MAX_INSIGHTS", "100")),
                "forget_days": int(os.getenv("AGENTIC_RAG_FORGET_DAYS", "90")),
                "extract_insights": os.getenv("AGENTIC_RAG_EXTRACT_INSIGHTS", "true").lower() == "true",
                "vector_store": {
                    "enabled": os.getenv("AGENTIC_RAG_VECTOR_STORE_ENABLED", "false").lower() == "true",
                    "db_path": os.getenv(
                        "AGENTIC_RAG_VECTOR_DB_PATH",
                        "holisticaquant/memory/data/financial_insights.sqlite",
                    ),
                    "model": os.getenv(
                        "AGENTIC_RAG_VECTOR_MODEL",
                        "sentence-transformers/all-MiniLM-L6-v2",
                    ),
                },
            },
            
            # 项目路径
            "project_root": str(PROJECT_ROOT),
            "debug": os.getenv("DEBUG", "false").lower() == "true",
            
            # 部署模式
            "deployment_mode": os.getenv("DEPLOYMENT_MODE", "development"),
        }
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # 支持嵌套配置的环境变量（如 LLM__PROVIDER -> config["llm"]["provider"]）
        for key, value in os.environ.items():
            if "__" in key:
                parts = key.lower().split("__")
                self._set_nested(self._config, parts, value)
    
    def _set_nested(self, config: dict, parts: list, value: Any):
        """设置嵌套配置值"""
        key = parts[0]
        if len(parts) == 1:
            # 类型转换
            if isinstance(config.get(key), bool):
                config[key] = value.lower() in ("true", "1", "yes")
            elif isinstance(config.get(key), int):
                try:
                    config[key] = int(value)
                except:
                    pass
            elif isinstance(config.get(key), float):
                try:
                    config[key] = float(value)
                except:
                    pass
            else:
                config[key] = value
        else:
            if key not in config:
                config[key] = {}
            self._set_nested(config[key], parts[1:], value)
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """深度合并配置"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值（支持点号路径）"""
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def set(self, key_path: str, value: Any):
        """动态更新配置值"""
        keys = key_path.split(".")
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def update(self, updates: dict):
        """批量更新配置"""
        self._config = self._deep_merge(self._config, updates)
    
    def get_llm_provider(self, priority: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取可用的LLM提供商（按优先级）
        
        Args:
            priority: 是否按优先级排序
            
        Returns:
            第一个可用的提供商配置，如果priority=True则按优先级返回
        """
        providers = self._config.get("llm", {}).get("providers", {})
        
        if not providers:
            return None
        
        # 按优先级排序并过滤已启用且有API key的
        available_providers = []
        for name, config in providers.items():
            if config.get("enabled", True) and config.get("api_key"):
                available_providers.append((config.get("priority", 999), name, config))
        
        if not available_providers:
            return None
        
        if priority:
            available_providers.sort(key=lambda x: x[0])
        
        return available_providers[0][2]  # 返回配置字典
    
    def get_builtin_api_keys(self) -> Dict[str, Optional[str]]:
        """
        获取内置API密钥（用于默认共享）
        
        Returns:
            包含各提供商内置密钥的字典
        """
        return {
            "doubao": os.getenv("BUILTIN_DOUBAO_API_KEY"),
            "chatgpt": os.getenv("BUILTIN_OPENAI_API_KEY"),
            "claude": os.getenv("BUILTIN_ANTHROPIC_API_KEY"),
            "deepseek": os.getenv("BUILTIN_DEEPSEEK_API_KEY"),
        }
    
    def get_provider_config_with_keys(
        self, 
        user_keys: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        获取LLM提供商配置，支持用户自定义密钥覆盖
        
        Args:
            user_keys: 用户自定义的API密钥字典，格式：{"doubao": "key", ...}
            
        Returns:
            更新后的LLM配置字典
        """
        config = self._config.copy()
        providers = config.get("llm", {}).get("providers", {})
        
        # 如果提供了用户密钥，优先使用用户密钥
        if user_keys:
            for provider_name, api_key in user_keys.items():
                if provider_name in providers and api_key:
                    providers[provider_name]["api_key"] = api_key
        
        return config
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()


# 全局配置实例
_global_config: Optional[GlobalConfig] = None


@lru_cache(maxsize=1)
def get_config(config_file: Optional[str] = None) -> GlobalConfig:
    """
    获取全局配置实例（单例模式）
    
    Args:
        config_file: 配置文件路径（可选）
        
    Returns:
        GlobalConfig实例
    """
    global _global_config
    if _global_config is None:
        _global_config = GlobalConfig(config_file)
    return _global_config


def reset_config():
    """重置配置（用于测试）"""
    global _global_config
    _global_config = None


# 向后兼容
DEFAULT_CONFIG = GlobalConfig().config
