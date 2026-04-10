import re
from typing import List, Optional
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.models.types import CatId


class AgentRouterV2:
    """升级版路由器 — 基于 CatRegistry + AgentRegistry"""

    def __init__(self, cat_registry: CatRegistry, agent_registry: AgentRegistry):
        self.cat_registry = cat_registry
        self.agent_registry = agent_registry
        self._mention_pattern = re.compile(r'@[\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff-]+')

    def parse_mentions(self, message: str) -> List[str]:
        raw = self._mention_pattern.findall(message)
        seen = set()
        result = []
        for m in raw:
            key = m[1:].lower()
            if key not in seen:
                seen.add(key)
                result.append(m)
        return result

    def resolve_targets(self, message: str) -> List[CatId]:
        mentions = self.parse_mentions(message)
        targets = []
        seen = set()
        for mention in mentions:
            config = self.cat_registry.get_by_mention(mention)
            if config and config.cat_id not in seen:
                targets.append(config.cat_id)
                seen.add(config.cat_id)
        if not targets:
            default_id = self.cat_registry.get_default_id()
            if default_id:
                targets.append(default_id)
        return targets

    def get_service(self, cat_id: CatId):
        return self.agent_registry.get(cat_id)

    def route_message(self, message: str) -> List[dict]:
        targets = self.resolve_targets(message)
        results = []
        for cat_id in targets:
            config = self.cat_registry.get(cat_id)
            service = self.agent_registry.get(cat_id)
            results.append({"breed_id": cat_id, "name": config.display_name, "service": service})
        return results
