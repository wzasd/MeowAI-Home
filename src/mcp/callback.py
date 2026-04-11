"""MCP Callback framework — at-least-once delivery with outbox persistence."""
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import httpx


@dataclass
class CallbackConfig:
    """Configuration for callback delivery."""

    invocation_id: str
    token: str
    api_url: str
    timeout: float = 30.0

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Invocation-Id": self.invocation_id,
        }


@dataclass
class DeliveryResult:
    """Result of callback delivery attempt."""

    status: str  # "delivered" | "failed" | "pending"
    attempts: int
    error: Optional[str] = None
    response_status: Optional[int] = None


class CallbackOutbox:
    """Persistent outbox for callback messages."""

    def __init__(self, persist_dir: Optional[str] = None):
        self._messages: Dict[str, Dict[str, Any]] = {}
        self._queues: Dict[str, list] = {}  # invocation_id -> list of message_ids
        self._persist_dir = Path(persist_dir) if persist_dir else None

        if self._persist_dir:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._restore()

    def queue(self, invocation_id: str, payload: Dict[str, Any]) -> str:
        """Queue a message for delivery."""
        msg_id = str(uuid.uuid4())[:8]
        message = {
            "id": msg_id,
            "invocation_id": invocation_id,
            "payload": payload,
            "retry_count": 0,
            "created_at": time.time(),
        }
        self._messages[msg_id] = message

        if invocation_id not in self._queues:
            self._queues[invocation_id] = []
        self._queues[invocation_id].append(msg_id)

        self._persist()
        return msg_id

    def dequeue(self, invocation_id: str) -> Optional[Dict[str, Any]]:
        """Get next message from queue (removes it)."""
        queue = self._queues.get(invocation_id, [])
        if not queue:
            return None

        msg_id = queue[0]
        return self._messages.get(msg_id)

    def peek(self, invocation_id: str) -> Optional[Dict[str, Any]]:
        """Peek at next message without removing."""
        queue = self._queues.get(invocation_id, [])
        if not queue:
            return None

        msg_id = queue[0]
        return self._messages.get(msg_id)

    def confirm_delivery(self, msg_id: str) -> None:
        """Mark message as delivered (remove from queue)."""
        if msg_id not in self._messages:
            return

        message = self._messages.pop(msg_id)
        invocation_id = message["invocation_id"]

        if invocation_id in self._queues:
            if msg_id in self._queues[invocation_id]:
                self._queues[invocation_id].remove(msg_id)

        self._persist()

    def increment_retry(self, msg_id: str) -> None:
        """Increment retry count for a message."""
        if msg_id in self._messages:
            self._messages[msg_id]["retry_count"] += 1
            self._persist()

    def size(self, invocation_id: str) -> int:
        """Get queue size for invocation."""
        return len(self._queues.get(invocation_id, []))

    def _persist(self) -> None:
        """Persist outbox to disk."""
        if not self._persist_dir:
            return

        data = {
            "messages": self._messages,
            "queues": self._queues,
        }
        persist_path = self._persist_dir / "outbox.json"
        # Atomic write
        temp_path = persist_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, default=str))
        temp_path.rename(persist_path)

    def _restore(self) -> None:
        """Restore outbox from disk."""
        if not self._persist_dir:
            return

        persist_path = self._persist_dir / "outbox.json"
        if not persist_path.exists():
            return

        try:
            data = json.loads(persist_path.read_text())
            self._messages = data.get("messages", {})
            self._queues = data.get("queues", {})
        except (json.JSONDecodeError, IOError):
            pass


class CallbackDelivery:
    """HTTP callback delivery with exponential backoff retry."""

    # Status codes that should not be retried (client errors)
    NON_RETRYABLE_STATUS = {400, 401, 403, 404, 422}

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    def send(
        self,
        config: CallbackConfig,
        payload: Dict[str, Any],
    ) -> DeliveryResult:
        """Send callback with retry."""
        last_error = None
        attempts = 0

        for attempt in range(self._max_retries):
            attempts += 1

            try:
                response = httpx.post(
                    config.api_url,
                    headers=config.headers,
                    json=payload,
                    timeout=config.timeout,
                )

                if response.status_code == 200:
                    return DeliveryResult(
                        status="delivered",
                        attempts=attempts,
                        response_status=response.status_code,
                    )

                # Non-retryable status code
                if response.status_code in self.NON_RETRYABLE_STATUS:
                    return DeliveryResult(
                        status="failed",
                        attempts=attempts,
                        response_status=response.status_code,
                        error=f"HTTP {response.status_code}: {response.text}",
                    )

                # Retryable status code (5xx, etc.)
                last_error = f"HTTP {response.status_code}: {response.text}"

            except Exception as e:
                last_error = str(e)

            # Don't retry on last attempt
            if attempt < self._max_retries - 1:
                delay = min(
                    self._base_delay * (2 ** attempt),
                    self._max_delay,
                )
                time.sleep(delay)

        return DeliveryResult(
            status="failed",
            attempts=attempts,
            error=last_error,
        )
