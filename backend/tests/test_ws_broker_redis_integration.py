"""Stage 3 — LIVE Redis integration test for the WebSocket incident broker.

Exercises the real production data path end-to-end (minus the FastAPI WS
transport and the SimPy worker thread):

    persistence.append_incident(payload, redis_client)   # real PUBLISH
        -> Redis pubsub:simulator:events                  # real TCP pub/sub
            -> SimulatorEventBroker (real SUBSCRIBE)
                -> ConnectionManager.broadcast            # KB_04 incident envelope
                    -> connected client

Skips automatically when no Redis is reachable, so the suite stays green on dev
boxes without Redis; runs for real under docker compose / CI where Redis exists.
Set REDIS_URL to point elsewhere (default redis://localhost:6379/0).
"""
import asyncio
import os
import time
from datetime import datetime, timezone

import pytest

from services.ws_broker import ConnectionManager, SimulatorEventBroker

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


async def _redis_available() -> bool:
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(REDIS_URL)
        await asyncio.wait_for(r.ping(), timeout=1.5)
        await r.aclose()
        return True
    except Exception:
        return False


class FakeWS:
    def __init__(self):
        self.sent: list = []

    async def send_json(self, data):
        self.sent.append(data)


@pytest.mark.asyncio
async def test_live_redis_publish_fans_out_to_ws_client(capsys):
    if not await _redis_available():
        pytest.skip(f"no Redis reachable at {REDIS_URL}")

    import redis.asyncio as aioredis
    from simulation import persistence
    from simulation.entities import IncidentPayload

    pub = aioredis.from_url(REDIS_URL)
    mgr = ConnectionManager()
    ws = FakeWS()
    mgr.connect(ws)
    broker = SimulatorEventBroker(mgr, redis_url=REDIS_URL)
    await broker.start()
    # Pub/sub has no backlog — let the subscriber finish SUBSCRIBE before publishing.
    await asyncio.sleep(0.5)

    payload = IncidentPayload(
        incident_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        type="robot_down",
        target_id=1,
        details={"recovery_seconds": 120},
        severity="warning",
        started_at=datetime.now(timezone.utc),
    )

    t0 = time.perf_counter()
    await persistence.append_incident(payload, redis_client=pub)  # REAL publish
    for _ in range(200):  # up to ~2s
        if ws.sent:
            break
        await asyncio.sleep(0.01)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    await broker.stop()
    await pub.aclose()

    assert len(ws.sent) == 1, "incident did not fan out over real Redis"
    env = ws.sent[0]
    assert env["v"] == 1 and env["type"] == "incident"
    assert env["payload"]["incident_id"] == payload.incident_id
    assert env["payload"]["type"] == "robot_down"
    # KB_10 inject->client budget is p95 <= 250 ms; this in-process hop is well under it.
    assert latency_ms < 1000, f"fan-out latency {latency_ms:.1f} ms unexpectedly high"
    with capsys.disabled():
        print(f"\n[live redis e2e] real publish -> fan-out latency = {latency_ms:.1f} ms")
