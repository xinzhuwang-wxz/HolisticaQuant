"""
LLM工厂模块

支持多个LLM提供商（豆包、chatgpt、claude、deepseek等）
按优先级自动选择可用的提供商
"""

import os
from typing import Optional, Dict, Any
from langchain_core.language_models import BaseChatModel
from loguru import logger

from holisticaquant.config.config import get_config


def create_llm(
    provider: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> BaseChatModel:
    """
    创建LLM实例
    
    优先级：豆包 > chatgpt > claude > deepseek
    
    Args:
        provider: 指定的提供商名称（可选，如果不指定则自动选择）
        config: 配置字典（可选，如果不指定则使用全局配置）
        
    Returns:
        LangChain LLM实例
        
    Raises:
        ValueError: 如果没有可用的LLM提供商
    """
    if config is None:
        config = get_config().config
    
    llm_config = config.get("llm", {})
    providers = llm_config.get("providers", {})
    
    # 如果指定了provider，尝试使用它
    if provider:
        if provider not in providers:
            raise ValueError(f"不支持的LLM提供商: {provider}")
        provider_config = providers[provider]
        if not provider_config.get("enabled", True):
            raise ValueError(f"LLM提供商 {provider} 未启用")
        if not provider_config.get("api_key"):
            raise ValueError(f"LLM提供商 {provider} 缺少API key")
        return _create_llm_by_provider(provider, provider_config, llm_config)
    
    # 自动选择：按优先级找到第一个可用的
    available_providers = []
    for name, provider_config in providers.items():
        if provider_config.get("enabled", True) and provider_config.get("api_key"):
            priority = provider_config.get("priority", 999)
            available_providers.append((priority, name, provider_config))
    
    if not available_providers:
        raise ValueError(
            "没有可用的LLM提供商。请设置以下环境变量之一：\n"
            "- DOUBAO_API_KEY（豆包）\n"
            "- OPENAI_API_KEY（ChatGPT）\n"
            "- ANTHROPIC_API_KEY（Claude）\n"
            "- DEEPSEEK_API_KEY（DeepSeek）"
        )
    
    # 按优先级排序
    available_providers.sort(key=lambda x: x[0])
    priority, provider_name, provider_config = available_providers[0]
    
    logger.info(f"使用LLM提供商: {provider_name} (优先级: {priority})")
    
    return _create_llm_by_provider(provider_name, provider_config, llm_config)


def _create_llm_by_provider(
    provider: str,
    provider_config: Dict[str, Any],
    llm_config: Dict[str, Any]
) -> BaseChatModel:
    """
    根据提供商创建LLM实例
    
    Args:
        provider: 提供商名称
        provider_config: 提供商配置
        llm_config: LLM通用配置
        
    Returns:
        LangChain LLM实例
    """
    base_url = provider_config.get("base_url")
    api_key = provider_config.get("api_key")
    model = provider_config.get("model")
    temperature = llm_config.get("temperature", 0.7)
    max_tokens = llm_config.get("max_tokens", 4000)
    
    if provider == "doubao":
        # 豆包（字节跳动）- 使用ChatOpenAI兼容接口
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    elif provider == "chatgpt":
        # ChatGPT (OpenAI)
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    elif provider == "claude":
        # Claude (Anthropic)
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ImportError:
            # 如果langchain_anthropic未安装，使用ChatOpenAI兼容接口
            logger.warning("langchain_anthropic未安装，尝试使用ChatOpenAI兼容接口")
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
    
    elif provider == "deepseek":
        # DeepSeek - 使用ChatOpenAI兼容接口
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    else:
        raise ValueError(f"不支持的LLM提供商: {provider}")

