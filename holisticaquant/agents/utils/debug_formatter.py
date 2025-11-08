"""
调试日志格式化工具

提供统一的可读性增强方法，用于在debug模式下追踪agent流程、工具调用以及state变更。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple
import json
import textwrap

DEFAULT_MAX_LEN = 400


def _safe_json_dumps(value: Any, max_len: int = DEFAULT_MAX_LEN) -> str:
    """优先使用JSON格式化对象，失败时退回repr，并截断长度。"""
    try:
        rendered = json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        rendered = repr(value)
    if len(rendered) > max_len:
        return f"{rendered[:max_len]}…（截断，原始长度 {len(rendered)}）"
    return rendered


def _format_lines(items: Iterable[Tuple[str, str]]) -> str:
    """将键值对渲染为统一缩进的多行文本。"""
    lines: List[str] = []
    for key, value in items:
        wrapped = textwrap.indent(value, prefix="    ").lstrip()
        first_line, *rest = wrapped.splitlines() or [""]
        lines.append(f"• {key}: {first_line}")
        for line in rest:
            lines.append(f"  {line}")
    return "\n".join(lines) if lines else "（无）"


def snapshot_state(state: Dict[str, Any], keys: Iterable[str], max_len: int = DEFAULT_MAX_LEN) -> Dict[str, str]:
    """截取state中指定key的快照（字符串化）。不存在的键会被跳过。"""
    snapshot: Dict[str, str] = {}
    for key in keys:
        if key in state:
            snapshot[key] = _safe_json_dumps(state[key], max_len=max_len)
    return snapshot


def format_state_snapshot(agent_name: str, stage: str, snapshot: Dict[str, str]) -> str:
    """格式化state快照为易读的多行文本。"""
    body = _format_lines(snapshot.items())
    return (
        f"\n╔══════════════════════════════════════════╗\n"
        f"║ 🧩 Agent: {agent_name} │ 阶段: {stage}\n"
        f"╠══════════════════════════════════════════╣\n"
        f"{textwrap.indent(body, '║ ')}\n"
        f"╚══════════════════════════════════════════╝"
    )


def format_agent_input_prompt(agent_name: str, prompt: str, max_len: int = 600) -> str:
    """格式化LLM输入提示信息。"""
    trimmed = prompt if len(prompt) <= max_len else f"{prompt[:max_len]}…（截断，原始长度 {len(prompt)}）"
    wrapped = textwrap.indent(trimmed, prefix="║ ")
    return (
        f"\n╔══════════════════════════════════════════╗\n"
        f"║ 🗝️ Agent: {agent_name} │ 生成LLM输入\n"
        f"╠══════════════════════════════════════════╣\n"
        f"{wrapped}\n"
        f"╚══════════════════════════════════════════╝"
    )


def format_tool_call(agent_name: str, tool_name: str, tool_args: Dict[str, Any]) -> str:
    """格式化工具调用输入日志。"""
    args_text = _safe_json_dumps(tool_args)
    wrapped = textwrap.indent(args_text, prefix="║ ")
    return (
        f"\n╔══════════════════════════════════════════╗\n"
        f"║ 🛠️ Agent: {agent_name} │ 调用工具 → {tool_name}\n"
        f"╠══════════════════════════════════════════╣\n"
        f"{wrapped}\n"
        f"╚══════════════════════════════════════════╝"
    )


def format_tool_result(agent_name: str, tool_name: str, result: str, max_len: int = DEFAULT_MAX_LEN) -> str:
    """格式化工具调用输出日志。"""
    if len(result) > max_len:
        result = f"{result[:max_len]}…（截断，原始长度 {len(result)}）"
    wrapped = textwrap.indent(result, prefix="║ ")
    return (
        f"\n╔══════════════════════════════════════════╗\n"
        f"║ 📤 Agent: {agent_name} │ 工具输出 ← {tool_name}\n"
        f"╠══════════════════════════════════════════╣\n"
        f"{wrapped}\n"
        f"╚══════════════════════════════════════════╝"
    )


def format_state_updates(agent_name: str, updates: Dict[str, Any]) -> str:
    """格式化_state更新的摘要信息。"""
    content_pairs = []
    for key, value in updates.items():
        if key == "output_summary":
            continue
        content_pairs.append((key, _safe_json_dumps(value)))
    body = _format_lines(content_pairs)
    return (
        f"\n╔══════════════════════════════════════════╗\n"
        f"║ 🧾 Agent: {agent_name} │ 写入State字段\n"
        f"╠══════════════════════════════════════════╣\n"
        f"{textwrap.indent(body, '║ ')}\n"
        f"╚══════════════════════════════════════════╝"
    )


def format_state_diff(agent_name: str, before: Dict[str, str], after: Dict[str, str]) -> str:
    """格式化state变更的差异对比。"""
    lines: List[str] = []
    keys = sorted(set(before.keys()) | set(after.keys()))
    for key in keys:
        before_val = before.get(key, "（无）")
        after_val = after.get(key, "（无）")
        if before_val == after_val:
            continue
        lines.append(f"• {key}")
        before_lines = textwrap.indent(before_val, prefix="    before: ")
        after_lines = textwrap.indent(after_val, prefix="    after : ")
        lines.append(before_lines)
        lines.append(after_lines)
    body = "\n".join(lines) if lines else "（此阶段State未发生变更）"
    return (
        f"\n╔══════════════════════════════════════════╗\n"
        f"║ 🔄 Agent: {agent_name} │ State差异对比\n"
        f"╠══════════════════════════════════════════╣\n"
        f"{textwrap.indent(body, '║ ')}\n"
        f"╚══════════════════════════════════════════╝"
    )

