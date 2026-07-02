from __future__ import annotations

from datetime import datetime
from typing import Any
import asyncio


class AuditSink:
    """Small audit sink that can later be swapped for PostgreSQL/OpenTelemetry."""

    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def emit(self, run_id: str, node: str, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "run_id": run_id,
            "node": node,
            "event_type": event_type,
            "payload": payload or {},
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        self._events.setdefault(run_id, []).append(event)
        for queue in self._subscribers.get(run_id, []):
            queue.put_nowait(event)
        return event

    def list(self, run_id: str) -> list[dict[str, Any]]:
        return list(self._events.get(run_id, []))

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(run_id, [])
        if queue in subscribers:
            subscribers.remove(queue)


audit_sink = AuditSink()
