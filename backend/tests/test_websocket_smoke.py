"""Smoke test for the /ws WebSocket endpoint.

Asserts the connect handshake, the initial-state envelope shape, and that
the connection-close path is graceful. The envelope shape is sourced from
KB_04_Data_Schema.md — any change to that file should also update this test.

Stage 1 baseline only: we verify the *current* envelope (`type`, `timestamp`,
`data`). Stage 4 will switch to the versioned envelope (`v`, `type`, `ts`,
`payload`) — update this test there.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sync_client():
    from main import app
    # G-044: enter TestClient as a context manager so the app LIFESPAN runs (starts state_manager + the WS
    # broker that emits the initial_state envelope). Without this the /ws handler has no state to send and
    # `receive_json()` blocks forever — the original hang.
    with TestClient(app) as c:
        yield c


def test_websocket_initial_state_envelope(sync_client):
    with sync_client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg.get("type") == "initial_state"
        assert "timestamp" in msg
        assert "data" in msg
        assert isinstance(msg["data"], dict)


def test_websocket_close_is_graceful(sync_client):
    with sync_client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.close()
