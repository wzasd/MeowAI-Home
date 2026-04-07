import asyncio
from typing import List, Dict, Any


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
