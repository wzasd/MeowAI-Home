from typing import Dict, Any
from src.models.types import CatId


class AgentRegistry:
    """Agent 服务实例注册表 — catId -> AgentService"""

    def __init__(self):
        self._services: Dict[CatId, Any] = {}

    def register(self, cat_id: CatId, service: Any) -> None:
        if cat_id in self._services:
            raise ValueError(f"Cat already registered: {cat_id}")
        self._services[cat_id] = service

    def get(self, cat_id: CatId) -> Any:
        if cat_id not in self._services:
            raise KeyError(f"Agent not registered: {cat_id}")
        return self._services[cat_id]

    def has(self, cat_id: CatId) -> bool:
        return cat_id in self._services

    def get_all_entries(self) -> Dict[CatId, Any]:
        return dict(self._services)

    def reset(self) -> None:
        self._services.clear()

    def unregister(self, cat_id: CatId) -> None:
        """Remove an agent from the registry."""
        if cat_id not in self._services:
            raise KeyError(f"Agent not registered: {cat_id}")
        del self._services[cat_id]
