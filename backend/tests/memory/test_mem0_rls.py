"""Stage 19 (CTO #3) — Postgres RLS on mem0_memories: DB-enforced namespace isolation behind the Python _authorize.

Proves the defense-in-depth: a direct SQL client (dropping to the non-superuser mem0_app role, as the adapter does)
sees ONLY the namespace it set, and NOTHING if it set none (fail-closed) — previously it saw everything.
"""
import os
import uuid

import pytest

_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))
skip = pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL — RLS not exercisable")


def _role_exists() -> bool:
    if not _HAS_DB:
        return False
    try:
        import psycopg2
        c = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["POSTGRES_URL"])
        cur = c.cursor()
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname='mem0_app'")
        ok = bool(cur.fetchone())
        c.close()
        return ok
    except Exception:
        return False


needs_rls = pytest.mark.skipif(not _role_exists(), reason="mem0_app role/RLS not migrated (0008) — skip")


@skip
@needs_rls
def test_direct_client_is_fail_closed_and_namespace_scoped():
    import psycopg2
    from memory.mem0_adapter import Mem0Adapter, embed  # noqa: F401 - embed import guards embedder availability
    try:
        embed("warmup")
    except Exception:
        pytest.skip("embedder unavailable")

    ns = f"incident:RLS-{uuid.uuid4().hex[:8]}"
    inc = ns.split(":", 1)[1]
    Mem0Adapter(incident_id=inc).add(ns, "rls isolation test row")

    conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["POSTGRES_URL"])
    cur = conn.cursor()
    cur.execute("SET ROLE mem0_app")                                  # drop to the non-superuser role (RLS applies)
    # (a) no namespace var set -> sees NOTHING (fail-closed)
    cur.execute("SELECT count(*) FROM mem0_memories WHERE namespace=%s", (ns,))
    assert cur.fetchone()[0] == 0
    # (b) a DIFFERENT namespace set -> still cannot see this one
    cur.execute("SELECT set_config('app.mem0_namespace','incident:SOMEONE-ELSE',false)")
    cur.execute("SELECT count(*) FROM mem0_memories WHERE namespace=%s", (ns,))
    assert cur.fetchone()[0] == 0
    # (c) the correct namespace set -> the row is visible (policy keys on the session var)
    cur.execute("SELECT set_config('app.mem0_namespace',%s,false)", (ns,))
    cur.execute("SELECT count(*) FROM mem0_memories WHERE namespace=%s", (ns,))
    assert cur.fetchone()[0] >= 1
    conn.close()


@skip
@needs_rls
def test_adapter_still_works_under_rls():
    """The adapter SET ROLEs + sets the var per op, so it reads/writes its own namespace normally under RLS."""
    from memory.mem0_adapter import Mem0Adapter, embed
    try:
        embed("warmup")
    except Exception:
        pytest.skip("embedder unavailable")
    inc = f"RLS-{uuid.uuid4().hex[:8]}"
    a = Mem0Adapter(incident_id=inc)
    a.add(f"incident:{inc}", "alpha")
    a.add(f"incident:{inc}", "beta")
    assert a.count(f"incident:{inc}") == 2
    assert len(a.search(f"incident:{inc}", "alpha", k=5)) >= 1


def test_python_authorize_still_first_gate():
    """RLS is defense-in-depth; the Python _authorize remains the first gate (no DB needed for this check)."""
    from memory.mem0_adapter import CrossNamespaceAccessError, Mem0Adapter
    a = Mem0Adapter(incident_id="A")
    with pytest.raises(CrossNamespaceAccessError):
        a._authorize("incident:B")
    a._authorize("incident:A")        # own namespace OK
    a._authorize("semantic:shared")   # shared namespace OK
