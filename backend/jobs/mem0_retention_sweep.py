"""Stage 12 — nightly Mem0 retention sweep (KB_14 §"Retention policy").

Purges `mem0_memories` rows whose `retained_until < now()`, and records the purge in `audit_chain`
(`action='memory.purge'`, payload `{purged_count, dry_run}`) — the purge itself is an audited action. Honest: with
no DB it raises; it never reports a fake purge count. Run from cron / a scheduler nightly:

    python -m jobs.mem0_retention_sweep            # purge
    python -m jobs.mem0_retention_sweep --dry-run  # count only, no delete, no audit row
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


def sweep(dry_run: bool = False) -> dict:
    dsn = _dsn()
    if not dsn:
        raise RuntimeError("mem0_retention_sweep: no DATABASE_URL/POSTGRES_URL configured")
    import psycopg
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM mem0_memories WHERE retained_until IS NOT NULL AND retained_until < now()")
        due = int(cur.fetchone()[0])
        if dry_run:
            return {"due": due, "purged": 0, "dry_run": True}
        cur.execute("DELETE FROM mem0_memories WHERE retained_until IS NOT NULL AND retained_until < now()")
        purged = cur.rowcount
    # Record the purge as an audited action (best-effort: never fail the sweep if the chain is down, but report it).
    audit_seq = None
    try:
        from memory.audit_chain import append
        audit_seq = append("job:mem0_retention_sweep", "memory.purge", {"purged_count": purged})
    except Exception as e:  # noqa: BLE001
        print(f"WARN: purge done ({purged} rows) but audit_chain append failed: {e}", file=sys.stderr)
    return {"due": due, "purged": purged, "dry_run": False, "audit_seq": audit_seq}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="mem0_retention_sweep")
    ap.add_argument("--dry-run", action="store_true", help="count expired rows; do not delete or audit")
    args = ap.parse_args(argv)
    result = sweep(dry_run=args.dry_run)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
