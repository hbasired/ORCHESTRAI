"""Stage 27 — durable-execution primitive tests: at-most-once effects, breaker state machine, saga compensation.

Infra-free legs use the in-process ledger fallback; DB-gated legs prove the cross-process claim table."""
from __future__ import annotations

import os
import threading
import time

import pytest

from agents.runtime.durable import (
    CircuitBreaker, CircuitOpenError, EffectAlreadyDone, EffectLedger, Saga, SagaStuckError, get_breaker,
)


# ---------------------------------------------------------------------------
# Effect ledger (idempotency)
# ---------------------------------------------------------------------------

def test_effect_runs_at_most_once_and_replay_returns_response(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    ledger = EffectLedger()
    assert ledger.claim("fx-1") is True
    ledger.complete("fx-1", {"actuated": True, "order": 42})
    with pytest.raises(EffectAlreadyDone) as e:
        ledger.claim("fx-1")
    assert e.value.response == {"actuated": True, "order": 42}  # replay returns the RECORDED outcome


def test_failed_effect_releases_and_becomes_retryable(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    ledger = EffectLedger()
    assert ledger.claim("fx-2") is True
    ledger.release("fx-2")            # the effect crashed before completing
    assert ledger.claim("fx-2") is True  # retry may re-claim


def test_concurrent_claim_is_exclusive(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    ledger = EffectLedger()
    assert ledger.claim("fx-3") is True
    assert ledger.claim("fx-3") is False  # in-flight: not claimable, not done


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

def _boom():
    raise ConnectionError("dependency down")


def test_breaker_opens_after_threshold_and_raises_named_error():
    br = CircuitBreaker("dep-a", failure_threshold=3, recovery_timeout_s=60.0)
    for _ in range(3):
        with pytest.raises(ConnectionError):
            br.call(_boom)
    assert br.state == "OPEN"
    with pytest.raises(CircuitOpenError) as e:
        br.call(lambda: "never runs")   # honest: the call is NOT attempted, no fabricated fallback
    assert "dep-a" in str(e.value)


def test_breaker_half_open_probe_recovers():
    br = CircuitBreaker("dep-b", failure_threshold=1, recovery_timeout_s=0.5)
    with pytest.raises(ConnectionError):
        br.call(_boom)
    assert br.state == "OPEN"
    time.sleep(0.55)
    assert br.state == "HALF_OPEN"
    assert br.call(lambda: "ok") == "ok"  # successful probe closes
    assert br.state == "CLOSED"


def test_breaker_half_open_probe_failure_reopens():
    br = CircuitBreaker("dep-c", failure_threshold=1, recovery_timeout_s=0.5)
    with pytest.raises(ConnectionError):
        br.call(_boom)
    time.sleep(0.55)
    with pytest.raises(ConnectionError):
        br.call(_boom)                    # probe fails
    assert br.state == "OPEN"


def test_breaker_registry_is_per_dependency_singleton():
    assert get_breaker("dep-reg") is get_breaker("dep-reg")
    assert get_breaker("dep-reg") is not get_breaker("dep-other")


# ---------------------------------------------------------------------------
# Saga
# ---------------------------------------------------------------------------

def test_saga_success_runs_all_steps_once(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    calls: list[str] = []
    saga = (Saga(key="s1")
            .add("reserve", lambda ctx: calls.append("reserve") or "R")
            .add("dispatch", lambda ctx: calls.append("dispatch") or "D"))
    out = saga.run()
    assert out == {"reserve": "R", "dispatch": "D"}
    assert calls == ["reserve", "dispatch"]


def test_saga_failure_compensates_in_reverse(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    undone: list[str] = []
    saga = (Saga(key="s2")
            .add("a", lambda ctx: "A", compensation=lambda ctx: undone.append("a"))
            .add("b", lambda ctx: "B", compensation=lambda ctx: undone.append("b"))
            .add("boom", lambda ctx: (_ for _ in ()).throw(RuntimeError("step failed"))))
    with pytest.raises(RuntimeError, match="step failed"):
        saga.run()
    assert undone == ["b", "a"]  # reverse order


def test_saga_replay_never_reexecutes_completed_steps(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    ledger = EffectLedger()  # shared across both runs = the durable state
    counter = {"n": 0}

    def once(ctx):
        counter["n"] += 1
        return f"ran-{counter['n']}"

    s1 = Saga(key="s3", ledger=ledger).add("only", once)
    assert s1.run() == {"only": "ran-1"}
    s2 = Saga(key="s3", ledger=ledger).add("only", once)   # a retry/replay of the same saga key
    assert s2.run() == {"only": "ran-1"}                   # recorded response reused
    assert counter["n"] == 1                               # the effect executed exactly once


def test_saga_stuck_compensation_is_surfaced_not_swallowed(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    saga = (Saga(key="s4")
            .add("a", lambda ctx: "A",
                 compensation=lambda ctx: (_ for _ in ()).throw(IOError("undo failed")),
                 compensation_retries=1)
            .add("boom", lambda ctx: (_ for _ in ()).throw(RuntimeError("step failed"))))
    with pytest.raises(SagaStuckError) as e:
        saga.run()
    assert e.value.stuck_compensations == ["a"]  # named for the operator — never silent


# ---------------------------------------------------------------------------
# DB-gated: the cross-process claim table
# ---------------------------------------------------------------------------

requires_db = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")),
    reason="no DATABASE_URL/POSTGRES_URL — effect-ledger table needs Postgres",
)


@requires_db
def test_effect_ledger_is_durable_across_instances():
    import psycopg
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    try:
        probe = psycopg.connect(dsn, connect_timeout=5); probe.close()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable")
    key = f"fx-db-{time.time_ns()}"
    l1 = EffectLedger()
    assert l1.claim(key) is True
    l1.complete(key, {"seq": 1})
    l2 = EffectLedger()   # a DIFFERENT instance (≈ another worker/process)
    with pytest.raises(EffectAlreadyDone) as e:
        l2.claim(key)
    assert e.value.response == {"seq": 1}


@requires_db
def test_stale_running_claims_are_reclaimable():
    import psycopg
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    try:
        probe = psycopg.connect(dsn, connect_timeout=5); probe.close()
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable")
    key = f"fx-stale-{time.time_ns()}"
    l1 = EffectLedger()
    assert l1.claim(key) is True      # ...and the worker "crashes" here (never completes)
    released = EffectLedger().reclaim_stale(lease_seconds=0.0)
    assert released >= 1
    assert EffectLedger().claim(key) is True  # retryable after the lease expired
