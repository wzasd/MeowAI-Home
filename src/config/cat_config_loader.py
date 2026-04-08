import json
from pathlib import Path
from typing import Any, Dict, Optional


class CatConfigLoader:
    """Singleton loader for cat-config.json"""

    _instance: Optional["CatConfigLoader"] = None
    _config: Optional[Dict[str, Any]] = None

    def __new__(cls, config_path: str = "config/cat-config.json"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_path = config_path
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton instance (for testing)"""
        cls._instance = None
        cls._config = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if self._config is None:
            config_file = Path(self._config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {self._config_path}")

            with open(config_file, "r", encoding="utf-8") as f:
                self._config = json.load(f)

        return self._config

    def get_breed(self, breed_id: str) -> Optional[Dict[str, Any]]:
        """Get breed configuration by ID"""
        config = self.load()
        for breed in config.get("breeds", []):
            if breed.get("id") == breed_id:
                return breed
        return None

    def get_breed_by_mention(self, mention: str) -> Optional[Dict[str, Any]]:
        """Get breed by @mention (role or name)"""
        config = self.load()
        mention_lower = mention.lower()

        for breed in config.get("breeds", []):
            patterns = breed.get("mentionPatterns", [])
            # Normalize patterns for comparison
            normalized_patterns = [p.lower() for p in patterns]

            if mention_lower in normalized_patterns:
                return breed

        return None

    def list_breeds(self) -> list:
        """List all breed configurations"""
        config = self.load()
        return config.get("breeds", [])
