"""Tests for MCP server health probe."""
import json
import sys
import tempfile
from pathlib import Path

import pytest

from src.capabilities.mcp_probe import (
    McpProbeResult,
    probe_mcp_capabilities,
    _probe_server_stdio,
)
from src.capabilities.models import CapabilityEntry, McpServerConfig


def _mock_mcp_server_script() -> str:
    return """
import sys, json
line = sys.stdin.readline()
print(json.dumps({"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05"}}), flush=True)
line = sys.stdin.readline()
line = sys.stdin.readline()
print(json.dumps({"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"read_file","description":"Read a file"}]}}), flush=True)
"""


def _mock_mcp_server_error_script() -> str:
    return """
import sys, json
line = sys.stdin.readline()
print(json.dumps({"jsonrpc":"2.0","id":1,"error":{"code":-32600,"message":"Invalid Request"}}), flush=True)
"""


def _mock_mcp_server_timeout_script() -> str:
    return """
import sys, time
line = sys.stdin.readline()
time.sleep(60)
"""


class TestMcpProbe:
    @pytest.mark.asyncio
    async def test_probe_server_connected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "mock_mcp.py"
            script_path.write_text(_mock_mcp_server_script(), encoding="utf-8")
            result = await _probe_server_stdio(
                "test-server",
                McpServerConfig(command=sys.executable, args=[str(script_path)]),
                timeout=5.0,
            )
            assert result.connectionStatus == "connected"
            assert len(result.tools) == 1
            assert result.tools[0]["name"] == "read_file"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_probe_server_initialize_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "mock_mcp_error.py"
            script_path.write_text(_mock_mcp_server_error_script(), encoding="utf-8")
            result = await _probe_server_stdio(
                "test-server",
                McpServerConfig(command=sys.executable, args=[str(script_path)]),
                timeout=5.0,
            )
            assert result.connectionStatus == "error"
            assert "Initialize error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_probe_server_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "mock_mcp_timeout.py"
            script_path.write_text(_mock_mcp_server_timeout_script(), encoding="utf-8")
            result = await _probe_server_stdio(
                "test-server",
                McpServerConfig(command=sys.executable, args=[str(script_path)]),
                timeout=0.5,
            )
            assert result.connectionStatus == "timeout"
            assert "timed out" in (result.error or "")

    @pytest.mark.asyncio
    async def test_probe_server_missing_command(self):
        result = await _probe_server_stdio(
            "test-server",
            McpServerConfig(command=""),
            timeout=5.0,
        )
        assert result.connectionStatus == "unsupported"
        assert "Missing command" in (result.error or "")

    @pytest.mark.asyncio
    async def test_probe_mcp_capabilities_skips_non_mcp(self):
        caps = [
            CapabilityEntry(id="design", type="skill", enabled=True, source="meowai"),
        ]
        results = await probe_mcp_capabilities(caps, timeout=1.0)
        assert results == []

    @pytest.mark.asyncio
    async def test_probe_mcp_capabilities_filters_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "mock_mcp.py"
            script_path.write_text(_mock_mcp_server_script(), encoding="utf-8")
            caps = [
                CapabilityEntry(
                    id="fs",
                    type="mcp",
                    enabled=True,
                    source="test",
                    mcpServer=McpServerConfig(command=sys.executable, args=[str(script_path)]),
                ),
            ]
            results = await probe_mcp_capabilities(caps, timeout=5.0)
            assert len(results) == 1
            assert results[0].connectionStatus == "connected"
