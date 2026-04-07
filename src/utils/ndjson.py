import json
from typing import AsyncIterator, Dict, Any


async def parse_ndjson_stream(ndjson: str) -> AsyncIterator[Dict[str, Any]]:
    """解析NDJSON字符串流

    NDJSON (Newline Delimited JSON) 是一种每行一个JSON对象的格式，
    常用于流式数据传输。

    Args:
        ndjson: NDJSON格式的字符串

    Yields:
        解析后的JSON对象字典
    """
    for line in ndjson.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            yield event
        except json.JSONDecodeError as e:
            # 记录错误但继续处理
            print(f"Failed to parse line: {line}, error: {e}")
            continue
