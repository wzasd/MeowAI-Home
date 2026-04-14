import asyncio
from typing import List, Dict, Any, AsyncIterator


async def run_cli_command(
    command: str,
    args: List[str],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """运行CLI命令并返回结果

    使用asyncio执行外部命令，支持超时控制和僵尸进程防护。

    Args:
        command: 要执行的命令
        args: 命令参数列表
        timeout: 超时时间（秒），默认30秒

    Returns:
        包含returncode、stdout、stderr的字典

    Raises:
        asyncio.TimeoutError: 命令执行超时
    """
    cmd = [command] + args
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode('utf-8'),
            "stderr": stderr.decode('utf-8')
        }
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise


async def run_cli_command_stream(
    command: str,
    args: List[str],
    timeout: float = 300.0
) -> AsyncIterator[str]:
    """运行CLI命令并流式返回stdout输出

    实时读取CLI的NDJSON输出，用于流式响应。

    Args:
        command: 要执行的命令
        args: 命令参数列表
        timeout: 超时时间（秒），默认300秒

    Yields:
        每一行stdout输出

    Raises:
        asyncio.TimeoutError: 命令执行超时
    """
    cmd = [command] + args
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        # Stream stdout line by line
        buffer = b""
        while True:
            try:
                chunk = await asyncio.wait_for(
                    process.stdout.read(1024),
                    timeout=1.0
                )
                if not chunk:
                    break
                buffer += chunk

                # Yield complete lines
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line:
                        yield line.decode('utf-8')

            except asyncio.TimeoutError:
                # Check if process is still running
                if process.returncode is not None:
                    break
                continue

        # Yield remaining buffer
        if buffer:
            yield buffer.decode('utf-8')

        # Wait for process to complete
        await asyncio.wait_for(process.wait(), timeout=timeout)

    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
