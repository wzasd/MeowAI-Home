import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

INDEX_PATH = Path.home() / ".meowai" / "nest-index.json"


def _index_path() -> Path:
    return INDEX_PATH


class NestRegistry:
    def __init__(self, index_path: Path = None):
        self.index_path = index_path or _index_path()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"version": 1, "projects": []}

    def _save(self, data) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def register(self, project_path: str) -> None:
        data = self._load()
        now = datetime.now(timezone.utc).isoformat()
        for project in data["projects"]:
            if project["path"] == project_path:
                project["last_used_at"] = now
                self._save(data)
                return
        data["projects"].append(
            {"path": project_path, "activated_at": now, "last_used_at": now}
        )
        self._save(data)

    def unregister(self, project_path: str) -> bool:
        data = self._load()
        original_len = len(data["projects"])
        data["projects"] = [p for p in data["projects"] if p["path"] != project_path]
        if len(data["projects"]) < original_len:
            self._save(data)
            return True
        return False

    def list_projects(self) -> List[Dict[str, Any]]:
        data = self._load()
        return list(data["projects"])

    def is_registered(self, project_path: str) -> bool:
        data = self._load()
        return any(p["path"] == project_path for p in data["projects"])

    def update_last_used(self, project_path: str) -> None:
        self.register(project_path)
