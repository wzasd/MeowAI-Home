"""Audit API routes."""
from fastapi import APIRouter, Query
from typing import Optional
from src.invocation.audit import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])

_audit_log = None


def get_audit_log():
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log


@router.get("/entries")
async def list_entries(
    category: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100,
):
    """Get audit entries with optional filters."""
    log = get_audit_log()
    return log.query(limit=limit, category=category, level=level)
