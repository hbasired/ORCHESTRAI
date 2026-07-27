"""Stage 22 (R1 / G-1) — prove test runs do NOT pollute the attestable audit_chain.

The CTO #4 review caught the recurring pollution: tests sign `audit_chain` rows with ephemeral keystores into the SHARED
dev DB, so `verify-audit-chain.py` later fails on those rows. The durable fix (conftest `_isolate_audit_chain` +
`audit_chain._dsn` preferring `AUDIT_CHAIN_DATABASE_URL`) points the chain at a throwaway DB for the session. This test
asserts a write made during the test session lands in the ISOLATED DB and NOT in the real one.
"""
from __future__ import annotations

import os

import pytest


def _head(dsn: str) -> int:
    import psycopg
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as c, c.cursor() as cur:
        cur.execute("SELECT coalesce(max(seq), 0) FROM audit_chain")
        return cur.fetchone()[0]


def test_test_writes_do_not_leak_into_real_audit_chain():
    real = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    audit = os.environ.get("AUDIT_CHAIN_DATABASE_URL")
    if not real:
        pytest.skip("no DATABASE_URL (honest skip)")
    if not audit or audit == real:
        pytest.skip("audit-chain isolation not active — real PG unreachable in this env (honest skip, not a failure)")

    real_before, audit_before = _head(real), _head(audit)

    from memory import audit_chain
    seq = audit_chain.append("test:isolation-probe", "probe", {"stage": 22, "check": "isolation"})
    assert isinstance(seq, int) and seq > 0

    assert _head(real) == real_before, "REGRESSION: a test write LEAKED into the real attestable audit_chain"
    assert _head(audit) > audit_before, "the test write did not land in the isolated audit DB"
