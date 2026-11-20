"""Durable job queue abstraction with explicit in-memory development adapter."""

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4


@dataclass(frozen=True)
class Job:
    id: str
    workspace_id: str
    kind: str
    payload: dict[str, Any]
    attempts: int = 0


class Queue(Protocol):
    async def enqueue(self, workspace_id: str, kind: str, payload: dict[str, Any]) -> Job: ...
    async def claim(self) -> Job: ...
    async def retry(self, job: Job) -> Job: ...


class InMemoryQueue:
    """Test/development only; lost on process restart and not cross-worker."""

    def __init__(self) -> None:
        self._jobs: asyncio.Queue[Job] = asyncio.Queue()

    async def enqueue(self, workspace_id: str, kind: str, payload: dict[str, Any]) -> Job:
        job = Job(id=f"job_{uuid4().hex}", workspace_id=workspace_id, kind=kind, payload=payload)
        await self._jobs.put(job)
        return job

    async def claim(self) -> Job:
        return await self._jobs.get()

    async def retry(self, job: Job) -> Job:
        retry = Job(id=job.id, workspace_id=job.workspace_id, kind=job.kind, payload=job.payload, attempts=job.attempts + 1)
        await self._jobs.put(retry)
        return retry


queue: Queue = InMemoryQueue()
