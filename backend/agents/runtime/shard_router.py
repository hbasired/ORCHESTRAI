"""Stage 25 (G-066 foothold) — multi-worker incident-sharding router with exactly-once guards.

Scale problem (CTO #5 R6): the runtime was single-caller — nothing prevented two workers from processing the SAME
incident twice (double actuation risk) or bounded concurrent throughput. This router adds the single-node foothold
(research §36.4):

  * **Deterministic sharding** — `shard_of(incident_id, n)` = stable sha256-hash → shard slot, so a fleet of workers
    can partition incidents without coordination.
  * **Exactly-once guard** — a Postgres **advisory lock** keyed on the incident id: the first worker to claim it
    processes; a concurrent duplicate is **suppressed** (returned honestly as `duplicate_suppressed`, never silently
    double-executed). With no DB configured it degrades honestly to an in-PROCESS lock registry (correct within one
    process; cross-process exactly-once REQUIRES the DB — stated, not hidden).
  * **Bounded concurrency** — `run_many()` drives N incidents through a ThreadPoolExecutor sized to CPU cores
    (uvicorn-worker guidance, research §36.4), reusing one compiled graph per pool.

Honest scope: this is the SINGLE-NODE foothold. Multi-node HA / read replicas / failover remain pilot/cloud work
(G-066 tail, Rule 9) — this module makes a single host safe under concurrent load, measurably (tests/scale/).
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

# In-process fallback registries (used ONLY when no DB is configured — honest degradation).
_LOCAL_LOCKS: set[str] = set()
_LOCAL_PROCESSED: set[str] = set()
_LOCAL_MU = threading.Lock()

# At-most-once ledger (found by this stage's own load test, 2026-07-02): the advisory lock alone prevents
# CONCURRENT double-processing but not SEQUENTIAL re-processing (first run completes → lock released → a late
# duplicate re-acquires and re-runs). The ledger closes that: a claim row is inserted under the lock BEFORE the
# run; a duplicate arriving later sees the claim and is suppressed; a FAILED run deletes its claim so a genuine
# retry stays possible.
_PROCESSED_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS incident_processed (
  incident_id  text PRIMARY KEY,
  processed_at timestamptz NOT NULL DEFAULT now()
)"""


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def shard_of(incident_id: str, n_shards: int) -> int:
    """Stable shard slot for an incident id (sha256 → int → mod). Deterministic across processes/hosts."""
    if n_shards <= 0:
        raise ValueError("n_shards must be >= 1")
    digest = hashlib.sha256(incident_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % n_shards


def _advisory_key(incident_id: str) -> int:
    """Stable signed-64-bit advisory-lock key for Postgres."""
    digest = hashlib.sha256(b"incident-lock:" + incident_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


class IncidentLock:
    """Context manager: exactly-once claim on an incident. `acquired` False => a peer already holds it."""

    def __init__(self, incident_id: str):
        self.incident_id = incident_id
        self.acquired = False
        self._conn: Any = None
        self._local = False

    def __enter__(self) -> "IncidentLock":
        dsn = _dsn()
        if dsn:
            try:
                import psycopg
                self._conn = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
                with self._conn.cursor() as cur:
                    cur.execute("SELECT pg_try_advisory_lock(%s)", (_advisory_key(self.incident_id),))
                    self.acquired = bool(cur.fetchone()[0])
                if not self.acquired:
                    self._conn.close()
                    self._conn = None
                return self
            except Exception:  # noqa: BLE001 — DB down: fall through to the local registry (honest, weaker)
                if self._conn is not None:
                    try:
                        self._conn.close()
                    except Exception:  # noqa: BLE001
                        pass
                    self._conn = None
        # In-process fallback (single-process guarantee only).
        self._local = True
        with _LOCAL_MU:
            if self.incident_id not in _LOCAL_LOCKS:
                _LOCAL_LOCKS.add(self.incident_id)
                self.acquired = True
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._conn is not None:
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (_advisory_key(self.incident_id),))
            finally:
                self._conn.close()
                self._conn = None
        elif self._local and self.acquired:
            with _LOCAL_MU:
                _LOCAL_LOCKS.discard(self.incident_id)


def _claim_processed(incident_id: str) -> Optional[bool]:
    """Insert the at-most-once claim. True=claimed, False=already processed, None=no DB (local fallback used)."""
    dsn = _dsn()
    if not dsn:
        with _LOCAL_MU:
            if incident_id in _LOCAL_PROCESSED:
                return False
            _LOCAL_PROCESSED.add(incident_id)
            return True
    try:
        import psycopg
        with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute(_PROCESSED_TABLE_SQL)
            cur.execute("INSERT INTO incident_processed (incident_id) VALUES (%s) ON CONFLICT DO NOTHING",
                        (incident_id,))
            return cur.rowcount == 1
    except Exception:  # noqa: BLE001 — DB down: honest local fallback (single-process guarantee only)
        with _LOCAL_MU:
            if incident_id in _LOCAL_PROCESSED:
                return False
            _LOCAL_PROCESSED.add(incident_id)
            return True


def _unclaim_processed(incident_id: str) -> None:
    """Release the claim after a FAILED run so a genuine retry stays possible."""
    dsn = _dsn()
    if dsn:
        try:
            import psycopg
            with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM incident_processed WHERE incident_id = %s", (incident_id,))
            return
        except Exception:  # noqa: BLE001
            pass
    with _LOCAL_MU:
        _LOCAL_PROCESSED.discard(incident_id)


def run_incident_guarded(incident: dict[str, Any], *, app: Any = None, **kwargs: Any) -> dict[str, Any]:
    """`run_incident` wrapped in the exactly-once guards: advisory lock (no CONCURRENT double-run) + processed
    ledger (no SEQUENTIAL re-run). Duplicates are suppressed HONESTLY (named status), never silently re-executed."""
    incident_id = str(incident.get("id") or incident.get("incident_id") or "")
    if not incident_id:
        raise ValueError("incident needs an 'id' (or 'incident_id') for exactly-once sharding")
    with IncidentLock(incident_id) as lock:
        if not lock.acquired:
            return {"incident_id": incident_id, "status": "duplicate_suppressed",
                    "detail": "another worker holds the advisory lock for this incident"}
        claimed = _claim_processed(incident_id)
        if claimed is False:
            return {"incident_id": incident_id, "status": "already_processed",
                    "detail": "at-most-once ledger: this incident id was already processed"}
        try:
            from agents.runtime.graph import run_incident
            result = run_incident(incident, app=app, **kwargs)
        except Exception:
            _unclaim_processed(incident_id)  # failed run releases the claim — retryable, no lost incident
            raise
        result["incident_id"] = incident_id
        result["status"] = "processed"
        return result


def run_many(incidents: list[dict[str, Any]], *, max_workers: Optional[int] = None,
             per_incident_timeout_s: float = 300.0, **kwargs: Any) -> dict[str, Any]:
    """Drive N incidents concurrently through one compiled graph. Returns results + honest throughput metrics.

    Concurrency-safety (found by this stage's own load test, 2026-07-02): the model stack loads lazily via
    in-function imports — triggering those imports from N worker threads simultaneously deadlocks on Python's
    import lock (the SAME defect class as the Stage-11.5 FastMCP stdio deadlock). So the FIRST incident runs
    synchronously in the calling thread (resolving every heavy import + model load exactly once), and only the
    remainder fan out to the pool. A per-future timeout makes a stuck run FAIL LOUDLY instead of hanging."""
    if not incidents:
        return {"backend": "n/a", "n": 0, "processed": 0, "duplicate_suppressed": 0,
                "max_workers": 0, "elapsed_s": 0.0, "throughput_per_s": None, "results": []}
    max_workers = max_workers or min(len(incidents), os.cpu_count() or 4)
    from agents.runtime.graph import build_runtime
    app, backend = build_runtime()
    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    # WARM leg: first incident in the main thread — all lazy imports/model loads happen here, single-threaded.
    results.append(run_incident_guarded(incidents[0], app=app, **kwargs))
    rest = incidents[1:]
    if rest:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = {pool.submit(run_incident_guarded, inc, app=app, **kwargs): inc for inc in rest}
            for fut in as_completed(futs, timeout=per_incident_timeout_s * max(1, len(rest))):
                # exceptions propagate — a failed incident FAILS the batch, no swallowing
                results.append(fut.result(timeout=per_incident_timeout_s))
    elapsed = time.perf_counter() - t0
    processed = sum(1 for r in results if r.get("status") == "processed")
    suppressed = sum(1 for r in results if r.get("status") in ("duplicate_suppressed", "already_processed"))
    return {
        "backend": backend,
        "n": len(incidents),
        "processed": processed,
        "suppressed": suppressed,
        "max_workers": max_workers,
        "elapsed_s": round(elapsed, 3),
        "throughput_per_s": round(processed / elapsed, 3) if elapsed > 0 else None,
        "results": results,
    }


__all__ = ["shard_of", "IncidentLock", "run_incident_guarded", "run_many"]
