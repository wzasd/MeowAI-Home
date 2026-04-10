import pytest
from src.utils.ndjson_stream import parse_ndjson_lines


@pytest.mark.asyncio
async def test_parse_valid_ndjson():
    lines = ['{"type":"text","content":"hello"}', '{"type":"done"}']
    events = []
    async for event in parse_ndjson_lines(lines):
        events.append(event)
    assert len(events) == 2
    assert events[0]["content"] == "hello"
    assert events[1]["type"] == "done"


@pytest.mark.asyncio
async def test_parse_skips_empty_lines():
    lines = ['', '{"type":"text"}', '  ', '{"type":"done"}']
    events = []
    async for event in parse_ndjson_lines(lines):
        events.append(event)
    assert len(events) == 2


@pytest.mark.asyncio
async def test_parse_handles_invalid_json():
    lines = ['not json', '{"type":"ok"}']
    events = []
    async for event in parse_ndjson_lines(lines):
        events.append(event)
    assert len(events) == 1
    assert events[0]["type"] == "ok"
