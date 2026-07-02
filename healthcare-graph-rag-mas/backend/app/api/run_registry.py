from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.models.schemas import BriefingResponse


@dataclass
class RunRegistry:
    runs: dict[str, BriefingResponse] = field(default_factory=dict)
    queues: dict[str, asyncio.Queue] = field(default_factory=dict)

    def create_pending(self, run_id: str, response: BriefingResponse) -> None:
        self.runs[run_id] = response
        self.queues[run_id] = asyncio.Queue()

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        queue = self.queues.get(run_id)
        if queue:
            await queue.put(event)

    def set_response(self, response: BriefingResponse) -> None:
        self.runs[response.run_id] = response

    def get(self, run_id: str) -> BriefingResponse | None:
        return self.runs.get(run_id)

    def queue(self, run_id: str) -> asyncio.Queue | None:
        return self.queues.get(run_id)


run_registry = RunRegistry()

