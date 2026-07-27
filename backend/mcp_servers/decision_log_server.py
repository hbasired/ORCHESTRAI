"""MCP server: decision_log — append_decision · query_decisions.

Writes/reads the REAL Postgres `decisions` table (alembic 0001) via psycopg. Honest-unavailable when no DB is
reachable (never a fake write/ack; Rule 1a). Per the Stage-11.5 task doc + KB_16, writes route directly to Postgres
*now*; when the immutable `audit_chain` (SHA-256 chained, ML-DSA-65 signed) lands at Stage 13.5, this server will
route through `backend/memory/audit_chain.py` instead. The TODO is marked in-code so the migration point is explicit.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_servers._common import ok, run_server, unavailable

# Warm the psycopg import on the MAIN thread at startup (avoids a worker-thread import-lock deadlock when a tool
# first imports it in the stdio subprocess). Best-effort: if psycopg is absent the tools report unavailable.
try:
    import psycopg  # noqa: E402,F401
except Exception:  # noqa: BLE001
    pass

mcp = FastMCP("decision_log")

_VALID_STATUS = ("pending", "accepted", "rejected", "modified", "executed")


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def _connect():
    """Open a short-lived psycopg connection (autocommit). Returns None if unavailable."""
    dsn = _dsn()
    if not dsn:
        return None
    try:
        import psycopg
        return psycopg.connect(dsn, autocommit=True, connect_timeout=5)
    except Exception:  # noqa: BLE001 - DB down / driver missing -> honest unavailable upstream
        return None


@mcp.tool()
def append_decision(decision: dict) -> dict:
    """Append one decision to the immutable decision ledger.

    `decision`: {decision_type (required), reasoning (required), confidence (0..1, required),
    actions?, expected_impact?, state_snapshot?, priority?, status?, requires_approval?, decision_id?}.
    Returns {available, decision_id, persisted: true} or {available: false, reason}.

    NOTE (Stage 13.5): when audit_chain lands, route this through backend/memory/audit_chain.py (chained + signed).
    """
    for req in ("decision_type", "reasoning", "confidence"):
        if req not in decision:
            return unavailable(f"decision missing required field {req!r}", input_error=True)
    try:
        confidence = float(decision["confidence"])
    except (TypeError, ValueError):
        return unavailable("confidence must be a float in [0,1]", input_error=True)
    if not 0.0 <= confidence <= 1.0:
        return unavailable("confidence out of range [0,1]", input_error=True)
    status = decision.get("status", "pending")
    if status not in _VALID_STATUS:
        return unavailable(f"status must be one of {_VALID_STATUS}", input_error=True)

    decision_id = str(decision.get("decision_id") or f"dec-{uuid.uuid4()}")
    conn = _connect()
    if conn is None:
        return unavailable("no Postgres reachable (set DATABASE_URL)")
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO decisions
                    (decision_id, decision_type, actions, reasoning, confidence,
                     expected_impact, state_snapshot, priority, status, requires_approval)
                VALUES (%s, %s, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
                ON CONFLICT (decision_id) DO NOTHING
                """,
                (decision_id, str(decision["decision_type"]),
                 json.dumps(decision.get("actions", [])), str(decision["reasoning"]), confidence,
                 json.dumps(decision.get("expected_impact")) if decision.get("expected_impact") is not None else None,
                 json.dumps(decision.get("state_snapshot")) if decision.get("state_snapshot") is not None else None,
                 decision.get("priority"), status, bool(decision.get("requires_approval", False))),
            )
            persisted = cur.rowcount > 0
        return ok({"decision_id": decision_id, "persisted": persisted,
                   "duplicate": not persisted})
    except Exception as e:  # noqa: BLE001
        return unavailable(f"write failed: {e}")
    finally:
        conn.close()


@mcp.tool()
def query_decisions(decision_type: Optional[str] = None, status: Optional[str] = None,
                    limit: int = 20) -> dict:
    """Query recent decisions, newest first. Optional filters by `decision_type` / `status`.

    Returns {available, count, decisions: [{decision_id, decision_type, status, confidence, reasoning, timestamp}]}.
    """
    limit = max(1, min(int(limit), 200))
    conn = _connect()
    if conn is None:
        return unavailable("no Postgres reachable (set DATABASE_URL)")
    try:
        clauses, params = [], []
        if decision_type:
            clauses.append("decision_type = %s"); params.append(decision_type)
        if status:
            clauses.append("status = %s"); params.append(status)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT decision_id, decision_type, status, confidence, reasoning, timestamp
                    FROM decisions{where} ORDER BY timestamp DESC LIMIT %s""",
                params,
            )
            rows = cur.fetchall()
        decisions = [{"decision_id": r[0], "decision_type": r[1], "status": r[2],
                      "confidence": float(r[3]) if r[3] is not None else None,
                      "reasoning": r[4],
                      "timestamp": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5])}
                     for r in rows]
        return ok({"count": len(decisions), "decisions": decisions})
    except Exception as e:  # noqa: BLE001
        return unavailable(f"query failed: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    run_server(mcp, "decision_log_server")
