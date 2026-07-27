"""Stage 25 — tests for the Art-72 post-market anomaly sweep.

Infra-free tests exercise the detector math (pure functions); a DB-gated leg runs the real collect+analyse against
the live audit_chain when Postgres is up. Honesty invariants under test: insufficient history => NO anomaly claim;
detectors are deterministic; a real spike IS flagged; a normal day is NOT."""
from __future__ import annotations

import os

import pytest

from jobs.post_market_anomaly_sweep import (
    MIN_HISTORY_DAYS,
    analyse,
    isoforest_last,
    robust_z_last,
)


def _features(counts_by_action: dict[str, list[int]]) -> dict:
    actions = sorted(counts_by_action)
    n = len(next(iter(counts_by_action.values())))
    counts = [[counts_by_action[a][i] for a in actions] for i in range(n)]
    total = [sum(row) for row in counts]
    return {
        "days": [f"2026-06-{i+1:02d}" for i in range(n)],
        "actions": actions,
        "counts": counts,
        "total": total,
        "distinct_actors": [2] * n,
        "deny_rate": [0.0] * n,
    }


# ---------------------------------------------------------------------------
# Honesty: insufficient history => no claim
# ---------------------------------------------------------------------------

def test_insufficient_history_makes_no_claim():
    feats = _features({"decision.trace": [5] * (MIN_HISTORY_DAYS - 1)})
    out = analyse(feats)
    assert out["status"] == "insufficient_history"
    assert out["anomalies"] == []  # honest-empty, not a fabricated "all clear" score
    assert out["days_required"] == MIN_HISTORY_DAYS


def test_robust_z_short_series_returns_none():
    assert robust_z_last([5.0] * (MIN_HISTORY_DAYS - 1)) is None


def test_isoforest_short_matrix_returns_none():
    assert isoforest_last([[1.0, 2.0]] * (MIN_HISTORY_DAYS - 1)) is None


# ---------------------------------------------------------------------------
# Detection: a real spike is flagged; a normal day is not
# ---------------------------------------------------------------------------

def test_spike_on_last_day_is_flagged():
    # 20 quiet days then a 30x surge in overrides — must flag.
    series = {"hitl_resolution": [2, 3, 2, 3, 2, 2, 3, 2, 3, 2, 2, 3, 2, 3, 2, 2, 3, 2, 3, 90]}
    out = analyse(_features(series))
    assert out["status"] == "ok"
    signals = {a["signal"] for a in out["anomalies"]}
    assert "action:hitl_resolution" in signals


def test_normal_day_is_not_flagged_by_robust_z():
    series = [10, 12, 11, 9, 10, 13, 11, 10, 12, 9, 11, 10, 12, 11, 10, 11]
    assert robust_z_last([float(x) for x in series]) is None


def test_flat_history_same_value_not_flagged():
    # MAD == 0 and last == median: nothing changed, nothing to flag.
    assert robust_z_last([7.0] * 20) is None


def test_flat_history_changed_value_is_flagged_inf():
    z = robust_z_last([7.0] * 19 + [0.0])
    assert z == float("inf")  # decision.trace silently stopping IS an anomaly


def test_detectors_are_deterministic():
    m = [[float(i % 5), float(i % 3)] for i in range(30)]
    assert isoforest_last(m) == isoforest_last(m)


# ---------------------------------------------------------------------------
# DB-gated live leg (real audit_chain)
# ---------------------------------------------------------------------------

requires_db = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")),
    reason="no DATABASE_URL/POSTGRES_URL — live sweep needs the Docker Postgres",
)


@requires_db
def test_live_dry_run_sweep_makes_no_fabricated_claims():
    import psycopg

    from jobs.post_market_anomaly_sweep import _dsn, collect_daily_features, sweep

    try:
        with psycopg.connect(_dsn(), connect_timeout=5) as conn:
            feats = collect_daily_features(conn, days=90)
    except psycopg.OperationalError:
        pytest.skip("Postgres not reachable")
    out = sweep(days=90, dry_run=True)
    assert out["dry_run"] is True
    assert "audit_seq" not in out  # dry run writes NOTHING
    if len(feats["days"]) < MIN_HISTORY_DAYS:
        assert out["status"] == "insufficient_history"  # the honest verdict for a young chain
    else:
        assert out["status"] == "ok"


def test_no_db_raises_not_fabricates(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    from jobs.post_market_anomaly_sweep import sweep

    with pytest.raises(RuntimeError):
        sweep(dry_run=True)
