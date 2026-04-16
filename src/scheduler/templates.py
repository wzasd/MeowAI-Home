"""Scheduler templates — preset task configurations for common use cases."""

from typing import Any, Dict, List, Optional


SCHEDULER_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "reminder",
        "name": "定时提醒",
        "description": "在指定时间发送提醒消息到目标线程",
        "actor_role": "assistant",
        "cost_tier": "low",
        "default_config": {
            "message": "这是你的定时提醒",
            "target_thread": "",
        },
    },
    {
        "id": "repo-activity",
        "name": "仓库活动汇总",
        "description": "定时抓取仓库最新提交、PR 和活动摘要",
        "actor_role": "developer",
        "cost_tier": "standard",
        "default_config": {
            "repo": "",
            "target_thread": "",
            "include_commits": True,
            "include_prs": True,
        },
    },
    {
        "id": "web-digest",
        "name": "每日资讯摘要",
        "description": "抓取指定 RSS/网页来源并生成摘要报告",
        "actor_role": "researcher",
        "cost_tier": "standard",
        "default_config": {
            "sources": [],
            "target_thread": "",
            "max_articles": 5,
        },
    },
]


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get a template by ID."""
    for t in SCHEDULER_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None


def list_templates() -> List[Dict[str, Any]]:
    """List all available templates."""
    return SCHEDULER_TEMPLATES.copy()
