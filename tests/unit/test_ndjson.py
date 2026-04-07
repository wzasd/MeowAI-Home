import pytest
from src.utils.ndjson import parse_ndjson_stream


@pytest.mark.asyncio
async def test_parse_simple_ndjson():
    ndjson = '{"type": "text", "content": "你好"}\n{"type": "text", "content": "世界"}\n'
    events = []
    async for event in parse_ndjson_stream(ndjson):
        events.append(event)

    assert len(events) == 2
    assert events[0]["content"] == "你好"
    assert events[1]["content"] == "世界"


@pytest.mark.asyncio
async def test_parse_ndjson_with_empty_lines():
    ndjson = '{"type": "text", "content": "你好"}\n\n{"type": "text", "content": "世界"}\n'
    events = []
    async for event in parse_ndjson_stream(ndjson):
        events.append(event)

    assert len(events) == 2
