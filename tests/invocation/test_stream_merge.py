import pytest
import asyncio
from src.invocation.stream_merge import merge_streams
from src.models.types import AgentMessage, AgentMessageType


def _make_stream(messages):
    async def gen():
        for m in messages:
            yield m
    return gen()


@pytest.mark.asyncio
async def test_merge_two_streams():
    s1 = _make_stream([
        AgentMessage(type=AgentMessageType.TEXT, content="a1", cat_id="opus"),
        AgentMessage(type=AgentMessageType.DONE, cat_id="opus"),
    ])
    s2 = _make_stream([
        AgentMessage(type=AgentMessageType.TEXT, content="b1", cat_id="codex"),
        AgentMessage(type=AgentMessageType.DONE, cat_id="codex"),
    ])
    results = []
    async for msg in merge_streams([s1, s2]):
        results.append(msg)
    assert len(results) == 4
    cat_ids = {m.cat_id for m in results}
    assert cat_ids == {"opus", "codex"}


@pytest.mark.asyncio
async def test_merge_single_stream():
    s1 = _make_stream([AgentMessage(type=AgentMessageType.TEXT, content="only", cat_id="opus")])
    results = []
    async for msg in merge_streams([s1]):
        results.append(msg)
    assert len(results) == 1
    assert results[0].content == "only"


@pytest.mark.asyncio
async def test_merge_handles_error():
    async def failing_gen():
        yield AgentMessage(type=AgentMessageType.TEXT, content="before", cat_id="opus")
        raise RuntimeError("boom")

    errors = []
    results = []
    async for msg in merge_streams([failing_gen()], on_error=lambda e: errors.append(e)):
        results.append(msg)
    assert len(results) >= 1
    assert len(errors) == 1
