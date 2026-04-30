"""In-memory pub/sub for streaming agent reasoning events to SSE clients."""
import asyncio
from collections import defaultdict
from typing import AsyncIterator

_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
_history: dict[str, list[dict]] = defaultdict(list)


async def publish(job_id: str, event: dict) -> None:
    _history[job_id].append(event)
    for q in list(_subscribers.get(job_id, ())):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def subscribe(job_id: str) -> AsyncIterator[dict]:
    """Yield historical events first, then live events. Caller breaks on done."""
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers[job_id].add(q)
    try:
        for past in list(_history.get(job_id, ())):
            yield past
        while True:
            event = await q.get()
            yield event
            if event.get("type") in ("done", "error"):
                break
    finally:
        _subscribers[job_id].discard(q)


def clear(job_id: str) -> None:
    _history.pop(job_id, None)
    _subscribers.pop(job_id, None)
