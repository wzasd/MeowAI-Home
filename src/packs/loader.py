"""Pack loader for YAML-based pack definitions"""
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml


class PackLoader:
    """Load pack definitions from YAML files."""

    def __init__(self, packs_dir: str = "packs"):
        self.packs_dir = Path(packs_dir)

    def load(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a pack by name from YAML file."""
        path = self.packs_dir / f"{name}.yaml"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def list_packs(self) -> List[str]:
        """List available pack names (without .yaml extension)."""
        if not self.packs_dir.exists():
            return []
        return sorted([p.stem for p in self.packs_dir.glob("*.yaml")])

    def validate(self, pack: Dict[str, Any]) -> List[str]:
        """Validate pack structure, return list of errors."""
        errors = []
        required = ["name", "display_name", "agents"]
        for field in required:
            if field not in pack:
                errors.append(f"Missing required field: {field}")

        if "agents" in pack:
            if not isinstance(pack["agents"], list):
                errors.append("agents must be a list")
            elif len(pack["agents"]) == 0:
                errors.append("agents list cannot be empty")
            else:
                for i, agent in enumerate(pack["agents"]):
                    if "cat_id" not in agent:
                        errors.append(f"agent[{i}] missing cat_id")
                    if "breed" not in agent:
                        errors.append(f"agent[{i}] missing breed")

        return errors
