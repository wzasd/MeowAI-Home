"""Governance REST API endpoints"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.governance.iron_laws import IRON_LAWS

router = APIRouter(prefix="/api/governance", tags=["governance"])

DEFAULT_DB_PATH = Path.home() / ".meowai" / "meowai.db"

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
    confirmed: bool = False


class GovernanceHealthResponse(BaseModel):
    """Governance health summary."""
    projects: List[GovernanceProject]


class DiscoverRequest(BaseModel):
    """Discover external projects request."""
    project_paths: List[str]


class ConfirmRequest(BaseModel):
    """Confirm/sync governance request."""
    project_path: str


class ProjectCreateRequest(BaseModel):
    """Create or update a governance project."""
    project_path: str
    status: str = "healthy"
    version: Optional[str] = None
    findings: List[GovernanceFinding] = Field(default_factory=list)
    confirmed: bool = False


# === Database helpers ===


async def _get_db(db_path: Path = DEFAULT_DB_PATH) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def _init_governance_table(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS governance_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_path TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'healthy',
            version TEXT,
            findings TEXT DEFAULT '[]',
            synced_at REAL,
            confirmed INTEGER DEFAULT 0
        )
    """)
    await db.commit()


async def _with_db(db_path: Path = DEFAULT_DB_PATH):
    db = await _get_db(db_path)
    await _init_governance_table(db)
    return db


def _row_to_project(row: aiosqlite.Row) -> GovernanceProject:
    findings_raw = json.loads(row["findings"] or "[]")
    findings = [GovernanceFinding(**f) for f in findings_raw]
    synced_at = None
    if row["synced_at"]:
        synced_at = datetime.utcfromtimestamp(row["synced_at"]).isoformat()
    return GovernanceProject(
        project_path=row["project_path"],
        status=row["status"],
        pack_version=row["version"],
        last_synced_at=synced_at,
        findings=findings,
        confirmed=bool(row["confirmed"]),
    )


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
    db = await _with_db()
    try:
        cursor = await db.execute(
            "SELECT project_path, status, version, findings, synced_at, confirmed FROM governance_projects"
        )
        rows = await cursor.fetchall()
        projects = [_row_to_project(row) for row in rows]
        return GovernanceHealthResponse(projects=projects)
    finally:
        await db.close()


@router.get("/projects")
async def list_governance_projects() -> Dict[str, Any]:
    """List all governance projects from SQLite."""
    db = await _with_db()
    try:
        cursor = await db.execute(
            "SELECT project_path, status, version, findings, synced_at, confirmed FROM governance_projects"
        )
        rows = await cursor.fetchall()
        projects = [_row_to_project(row) for row in rows]
        return {"projects": [p.model_dump() for p in projects]}
    finally:
        await db.close()


@router.post("/projects")
async def upsert_governance_project(request: ProjectCreateRequest) -> Dict[str, Any]:
    """Create or update a governance project."""
    db = await _with_db()
    try:
        findings_json = json.dumps([f.model_dump() for f in request.findings])
        synced_at = time.time()
        confirmed_int = 1 if request.confirmed else 0
        await db.execute("""
            INSERT INTO governance_projects
            (project_path, status, version, findings, synced_at, confirmed)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_path) DO UPDATE SET
                status = excluded.status,
                version = excluded.version,
                findings = excluded.findings,
                synced_at = excluded.synced_at,
                confirmed = excluded.confirmed
        """, (
            request.project_path,
            request.status,
            request.version,
            findings_json,
            synced_at,
            confirmed_int,
        ))
        await db.commit()
        return {"success": True, "project_path": request.project_path}
    finally:
        await db.close()


@router.delete("/projects/{project_path:path}")
async def delete_governance_project(project_path: str) -> Dict[str, Any]:
    """Delete a governance project by path."""
    db = await _with_db()
    try:
        cursor = await db.execute(
            "DELETE FROM governance_projects WHERE project_path = ?", (project_path,)
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_path}")
        return {"success": True, "deleted": project_path}
    finally:
        await db.close()


@router.post("/discover")
async def discover_projects(request: DiscoverRequest) -> Dict[str, Any]:
    """Discover external projects not yet in governance registry."""
    db = await _with_db()
    try:
        cursor = await db.execute(
            "SELECT project_path FROM governance_projects"
        )
        rows = await cursor.fetchall()
        existing = {row["project_path"] for row in rows}
        unsynced = [path for path in request.project_paths if path not in existing]
        return {"unsynced": unsynced}
    finally:
        await db.close()


@router.post("/confirm")
async def confirm_governance(request: ConfirmRequest) -> Dict[str, Any]:
    """Sync governance rules for a project."""
    db = await _with_db()
    try:
        synced_at = time.time()
        await db.execute("""
            INSERT INTO governance_projects
            (project_path, status, version, findings, synced_at, confirmed)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_path) DO UPDATE SET
                status = excluded.status,
                version = excluded.version,
                findings = excluded.findings,
                synced_at = excluded.synced_at,
                confirmed = excluded.confirmed
        """, (
            request.project_path,
            "healthy",
            "1.0.0",
            "[]",
            synced_at,
            1,
        ))
        await db.commit()
        return {"success": True, "project_path": request.project_path, "status": "healthy"}
    finally:
        await db.close()
