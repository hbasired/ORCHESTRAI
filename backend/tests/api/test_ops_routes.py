"""Stage 25 (G-021) — ops cascade/post-market endpoints: real-data-only + honest-503 invariants."""
from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.ops_routes import router


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_no_db_gives_honest_503_not_fabricated_cascade(client, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    for path in ("/ops/cascade", "/ops/post-market"):
        r = client.get(path)
        assert r.status_code == 503, f"{path} must be honest-unavailable without a DB"
        assert "honest" in r.json()["detail"] or "unreachable" in r.json()["detail"]


def test_page_serves_without_db(client, monkeypatch):
    # The static page itself renders (its fetches will surface the 503 client-side — honest).
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    r = client.get("/ops/")
    assert r.status_code == 200
    assert "audit_chain" in r.text  # names its real source


requires_db = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")),
    reason="no DATABASE_URL/POSTGRES_URL — live ops view needs the Docker Postgres",
)


@requires_db
def test_live_cascade_reads_real_chain(client):
    import psycopg
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    try:
        probe = psycopg.connect(dsn, connect_timeout=5); probe.close()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable")
    r = client.get("/ops/cascade")
    assert r.status_code == 200
    body = r.json()
    assert body["rows_scanned"] > 0  # the real chain has rows
    # Latency deltas are real non-negative numbers.
    for steps in body["incidents"].values():
        assert all(s["delta_ms"] >= 0 for s in steps)


@requires_db
def test_live_post_market_shows_sweep_and_rotation(client):
    import psycopg
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    try:
        probe = psycopg.connect(dsn, connect_timeout=5); probe.close()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable")
    r = client.get("/ops/post-market")
    assert r.status_code == 200
    body = r.json()
    assert body["chain_rows"] >= 428  # the chain as of the Stage-25 drill
    assert body["recent_sweeps"], "the Stage-25 sweep row must be visible"
    assert any(rot["key_type"] == "identity" for rot in body["recent_rotations"])
