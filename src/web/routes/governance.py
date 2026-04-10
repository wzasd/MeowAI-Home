"""Governance REST API endpoints"""
from fastapi import APIRouter
from typing import List, Dict, Any

from src.governance.iron_laws import IRON_LAWS

router = APIRouter(prefix="/api/governance", tags=["governance"])


@router.get("/iron-laws")
async def get_iron_laws():
    """Get all iron laws (system safety rules)."""
    return {
        "laws": [
            {"id": i + 1, "title": law["title"], "description": law["description"]}
            for i, law in enumerate(IRON_LAWS)
        ]
    }
