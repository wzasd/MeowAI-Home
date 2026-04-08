"""MCP 回调格式解析器"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """工具调用"""
    tool_name: str
    params: Dict[str, Any]


@dataclass
class CallbackParseResult:
    """回调解析结果"""
    clean_content: str          # 移除回调标记的干净内容
    tool_calls: List[ToolCall]  # 工具调用列表
    targetCats: List[str]       # 结构化路由


# 回调标记正则: <mcp:tool_name>...</mcp:tool_name>
CALLBACK_PATTERN = re.compile(
    r'<mcp:(\w+)>\s*({.*?})\s*</mcp:\w+>',
    re.DOTALL | re.IGNORECASE
)


def parse_callbacks(content: str) -> CallbackParseResult:
    """
    解析 MCP 回调标记

    Args:
        content: 猫回复的原始内容

    Returns:
        CallbackParseResult

    Example:
        Input: "Hello\\n<mcp:post_message>{\\"content\\": \\"Hi\\"}</mcp:post_message>"
        Output: CallbackParseResult(
            clean_content="Hello",
            tool_calls=[ToolCall("post_message", {"content": "Hi"})],
            targetCats=[]
        )
    """
    tool_calls = []
    target_cats = []
    clean_parts = []

    last_end = 0
    for match in CALLBACK_PATTERN.finditer(content):
        # 添加匹配前的内容
        clean_parts.append(content[last_end:match.start()])

        tool_name = match.group(1).lower()
        params_str = match.group(2)

        try:
            params = json.loads(params_str)
            tool_calls.append(ToolCall(tool_name=tool_name, params=params))

            # 特别处理 targetCats
            if tool_name == "targetcats" and "cats" in params:
                target_cats.extend(params["cats"])
        except json.JSONDecodeError:
            # JSON 解析失败，保留原始内容
            clean_parts.append(match.group(0))

        last_end = match.end()

    # 添加剩余内容
    clean_parts.append(content[last_end:])

    # 合并干净内容
    clean_content = "".join(clean_parts).strip()

    return CallbackParseResult(
        clean_content=clean_content,
        tool_calls=tool_calls,
        targetCats=target_cats
    )


def strip_callback_markers(content: str) -> str:
    """
    仅移除回调标记，不解析参数

    Args:
        content: 原始内容

    Returns:
        移除标记后的内容
    """
    return CALLBACK_PATTERN.sub("", content).strip()
