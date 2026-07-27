"""Stage 12 — Mem0 namespace isolation (NIST RMF cross-tenant memory-leakage guard, KB_14).

The authorization check runs BEFORE any embedding/DB I/O, so the rejection tests need no infra. A live round-trip
test (real embedder + pgvector) is gated on DATABASE_URL.
"""
import os
import uuid

import pytest

from memory.mem0_adapter import CrossNamespaceAccessError, Mem0Adapter

_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))


def test_foreign_incident_namespace_rejected_on_search():
    m = Mem0Adapter(incident_id="A", operator_id="op1")
    with pytest.raises(CrossNamespaceAccessError):
        m.search("incident:B", "anything")


def test_foreign_operator_namespace_rejected_on_add():
    m = Mem0Adapter(incident_id="A", operator_id="op1")
    with pytest.raises(CrossNamespaceAccessError):
        m.add("operator:someone-else", "leak attempt")


def test_own_and_shared_namespaces_authorized():
    m = Mem0Adapter(incident_id="A", operator_id="op1")
    # _authorize returns None (no raise) for the bound context + the shared namespaces.
    for ns in ("incident:A", "operator:op1", "semantic:sop-123", "procedural:expedite", "agent:embodied"):
        m._authorize(ns)  # must not raise


def test_no_context_still_allows_shared_but_blocks_tenant():
    m = Mem0Adapter()  # no incident/operator bound
    m._authorize("semantic:x")  # shared OK
    with pytest.raises(CrossNamespaceAccessError):
        m._authorize("incident:anything")


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: live pgvector round-trip not exercisable")
@pytest.mark.timeout(180)
def test_live_add_and_semantic_search_roundtrip():
    ns = f"incident:{uuid.uuid4()}"
    m = Mem0Adapter(incident_id=ns.split(":", 1)[1])
    m.add(ns, "Stage 3 machining overstrain; torque spike preceded the crack", {"severity": "warning"})
    m.add(ns, "Stage 7 assembly nominal; no action needed", {})
    hits = m.search(ns, "what failed on the machining stage?", k=2)
    assert hits, "expected at least one memory back"
    assert "machining" in hits[0]["content"].lower()  # semantic search ranks the relevant memory first
    assert 0.0 <= hits[0]["score"] <= 1.0001
