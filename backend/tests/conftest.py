"""
Pytest Configuration and Fixtures
"""

import asyncio
import os
from typing import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


# --- R1/G-1: isolate the audit_chain so test runs never pollute the attestable (dev/prod) chain ------------------
# The recurring CTO-flagged pollution: tests sign audit_chain rows with EPHEMERAL keystores into the SHARED dev DB, so
# `verify-audit-chain.py` later fails on those rows. Fix: for the whole test SESSION, point `AUDIT_CHAIN_DATABASE_URL`
# (preferred by audit_chain._dsn) at a THROWAWAY database migrated to head, then drop it. Honest fallback: if a real PG
# isn't reachable / migration fails, leave the env untouched (tests degrade exactly as before — no silent breakage).
@pytest.fixture(scope="session", autouse=True)
def _isolate_audit_chain():
    base = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not base or os.environ.get("AUDIT_CHAIN_DATABASE_URL") or os.environ.get("AUDIT_CHAIN_NO_ISOLATE") == "1":
        yield
        return
    p = urlsplit(base)
    test_db = (p.path.lstrip("/") or "manufacturing") + "_pytest_audit"
    admin = urlunsplit((p.scheme, p.netloc, "/postgres", "", ""))
    created = False
    try:
        import psycopg
        with psycopg.connect(admin, autocommit=True, connect_timeout=5) as c, c.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{test_db}"')
            cur.execute(f'CREATE DATABASE "{test_db}"')
        created = True
        audit_url = urlunsplit((p.scheme, p.netloc, "/" + test_db, p.query, p.fragment))
        # Build the full schema (audit_chain table + immutability triggers come from the migrations) in the throwaway DB.
        import subprocess
        env = {**os.environ, "DATABASE_URL": audit_url}
        r = subprocess.run(["alembic", "upgrade", "head"], cwd=os.path.dirname(os.path.dirname(__file__)),
                           env=env, capture_output=True, text=True, timeout=240)
        if r.returncode != 0:
            raise RuntimeError(f"alembic upgrade on isolated audit DB failed: {r.stderr[-400:]}")
        os.environ["AUDIT_CHAIN_DATABASE_URL"] = audit_url
        yield
    except Exception as e:  # noqa: BLE001 - honest fallback: no isolation, tests behave as before
        print(f"[conftest] audit-chain isolation unavailable ({type(e).__name__}: {e}); using shared DB")
        yield
    finally:
        os.environ.pop("AUDIT_CHAIN_DATABASE_URL", None)
        if created:
            try:
                import psycopg
                with psycopg.connect(admin, autocommit=True, connect_timeout=5) as c, c.cursor() as cur:
                    cur.execute(f'DROP DATABASE IF EXISTS "{test_db}" WITH (FORCE)')
            except Exception:  # noqa: BLE001
                pass

# Create event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def app():
    """Create test application instance."""
    from main import app
    yield app


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async test client that RUNS THE APP LIFESPAN (G-044 fix).

    Previously this used a bare `ASGITransport(app=app)` with NO lifespan, so `state_manager` /
    `decision_engine` / `SimWorld` never initialised and every endpoint returned 503 (the 21 `test_api` failures).
    Wrapping the client in the app's `lifespan_context` initialises those services; the lifespan degrades
    gracefully when optional infra (Neo4j / Firebase / MQTT) is absent (verified — `/health` + `/ready` → 200),
    so the live app path is genuinely exercised even on a minimal stack.
    """
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
def sample_robot_state():
    """Sample robot state for testing."""
    return {
        "id": 1,
        "position": {"x": 25.5, "y": 15.0},
        "battery": 75.0,
        "speed": 1.2,
        "task": "Transporting to Stage 3",
        "status": "working",
        "task_queue_length": 3
    }


@pytest.fixture
def sample_stage_state():
    """Sample stage state for testing."""
    return {
        "id": 1,
        "name": "Assembly",
        "queue_depth": 12,
        "throughput": 100.5,
        "cycle_time": 45.0,
        "defect_rate": 2.5,
        "energy_consumption": 15.0,
        "status": "normal",
        "utilization": 85.0
    }


@pytest.fixture
def sample_decision_request():
    """Sample decision request for testing."""
    return {
        "priority": "throughput",
        "constraints": [],
        "force_decision": False
    }


@pytest.fixture
def sample_features():
    """Sample feature vector for ML model testing."""
    import numpy as np
    return np.random.randn(200).astype(np.float32)
