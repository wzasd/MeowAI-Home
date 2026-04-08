"""MCP 工具实现"""
from typing import Any, Dict, List
import subprocess
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
    matches = []

    # 使用 grep 进行搜索
    try:
        # 限制搜索范围，避免搜索过大
        result = subprocess.run(
            ["grep", "-r", "-n", "--include=*.py", "--include=*.md", query, path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            for line in result.stdout.splitlines()[:10]:  # 最多返回 10 条
                # 格式: file:line:content
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        matches.append({
                            "file": parts[0],
                            "line": int(parts[1]),
                            "content": parts[2][:100]  # 截断内容
                        })
    except subprocess.TimeoutExpired:
        return {"matches": [], "error": "Search timeout"}
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
