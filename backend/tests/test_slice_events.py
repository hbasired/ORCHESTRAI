"""Stage 6 — slice event envelope tests (AC5): canonical KB_04 family on /ws.

No Redis required: drives SimulatorEventBroker.handle_raw directly with a fake
ConnectionManager client, the same pattern as tests/test_ws_broker.py.
"""
from __future__ import annotations

import json

import pytest

from services.ws_broker import (
    SLICE_EVENT_TYPES,
    ConnectionManager,
    SimulatorEventBroker,
    build_incident_envelope,
    build_slice_envelope,
)


class FakeWS:
    def __init__(self):
        self.messages = []

    async def send_json(self, data):
        self.messages.append(data)


def test_build_slice_envelope_shape():
    env = build_slice_envelope("prediction", {"stage_id": 3, "prediction": {"p_fail": 0.91}})
    assert env["v"] == 1
    assert env["type"] == "prediction"
    assert "ts" in env
    assert env["incident_id"] is None
    assert env["payload"]["stage_id"] == 3


def test_build_slice_envelope_rejects_unknown_type():
    with pytest.raises(ValueError):
        build_slice_envelope("telemetry_dump", {})


def test_all_slice_types_build():
    for t in SLICE_EVENT_TYPES:
        assert build_slice_envelope(t, {})["type"] == t


@pytest.mark.asyncio
async def test_broker_fans_out_slice_envelope_as_is():
    manager = ConnectionManager()
    ws = FakeWS()
    manager.connect(ws)
    broker = SimulatorEventBroker(manager)
    envelope = build_slice_envelope("intervention", {"stage_id": 3, "kind": "preventive_maintenance"})
    delivered = await broker.handle_raw(json.dumps(envelope))
    assert delivered == 1
    assert ws.messages[0]["type"] == "intervention"
    assert ws.messages[0]["payload"]["kind"] == "preventive_maintenance"


@pytest.mark.asyncio
async def test_legacy_incident_path_still_wraps():
    manager = ConnectionManager()
    ws = FakeWS()
    manager.connect(ws)
    broker = SimulatorEventBroker(manager)
    raw_incident = {"incident_id": "abc-123", "type": "machine_crack", "target_id": 3}
    delivered = await broker.handle_raw(json.dumps(raw_incident))
    assert delivered == 1
    assert ws.messages[0]["type"] == "incident"
    assert ws.messages[0]["incident_id"] == "abc-123"
    assert ws.messages[0] == build_incident_envelope(raw_incident) | {"ts": ws.messages[0]["ts"]}


@pytest.mark.asyncio
async def test_malformed_and_unidentified_messages_skipped():
    manager = ConnectionManager()
    ws = FakeWS()
    manager.connect(ws)
    broker = SimulatorEventBroker(manager)
    assert await broker.handle_raw("{not json") is None
    assert await broker.handle_raw(json.dumps({"no_incident_id": True})) is None
    assert ws.messages == []
