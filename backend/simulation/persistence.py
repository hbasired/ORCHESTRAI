"""Async persistence path: SimPy incident → Redis pubsub → Postgres `incidents` insert.

Stage 2 acceptance criterion: Postgres write failure does not crash the
simulator; the event is durable in Redis and retried on next tick.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .entities import Incident, IncidentPayload

logger = logging.getLogger(__name__)

# Module-level retry queue. Surviving simulator restarts is a Stage 3 concern;
# for Stage 2 we keep an in-process FIFO and a Redis pubsub publish on every
# event so the WebSocket broker (Stage 3) can fan out independently.
_RETRY_QUEUE: asyncio.Queue[IncidentPayload] = asyncio.Queue()


async def append_incident(
    payload: IncidentPayload,
    *,
    postgres_writer: Optional[Any] = None,
    redis_client: Optional[Any] = None,
) -> bool:
    """Persist an incident.

    Order:
      1. Always publish to Redis `pubsub:simulator:events` (durability).
      2. Best-effort Postgres `incidents` insert.
      3. On Postgres failure, enqueue for retry on next tick.

    Returns True if the Postgres insert succeeded on this call. (Redis publish
    is best-effort and does not block the return value.)
    """
    # Step 1: Redis pub/sub. Non-blocking; failures are logged but do not abort.
    if redis_client is not None:
        try:
            await redis_client.publish(
                "pubsub:simulator:events",
                json.dumps(payload.model_dump(mode="json"), default=str),
            )
        except Exception as e:
            logger.warning("Redis publish failed for incident %s: %s", payload.incident_id, e)

    # Step 2: Postgres insert.
    if postgres_writer is not None:
        try:
            await postgres_writer.insert_incident(payload.model_dump(mode="json"))
            return True
        except Exception as e:
            logger.warning("Postgres incidents insert failed for %s: %s", payload.incident_id, e)
            await _RETRY_QUEUE.put(payload)
            return False

    return False


async def drain_retry_queue(postgres_writer: Any, *, max_per_call: int = 50) -> int:
    """Drain the retry FIFO into Postgres. Called by the worker on each tick."""
    if postgres_writer is None:
        return 0
    drained = 0
    while drained < max_per_call:
        try:
            payload = _RETRY_QUEUE.get_nowait()
        except asyncio.QueueEmpty:
            break
        try:
            await postgres_writer.insert_incident(payload.model_dump(mode="json"))
            drained += 1
        except Exception as e:
            logger.warning("Retry insert failed for %s: %s", payload.incident_id, e)
            await _RETRY_QUEUE.put(payload)
            break
    return drained


def _retry_queue_size() -> int:
    """Test hook."""
    return _RETRY_QUEUE.qsize()
