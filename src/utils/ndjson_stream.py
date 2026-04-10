import json
from typing import AsyncIterator, Dict, Any, Iterable


async def parse_ndjson_lines(lines: Iterable[str]) -> AsyncIterator[Dict[str, Any]]:
    """流式解析 NDJSON 行"""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
            yield event
        except json.JSONDecodeError:
            continue
