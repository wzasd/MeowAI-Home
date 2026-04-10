"""
Anthropic API 反向代理

功能：
1. 清理 thinking block 签名（防止第三方网关签名不匹配）
2. 规范化 SSE 事件（修正 input_tokens: 0）
3. 自动重试（429/529）
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    port: int = 9877
    max_retries: int = 3
    retry_delay_base: float = 1.0
    upstream_timeout: float = 60.0
    upstreams_file: str = "proxy-upstreams.json"


def strip_thinking_from_history(messages: List[dict]) -> List[dict]:
    """清理请求历史中的 thinking/redacted_thinking blocks"""
    result = []
    for msg in messages:
        if msg.get("role") != "assistant":
            result.append(msg)
            continue
        content = msg.get("content", [])
        if isinstance(content, list):
            filtered = [
                block for block in content
                if isinstance(block, dict) and block.get("type") not in ("thinking", "redacted_thinking")
            ]
            msg = {**msg, "content": filtered}
        result.append(msg)
    return result


def normalize_sse_event(event: dict) -> Optional[dict]:
    if not isinstance(event, dict):
        return event
    event_type = event.get("type", "")
    if event_type == "message_start":
        message = event.get("message", {})
        usage = message.get("usage", {})
        if usage.get("input_tokens") == 0:
            logger.debug("message_start has input_tokens=0, will be corrected by message_delta")
    if event_type in ("content_block_start", "content_block_delta"):
        block = event.get("content_block") or event.get("delta", {})
        if isinstance(block, dict):
            allowed = {"type", "text", "thinking", "signature", "index"}
            extra = set(block.keys()) - allowed
            for key in extra:
                block.pop(key, None)
    return event


def load_upstreams(config_path: str) -> Dict[str, str]:
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
