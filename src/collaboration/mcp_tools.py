"""MCP 工具实现"""
from typing import Any, Dict, List
import os

from src.thread.models import Thread


async def post_message_tool(thread: Thread, content: str) -> Dict[str, Any]:
    """
    发送消息到当前 thread

    Args:
        thread: 当前 thread 实例
        content: 消息内容

    Returns:
        {"status": "sent", "message_preview": str}
    """
    thread.add_message("assistant", content)
    return {
        "status": "sent",
        "message_preview": content[:50] + "..." if len(content) > 50 else content
    }


async def search_files_tool(query: str, path: str = ".") -> Dict[str, Any]:
    """
    搜索项目文件内容

    Args:
        query: 搜索关键词
        path: 搜索路径（默认当前目录）

    Returns:
        {"matches": [{"file": str, "line": int, "content": str}]}
    """
    from pathlib import Path

    matches = []
    max_matches = 10

    try:
        base_path = Path(path)

        # 遍历 .py 和 .md 文件
        for pattern in ["*.py", "*.md"]:
            for file_path in base_path.rglob(pattern):
                if len(matches) >= max_matches:
                    break

                try:
                    # 逐行读取文件
                    with file_path.open('r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if query.lower() in line.lower():  # 大小写不敏感
                                matches.append({
                                    "file": str(file_path.relative_to(base_path)),
                                    "line": line_num,
                                    "content": line.strip()[:100]  # 截断内容
                                })

                                if len(matches) >= max_matches:
                                    break
                except Exception:
                    # 跳过无法读取的文件
                    continue

            if len(matches) >= max_matches:
                break

    except Exception as e:
        return {"matches": [], "error": str(e)}

    return {"matches": matches}


async def target_cats_tool(cats: List[str]) -> Dict[str, Any]:
    """
    声明下一个回复的猫（结构化路由）

    Args:
        cats: 猫 ID 列表

    Returns:
        {"targetCats": List[str]}
    """
    return {"targetCats": cats}


# 工具注册配置（供 MCPClient 使用）
TOOL_REGISTRY = {
    "post_message": {
        "description": "发送消息到当前 thread",
        "parameters": {
            "content": {
                "type": "string",
                "description": "消息内容"
            }
        },
        "handler": post_message_tool
    },
    "search_files": {
        "description": "搜索项目文件内容",
        "parameters": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "path": {
                "type": "string",
                "description": "搜索路径（默认当前目录）",
                "default": "."
            }
        },
        "handler": search_files_tool
    },
    "targetCats": {
        "description": "声明下一个回复的猫",
        "parameters": {
            "cats": {
                "type": "array",
                "description": "猫 ID 列表",
                "items": {"type": "string"}
            }
        },
        "handler": target_cats_tool
    }
}
