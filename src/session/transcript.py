"""TranscriptWriter — buffered NDJSON writer per session with sparse index."""
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TranscriptEntry:
    role: str
    content: str
    timestamp: float
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
        }


INDEX_STRIDE = 100


class TranscriptWriter:
    """Buffered NDJSON writer with sparse byte-offset index."""

    def __init__(self, base_dir: str = "data/transcripts"):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return self._base_dir / session_id

    def _events_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "events.jsonl"

    def _index_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "index.json"

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an entry to the transcript."""
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        entry = TranscriptEntry(
            role=role,
            content=content,
            timestamp=time.time(),
            tool_calls=tool_calls,
            metadata=metadata or {},
        )

        events_path = self._events_path(session_id)

        # Get current line count for indexing
        line_count = 0
        if events_path.exists():
            with open(events_path, "rb") as f:
                line_count = sum(1 for _ in f)

        # Write entry
        with open(events_path, "a", encoding="utf-8") as f:
            line = json.dumps(entry.to_dict(), ensure_ascii=False)
            f.write(line + "\n")

        # Update index if at stride boundary
        if (line_count + 1) % INDEX_STRIDE == 0:
            self._update_index(session_id, line_count + 1)

    def _update_index(self, session_id: str, entry_count: int) -> None:
        """Update sparse index with byte offset."""
        events_path = self._events_path(session_id)
        index_path = self._index_path(session_id)

        # Calculate byte offset for the next entry (current file size)
        offset = events_path.stat().st_size

        index = {}
        if index_path.exists():
            index = json.loads(index_path.read_text())

        if "offsets" not in index:
            index["offsets"] = {}

        index["offsets"][str(entry_count)] = offset
        index["last_entry_count"] = entry_count

        index_path.write_text(json.dumps(index))

    def read(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read events from transcript. Returns most recent first if limit specified."""
        events_path = self._events_path(session_id)
        if not events_path.exists():
            return []

        events = []
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        if limit and len(events) > limit:
            events = events[-limit:]

        return events

    def digest(self, session_id: str) -> Dict[str, Any]:
        """Extract digest: tool names, file paths, errors."""
        events = self.read(session_id)

        tool_names = set()
        file_paths = set()
        errors = []

        # Pattern for file paths
        path_pattern = re.compile(r"[\w\-/\\]+\.(py|js|ts|json|md|txt|yaml|yml|sql)\b")

        for event in events:
            content = event.get("content", "")

            # Extract tool calls
            tc = event.get("tool_calls")
            if tc:
                for tool in tc:
                    name = tool.get("name")
                    if name:
                        tool_names.add(name)

            # Extract file paths from content
            paths = path_pattern.findall(content)
            # Get full matches
            for match in path_pattern.finditer(content):
                file_paths.add(match.group(0))

            # Extract errors (simple pattern matching)
            if "error" in content.lower() or "exception" in content.lower():
                # Extract error line
                lines = content.split("\n")
                for line in lines:
                    if "error" in line.lower() or "exception" in line.lower():
                        errors.append(line.strip())

        # Count messages
        user_count = sum(1 for e in events if e.get("role") == "user")
        assistant_count = sum(1 for e in events if e.get("role") == "assistant")

        return {
            "tool_names": sorted(list(tool_names)),
            "file_paths": sorted(list(file_paths)),
            "errors": errors[:10],  # Cap at 10
            "message_count": len(events),
            "user_count": user_count,
            "assistant_count": assistant_count,
        }
