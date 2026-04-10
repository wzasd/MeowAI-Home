"""Agent management REST API endpoints"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from src.router.discovery import AgentDiscovery, AgentDescriptor

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Global instance (set during app initialization)
agent_discovery: AgentDiscovery = None


def set_agent_discovery(discovery: AgentDiscovery):
    global agent_discovery
    agent_discovery = discovery


@router.get("", response_model=List[Dict[str, Any]])
async def list_agents():
    """List all registered agents."""
    if not agent_discovery:
        raise HTTPException(500, "Agent discovery not initialized")
    agents = agent_discovery.list_agents()
    return [
        {
            "cat_id": a.cat_id,
            "breed": a.breed,
            "display_name": a.display_name,
            "capabilities": a.capabilities,
            "provider": a.provider,
        }
        for a in agents
    ]


@router.get("/{cat_id}")
async def get_agent(cat_id: str):
    """Get a specific agent by ID."""
    if not agent_discovery:
        raise HTTPException(500, "Agent discovery not initialized")
    agent = agent_discovery.get_agent(cat_id)
    if not agent:
        raise HTTPException(404, f"Agent not found: {cat_id}")
    return {
        "cat_id": agent.cat_id,
        "breed": agent.breed,
        "display_name": agent.display_name,
        "capabilities": agent.capabilities,
        "provider": agent.provider,
        "config": agent.config,
    }


@router.post("")
async def register_agent(agent: Dict[str, Any]):
    """Register a new agent."""
    if not agent_discovery:
        raise HTTPException(500, "Agent discovery not initialized")

    required = ["cat_id", "breed", "display_name", "capabilities", "provider"]
    for field in required:
        if field not in agent:
            raise HTTPException(400, f"Missing required field: {field}")

    descriptor = AgentDescriptor(
        cat_id=agent["cat_id"],
        breed=agent["breed"],
        display_name=agent["display_name"],
        capabilities=agent["capabilities"],
        provider=agent["provider"],
        config=agent.get("config"),
    )

    success = agent_discovery.register(descriptor)
    if not success:
        raise HTTPException(409, f"Agent already exists: {agent['cat_id']}")

    return {"status": "registered", "cat_id": agent["cat_id"]}


@router.delete("/{cat_id}")
async def deregister_agent(cat_id: str):
    """Remove an agent."""
    if not agent_discovery:
        raise HTTPException(500, "Agent discovery not initialized")

    success = agent_discovery.deregister(cat_id)
    if not success:
        raise HTTPException(404, f"Agent not found: {cat_id}")

    return {"status": "deregistered"}
