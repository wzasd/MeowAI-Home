"""Capability orchestrator REST API endpoints."""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from src.capabilities.orchestrator import (
    build_board_response,
    get_or_bootstrap,
    toggle_capability,
)
from src.capabilities.models import CapabilityPatchRequest
from src.capabilities.mcp_probe import probe_mcp_capabilities

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("")
async def get_capabilities(project_path: str, probe: bool = False) -> Dict[str, Any]:
    """Get the capability board for a project, bootstrapping if necessary."""
    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")
    config = get_or_bootstrap(project_path)
    probe_results = None
    if probe:
        probe_results = await probe_mcp_capabilities(config.capabilities)
    response = await build_board_response(project_path, config, probe_results=probe_results)
    return response.model_dump()


@router.patch("")
async def patch_capability(request: CapabilityPatchRequest) -> Dict[str, Any]:
    """Toggle a capability globally or per-cat."""
    project_root = request.projectPath
    if not project_root:
        raise HTTPException(status_code=400, detail="projectPath is required")

    config = get_or_bootstrap(project_root)
    try:
        cap = toggle_capability(
            project_root=project_root,
            config=config,
            capability_id=request.capabilityId,
            capability_type=request.capabilityType,
            scope=request.scope,
            enabled=request.enabled,
            cat_id=request.catId,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"ok": True, "capability": cap.model_dump()}
