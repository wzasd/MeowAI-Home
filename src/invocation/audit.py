"""Append-only audit log for tracking agent actions."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import json
from pathlib import Path


@dataclass
class AuditEntry:
    id: str
    timestamp: str
    level: Literal["info", "warning", "error", "critical"]
    category: Literal["file", "command", "network", "auth", "system"]
    actor: str
    action: str
    details: str
    threadId: str = ""


class AuditLog:
    """Append-only audit log stored as NDJSON files."""

    def __init__(self, log_dir: str = ".claude/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def append(self, entry: AuditEntry) -> None:
        """Append an entry to today's log file."""
        date = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"{date}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps({
                "id": entry.id,
                "timestamp": entry.timestamp,
                "level": entry.level,
                "category": entry.category,
                "actor": entry.actor,
                "action": entry.action,
                "details": entry.details,
                "threadId": entry.threadId,
            }) + "\n")

    def query(self, limit: int = 100, category: str = None, level: str = None) -> list[dict]:
        """Query audit entries with optional filters."""
        entries = []
        for log_file in sorted(self.log_dir.glob("*.jsonl"), reverse=True):
            if not log_file.exists():
                continue
            with open(log_file) as f:
                for line in f:
                    if len(entries) >= limit:
                        break
                    try:
                        data = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    if category and data.get("category") != category:
                        continue
                    if level and data.get("level") != level:
                        continue
                    entries.append(data)
        return entries[:limit]
