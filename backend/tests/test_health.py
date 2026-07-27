"""Smoke test for GET /health.

Stage 1 (2026-05-11) — the first test the CI gate enforces. Verifies the
health endpoint stays compatible with the orchestration probe contract
documented in KB_01_System_Architecture.md.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_200_and_expected_shape(client):
    response = await client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] in {"healthy", "degraded"}
    assert "timestamp" in body
    assert "version" in body
    assert "components" in body

    components = body["components"]
    for key in ("state_manager", "decision_engine", "mqtt_listener", "video_processor"):
        assert key in components, f"missing component key: {key}"

    assert "simulation_mode" in body
    assert "websocket_clients" in body


@pytest.mark.asyncio
async def test_ready_returns_boolean(client):
    response = await client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["ready"], bool)
    assert "timestamp" in body
