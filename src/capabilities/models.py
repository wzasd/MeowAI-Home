"""Pydantic models for the Capability Orchestrator."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class McpServerConfig(BaseModel):
    """MCP server transport configuration."""

    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    transport: Optional[str] = None
    url: Optional[str] = None
    resolver: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    workingDir: Optional[str] = None


class CatOverride(BaseModel):
    """Per-cat override for a capability."""

    catId: str
    enabled: bool


class CapabilityEntry(BaseModel):
    """A single capability entry in capabilities.json."""

    id: str
    type: Literal["mcp", "skill"]
    enabled: bool = True
    source: str = "external"
    mcpServer: Optional[McpServerConfig] = None
    overrides: List[CatOverride] = Field(default_factory=list)
    description: Optional[str] = None
    triggers: Optional[List[str]] = None


class CapabilitiesConfig(BaseModel):
    """Root schema for .neowai/capabilities.json."""

    version: Literal[1] = 1
    capabilities: List[CapabilityEntry] = Field(default_factory=list)


# ── API Response Models ──


class CapabilityBoardItem(BaseModel):
    """Single item in the capability board response."""

    id: str
    type: Literal["mcp", "skill"]
    source: str
    enabled: bool
    description: Optional[str] = None
    triggers: Optional[List[str]] = None
    cats: Dict[str, bool] = Field(default_factory=dict)
    connectionStatus: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    probeError: Optional[str] = None


class CapabilityBoardResponse(BaseModel):
    """GET /api/capabilities response."""

    items: List[CapabilityBoardItem] = Field(default_factory=list)
    projectPath: str


class CapabilityPatchRequest(BaseModel):
    """PATCH /api/capabilities request body."""

    capabilityId: str
    capabilityType: Literal["mcp", "skill"]
    scope: Literal["global", "cat"]
    enabled: bool
    catId: Optional[str] = None
    projectPath: Optional[str] = None


# ── Discovery / Resolver Models ──


class McpServerDescriptor(BaseModel):
    """Lightweight descriptor used during discovery and resolution."""

    name: str
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    enabled: bool = True
    source: str = "external"
    transport: Optional[str] = None
    url: Optional[str] = None
    resolver: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    env: Optional[Dict[str, str]] = None
    workingDir: Optional[str] = None
