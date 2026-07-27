"""Stage 3 — WebSocket incident broker (Redis pub/sub fan-out).

The SimPy ``SimWorld`` (Stage 2) publishes every incident to the Redis channel
``pubsub:simulator:events`` via ``backend/simulation/persistence.append_incident``.
This module is the *subscriber* side: a ``SimulatorEventBroker`` listens on that
channel and fans each incident out to all connected WebSocket clients using the
canonical KB_04 ``incident`` envelope.

Decoupling publisher (simulator) from subscriber (fan-out) through Redis pub/sub
means every uvicorn worker subscribes independently and serves only the clients
connected to it — the standard multi-worker WebSocket fan-out pattern.

No theatrical fallbacks: this module emits real envelopes for real incidents and
returns nothing when there is nothing to send.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# The channel persistence.append_incident publishes to (KB_04 / Stage 2 hand-off).
SIMULATOR_EVENTS_CHANNEL = "pubsub:simulator:events"
# A slow client must never stall the whole broadcast loop.
DEFAULT_SEND_TIMEOUT = 2.0
# Stage 6 slice event types riding the same channel + envelope family (KB_04).
SLICE_EVENT_TYPES = ("prediction", "diagnosis", "intervention", "ab_report")


@runtime_checkable
class WSLike(Protocol):
    """Minimal structural type for anything we can broadcast to (FastAPI WebSocket / test double)."""

    async def send_json(self, data: Any) -> None: ...


def build_incident_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """Wrap a raw ``IncidentPayload`` dict in the canonical KB_04 outbound envelope.

    KB_04 §"WebSocket message envelopes":
        {"v": 1, "type": "incident", "ts": <iso8601>, "incident_id": <uuid|null>, "payload": {...}}
    """
    return {
        "v": 1,
        "type": "incident",
        "ts": datetime.now(timezone.utc).isoformat(),
        "incident_id": payload.get("incident_id"),
        "payload": payload,
    }


def build_slice_envelope(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Canonical envelope for Stage-6 slice events (same KB_04 family as incidents).

    Slice events are published to the simulator channel ALREADY enveloped (the
    publisher knows the event type); ``handle_raw`` recognises the envelope and
    fans it out as-is. ``incident_id`` is null unless the event is attributable
    to a specific incident.
    """
    if event_type not in SLICE_EVENT_TYPES:
        raise ValueError(f"unknown slice event type: {event_type!r} (allowed: {SLICE_EVENT_TYPES})")
    return {
        "v": 1,
        "type": event_type,
        "ts": datetime.now(timezone.utc).isoformat(),
        "incident_id": payload.get("incident_id"),
        "payload": payload,
    }


class ConnectionManager:
    """Tracks connected WebSocket clients and broadcasts to them, pruning dead ones."""

    def __init__(self, *, send_timeout: float = DEFAULT_SEND_TIMEOUT) -> None:
        self._clients: set[WSLike] = set()
        self._send_timeout = send_timeout

    def connect(self, ws: WSLike) -> None:
        self._clients.add(ws)

    def disconnect(self, ws: WSLike) -> None:
        self._clients.discard(ws)

    @property
    def active_count(self) -> int:
        return len(self._clients)

    async def broadcast(self, message: dict[str, Any]) -> int:
        """Send ``message`` to every client. Prune any that error or time out.

        Returns the number of clients the message was delivered to. Never raises
        on a per-client failure — a single bad client cannot break the fan-out.
        """
        if not self._clients:
            return 0
        delivered = 0
        dead: list[WSLike] = []
        for ws in list(self._clients):
            try:
                await asyncio.wait_for(ws.send_json(message), timeout=self._send_timeout)
                delivered += 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # disconnect / timeout / serialization
                logger.warning("ws_broker: dropping client after send failure: %s", exc)
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)
        return delivered


async def _aclose(obj: Any) -> None:
    """Best-effort async close that tolerates redis-py version differences (aclose vs close)."""
    for name in ("aclose", "close"):
        fn = getattr(obj, name, None)
        if fn is None:
            continue
        try:
            res = fn()
            if asyncio.iscoroutine(res):
                await res
            return
        except Exception:
            return


class SimulatorEventBroker:
    """Subscribes to the simulator incident channel and fans incidents out via a ConnectionManager."""

    def __init__(
        self,
        manager: ConnectionManager,
        *,
        redis_client: Any = None,
        redis_url: Optional[str] = None,
        channel: str = SIMULATOR_EVENTS_CHANNEL,
        reconnect_backoff: float = 2.0,
    ) -> None:
        self._manager = manager
        self._redis = redis_client
        self._owns_redis = redis_client is None  # close it on stop() only if we created it
        self._redis_url = redis_url
        self._channel = channel
        self._backoff = reconnect_backoff
        self._task: Optional[asyncio.Task] = None
        self._stopped = asyncio.Event()

    async def _ensure_redis(self) -> Any:
        if self._redis is not None:
            return self._redis
        import redis.asyncio as aioredis  # local import: keep module import-safe

        self._redis = aioredis.from_url(self._redis_url or "redis://localhost:6379/0")
        return self._redis

    async def handle_raw(self, raw: Any) -> Optional[int]:
        """Decode one raw Redis message, build the envelope, and broadcast it.

        Returns the delivery count, or ``None`` when the message is skipped
        (malformed / not an incident). Pure enough to unit-test without Redis.
        """
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            payload = json.loads(raw)
        except Exception as exc:
            logger.warning("ws_broker: skipping malformed incident message: %s", exc)
            return None
        if not isinstance(payload, dict):
            logger.warning("ws_broker: skipping non-dict message")
            return None
        # Stage-6 slice events arrive ALREADY enveloped (v=1, type in
        # SLICE_EVENT_TYPES) — fan them out as-is.
        if payload.get("v") == 1 and payload.get("type") in SLICE_EVENT_TYPES:
            return await self._manager.broadcast(payload)
        # Legacy path: raw IncidentPayload dicts get wrapped here.
        if not payload.get("incident_id"):
            logger.warning("ws_broker: skipping incident message with no incident_id")
            return None
        envelope = build_incident_envelope(payload)
        return await self._manager.broadcast(envelope)

    # How long get_message blocks before returning None so the loop can re-check
    # _stopped. Bounded so shutdown is prompt; large enough to stay near-idle.
    _POLL_TIMEOUT = 1.0

    async def _run(self) -> None:
        while not self._stopped.is_set():
            pubsub = None
            try:
                redis = await self._ensure_redis()
                pubsub = redis.pubsub()
                await pubsub.subscribe(self._channel)
                logger.info("ws_broker: subscribed to %s", self._channel)
                # Poll with a bounded timeout instead of `async for pubsub.listen()`:
                # the loop re-checks _stopped and exits *between* reads, so stop()
                # never has to cancel an in-flight socket read — that cancellation
                # deadlocks redis-py's pubsub teardown on the Windows Proactor loop.
                while not self._stopped.is_set():
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=self._POLL_TIMEOUT
                    )
                    if message is None:
                        continue  # timeout tick (or ignored subscribe frame)
                    if not isinstance(message, dict) or message.get("type") != "message":
                        continue
                    await self.handle_raw(message.get("data"))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(
                    "ws_broker: subscribe loop error (%s); reconnecting in %ss", exc, self._backoff
                )
                try:
                    await asyncio.sleep(self._backoff)
                except asyncio.CancelledError:
                    break
            finally:
                if pubsub is not None:
                    # The loop exits between reads, so the connection is idle here
                    # and aclose() can unsubscribe + close cleanly.
                    await _aclose(pubsub)

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopped.clear()
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the subscribe loop. Guaranteed bounded: the loop exits on its own
        within ~_POLL_TIMEOUT of seeing _stopped; cancel is only a last-resort
        fallback, and the whole wait is time-boxed so shutdown can never hang."""
        self._stopped.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=self._POLL_TIMEOUT + 4.0)
            except asyncio.TimeoutError:
                # Loop didn't exit cleanly — cancel as a fallback, also time-boxed.
                self._task.cancel()
                try:
                    await asyncio.wait_for(self._task, timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
                except Exception:  # pragma: no cover - defensive
                    pass
            except asyncio.CancelledError:
                pass
            except Exception:  # pragma: no cover - defensive
                pass
            self._task = None
        if self._owns_redis and self._redis is not None:
            await _aclose(self._redis)
            self._redis = None


__all__ = [
    "SIMULATOR_EVENTS_CHANNEL",
    "SLICE_EVENT_TYPES",
    "build_incident_envelope",
    "build_slice_envelope",
    "ConnectionManager",
    "SimulatorEventBroker",
]
