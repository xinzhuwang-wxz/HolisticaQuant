"""
Scenario Repository

提供对场景化学习与投研模板等轻量化配置的读取接口。
默认使用 JSON 存储，便于在 MVP 阶段快速维护，可随时替换为 SQLite。
"""

from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict, List, Optional

SCENARIO_FILE = Path(__file__).resolve().parent / "scenario_library.json"


class ScenarioRepositoryError(RuntimeError):
    """场景仓库加载异常"""


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ScenarioRepositoryError(f"场景配置文件不存在: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ScenarioRepositoryError(f"场景配置文件解析失败: {exc}") from exc


@lru_cache(maxsize=1)
def load_scenario_library() -> Dict[str, Any]:
    """加载并缓存场景配置"""
    return _load_json(SCENARIO_FILE)


def get_learning_topics() -> List[Dict[str, Any]]:
    """返回所有学习工坊主题"""
    data = load_scenario_library()
    return data.get("learning_workshop", {}).get("topics", [])


def get_learning_topic_by_id(topic_id: str) -> Optional[Dict[str, Any]]:
    """通过ID获取学习工坊主题"""
    for topic in get_learning_topics():
        if topic.get("id") == topic_id:
            return topic
    return None


def get_learning_topic_summaries() -> List[Dict[str, str]]:
    """获取学习工坊主题的简要摘要，供提示词使用"""
    summaries: List[Dict[str, str]] = []
    for topic in get_learning_topics():
        summaries.append(
            {
                "id": topic.get("id", ""),
                "title": topic.get("title", ""),
                "knowledge_point": topic.get("knowledge_point", ""),
                "scenario_summary": topic.get("scenario_summary", "")[:120],
            }
        )
    return summaries


def get_research_templates() -> List[Dict[str, Any]]:
    """返回所有投研实验室模板"""
    data = load_scenario_library()
    return data.get("research_lab", {}).get("templates", [])


def get_research_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """通过ID获取投研模板"""
    for template in get_research_templates():
        if template.get("id") == template_id:
            return template
    return None


def get_research_template_summaries() -> List[Dict[str, str]]:
    """获取投研模板摘要，便于提示词引用"""
    summaries: List[Dict[str, str]] = []
    for template in get_research_templates():
        summaries.append(
            {
                "id": template.get("id", ""),
                "title": template.get("title", ""),
                "description": template.get("description", "")[:120],
            }
        )
    return summaries

