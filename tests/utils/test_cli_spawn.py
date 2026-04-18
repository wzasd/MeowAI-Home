import pytest
import asyncio
import sys
from src.utils.cli_spawn import spawn_cli


@pytest.mark.asyncio
async def test_spawn_cli_with_echo():
    """echo outputs text, not JSON, so no events should be yielded"""
    events = []
    async for event in spawn_cli("echo", ['not json']):
        events.append(event)
    assert len(events) == 0  # echo output is not valid JSON


@pytest.mark.asyncio
async def test_spawn_cli_timeout():
    """sleep should timeout"""
    with pytest.raises(asyncio.TimeoutError):
        async for event in spawn_cli("sleep", ["10"], timeout=0.5):
            pass


@pytest.mark.asyncio
async def test_spawn_cli_json_output():
    """Test with a command that outputs valid JSON"""
    events = []
    async for event in spawn_cli("echo", ['{"type":"text","content":"hello"}']):
        events.append(event)
    assert len(events) == 1
    assert events[0]["type"] == "text"
    assert events[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_spawn_cli_nonzero_exit_with_stderr():
    """CLI that prints JSON then writes stderr and exits non-zero should raise"""
    script = (
        "import sys; "
        "print('{\"type\":\"text\",\"content\":\"hello\"}'); "
        "print('something went wrong', file=sys.stderr); "
        "sys.exit(1)"
    )
    events = []
    with pytest.raises(RuntimeError) as exc_info:
        async for event in spawn_cli(sys.executable, ["-c", script]):
            events.append(event)
    assert len(events) == 1
    assert "exited with code 1" in str(exc_info.value)
    assert "something went wrong" in str(exc_info.value)
