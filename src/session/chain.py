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
    # Runtime stats
    message_count: int = 0
    tokens_used: int = 0
    latency_ms: int = 0
    turn_count: int = 0
    # Invocation metadata
    cli_command: str = ""
    default_model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    budget_max_prompt: int = 0
    budget_max_context: int = 0


class SessionChain:
    MAX_RESTORE_FAILURES = 3

    def __init__(self):
        self._chains: Dict[Tuple[str, str], List[SessionRecord]] = {}

    def create(
        self,
        cat_id: str,
        thread_id: str,
        session_id: str,
        message_count: int = 0,
        tokens_used: int = 0,
        latency_ms: int = 0,
        turn_count: int = 0,
        cli_command: str = "",
        default_model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
        budget_max_prompt: int = 0,
        budget_max_context: int = 0,
    ) -> SessionRecord:
        key = (cat_id, thread_id)
        if key not in self._chains:
            self._chains[key] = []
        for existing in self._chains[key]:
            if existing.status == SessionStatus.ACTIVE:
                existing.status = SessionStatus.SEALED
        record = SessionRecord(
            cat_id=cat_id,
            thread_id=thread_id,
            session_id=session_id,
            message_count=message_count,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            turn_count=turn_count,
            cli_command=cli_command,
            default_model=default_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
            budget_max_prompt=budget_max_prompt,
            budget_max_context=budget_max_context,
        )
        self._chains[key].append(record)
        return record

    def update_stats(
        self,
        cat_id: str,
        thread_id: str,
        session_id: str,
        message_count: int = 0,
        tokens_used: int = 0,
        latency_ms: int = 0,
        turn_count: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> Optional[SessionRecord]:
        key = (cat_id, thread_id)
        for record in reversed(self._chains.get(key, [])):
            if record.session_id == session_id and record.status == SessionStatus.ACTIVE:
                record.message_count += message_count
                record.tokens_used += tokens_used
                record.latency_ms += latency_ms
                record.turn_count += turn_count
                record.prompt_tokens += prompt_tokens
                record.completion_tokens += completion_tokens
                record.cache_read_tokens += cache_read_tokens
                record.cache_creation_tokens += cache_creation_tokens
                return record
        return None

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
        return (
            active is not None
            and active.consecutive_restore_failures >= self.MAX_RESTORE_FAILURES
        )
