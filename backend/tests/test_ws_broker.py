"""Stage 3 — unit tests for the WebSocket incident broker.

These exercise the broker's core (envelope shape, broadcast pruning, malformed
handling, and the subscribe loop) with in-process fakes — no live Redis or
running app required.
"""
import asyncio
import json

import pytest

from services.ws_broker import (
    SIMULATOR_EVENTS_CHANNEL,
    ConnectionManager,
    SimulatorEventBroker,
    build_incident_envelope,
)

SAMPLE = {
    "incident_id": "11111111-1111-1111-1111-111111111111",
    "type": "robot_down",
    "target_id": 1,
    "details": {},
    "severity": "warning",
    "started_at": "2026-05-31T00:00:00+00:00",
    "ended_at": None,
}


class FakeWS:
    """Minimal WebSocket double: records sent messages, can simulate a dead client."""

    def __init__(self, fail: bool = False):
        self.sent: list = []
        self.fail = fail

    async def send_json(self, data):
        if self.fail:
            raise RuntimeError("client gone")
        self.sent.append(data)


class RecordingManager:
    def __init__(self):
        self.messages: list = []

    async def broadcast(self, message):
        self.messages.append(message)
        return 1


def test_build_incident_envelope_matches_kb04_shape():
    env = build_incident_envelope(SAMPLE)
    assert env["v"] == 1
    assert env["type"] == "incident"
    assert env["incident_id"] == SAMPLE["incident_id"]
    assert env["payload"] == SAMPLE
    assert isinstance(env["ts"], str) and "T" in env["ts"]
    # envelope must carry exactly the canonical keys
    assert set(env.keys()) == {"v", "type", "ts", "incident_id", "payload"}


@pytest.mark.asyncio
async def test_broadcast_delivers_and_prunes_dead_clients():
    mgr = ConnectionManager(send_timeout=1.0)
    good, bad = FakeWS(), FakeWS(fail=True)
    mgr.connect(good)
    mgr.connect(bad)
    assert mgr.active_count == 2

    delivered = await mgr.broadcast({"hello": "world"})

    assert delivered == 1
    assert good.sent == [{"hello": "world"}]
    assert mgr.active_count == 1  # dead client pruned


@pytest.mark.asyncio
async def test_broadcast_prunes_slow_client_on_timeout():
    mgr = ConnectionManager(send_timeout=0.05)

    class SlowWS:
        def __init__(self):
            self.sent = []

        async def send_json(self, data):
            await asyncio.sleep(1.0)  # exceeds send_timeout
            self.sent.append(data)

    mgr.connect(SlowWS())
    good = FakeWS()
    mgr.connect(good)

    delivered = await mgr.broadcast({"x": 1})

    assert delivered == 1
    assert mgr.active_count == 1  # slow client pruned


@pytest.mark.asyncio
async def test_handle_raw_wraps_and_broadcasts_str_and_bytes():
    mgr = RecordingManager()
    broker = SimulatorEventBroker(mgr, redis_client=object())

    assert await broker.handle_raw(json.dumps(SAMPLE)) == 1
    assert await broker.handle_raw(json.dumps(SAMPLE).encode("utf-8")) == 1
    assert len(mgr.messages) == 2
    assert mgr.messages[0]["type"] == "incident"
    assert mgr.messages[0]["payload"]["incident_id"] == SAMPLE["incident_id"]


@pytest.mark.asyncio
async def test_handle_raw_skips_malformed_and_idless():
    mgr = RecordingManager()
    broker = SimulatorEventBroker(mgr, redis_client=object())

    assert await broker.handle_raw("not json{{") is None
    assert await broker.handle_raw(json.dumps({"type": "robot_down"})) is None  # no incident_id
    assert await broker.handle_raw(json.dumps(["a", "list"])) is None
    assert mgr.messages == []


@pytest.mark.asyncio
async def test_broker_run_loop_fans_message_to_client():
    """End-to-end of the subscribe loop with a fake Redis pub/sub (no server)."""

    class FakePubSub:
        """Fake of the redis.asyncio PubSub get_message() polling API the broker uses."""

        def __init__(self):
            # One real "message" frame to deliver, then quiet (None on every poll),
            # mirroring a live channel that goes idle until stop().
            self._frames = [
                {"type": "message", "channel": SIMULATOR_EVENTS_CHANNEL, "data": json.dumps(SAMPLE)},
            ]

        async def subscribe(self, ch):
            self.ch = ch

        async def get_message(self, ignore_subscribe_messages=False, timeout=None):
            if self._frames:
                return self._frames.pop(0)
            await asyncio.sleep(min(timeout or 0.01, 0.02))  # idle tick, like a real timeout
            return None

        async def unsubscribe(self, ch):
            pass

        async def aclose(self):
            pass

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    mgr = ConnectionManager()
    ws = FakeWS()
    mgr.connect(ws)
    broker = SimulatorEventBroker(mgr, redis_client=FakeRedis())

    await broker.start()
    for _ in range(100):  # up to ~2s
        if ws.sent:
            break
        await asyncio.sleep(0.02)
    await broker.stop()

    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "incident"
    assert ws.sent[0]["payload"]["incident_id"] == SAMPLE["incident_id"]
