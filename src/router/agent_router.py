import re
from typing import List, Dict, Any, Optional
from src.config import CatConfigLoader
from src.cats.orange.service import OrangeService
from src.cats.inky.service import InkyService
from src.cats.patch.service import PatchService


# Role to breed mapping (position-based routing)
ROLE_TO_BREED = {
    # Development -> Orange
    "developer": "orange",
    "coder": "orange",
    "implementer": "orange",

    # Review -> Inky
    "reviewer": "inky",
    "audit": "inky",
    "inspector": "inky",

    # Research -> Patch
    "researcher": "patch",
    "designer": "patch",
    "creative": "patch",
}


class AgentRouter:
    """Route @mentions to corresponding agent services"""

    def __init__(self, config_path: str = "config/cat-config.json"):
        self.config_loader = CatConfigLoader(config_path)
        self._services: Dict[str, Any] = {}  # breed_id -> service instance

    def parse_mentions(self, message: str) -> List[str]:
        """Extract @mentions from message"""
        pattern = r'@\w+'
        mentions = re.findall(pattern, message)
        return [m.lower() for m in mentions]

    def get_service(self, breed_id: str):
        """Get or create service instance (cached)"""
        if breed_id not in self._services:
            breed_config = self.config_loader.get_breed(breed_id)
            if not breed_config:
                raise ValueError(f"Breed not found: {breed_id}")

            # Create service based on breed
            service_class = self._get_service_class(breed_id)
            self._services[breed_id] = service_class(breed_config)

        return self._services[breed_id]

    def _get_service_class(self, breed_id: str):
        """Get service class for breed"""
        if breed_id == "orange":
            return OrangeService
        elif breed_id == "inky":
            return InkyService
        elif breed_id == "patch":
            return PatchService
        else:
            raise ValueError(f"Unknown breed: {breed_id}")

    def route_message(self, message: str) -> List[Dict[str, Any]]:
        """Route message to agents based on @mentions"""
        mentions = self.parse_mentions(message)

        if not mentions:
            # Default to @dev if no mentions
            mentions = ["@dev"]

        results = []
        seen_breeds = set()

        for mention in mentions:
            # Remove @ prefix
            mention_text = mention[1:]  # Remove @

            # Try role-based mapping first
            breed_id = ROLE_TO_BREED.get(mention_text)

            # Fall back to mention pattern matching
            if not breed_id:
                breed_config = self.config_loader.get_breed_by_mention(mention)
                if breed_config:
                    breed_id = breed_config["id"]

            if breed_id and breed_id not in seen_breeds:
                service = self.get_service(breed_id)
                results.append({
                    "breed_id": breed_id,
                    "name": service.name,
                    "service": service
                })
                seen_breeds.add(breed_id)

        return results
