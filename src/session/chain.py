from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import time


class SessionStatus(str, Enum):
    ACTIVE = "active"
    SEALED = "sealed"


@dataclass
class SessionRecord:
    cat_id: str
    thread_id: str
    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    consecutive_restore_failures: int = 0
    created_at: float = field(default_factory=time.time)


class SessionChain:
    MAX_RESTORE_FAILURES = 3

    def __init__(self):
        self._chains: Dict[Tuple[str, str], List[SessionRecord]] = {}

    def create(self, cat_id: str, thread_id: str, session_id: str) -> SessionRecord:
        key = (cat_id, thread_id)
        if key not in self._chains:
            self._chains[key] = []
        record = SessionRecord(cat_id=cat_id, thread_id=thread_id, session_id=session_id)
        self._chains[key].append(record)
        return record

    def get_active(self, cat_id: str, thread_id: str) -> Optional[SessionRecord]:
        key = (cat_id, thread_id)
        for record in reversed(self._chains.get(key, [])):
            if record.status == SessionStatus.ACTIVE:
                return record
        return None

    def seal(self, cat_id: str, thread_id: str) -> None:
        active = self.get_active(cat_id, thread_id)
        if active:
            active.status = SessionStatus.SEALED

    def should_auto_seal(self, cat_id: str, thread_id: str) -> bool:
        active = self.get_active(cat_id, thread_id)
        return active is not None and active.consecutive_restore_failures >= self.MAX_RESTORE_FAILURES
