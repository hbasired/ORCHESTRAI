"""Stage 25 — EU AI Act Art-72 post-market monitoring: nightly anomaly sweep over the live audit_chain.

Operationalises `compliance/post-market-monitoring-plan.md` (Stage 22, Annex IV §11): actively collect + analyse
lifetime performance data and evaluate continuous compliance (Art-72(1)-(2)). The sweep builds a per-day feature
matrix from the append-only signed `audit_chain` (row counts per action + total + distinct actors + governance deny
rate) and runs two detectors over it (research §36.2 — no new deps, Rule 9):

  1. rolling robust-Z (median/MAD, Iglewicz–Hoaglin |z| >= 3.5) per action series — catches rate spikes/drops
     (e.g. a surge in `hitl` overrides or `rbac.check` denials, a silent stop in `decision.trace`);
  2. sklearn IsolationForest (already a dependency) over the multivariate daily matrix — catches joint drift.

HONESTY: with < MIN_HISTORY_DAYS days of chain data the sweep reports `status="insufficient_history"` and makes NO
anomaly claim — it never fabricates a score. With no DB it raises. Each real (non-dry) run appends a signed
`post_market.sweep` audit row (the monitoring itself is audited evidence) and writes a JSON report under
`compliance/post-market-monitoring/reports/`. Run nightly:

    python -m jobs.post_market_anomaly_sweep            # sweep + audit row + report file
    python -m jobs.post_market_anomaly_sweep --dry-run  # sweep only; no audit row, no report file
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

MIN_HISTORY_DAYS = 14          # below this, no anomaly claim (honest-empty)
ROBUST_Z_THRESHOLD = 3.5       # Iglewicz–Hoaglin modified-Z cutoff
ISOFOREST_CONTAMINATION = 0.05 # expected anomaly fraction; deterministic via random_state
REPORT_DIR = Path(__file__).resolve().parents[2] / "compliance" / "post-market-monitoring" / "reports"


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


# ---------------------------------------------------------------------------
# Feature collection (live audit_chain → per-day matrix)
# ---------------------------------------------------------------------------

def collect_daily_features(conn: Any, days: int = 90) -> dict[str, Any]:
    """Per-day counts by action + total + distinct actors + governance deny rate, oldest→newest."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT (ts AT TIME ZONE 'UTC')::date AS day, action, count(*)
            FROM audit_chain
            WHERE ts >= now() - make_interval(days => %s)
            GROUP BY 1, 2 ORDER BY 1
            """,
            (days,),
        )
        rows = cur.fetchall()
        cur.execute(
            """
            SELECT (ts AT TIME ZONE 'UTC')::date AS day, count(DISTINCT actor)
            FROM audit_chain
            WHERE ts >= now() - make_interval(days => %s)
            GROUP BY 1 ORDER BY 1
            """,
            (days,),
        )
        actor_rows = dict(cur.fetchall())
        # Governance denials: rbac.check / mac.read rows whose payload says allowed=false.
        cur.execute(
            """
            SELECT (ts AT TIME ZONE 'UTC')::date AS day,
                   count(*) FILTER (WHERE (payload->>'allowed') = 'false')::float
                     / NULLIF(count(*), 0)
            FROM audit_chain
            WHERE action IN ('rbac.check', 'mac.read')
              AND ts >= now() - make_interval(days => %s)
            GROUP BY 1 ORDER BY 1
            """,
            (days,),
        )
        deny_rows = {d: (r or 0.0) for d, r in cur.fetchall()}

    day_set = sorted({r[0] for r in rows} | set(actor_rows) | set(deny_rows))
    actions = sorted({r[1] for r in rows})
    counts: dict[Any, dict[str, int]] = {d: {} for d in day_set}
    for day, action, n in rows:
        counts[day][action] = int(n)
    return {
        "days": [d.isoformat() for d in day_set],
        "actions": actions,
        # matrix[i][j] = count of actions[j] on days[i]; plus derived columns appended by build_matrix()
        "counts": [[counts[d].get(a, 0) for a in actions] for d in day_set],
        "total": [sum(counts[d].values()) for d in day_set],
        "distinct_actors": [int(actor_rows.get(d, 0)) for d in day_set],
        "deny_rate": [float(deny_rows.get(d, 0.0)) for d in day_set],
    }


# ---------------------------------------------------------------------------
# Detectors (pure functions — unit-testable infra-free)
# ---------------------------------------------------------------------------

def robust_z_last(series: list[float], threshold: float = ROBUST_Z_THRESHOLD) -> Optional[float]:
    """Modified-Z of the LAST point vs the history before it. None = not flaggable (flat/short history)."""
    if len(series) < MIN_HISTORY_DAYS:
        return None
    history, last = series[:-1], series[-1]
    med = _median(history)
    mad = _median([abs(x - med) for x in history])
    if mad == 0.0:
        # Flat history: any deviation is infinite-z; flag only a real change, honestly capped.
        return None if last == med else float("inf")
    z = 0.6745 * (last - med) / mad
    return z if abs(z) >= threshold else None


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return float(s[mid]) if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def isoforest_last(matrix: list[list[float]]) -> Optional[dict[str, float]]:
    """IsolationForest verdict for the last day vs the rest. None = insufficient history (honest-empty)."""
    if len(matrix) < MIN_HISTORY_DAYS:
        return None
    from sklearn.ensemble import IsolationForest  # already a project dependency

    clf = IsolationForest(contamination=ISOFOREST_CONTAMINATION, random_state=0)
    clf.fit(matrix[:-1])
    pred = int(clf.predict([matrix[-1]])[0])          # -1 anomaly / 1 normal
    score = float(clf.score_samples([matrix[-1]])[0])  # lower = more anomalous
    return {"anomaly": pred == -1, "score": score}


def analyse(features: dict[str, Any]) -> dict[str, Any]:
    """Run both detectors over the collected features. Pure; deterministic."""
    n_days = len(features["days"])
    if n_days < MIN_HISTORY_DAYS:
        return {
            "status": "insufficient_history",
            "days_observed": n_days,
            "days_required": MIN_HISTORY_DAYS,
            "anomalies": [],  # honest-empty: NO claim either way
        }
    anomalies: list[dict[str, Any]] = []
    # Per-action robust-Z on the most recent day.
    for j, action in enumerate(features["actions"]):
        series = [float(row[j]) for row in features["counts"]]
        z = robust_z_last(series)
        if z is not None:
            anomalies.append({"detector": "robust_z", "signal": f"action:{action}",
                              "z": (None if z == float("inf") else round(z, 2)),
                              "last_value": series[-1]})
    for name in ("total", "distinct_actors", "deny_rate"):
        z = robust_z_last([float(x) for x in features[name]])
        if z is not None:
            anomalies.append({"detector": "robust_z", "signal": name,
                              "z": (None if z == float("inf") else round(z, 2)),
                              "last_value": features[name][-1]})
    # Multivariate IsolationForest over counts + derived columns.
    matrix = [row + [float(t), float(a), float(d)] for row, t, a, d in
              zip(features["counts"], features["total"], features["distinct_actors"], features["deny_rate"])]
    iso = isoforest_last(matrix)
    if iso is not None and iso["anomaly"]:
        anomalies.append({"detector": "isolation_forest", "signal": "daily_profile",
                          "score": round(iso["score"], 4)})
    return {"status": "ok", "days_observed": n_days, "anomalies": anomalies}


# ---------------------------------------------------------------------------
# Sweep entrypoint
# ---------------------------------------------------------------------------

def sweep(days: int = 90, dry_run: bool = False) -> dict[str, Any]:
    dsn = _dsn()
    if not dsn:
        raise RuntimeError("post_market_anomaly_sweep: no DATABASE_URL/POSTGRES_URL configured")
    import psycopg
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
        features = collect_daily_features(conn, days=days)
    result = analyse(features)
    result["swept_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    result["window_days"] = days
    result["dry_run"] = dry_run
    if dry_run:
        return result
    # The monitoring run is itself audited evidence (Art-72 → Art-12).
    audit_seq = None
    try:
        from memory.audit_chain import append
        audit_seq = append("job:post_market_anomaly_sweep", "post_market.sweep",
                           {"status": result["status"], "days_observed": result["days_observed"],
                            "anomaly_count": len(result["anomalies"])})
    except Exception as e:  # noqa: BLE001
        print(f"WARN: sweep done but audit_chain append failed: {e}", file=sys.stderr)
    result["audit_seq"] = audit_seq
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{dt.date.today().isoformat()}.json"
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["report_path"] = str(report_path)
    return result


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="post_market_anomaly_sweep")
    ap.add_argument("--days", type=int, default=90, help="lookback window (days)")
    ap.add_argument("--dry-run", action="store_true", help="analyse only; no audit row, no report file")
    args = ap.parse_args(argv)
    result = sweep(days=args.days, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    # Nonzero exit when anomalies found → a cron/CI wrapper can alert on it. insufficient_history exits 0 (no claim).
    return 2 if result.get("anomalies") else 0


if __name__ == "__main__":
    raise SystemExit(main())
