"""SignalSource — source configuration for content aggregation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceTier(str, Enum):
    """Priority tier for sources."""
    P0 = "p0"  # Critical - real-time monitoring
    P1 = "p1"  # Important - hourly check
    P2 = "p2"  # Normal - daily check
    P3 = "p3"  # Archive - weekly check


class FetchMethod(str, Enum):
    """Method for fetching content."""
    RSS = "rss"
    JSON = "json"
    WEBPAGE = "webpage"


@dataclass
class SourceConfig:
    """Configuration for a content source."""
    source_id: str
    name: str
    url: str
    method: FetchMethod
    tier: SourceTier = SourceTier.P2
    schedule: str = "daily"  # cron expression or preset
    keywords: List[str] = field(default_factory=list)
    selectors: Optional[Dict[str, str]] = None  # CSS selectors for webpage
    headers: Optional[Dict[str, str]] = None  # HTTP headers
    timeout: int = 30
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class SignalSource:
    """Registry for signal sources."""

    def __init__(self):
        self._sources: Dict[str, SourceConfig] = {}

    def register(self, config: SourceConfig) -> None:
        """Register a source configuration."""
        self._sources[config.source_id] = config

    def unregister(self, source_id: str) -> bool:
        """Remove a source."""
        if source_id in self._sources:
            del self._sources[source_id]
            return True
        return False

    def get(self, source_id: str) -> Optional[SourceConfig]:
        """Get source configuration."""
        return self._sources.get(source_id)

    def list_all(self) -> List[SourceConfig]:
        """List all sources."""
        return list(self._sources.values())

    def list_enabled(self) -> List[SourceConfig]:
        """List enabled sources."""
        return [s for s in self._sources.values() if s.enabled]

    def list_by_tier(self, tier: SourceTier) -> List[SourceConfig]:
        """List sources by tier."""
        return [s for s in self._sources.values() if s.tier == tier]

    def list_by_method(self, method: FetchMethod) -> List[SourceConfig]:
        """List sources by fetch method."""
        return [s for s in self._sources.values() if s.method == method]

    def update(self, source_id: str, **updates) -> bool:
        """Update source configuration."""
        if source_id not in self._sources:
            return False

        source = self._sources[source_id]
        for key, value in updates.items():
            if hasattr(source, key):
                setattr(source, key, value)
        return True

    def to_yaml(self) -> str:
        """Export sources to YAML format."""
        import yaml
        data = {
            "sources": [
                {
                    "id": s.source_id,
                    "name": s.name,
                    "url": s.url,
                    "method": s.method.value,
                    "tier": s.tier.value,
                    "schedule": s.schedule,
                    "keywords": s.keywords,
                    "selectors": s.selectors,
                    "headers": s.headers,
                    "timeout": s.timeout,
                    "enabled": s.enabled,
                }
                for s in self._sources.values()
            ]
        }
        return yaml.dump(data, allow_unicode=True, sort_keys=False)

    def from_yaml(self, yaml_str: str) -> None:
        """Load sources from YAML."""
        import yaml
        data = yaml.safe_load(yaml_str)
        for s in data.get("sources", []):
            config = SourceConfig(
                source_id=s["id"],
                name=s["name"],
                url=s["url"],
                method=FetchMethod(s["method"]),
                tier=SourceTier(s.get("tier", "p2")),
                schedule=s.get("schedule", "daily"),
                keywords=s.get("keywords", []),
                selectors=s.get("selectors"),
                headers=s.get("headers"),
                timeout=s.get("timeout", 30),
                enabled=s.get("enabled", True),
            )
            self.register(config)
