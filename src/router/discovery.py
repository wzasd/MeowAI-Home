"""Agent hot registration — add/remove agents at runtime"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.models.agent_registry import AgentRegistry


@dataclass(frozen=True)
class AgentService:
    """Simple service wrapper for agent metadata."""
    cat_id: str
    breed: str
    display_name: str
    provider: str
    capabilities: List[str]
    config: Optional[Dict] = None


@dataclass
class AgentDescriptor:
    """Descriptor for registering a new agent."""
    cat_id: str
    breed: str           # "ragdoll" | "maine_coon" | "siamese" | etc.
    display_name: str
    capabilities: tuple  # Frozen dataclass needs hashable types
    provider: str        # "claude" | "codex" | "gemini" | etc.
    config: Optional[Dict] = None


class AgentDiscovery:
    """Hot-registration: add/remove agents at runtime without restart."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def register(self, descriptor: AgentDescriptor) -> bool:
        """Register a new agent. Returns False if cat_id already exists."""
        if self.registry.has(descriptor.cat_id):
            return False
        # Store agent metadata in registry
        service = AgentService(
            cat_id=descriptor.cat_id,
            breed=descriptor.breed,
            display_name=descriptor.display_name,
            provider=descriptor.provider,
            capabilities=descriptor.capabilities,
            config=descriptor.config or {},
        )
        self.registry.register(descriptor.cat_id, service)
        return True

    def deregister(self, cat_id: str) -> bool:
        """Remove an agent from registry."""
        if not self.registry.has(cat_id):
            return False
        self.registry.unregister(cat_id)
        return True

    def list_agents(self) -> List[AgentDescriptor]:
        """List all registered agents."""
        descriptors = []
        for cat_id, service in self.registry.get_all_entries().items():
            descriptors.append(AgentDescriptor(
                cat_id=cat_id,
                breed=getattr(service, 'breed', 'unknown'),
                display_name=getattr(service, 'display_name', cat_id),
                capabilities=getattr(service, 'capabilities', []),
                provider=getattr(service, 'provider', 'unknown'),
                config=getattr(service, 'config', None),
            ))
        return descriptors

    def get_agent(self, cat_id: str) -> Optional[AgentDescriptor]:
        """Get a single agent descriptor by cat_id."""
        if not self.registry.has(cat_id):
            return None
        service = self.registry.get(cat_id)
        return AgentDescriptor(
            cat_id=cat_id,
            breed=getattr(service, 'breed', 'unknown'),
            display_name=getattr(service, 'display_name', cat_id),
            capabilities=getattr(service, 'capabilities', []),
            provider=getattr(service, 'provider', 'unknown'),
            config=getattr(service, 'config', None),
        )
