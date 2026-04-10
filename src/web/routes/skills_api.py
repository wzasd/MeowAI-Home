"""Skills REST API endpoints"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/skills", tags=["skills"])

# Global instance (set during app initialization)
skill_loader = None
skill_router = None
chain_tracker = None


def set_skill_instances(loader, router, tracker):
    global skill_loader, skill_router, chain_tracker
    skill_loader = loader
    skill_router = router
    chain_tracker = tracker


@router.get("", response_model=List[Dict[str, Any]])
async def list_skills():
    """List all available skills."""
    if not skill_loader:
        raise HTTPException(500, "Skill system not initialized")

    skills = []
    for skill_id in skill_loader.list_skills():
        manifest = skill_loader.get_manifest(skill_id)
        if manifest:
            skills.append({
                "id": skill_id,
                "name": manifest.get("name", skill_id),
                "description": manifest.get("description", ""),
                "triggers": manifest.get("triggers", []),
            })
    return skills


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """Get skill details."""
    if not skill_loader:
        raise HTTPException(500, "Skill system not initialized")

    manifest = skill_loader.get_manifest(skill_id)
    if not manifest:
        raise HTTPException(404, f"Skill not found: {skill_id}")

    return manifest


@router.get("/chains/{thread_id}")
async def get_chain_status(thread_id: str):
    """Get active skill chain for a thread."""
    if not chain_tracker:
        raise HTTPException(500, "Chain tracker not initialized")

    chain = chain_tracker.get_active(thread_id)
    if not chain:
        return {"active": False}

    return {
        "active": True,
        "chain_id": chain.chain_id,
        "skills": chain.skills,
        "current_index": chain.current_index,
        "current_skill": chain.current_skill,
        "progress": f"{chain.current_index}/{len(chain.skills)}",
    }
