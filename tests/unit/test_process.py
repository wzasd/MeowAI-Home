import pytest
import asyncio
from src.utils.process import run_cli_command


@pytest.mark.asyncio
async def test_run_simple_command():
    result = await run_cli_command("echo", ["hello"])
    assert result["stdout"] == "hello\n"
    assert result["returncode"] == 0


@pytest.mark.asyncio
async def test_run_command_with_timeout():
    with pytest.raises(asyncio.TimeoutError):
        await run_cli_command("sleep", ["10"], timeout=0.1)
