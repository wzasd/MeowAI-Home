import asyncio
import json
import os
from typing import AsyncIterator, Dict, Any, List, Optional

KILL_GRACE_MS = 3.0


async def spawn_cli(
    command: str,
    args: List[str],
    timeout: float = 300.0,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """spawn CLI 子进程，流式解析 NDJSON 输出

    Features: streaming line-by-line, SIGTERM->SIGKILL escalation, zombie prevention
    """
    cmd = [command] + args
    child_env = dict(os.environ)
    if env:
        for k, v in env.items():
            if v is None:
                child_env.pop(k, None)
            else:
                child_env[k] = v

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=child_env,
        cwd=cwd,
    )

    try:
        while True:
            try:
                line_bytes = await asyncio.wait_for(
                    process.stdout.readline(), timeout=timeout
                )
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError()
            if not line_bytes:
                break
            decoded = line_bytes.decode("utf-8", errors="replace")
            stripped = decoded.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
                yield event
            except json.JSONDecodeError:
                continue

        await process.wait()

    except asyncio.TimeoutError:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=KILL_GRACE_MS)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
        raise
    finally:
        pass
