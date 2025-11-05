"""
Base Agent 基类

封装所有agent的通用逻辑，减少代码冗余
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
import json
from datetime import datetime
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from loguru import logger

from .agent_states import AgentState, update_trace, add_error

# 工具结果截断配置（默认值，会被配置覆盖）
MAX_TOOL_RESULT_LENGTH = 3000  # 每个工具结果最多3000字符

def get_max_tool_result_length(config: Optional[Dict[str, Any]] = None) -> int:
    """从配置读取工具结果最大长度"""
    if config is None:
        from holisticaquant.config.config import get_config
        config = get_config().config
    return config.get("tools", {}).get("max_result_length", MAX_TOOL_RESULT_LENGTH)

def truncate_tool_result(result: str, max_length: Optional[int] = None, config: Optional[Dict[str, Any]] = None) -> str:
    """
    截断工具结果，避免token过多
    
    Args:
        result: 工具返回的原始结果
        max_length: 最大长度（可选，默认从配置读取）
        config: 配置字典（可选）
    
    Returns:
        截断后的结果（如果被截断，会添加提示信息）
    """
    if max_length is None:
        max_length = get_max_tool_result_length(config)
    if len(result) <= max_length:
        return result
    truncated = result[:max_length]
    return f"{truncated}\n\n...（结果已截断，原始长度: {len(result)}字符）"


class BaseAgent(ABC):
    """
    Agent基类
    
    封装通用功能：
    1. LLM访问
    2. 工具调用处理
    3. 错误处理和追踪
    4. 消息历史管理
    """
    
    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化Agent
        
        Args:
            name: agent名称
            llm: LangChain LLM实例
            tools: 工具列表（可选）
            config: 配置字典（可选）
        """
        self.name = name
        self.llm = llm
        self.tools = tools or []
        self.config = config or {}
        self.debug = self.config.get("debug", False)
    
    def handle_tool_calls(
        self,
        result: Any,
        messages: List[Any],
        state: Optional[AgentState] = None,
        max_iterations: Optional[int] = None
    ) -> tuple[List[Any], Dict[str, str], Any]:
        """
        处理工具调用（循环处理直到没有工具调用）
        
        Args:
            result: LLM返回结果
            messages: 消息历史
            state: Agent状态（可选，用于获取trigger_time）
            max_iterations: 最大迭代次数（可选，默认从配置读取）
            
        Returns:
            (更新后的消息列表, 工具调用结果字典, 最终LLM结果)
        """
        # 从配置读取max_iterations
        if max_iterations is None:
            max_iterations = self.config.get("agents", {}).get("max_iterations", 3)
        tool_results = {}
        messages.append(result)
        iteration = 0
        final_result = result  # 保存最终的LLM结果
        called_tools = set()  # 记录已调用的工具（工具名+参数），避免重复调用
        
        # 从state中获取trigger_time（如果可用）
        trigger_time_from_state = None
        if state and "context" in state and "trigger_time" in state["context"]:
            trigger_time_from_state = state["context"]["trigger_time"]
            if self.debug:
                logger.info(f"{self.name}: 从state中获取trigger_time: {trigger_time_from_state}")
        else:
            if self.debug:
                logger.warning(f"{self.name}: 无法从state中获取trigger_time，state={state}")
        
        while iteration < max_iterations:
            tool_calls = result.tool_calls if hasattr(result, 'tool_calls') and result.tool_calls else []
            
            if not tool_calls:
                # 如果没有工具调用，检查是否有content
                if not result.content or not result.content.strip():
                    # 如果content为空，但之前有工具调用，强制LLM生成内容
                    if tool_results:
                        if self.debug:
                            logger.warning(f"{self.name}: LLM返回空content但有工具调用结果，强制生成内容")
                        # 最后一次调用，不绑定工具，强制生成文本
                        # 关键优化：使用工具结果摘要，而不是整个messages历史，避免token过多
                        tool_summaries = []
                        for tool_name, tool_result in tool_results.items():
                            summary_length = min(500, len(tool_result))  # 每个工具结果最多500字符摘要
                            summary = tool_result[:summary_length]
                            if len(tool_result) > summary_length:
                                summary += f"\n...（已截断，完整结果共 {len(tool_result)} 字符）"
                            tool_summaries.append(f"**{tool_name}**:\n{summary}")
                        
                        tool_summary_text = "\n\n".join(tool_summaries)
                        tool_names = list(tool_results.keys())
                        
                        force_prompt = f"""**重要任务**：基于以下工具调用结果生成分析报告。

**已调用工具**：{', '.join(tool_names)}

**工具调用结果摘要**：

{tool_summary_text}

**要求**：请基于上述工具调用结果生成分析报告，不要再次调用工具。"""
                        
                        chain = self._create_chain(self.llm)
                        # 使用简洁的消息列表，而不是整个messages历史
                        from langchain_core.messages import SystemMessage, HumanMessage
                        force_messages = [
                            SystemMessage(content=self._get_system_message()),
                            HumanMessage(content=force_prompt)
                        ]
                        result = chain.invoke({
                            "user_input": force_prompt,
                            "messages": force_messages,
                        })
                        messages.append(result)
                        final_result = result
                break
            
            # 如果达到最大迭代次数，强制生成内容而不是继续调用工具
            if iteration >= max_iterations - 1:
                if self.debug:
                    logger.warning(f"{self.name}: 已达到最大迭代次数（{max_iterations}），强制生成内容而不是继续调用工具")
                # 最后一次迭代，不执行工具调用，直接强制生成内容
                if tool_results:
                    # 不绑定工具，强制生成文本
                    # 关键优化：使用工具结果摘要，而不是整个messages历史，避免token过多
                    tool_summaries = []
                    for tool_name, tool_result in tool_results.items():
                        summary_length = min(500, len(tool_result))  # 每个工具结果最多500字符摘要
                        summary = tool_result[:summary_length]
                        if len(tool_result) > summary_length:
                            summary += f"\n...（已截断，完整结果共 {len(tool_result)} 字符）"
                        tool_summaries.append(f"**{tool_name}**:\n{summary}")
                    
                    tool_summary_text = "\n\n".join(tool_summaries)
                    tool_names = list(tool_results.keys())
                    
                    chain = self._create_chain(self.llm)
                    continue_prompt = f"""**重要任务**：基于以下工具调用结果立即生成内容。

**已调用工具**：{', '.join(tool_names)}

**工具调用结果摘要**：

{tool_summary_text}

"""
                    if self.name == "plan_analyst":
                        continue_prompt += "**重要**：请基于上述工具调用结果立即输出JSON格式的数据收集计划。禁止输出思考过程、推理过程或任何标记。直接输出纯JSON对象，不要有任何其他文本。"
                    else:
                        continue_prompt += "**重要**：请基于上述工具调用结果立即生成分析报告，不要进行思考或推理，直接输出报告内容。不要再次调用工具。"
                    
                    # 使用简洁的消息列表，而不是整个messages历史
                    from langchain_core.messages import SystemMessage, HumanMessage
                    force_messages = [
                        SystemMessage(content=self._get_system_message()),
                        HumanMessage(content=continue_prompt)
                    ]
                    
                    result = chain.invoke({
                        "user_input": continue_prompt,
                        "messages": force_messages,
                    })
                    messages.append(result)
                    final_result = result
                    break
            
            # 执行所有工具调用（优化：支持并行执行）
            tool_messages = []
            
            # 第一步：收集所有需要执行的工具调用（排除重复的）
            tools_to_execute = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                
                # 强制使用state中的trigger_time（如果存在），忽略LLM提供的trigger_time
                # 这样可以确保数据一致性，避免LLM提供过时的trigger_time
                if trigger_time_from_state:
                    # 总是使用state中的trigger_time，覆盖LLM提供的值
                    old_trigger_time = tool_args.get("trigger_time")
                    if old_trigger_time != trigger_time_from_state:
                        if self.debug and old_trigger_time:
                            logger.debug(f"{self.name}: 工具 {tool_name} LLM提供的trigger_time ({old_trigger_time}) 已替换为state中的值 ({trigger_time_from_state})")
                        tool_args["trigger_time"] = trigger_time_from_state
                    elif self.debug:
                        logger.debug(f"{self.name}: 工具 {tool_name} 使用trigger_time: {trigger_time_from_state}")
                elif self.debug:
                    logger.debug(f"{self.name}: 工具 {tool_name} 未设置trigger_time，将使用工具默认值")
                
                # 生成工具调用唯一标识
                import json
                tool_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
                
                # 检查是否已经调用过相同的工具
                if tool_key in called_tools:
                    if self.debug:
                        logger.warning(f"{self.name}: 跳过重复的工具调用 {tool_name} with args {tool_args}")
                    if tool_name in tool_results:
                        tool_message = ToolMessage(
                            content=f"（已调用过，使用之前的结果）{tool_results[tool_name]}",
                            tool_call_id=tool_call.get("id", ""),
                        )
                        tool_messages.append(tool_message)
                    else:
                        tool_message = ToolMessage(
                            content=f"（已调用过此工具，但之前的结果不可用）",
                            tool_call_id=tool_call.get("id", ""),
                        )
                        tool_messages.append(tool_message)
                    continue
                
                # 记录已调用的工具
                called_tools.add(tool_key)
                
                # 找到对应的工具
                tool_func = None
                for tool in self.tools:
                    if tool.name == tool_name:
                        tool_func = tool
                        break
                
                if not self.tools:
                    logger.error(f"{self.name}: LLM返回了工具调用 {tool_name}，但此agent没有工具。")
                    tool_message = ToolMessage(
                        content=f"错误: 此agent没有工具可用，无法调用 {tool_name}。请直接生成报告，不要调用任何工具。",
                        tool_call_id=tool_call.get("id", ""),
                    )
                    tool_messages.append(tool_message)
                    continue
                
                if tool_func:
                    tools_to_execute.append((tool_call, tool_func, tool_name, tool_args))
                else:
                    # 构建可用工具列表
                    available_tools = [tool.name for tool in self.tools] if self.tools else []
                    available_tools_str = ", ".join(available_tools) if available_tools else "无"
                    
                    logger.warning(f"{self.name}: 未找到工具 {tool_name}。可用工具: {available_tools_str}")
                    tool_message = ToolMessage(
                        content=f"错误: 未找到工具 {tool_name}。此agent的可用工具列表: [{available_tools_str}]。请只使用可用工具，不要调用不存在的工具。",
                        tool_call_id=tool_call.get("id", ""),
                    )
                    tool_messages.append(tool_message)
            
            # 第二步：并行执行工具调用
            if tools_to_execute:
                if self.debug:
                    logger.info(f"{self.name}: 并行执行 {len(tools_to_execute)} 个工具调用")
                
                import concurrent.futures
                import threading
                
                def execute_single_tool(tool_call, tool_func, tool_name, tool_args):
                    """执行单个工具的工具函数"""
                    try:
                        # 参数类型转换：确保 web_search 的 query 是字符串
                        if tool_name == "web_search" and "query" in tool_args:
                            if isinstance(tool_args["query"], list):
                                tool_args["query"] = " ".join(tool_args["query"])  # 列表转字符串
                                if self.debug:
                                    logger.debug(f"{self.name}: web_search query参数从列表转换为字符串: {tool_args['query'][:100]}...")
                            elif not isinstance(tool_args["query"], str):
                                tool_args["query"] = str(tool_args["query"])  # 其他类型转字符串
                                if self.debug:
                                    logger.debug(f"{self.name}: web_search query参数转换为字符串: {tool_args['query'][:100]}...")
                        
                        if self.debug:
                            logger.info(f"{self.name}: 开始执行工具 {tool_name} with args {tool_args}")
                        tool_result = tool_func.invoke(tool_args)
                        
                        # 检查返回结果是否包含错误信息
                        result_str = str(tool_result)
                        is_error = (
                            result_str.startswith("错误:") or 
                            result_str.startswith("错误") or
                            "失败" in result_str or
                            "error" in result_str.lower()
                        )
                        
                        # 记录工具调用结果到metadata（用于追踪失败的工具）
                        if state and "metadata" in state:
                            if "tool_stats" not in state["metadata"]:
                                state["metadata"]["tool_stats"] = {}
                            if tool_name not in state["metadata"]["tool_stats"]:
                                state["metadata"]["tool_stats"][tool_name] = {
                                    "success_count": 0,
                                    "failure_count": 0,
                                    "last_success": None,
                                    "last_failure": None,
                                }
                            
                            if is_error:
                                state["metadata"]["tool_stats"][tool_name]["failure_count"] += 1
                                state["metadata"]["tool_stats"][tool_name]["last_failure"] = datetime.now().isoformat()
                                if self.debug:
                                    logger.warning(f"{self.name}: 工具 {tool_name} 返回错误结果")
                            else:
                                state["metadata"]["tool_stats"][tool_name]["success_count"] += 1
                                state["metadata"]["tool_stats"][tool_name]["last_success"] = datetime.now().isoformat()
                        
                        return tool_call, tool_name, result_str, None
                    except Exception as e:
                        error_msg = f"工具 {tool_name} 调用失败: {e}"
                        logger.error(f"{self.name}: {error_msg}")
                        
                        # 记录失败到metadata
                        if state and "metadata" in state:
                            if "tool_stats" not in state["metadata"]:
                                state["metadata"]["tool_stats"] = {}
                            if tool_name not in state["metadata"]["tool_stats"]:
                                state["metadata"]["tool_stats"][tool_name] = {
                                    "success_count": 0,
                                    "failure_count": 0,
                                    "last_success": None,
                                    "last_failure": None,
                                }
                            state["metadata"]["tool_stats"][tool_name]["failure_count"] += 1
                            state["metadata"]["tool_stats"][tool_name]["last_failure"] = datetime.now().isoformat()
                        
                        return tool_call, tool_name, f"错误: {error_msg}", error_msg
                
                # 使用线程池并行执行（因为工具是同步的）
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tools_to_execute), 6)) as executor:
                    futures = {
                        executor.submit(execute_single_tool, tc, tf, tn, ta): (tc, tn)
                        for tc, tf, tn, ta in tools_to_execute
                    }
                    
                    for future in concurrent.futures.as_completed(futures):
                        tool_call, tool_name, result, error = future.result()
                        
                        # 存储结果（完整结果，用于工具结果字典）
                        tool_results[tool_name] = result
                        
                        # 截断工具结果，避免token过多
                        truncated_result = truncate_tool_result(result, config=self.config)
                        if len(truncated_result) < len(result):
                            if self.debug:
                                logger.warning(
                                    f"{self.name}: 工具 {tool_name} 的结果过长（{len(result)}字符），"
                                    f"已截断为 {len(truncated_result)} 字符"
                                )
                        
                        # 创建工具消息（使用截断后的结果）
                        tool_message = ToolMessage(
                            content=truncated_result,
                            tool_call_id=tool_call.get("id", ""),
                        )
                        tool_messages.append(tool_message)
            
            # 将工具结果添加到消息历史
            if tool_messages:
                messages.extend(tool_messages)
            else:
                # 如果所有工具调用都被跳过了（重复），但仍然有工具调用请求，强制LLM生成内容
                if self.debug:
                    logger.warning(f"{self.name}: 所有工具调用都被跳过，强制LLM生成内容")
                # 不继续工具调用循环，直接生成内容
                break
            
            # 如果agent没有工具，但LLM返回了工具调用，强制生成内容而不是继续循环
            if not self.tools and tool_calls:
                if self.debug:
                    logger.warning(f"{self.name}: agent没有工具但LLM返回了工具调用，强制生成内容（不绑定工具）")
                # 不绑定工具，强制生成文本
                chain = self._create_chain(self.llm)
                result = chain.invoke({
                    "user_input": self._get_continue_prompt() + "\n\n**重要**：你没有工具可用，请直接生成报告，不要尝试调用任何工具。",
                    "messages": messages,
                })
                messages.append(result)
                final_result = result
                break
            
            # 继续调用LLM（基于工具结果）
            if self.tools:
                llm_with_tools = self.llm.bind_tools(self.tools)
                chain = self._create_chain(llm_with_tools)
            else:
                chain = self._create_chain(self.llm)
            
            result = chain.invoke({
                "user_input": self._get_continue_prompt(),
                "messages": messages,
            })
            
            messages.append(result)
            final_result = result  # 更新最终结果
            iteration += 1
        
        # 如果最终结果没有content但有工具调用结果，强制生成一次（不绑定工具）
        if final_result and (not final_result.content or not final_result.content.strip()):
            tool_calls = final_result.tool_calls if hasattr(final_result, 'tool_calls') and final_result.tool_calls else []
            if tool_results or iteration >= max_iterations:
                if self.debug:
                    logger.warning(f"{self.name}: 最终结果没有content，强制生成内容（工具调用结果: {len(tool_results)}个，迭代次数: {iteration}）")
                # 最后一次调用，不绑定工具，强制生成文本
                # 关键优化：使用工具结果摘要，而不是整个messages历史，避免token过多
                chain = self._create_chain(self.llm)
                
                if tool_results:
                    # 构建工具结果摘要
                    tool_summaries = []
                    for tool_name, tool_result in tool_results.items():
                        summary_length = min(500, len(tool_result))  # 每个工具结果最多500字符摘要
                        summary = tool_result[:summary_length]
                        if len(tool_result) > summary_length:
                            summary += f"\n...（已截断，完整结果共 {len(tool_result)} 字符）"
                        tool_summaries.append(f"**{tool_name}**:\n{summary}")
                    
                    tool_summary_text = "\n\n".join(tool_summaries)
                    tool_names = list(tool_results.keys())
                    
                    continue_prompt = f"""**重要任务**：基于以下工具调用结果立即生成内容。

**已调用工具**：{', '.join(tool_names)}

**工具调用结果摘要**：

{tool_summary_text}

"""
                else:
                    continue_prompt = self._get_continue_prompt()
                
                if self.name == "plan_analyst":
                    # plan_analyst需要输出JSON格式的计划
                    if tool_results:
                        continue_prompt += "**重要**：请基于上述工具调用结果立即输出JSON格式的数据收集计划。禁止输出思考过程、推理过程或任何标记（如<thinking>、</reasoning>等）。直接输出纯JSON对象，不要有任何其他文本。"
                    else:
                        continue_prompt += "**重要**：请立即输出JSON格式的数据收集计划。禁止输出思考过程、推理过程或任何标记（如<thinking>、</reasoning>等）。直接输出纯JSON对象，不要有任何其他文本。"
                elif tool_results:
                    continue_prompt += "**重要**：请基于上述工具调用结果立即生成分析报告。你已经调用了所有必要的工具，现在必须生成报告内容。不要再次调用工具，不要输出思考过程，直接输出报告内容。"
                else:
                    continue_prompt += "**重要**：请立即生成分析报告。不要输出思考过程，直接输出报告内容。"
                
                # 使用简洁的消息列表，而不是整个messages历史
                from langchain_core.messages import SystemMessage, HumanMessage
                force_messages = [
                    SystemMessage(content=self._get_system_message()),
                    HumanMessage(content=continue_prompt)
                ]
                
                result = chain.invoke({
                    "user_input": continue_prompt,
                    "messages": force_messages,
                })
                messages.append(result)
                final_result = result
                
                # 如果强制生成后仍然是空的，再次尝试
                if not final_result.content or not final_result.content.strip():
                    if self.debug:
                        logger.warning(f"{self.name}: 强制生成后仍然为空，再次尝试生成")
                    # 最后一次尝试：使用更明确的提示词，要求输出JSON格式
                    if self.name == "plan_analyst":
                        # plan_analyst需要输出JSON格式的计划
                        final_prompt = (
                            "**关键要求**：\n"
                            "1. 直接输出JSON对象，不要有任何其他文本\n"
                            "2. 禁止输出思考过程、推理过程、代码块标记或任何标记（如<thinking>、</reasoning>、</think>、<reasoning>等）\n"
                            "3. 直接输出纯JSON，格式如下：\n"
                            '{"intent": "...", "tickers": [...], "data_sources": [...], "time_range": "...", "focus_areas": [...], "priority": "...", "estimated_complexity": "..."}\n'
                            "**重要**：只输出JSON对象，不要有任何前缀、后缀或标记。"
                        )
                    else:
                        # 更明确的prompt，强调必须生成内容，并包含工具结果摘要
                        if tool_results:
                            tool_summaries = []
                            for tool_name, tool_result in tool_results.items():
                                summary_length = min(300, len(tool_result))  # 进一步减少到300字符
                                summary = tool_result[:summary_length]
                                if len(tool_result) > summary_length:
                                    summary += f"\n...（已截断，完整结果共 {len(tool_result)} 字符）"
                                tool_summaries.append(f"**{tool_name}**:\n{summary}")
                            
                            tool_summary_text = "\n\n".join(tool_summaries)
                            final_prompt = f"""**关键要求**：

1. 你必须生成分析报告，不能返回空内容
2. 基于以下工具调用结果生成报告：

{tool_summary_text}

3. 不要输出思考过程、推理过程或任何标记
4. 直接输出报告内容，不要有任何前缀或后缀
5. 如果工具调用结果为空，请说明数据收集情况并给出基于现有信息的分析

**重要**：必须生成内容，不能返回空字符串。"""
                        else:
                            final_prompt = (
                                "**关键要求**：\n"
                                "1. 你必须生成分析报告，不能返回空内容\n"
                                "2. 基于上述工具调用结果生成报告\n"
                                "3. 不要输出思考过程、推理过程或任何标记\n"
                                "4. 直接输出报告内容，不要有任何前缀或后缀\n"
                                "5. 如果工具调用结果为空，请说明数据收集情况并给出基于现有信息的分析\n"
                                "**重要**：必须生成内容，不能返回空字符串。"
                            )
                    
                    # 使用简洁的消息列表
                    final_force_messages = [
                        SystemMessage(content=self._get_system_message()),
                        HumanMessage(content=final_prompt)
                    ]
                    
                    result = chain.invoke({
                        "user_input": final_prompt,
                        "messages": final_force_messages,
                    })
                    messages.append(result)
                    final_result = result
                    
                    # 如果最终还是空的，记录详细错误信息并抛出异常
                    if not final_result.content or not final_result.content.strip():
                        error_msg = (
                            f"{self.name}: 多次尝试后仍然无法生成内容！\n"
                            f"  - 工具调用结果数量: {len(tool_results) if tool_results else 0}\n"
                            f"  - 工具调用结果: {list(tool_results.keys()) if tool_results else []}\n"
                            f"  - 迭代次数: {iteration}\n"
                            f"  - 最终结果类型: {type(final_result)}\n"
                        )
                        if hasattr(final_result, '__dict__'):
                            error_msg += f"  - 最终结果属性: {final_result.__dict__}\n"
                        logger.error(error_msg)
                        raise ValueError(f"{self.name}: 多次尝试后仍然无法生成内容。请检查工具调用结果和LLM配置。")
        
        if self.debug:
            logger.info(f"{self.name}: 工具调用完成 - {len(tool_results)}个工具，迭代{iteration}轮")
        
        return messages, tool_results, final_result
    
    def _create_chain(self, llm):
        """创建LLM链（子类可重写）"""
        system_message = self._get_system_message()
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "{user_input}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        return prompt | llm
    
    def _get_continue_prompt(self) -> str:
        """获取继续处理的提示词（子类可重写）"""
        return "请继续处理。"
    
    @abstractmethod
    def _get_system_message(self) -> str:
        """获取系统提示词（子类必须实现）"""
        pass
    
    @abstractmethod
    def _get_user_input(self, state: AgentState, memory_context: str = "") -> str:
        """获取用户输入（子类必须实现）"""
        pass
    
    def _get_structured_output_schema(self) -> Optional[Type[BaseModel]]:
        """
        获取结构化输出Schema（可选）
        
        如果子类需要结构化输出，重写此方法返回Pydantic模型类
        如果返回None，则使用传统文本输出方式
        
        Returns:
            Pydantic模型类或None
        """
        return None
    
    def _needs_text_report(self) -> bool:
        """
        是否需要生成文本报告
        
        如果返回True，在获取结构化数据后，会额外调用LLM生成文本报告
        
        Returns:
            bool
        """
        return False
    
    @abstractmethod
    def _validate_state(self, state: AgentState):
        """验证状态（子类必须实现）"""
        pass
    
    @abstractmethod
    def _process_result(
        self, 
        state: AgentState, 
        structured_data: Optional[BaseModel],
        text_content: Optional[str],
        tool_results: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        处理结果（子类必须实现）
        
        Args:
            state: Agent状态
            structured_data: 结构化数据（Pydantic模型实例），如果未使用structured output则为None
            text_content: 文本内容（报告等），如果未生成文本报告则为None
            tool_results: 工具调用结果字典
            
        Returns:
            更新的状态字典
        """
        pass
    
    def process(self, state: AgentState) -> AgentState:
        """
        处理状态（主入口）
        
        Args:
            state: 状态字典
            
        Returns:
            更新的状态字典
        """
        try:
            # 1. 验证状态
            self._validate_state(state)
            
            # 2. 构建用户输入
            user_input = self._get_user_input(state)
            
            # 4. 调用LLM
            if "messages" not in state:
                raise ValueError("state必须包含messages字段")
            messages = state["messages"]
            
            # 创建LLM（绑定工具如果需要）
            if self.tools:
                llm_with_tools = self.llm.bind_tools(self.tools)
                chain = self._create_chain(llm_with_tools)
            else:
                chain = self._create_chain(self.llm)
            
            result = chain.invoke({
                "user_input": user_input,
                "messages": messages,
            })
            
            # 诊断：检查LLM返回结果
            if self.debug:
                logger.info(f"{self.name}: LLM返回结果类型: {type(result)}")
                logger.info(f"{self.name}: LLM返回结果是否有content: {hasattr(result, 'content')}")
                if hasattr(result, 'content'):
                    logger.info(f"{self.name}: LLM返回content长度: {len(result.content) if result.content else 0}")
                    logger.info(f"{self.name}: LLM返回content前200字符: {result.content[:200] if result.content else 'None'}")
                if hasattr(result, 'tool_calls'):
                    logger.info(f"{self.name}: LLM返回tool_calls: {result.tool_calls if result.tool_calls else 'None'}")
            
            # 5. 处理工具调用（如果需要）
            if self.tools:
                messages, tool_results, final_result = self.handle_tool_calls(result, messages, state=state)
            else:
                tool_results = {}
                messages.append(result)
                final_result = result
                
                # 诊断：检查最终结果
                if self.debug:
                    logger.info(f"{self.name}: 最终结果类型: {type(final_result)}")
                    logger.info(f"{self.name}: 最终结果是否有content: {hasattr(final_result, 'content')}")
                    if hasattr(final_result, 'content'):
                        logger.info(f"{self.name}: 最终结果content长度: {len(final_result.content) if final_result.content else 0}")
                        if not final_result.content or not final_result.content.strip():
                            logger.error(f"{self.name}: 最终结果content为空！")
                            logger.error(f"{self.name}: 用户输入长度: {len(user_input)}")
                            logger.error(f"{self.name}: 消息历史长度: {len(messages)}")
                            logger.error(f"{self.name}: 用户输入前500字符: {user_input[:500]}")
            
            # 6. 处理结构化输出（如果需要）
            structured_data = None
            text_content = None
            use_structured_output = False
            
            schema = self._get_structured_output_schema()
            if schema:
                # 使用structured output获取结构化数据
                try:
                    if self.debug:
                        logger.info(f"{self.name}: 使用structured output获取结构化数据")
                    
                    # 准备用于structured output的消息历史（包含工具调用结果）
                    structured_messages = messages.copy()
                    
                    # 创建structured output chain
                    structured_llm = self.llm.with_structured_output(schema)
                    structured_chain = self._create_chain(structured_llm)
                    
                    # 获取结构化数据
                    structured_data = structured_chain.invoke({
                        "user_input": user_input,
                        "messages": structured_messages,
                    })
                    
                    use_structured_output = True
                    if self.debug:
                        logger.info(f"{self.name}: 成功获取结构化数据: {type(structured_data)}")
                        
                except Exception as e:
                    error_msg = f"{self.name}: 获取结构化数据失败: {e}"
                    logger.error(error_msg)
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    # 如果structured output失败，尝试从文本内容中提取JSON
                    logger.warning(f"{self.name}: 回退到文本解析模式，尝试从文本中提取结构化数据")
                    use_structured_output = False
                    
                    # 尝试从final_result的content中提取JSON（如果有）
                    if hasattr(final_result, 'content') and final_result.content:
                        try:
                            import re
                            # 尝试从文本中提取JSON
                            content = final_result.content
                            # 查找JSON对象或数组
                            json_patterns = [
                                r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # JSON对象
                                r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # JSON数组
                            ]
                            for pattern in json_patterns:
                                matches = re.findall(pattern, content, re.DOTALL)
                                for match in matches:
                                    try:
                                        parsed_json = json.loads(match)
                                        # 尝试创建schema实例
                                        if schema:
                                            structured_data = schema(**parsed_json)
                                            logger.info(f"{self.name}: 成功从文本中提取结构化数据")
                                            use_structured_output = True
                                            break
                                    except (json.JSONDecodeError, Exception) as parse_err:
                                        if self.debug:
                                            logger.debug(f"{self.name}: JSON解析失败: {parse_err}")
                                        continue
                                if structured_data:
                                    break
                        except Exception as parse_error:
                            if self.debug:
                                logger.debug(f"{self.name}: 从文本中提取JSON失败: {parse_error}")
                    # 如果提取失败，structured_data保持为None，将在_process_result中使用占位值
            
            # 7. 生成文本报告（如果需要）
            if self._needs_text_report():
                try:
                    if self.debug:
                        logger.info(f"{self.name}: 生成文本报告")
                    
                    # 构建专门的报告生成prompt
                    # 关键优化：不复制整个messages历史，而是直接使用工具结果摘要，避免token过多
                    # 这样可以减少prompt tokens，确保有足够空间生成内容
                    if tool_results:
                        # 如果有工具调用结果，构建工具结果摘要（限制长度，避免token过多）
                        tool_summaries = []
                        for tool_name, tool_result in tool_results.items():
                            # 进一步截断工具结果摘要，只保留关键信息
                            summary_length = min(500, len(tool_result))  # 每个工具结果最多500字符摘要
                            summary = tool_result[:summary_length]
                            if len(tool_result) > summary_length:
                                summary += f"\n...（已截断，完整结果共 {len(tool_result)} 字符）"
                            tool_summaries.append(f"**{tool_name}**:\n{summary}")
                        
                        tool_summary_text = "\n\n".join(tool_summaries)
                        tool_names = list(tool_results.keys())
                        
                        report_prompt = f"""**重要任务**：基于以下工具调用结果生成详细的分析报告（Markdown格式）。

**已调用工具**：{', '.join(tool_names)}

**工具调用结果摘要**：

{tool_summary_text}

**要求**：
1. 基于上述工具调用结果生成详细的分析报告
2. 报告必须包含实质性内容，不能为空
3. 直接输出报告内容，不要包含任何思考过程、推理过程或内部对话
4. 禁止输出任何标记（如<thinking>、</thinking>、<reasoning>、</reasoning>、</think>等）
5. 只输出最终的Markdown格式报告，不要有任何前缀或后缀
"""
                    else:
                        # 如果没有工具调用结果，使用原始查询
                        report_prompt = user_input + "\n\n请生成详细的分析报告（Markdown格式）。\n\n"
                    
                    if structured_data:
                        report_prompt += "\n**结构化数据**：已提取并验证。请结合上述工具调用结果和结构化数据生成报告。\n\n"
                    
                    # 准备用于生成报告的消息历史（只包含系统消息和用户查询，不包含整个对话历史）
                    # 这样可以大幅减少token使用，确保有足够空间生成内容
                    from langchain_core.messages import SystemMessage, HumanMessage
                    report_messages = [
                        SystemMessage(content=self._get_system_message()),
                        HumanMessage(content=report_prompt)
                    ]
                    
                    if self.debug:
                        # 估算token使用（粗略估算：1 token ≈ 4字符）
                        estimated_tokens = sum(len(msg.content) if hasattr(msg, 'content') else 0 for msg in report_messages) / 4
                        logger.debug(f"{self.name}: 报告生成prompt估算tokens: {estimated_tokens:.0f}")
                    
                    # 创建用于生成报告的chain（不绑定工具，只生成文本）
                    report_chain = self._create_chain(self.llm)
                    report_result = report_chain.invoke({
                        "user_input": report_prompt,
                        "messages": report_messages,
                    })
                    
                    text_content = report_result.content if hasattr(report_result, 'content') else str(report_result)
                    
                    # 详细debug日志：记录原始LLM返回
                    if self.debug:
                        logger.debug(f"{self.name}: LLM原始返回 - 类型: {type(report_result)}")
                        logger.debug(f"{self.name}: LLM原始返回 - 是否有content: {hasattr(report_result, 'content')}")
                        if hasattr(report_result, 'content'):
                            logger.debug(f"{self.name}: LLM原始content长度: {len(report_result.content) if report_result.content else 0}")
                            logger.debug(f"{self.name}: LLM原始content前500字符: {report_result.content[:500] if report_result.content else 'None'}")
                        if hasattr(report_result, 'response_metadata'):
                            logger.debug(f"{self.name}: LLM response_metadata: {report_result.response_metadata}")
                        if hasattr(report_result, 'finish_reason'):
                            logger.debug(f"{self.name}: LLM finish_reason: {report_result.finish_reason}")
                    
                    # 清理思考过程标记（以防LLM仍然输出）
                    if text_content:
                        import re
                        thinking_patterns = [
                            r'<thinking>.*?</thinking>',
                            r'</?thinking>',
                            r'<reasoning>.*?</reasoning>',
                            r'</?reasoning>',
                            r'</?redacted_reasoning>',
                            r'</?think>',
                            r'<thought>.*?</thought>',
                            r'</?thought>',
                        ]
                        original_length = len(text_content)
                        for pattern in thinking_patterns:
                            text_content = re.sub(pattern, '', text_content, flags=re.DOTALL | re.IGNORECASE)
                        text_content = text_content.strip()
                        
                        if self.debug and len(text_content) < original_length:
                            logger.debug(f"{self.name}: 清理思考过程标记后，长度从 {original_length} 变为 {len(text_content)}")
                    
                    # 如果文本报告为空，记录详细错误并抛出异常（不使用默认值）
                    if not text_content or not text_content.strip():
                        error_msg = (
                            f"{self.name}: 文本报告生成结果为空！\n"
                            f"  - 原始content: {report_result.content if hasattr(report_result, 'content') else 'N/A'}\n"
                            f"  - 清理后content: {text_content}\n"
                            f"  - LLM类型: {type(report_result)}\n"
                            f"  - 工具调用结果数量: {len(tool_results) if tool_results else 0}\n"
                            f"  - 工具调用结果: {list(tool_results.keys()) if tool_results else []}\n"
                        )
                        if hasattr(report_result, 'response_metadata'):
                            error_msg += f"  - response_metadata: {report_result.response_metadata}\n"
                        if hasattr(report_result, 'finish_reason'):
                            error_msg += f"  - finish_reason: {report_result.finish_reason}\n"
                        logger.error(error_msg)
                        raise ValueError(f"{self.name}: 文本报告生成失败，LLM返回空内容。请检查工具调用结果和LLM配置。")
                    
                    if self.debug:
                        logger.info(f"{self.name}: 文本报告生成成功，长度: {len(text_content)}")
                        logger.debug(f"{self.name}: 文本报告内容前200字符: {text_content[:200]}")
                        
                except Exception as e:
                    error_msg = f"{self.name}: 生成文本报告失败: {e}"
                    logger.error(error_msg)
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    # 如果文本报告生成失败，重新抛出异常，不继续执行
                    # 因为后续的_process_result需要text_content，如果为空会报错
                    raise
            
            # 8. 如果没有使用structured output，使用传统方式获取文本内容
            if not use_structured_output:
                text_content = final_result.content if hasattr(final_result, 'content') else str(final_result)
            
            # 9. 处理结果
            updates = self._process_result(state, structured_data, text_content, tool_results)
            
            # 7. 更新追踪
            if "output_summary" not in updates:
                raise ValueError("_process_result必须返回output_summary字段")
            output_summary = updates["output_summary"]
            update_trace(state, self.name.replace("_", "-"), self.name, "处理任务", output_summary)
            
            # 8. 更新消息历史
            state["messages"] = messages
            
            # 9. 更新状态
            for key, value in updates.items():
                if key != "output_summary":
                    state[key] = value
            
            return state
            
        except Exception as e:
            error_msg = f"{self.name}: 处理失败 - {e}"
            logger.error(error_msg)
            add_error(state, error_msg)
            update_trace(state, self.name.replace("_", "-"), self.name, "处理失败", error=str(e))
            raise
    
    def create_node(self):
        """
        创建LangGraph节点函数
        
        Returns:
            node函数
        """
        def node(state: AgentState) -> AgentState:
            return self.process(state)
        return node

