"""MCP server health probe — discover connection status and available tools."""
import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.capabilities.models import CapabilityEntry, McpServerConfig


@dataclass
class McpProbeResult:
    """Result of probing a single MCP server."""

    capabilityId: str
    connectionStatus: str  # "connected", "error", "timeout", "unsupported"
    tools: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


async def _send_request(
    writer: asyncio.StreamWriter,
    request_id: int,
    method: str,
    params: Optional[Dict[str, Any]] = None,
) -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        payload["params"] = params
    data = json.dumps(payload) + "\n"
    writer.write(data.encode("utf-8"))
    await writer.drain()


async def _read_response(
    reader: asyncio.StreamReader,
    request_id: int,
    timeout: float,
) -> Optional[Dict[str, Any]]:
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        line = await asyncio.wait_for(reader.readline(), timeout=remaining)
        if not line:
            return None
        try:
            msg = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue
        if msg.get("id") == request_id:
            return msg
        # Ignore notifications and other responses


async def _probe_server_stdio(
    cap_id: str,
    mcp: McpServerConfig,
    timeout: float = 10.0,
) -> McpProbeResult:
    command = mcp.command
    if not command:
        return McpProbeResult(
            capabilityId=cap_id,
            connectionStatus="unsupported",
            error="Missing command in MCP server config",
        )

    cmd = [command] + (mcp.args or [])
    env = None
    if mcp.env:
        import os
        env = {**os.environ, **mcp.env}

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except Exception as e:
        return McpProbeResult(
            capabilityId=cap_id,
            connectionStatus="error",
            error=f"Failed to start process: {e}",
        )

    try:
        assert process.stdin is not None
        assert process.stdout is not None

        writer = process.stdin
        reader = process.stdout

        # 1. Initialize
        await _send_request(
            writer,
            request_id=1,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "meowai-probe", "version": "0.1.0"},
            },
        )
        init_resp = await _read_response(reader, 1, timeout)
        if init_resp is None:
            return McpProbeResult(
                capabilityId=cap_id,
                connectionStatus="error",
                error="No response to initialize request",
            )
        if "error" in init_resp:
            return McpProbeResult(
                capabilityId=cap_id,
                connectionStatus="error",
                error=f"Initialize error: {init_resp['error']}",
            )

        # 2. Send initialized notification
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        writer.write(json.dumps(notif).encode("utf-8") + b"\n")
        await writer.drain()

        # 3. tools/list
        await _send_request(
            writer,
            request_id=2,
            method="tools/list",
            params={},
        )
        tools_resp = await _read_response(reader, 2, timeout)
        if tools_resp is None:
            return McpProbeResult(
                capabilityId=cap_id,
                connectionStatus="error",
                error="No response to tools/list request",
            )
        if "error" in tools_resp:
            return McpProbeResult(
                capabilityId=cap_id,
                connectionStatus="error",
                error=f"tools/list error: {tools_resp['error']}",
            )

        tools = tools_resp.get("result", {}).get("tools", [])
        if not isinstance(tools, list):
            tools = []

        return McpProbeResult(
            capabilityId=cap_id,
            connectionStatus="connected",
            tools=tools,
        )

    except asyncio.TimeoutError:
        return McpProbeResult(
            capabilityId=cap_id,
            connectionStatus="timeout",
            error=f"Probe timed out after {timeout}s",
        )
    except Exception as e:
        return McpProbeResult(
            capabilityId=cap_id,
            connectionStatus="error",
            error=str(e),
        )
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()


async def probe_mcp_capabilities(
    capabilities: List[CapabilityEntry],
    timeout: float = 10.0,
) -> List[McpProbeResult]:
    """Probe all MCP servers in the config and return their statuses."""
    results: List[McpProbeResult] = []
    for cap in capabilities:
        if cap.type != "mcp" or not cap.mcpServer:
            continue
        result = await _probe_server_stdio(cap.id, cap.mcpServer, timeout=timeout)
        results.append(result)
    return results
