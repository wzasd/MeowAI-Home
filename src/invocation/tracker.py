import asyncio
from typing import Dict, Optional, Tuple


class _TrackedInvocation:
    def __init__(self):
        self.controller = asyncio.Event()
        self._cancelled = False

    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self):
        self._cancelled = True
        self.controller.set()


class InvocationTracker:
    def __init__(self):
        self._slots: Dict[Tuple[str, str], _TrackedInvocation] = {}

    def start(self, thread_id: str, cat_id: str) -> _TrackedInvocation:
        key = (thread_id, cat_id)
        existing = self._slots.get(key)
        if existing:
            existing.cancel()
        invocation = _TrackedInvocation()
        self._slots[key] = invocation
        return invocation

    def complete(self, thread_id: str, cat_id: str, invocation: _TrackedInvocation) -> None:
        key = (thread_id, cat_id)
        if self._slots.get(key) is invocation:
            del self._slots[key]

    def cancel(self, thread_id: str, cat_id: str) -> None:
        key = (thread_id, cat_id)
        existing = self._slots.get(key)
        if existing:
            existing.cancel()
            del self._slots[key]

    def cancel_all(self, thread_id: str) -> None:
        keys_to_remove = [k for k in self._slots if k[0] == thread_id]
        for key in keys_to_remove:
            self._slots[key].cancel()
            del self._slots[key]

    def is_active(self, thread_id: str, cat_id: str) -> bool:
        return (thread_id, cat_id) in self._slots

    def is_any_active(self, thread_id: str) -> bool:
        """Check if any cat is currently invoking for this thread."""
        return any(k[0] == thread_id for k in self._slots)

    def get_active_cats(self, thread_id: str) -> list:
        """Get list of cat_ids currently invoking for this thread."""
        return [k[1] for k in self._slots if k[0] == thread_id]
