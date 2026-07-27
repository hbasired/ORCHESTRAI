"""Stage 13 — CDC listener: drains the `cdc_outbox` and injects DB-driven changes into the live SimWorld.

Design (research §22, KB_05 §97): a durable transactional outbox + `LISTEN/NOTIFY` signal + drain-on-connect.
- `LISTEN cdc_events` — the low-latency signal.
- On each notify AND on startup, **drain** unprocessed outbox rows (ordered by serial id, `FOR UPDATE SKIP LOCKED`),
  convert each row-diff to an `InjectRequest`, inject into the SimWorld, mark the row processed.
- Durable: rows missed while the listener was offline are caught by the startup drain. Ordered: serial id.

Concurrency: a **background daemon thread** runs the listen loop with SYNC psycopg. This is deliberate — psycopg's
async mode cannot use Windows' ProactorEventLoop (which the rest of the app needs for the MCP stdio subprocesses),
and changing the global loop policy would break that. The SimWorld's `inject()` is already thread-safe, so a thread
fits naturally. Clean shutdown: a stop flag + a bounded join (the Stage-11 ws_broker/api_client lesson).

Honest degradation (Rule 1a): no DB → the listener doesn't start (logged, not faked); no SimWorld bound → the row is
LEFT UNPROCESSED (retried on the next drain), never marked done without actually injecting.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

CDC_CHANNEL = "cdc_events"
_TROUBLE_STATUSES = {"broken", "down", "degraded", "offline", "fault", "maintenance", "error"}


def change_to_inject(table_name: str, change: dict) -> Optional[Any]:
    """Pure converter: a CDC change event → an `InjectRequest` (or None if not actionable). Unit-testable, no I/O."""
    from simulation.entities import InjectRequest

    # Stage 37 (G-024): a VALUE edit (the trigger emits {column, old, new, target_id}) → DIAGNOSE the induced problem
    # (root-cause reasoning, not a canned incident). Checked FIRST because value-edit rows carry a `column` key on the
    # SAME tables (stages/inventory/suppliers) as the status/incident branches below, which would otherwise swallow them.
    if "column" in change:
        try:
            from ingestion.cdc_reasoner import diagnose_change
            problem = diagnose_change(str(change.get("table") or table_name), str(change["column"]),
                                      change.get("old"), change.get("new"),
                                      target_id=change.get("target_id"), context=change.get("context"))
            if problem is None:
                return None                # benign edit — honest no-op
            inc = problem.to_incident()
            return InjectRequest(type=inc["type"], target_id=inc.get("target_id"),
                                 details=inc.get("details", {}), severity=inc.get("severity", "warning"))
        except Exception:  # noqa: BLE001 — a malformed value-edit row must not crash the listener
            return None

    if table_name == "incidents":
        try:
            return InjectRequest(
                type=change["type"], target_id=change.get("target_id"),
                details=dict(change.get("details") or {}, source="cdc:incidents"),
                severity=change.get("severity", "warning"))
        except Exception:  # noqa: BLE001 - a malformed external row must not crash the listener
            return None

    if table_name == "stages":
        new_status = str(change.get("new_status", "")).lower()
        if new_status not in _TROUBLE_STATUSES:
            return None
        try:
            return InjectRequest(
                type="machine_crack", target_id=int(change["stage_id"]),
                details={"source": "cdc:stages.status", "new_status": new_status,
                         "old_status": change.get("old_status")},
                severity="critical" if new_status in ("broken", "down", "fault") else "warning")
        except Exception:  # noqa: BLE001
            return None

    return None


class CDCListener:
    """LISTENs on `cdc_events` (sync psycopg, background thread) and drains the outbox into the SimWorld."""

    def __init__(self, dsn: Optional[str] = None, *, drain_limit: int = 200) -> None:
        self._dsn = dsn or os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        self._drain_limit = drain_limit
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ready = threading.Event()    # set after the thread connects + does the initial drain
        self._failed = threading.Event()   # set if the thread can't connect
        self.injected = 0                  # observability/test counter (thread-incremented int)

    async def start(self) -> bool:
        """Spawn the listen thread; wait (bounded) for it to connect + drain the backlog. False if no DB."""
        if not self._dsn:
            logger.warning("CDCListener: no DATABASE_URL; CDC ingestion disabled")
            return False
        self._stop.clear(); self._ready.clear(); self._failed.clear()
        self._thread = threading.Thread(target=self._run_loop, name="cdc-listener", daemon=True)
        self._thread.start()
        # Wait for the thread to signal ready (connected + initial drain done) or failed.
        await asyncio.to_thread(self._wait_ready_or_failed, 10.0)
        if self._failed.is_set() or not self._ready.is_set():
            logger.warning("CDCListener: could not start (DB unreachable?); CDC disabled")
            return False
        logger.info("CDCListener started (channel=%s)", CDC_CHANNEL)
        return True

    def _wait_ready_or_failed(self, timeout: float) -> None:
        deadline = threading.TIMEOUT_MAX if timeout is None else timeout
        # Poll both events.
        end = __import__("time").monotonic() + deadline
        while __import__("time").monotonic() < end:
            if self._ready.is_set() or self._failed.is_set():
                return
            __import__("time").sleep(0.05)

    def _run_loop(self) -> None:
        import psycopg
        listen_conn = drain_conn = None
        try:
            listen_conn = psycopg.connect(self._dsn, autocommit=True)
            drain_conn = psycopg.connect(self._dsn, autocommit=False)
            listen_conn.execute(f"LISTEN {CDC_CHANNEL}")
        except Exception:  # noqa: BLE001 - DB unreachable → honest disable
            self._failed.set()
            for c in (listen_conn, drain_conn):
                try:
                    c and c.close()
                except Exception:  # noqa: BLE001
                    pass
            return
        try:
            self._drain(drain_conn)   # catch backlog written while offline
            self._ready.set()
            while not self._stop.is_set():
                # Block up to 1s for notifications, then re-check stop; drain when any arrive.
                got = False
                for _n in listen_conn.notifies(timeout=1.0):
                    got = True
                if got:
                    self._drain(drain_conn)
        except Exception:  # noqa: BLE001
            logger.warning("CDCListener loop error", exc_info=True)
        finally:
            for c in (listen_conn, drain_conn):
                try:
                    c.close()
                except Exception:  # noqa: BLE001
                    pass

    def _drain(self, conn: Any) -> int:
        """Convert + inject all unprocessed outbox rows on `conn`. Returns the number injected this pass."""
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, table_name, change FROM cdc_outbox WHERE processed_at IS NULL "
                    "ORDER BY id FOR UPDATE SKIP LOCKED LIMIT %s", (self._drain_limit,))
                rows = cur.fetchall()
                done_ids = []
                for outbox_id, table_name, change in rows:
                    if self._apply(table_name, change):
                        done_ids.append(outbox_id)
                if done_ids:
                    cur.execute("UPDATE cdc_outbox SET processed_at = now() WHERE id = ANY(%s)", (done_ids,))
            conn.commit()
            self.injected += len(done_ids)
            return len(done_ids)
        except Exception:  # noqa: BLE001
            try:
                conn.rollback()
            except Exception:  # noqa: BLE001
                pass
            logger.warning("CDCListener drain failed", exc_info=True)
            return 0

    def _apply(self, table_name: str, change: dict) -> bool:
        """Inject one change into the SimWorld. True → mark processed; False → retry on the next drain."""
        req = change_to_inject(table_name, change)
        if req is None:
            return True  # benign / non-actionable — handled (don't retry forever)
        try:
            from api.simulation_routes import get_sim_world
            sw = get_sim_world()
        except Exception:  # noqa: BLE001
            sw = None
        if sw is None:
            return False  # no live world yet → leave unprocessed, retry on the next drain (durability)
        try:
            # Stage 19 (G-074/OTel): the CDC ingestion boundary is now traced (DB-write → SimWorld inject).
            from observability.otel_init import traced_span
            with traced_span("cdc.ingest", **{"cdc.table": table_name}):
                sw.inject(req)
            return True
        except Exception:  # noqa: BLE001 - a bad inject shouldn't wedge the queue
            logger.warning("CDCListener inject failed for %s; skipping", table_name, exc_info=True)
            return True

    async def stop(self) -> None:
        """Signal stop + join the listen thread (bounded)."""
        self._stop.set()
        if self._thread is not None:
            await asyncio.to_thread(self._thread.join, 6.0)
            self._thread = None


__all__ = ["CDCListener", "change_to_inject", "CDC_CHANNEL"]
