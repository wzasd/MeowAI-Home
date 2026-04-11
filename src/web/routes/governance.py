"""Governance REST API endpoints"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.governance.iron_laws import IRON_LAWS

router = APIRouter(prefix="/api/governance", tags=["governance"])


# === Models ===

class GovernanceFinding(BaseModel):
    """A governance finding (issue or status)."""
    rule: str
    severity: str = "info"  # error, warning, info
    message: str


class GovernanceProject(BaseModel):
    """Governance health for a project."""
    project_path: str
    status: str = "never-synced"  # healthy, stale, missing, never-synced
    pack_version: Optional[str] = None
    last_synced_at: Optional[str] = None
    findings: List[GovernanceFinding] = Field(default_factory=list)


class GovernanceHealthResponse(BaseModel):
    """Governance health summary."""
    projects: List[GovernanceProject]


class DiscoverRequest(BaseModel):
    """Discover external projects request."""
    project_paths: List[str]


class ConfirmRequest(BaseModel):
    """Confirm/sync governance request."""
    project_path: str


# === In-memory storage (TODO: replace with database) ===

_projects: Dict[str, GovernanceProject] = {}


def _ensure_default_projects():
    """Ensure default governance projects exist."""
    if not _projects:
        defaults = [
            GovernanceProject(
                project_path="/projects/meowai-home",
                status="healthy",
                pack_version="1.0.0",
                last_synced_at=datetime.utcnow().isoformat(),
                findings=[],
            ),
            GovernanceProject(
                project_path="/projects/shared-libs",
                status="stale",
                pack_version="0.9.0",
                last_synced_at="2026-04-08T10:00:00",
                findings=[
                    GovernanceFinding(
                        rule="iron-law-1",
                        severity="warning",
                        message="数据安全铁律版本不一致，建议同步",
                    )
                ],
            ),
        ]
        for p in defaults:
            _projects[p.project_path] = p


# === Endpoints ===

@router.get("/iron-laws")
async def get_iron_laws():
    """Get all iron laws (system safety rules)."""
    return {
        "laws": [
            {"id": i + 1, "title": law["title"], "description": law["description"]}
            for i, law in enumerate(IRON_LAWS)
        ]
    }


@router.get("/health", response_model=GovernanceHealthResponse)
async def get_governance_health() -> GovernanceHealthResponse:
    """Get governance health status for all projects."""
    _ensure_default_projects()
    return GovernanceHealthResponse(projects=list(_projects.values()))


@router.post("/discover")
async def discover_projects(request: DiscoverRequest) -> Dict[str, Any]:
    """Discover external projects not yet in governance registry."""
    _ensure_default_projects()

    unsynced = []
    for path in request.project_paths:
        if path not in _projects:
            unsynced.append(path)

    return {"unsynced": unsynced}


@router.post("/confirm")
async def confirm_governance(request: ConfirmRequest) -> Dict[str, Any]:
    """Sync governance rules for a project."""
    _ensure_default_projects()

    if request.project_path not in _projects:
        # Create new project entry
        _projects[request.project_path] = GovernanceProject(
            project_path=request.project_path,
            status="healthy",
            pack_version="1.0.0",
            last_synced_at=datetime.utcnow().isoformat(),
            findings=[],
        )
    else:
        # Update existing project
        project = _projects[request.project_path]
        project.status = "healthy"
        project.pack_version = "1.0.0"
        project.last_synced_at = datetime.utcnow().isoformat()
        project.findings = []

    return {"success": True, "project_path": request.project_path, "status": "healthy"}
