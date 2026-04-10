"""WebSocket connection manager for MeowAI Home."""

from fastapi import WebSocket
from typing import Dict, List


class ConnectionManager:
    """Manages active WebSocket connections per thread."""

    def __init__(self):
        # thread_id -> list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}

    def add(self, thread_id: str, ws: WebSocket):
        if thread_id not in self._connections:
            self._connections[thread_id] = []
        self._connections[thread_id].append(ws)

    def remove(self, thread_id: str, ws: WebSocket):
        if thread_id in self._connections:
            self._connections[thread_id].remove(ws)
            if not self._connections[thread_id]:
                del self._connections[thread_id]

    async def broadcast(self, thread_id: str, data: dict):
        """Send data to all connections for a thread."""
        if thread_id in self._connections:
            for ws in self._connections[thread_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass  # Connection already closed

    def get_connections(self, thread_id: str) -> List[WebSocket]:
        return self._connections.get(thread_id, [])
