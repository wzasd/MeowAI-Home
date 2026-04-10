"""Pack REST API endpoints"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from src.packs.loader import PackLoader
from src.packs.store import PackStore

router = APIRouter(prefix="/api/packs", tags=["packs"])

# Global instances (set during app initialization)
pack_loader: PackLoader = None
pack_store: PackStore = None


def set_pack_instances(loader: PackLoader, store: PackStore):
    global pack_loader, pack_store
    pack_loader = loader
    pack_store = store


@router.get("", response_model=List[Dict[str, Any]])
async def list_packs():
    """List all available packs."""
    if not pack_loader:
        raise HTTPException(500, "Pack system not initialized")
    packs = []
    for name in pack_loader.list_packs():
        pack = pack_loader.load(name)
        if pack:
            packs.append({
                "name": pack.get("name", name),
                "display_name": pack.get("display_name", name),
                "description": pack.get("description", ""),
                "agents": len(pack.get("agents", [])),
                "skills": len(pack.get("skills", [])),
            })
    return packs


@router.get("/{name}")
async def get_pack(name: str):
    """Get detailed pack information."""
    if not pack_loader:
        raise HTTPException(500, "Pack system not initialized")
    pack = pack_loader.load(name)
    if not pack:
        raise HTTPException(404, f"Pack not found: {name}")
    return pack


@router.post("/{name}/activate")
async def activate_pack(name: str, thread_id: str):
    """Activate a pack for a thread."""
    if not pack_loader or not pack_store:
        raise HTTPException(500, "Pack system not initialized")

    pack = pack_loader.load(name)
    if not pack:
        raise HTTPException(404, f"Pack not found: {name}")

    agents = [a["cat_id"] for a in pack.get("agents", [])]
    activation_id = pack_store.activate(name, thread_id, agents)

    return {
        "id": activation_id,
        "pack_name": name,
        "thread_id": thread_id,
        "agents": agents,
    }


@router.delete("/{name}/deactivate")
async def deactivate_pack(name: str, thread_id: str):
    """Deactivate a pack for a thread."""
    if not pack_store:
        raise HTTPException(500, "Pack system not initialized")

    success = pack_store.deactivate(name, thread_id)
    if not success:
        raise HTTPException(404, f"Pack not active: {name}")

    return {"status": "deactivated"}


@router.get("/active/{thread_id}")
async def get_active_packs(thread_id: str):
    """Get all active packs for a thread."""
    if not pack_store:
        raise HTTPException(500, "Pack system not initialized")
    return pack_store.get_active(thread_id)
