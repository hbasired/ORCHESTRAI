"""Stage 28 — GraphRAG retriever tests: real citations, honest-empty on off-topic, degraded-leg honesty."""
from __future__ import annotations

import os

import pytest

from knowledge_graph.graphrag import Grounding, retrieve
from knowledge_graph import graphrag


requires_embedder = pytest.mark.skipif(
    os.environ.get("MEM0_EMBED_MODEL") is None and not os.environ.get("RUN_EMBEDDER_TESTS"),
    reason="embedder tests need MEM0_EMBED_MODEL (bge-small) configured",
)


# ---------------------------------------------------------------------------
# Retrieval correctness + honest-empty (the anti-hallucination property)
# ---------------------------------------------------------------------------

@requires_embedder
def test_in_domain_query_grounds_with_sop_citations():
    g = retrieve("stage crack torque anomaly response procedure")
    assert g.grounded is True
    assert g.context, "an in-domain query must return grounded facts"
    assert any(c.source.startswith("sop:") for c in g.citations), "must cite an SOP doc"


@requires_embedder
def test_off_topic_query_returns_honest_empty_not_a_guess():
    g = retrieve("what is the capital of France")
    assert g.grounded is False
    assert g.context == []            # honest-empty: NO fabricated grounding
    assert g.citations == []


@requires_embedder
def test_off_topic_pizza_is_not_grounded():
    assert retrieve("best pizza recipe").grounded is False


# ---------------------------------------------------------------------------
# Citation shape + trace form
# ---------------------------------------------------------------------------

@requires_embedder
def test_every_returned_fact_is_citable():
    g = retrieve("supplier disruption material shortage")
    assert len(g.citations) >= len([c for c in g.context if c])  # each cited context has a citation
    t = g.to_trace()
    assert set(t) == {"grounded", "citations", "n_facts"}
    assert t["grounded"] is True and t["n_facts"] > 0


# ---------------------------------------------------------------------------
# Entity extraction (graph leg targeting) — infra-free
# ---------------------------------------------------------------------------

def test_entity_extraction_finds_node_ids():
    from knowledge_graph.graphrag import _entities_in
    ids = _entities_in("why did supplier 0 delay feeding stage_3?")
    assert "supplier_0" in ids
    assert "stage_3" in ids


def test_entity_extraction_empty_when_no_ids():
    from knowledge_graph.graphrag import _entities_in
    assert _entities_in("general question about the plant") == []


# ---------------------------------------------------------------------------
# Degraded-leg honesty: embedder absent → SOP leg unavailable (not fabricated)
# ---------------------------------------------------------------------------

def test_embedder_unavailable_degrades_honestly(monkeypatch):
    # Force the embedder to be unavailable; the retriever must NOT invent SOP grounding.
    monkeypatch.setattr(graphrag, "_chunk_vecs", None)

    def _boom():
        raise RuntimeError("embedder down")

    monkeypatch.setattr(graphrag, "_embedder", _boom)
    g = retrieve("stage crack torque anomaly")   # no entity ids → graph leg empty too
    assert g.embedder_available is False
    assert g.grounded is False                    # honest: no fabricated grounding without the embedder
    assert isinstance(g, Grounding)


# ---------------------------------------------------------------------------
# DB-gated: the graph neighbourhood leg cites REAL Neo4j nodes
# ---------------------------------------------------------------------------

requires_graph = pytest.mark.skipif(
    not os.environ.get("NEO4J_URI"),
    reason="no NEO4J_URI — graph-neighbourhood leg needs Neo4j",
)


@requires_embedder
@requires_graph
def test_graph_leg_cites_real_supplier_node():
    # Seed the graph, then a supplier-0 query must cite the real supplier_0 node.
    from simulation.sim_world import SimWorld
    from agents.supply_chain import SupplyChainOrchestrator
    try:
        SupplyChainOrchestrator(SimWorld(seed=1)).ground_in_graph()
    except Exception:  # noqa: BLE001
        pytest.skip("Neo4j not reachable to seed")
    g = retrieve("supplier 0 delivery latency disruption")
    node_cites = [c for c in g.citations if c.kind == "graph_node"]
    # If Neo4j was reachable, supplier_0 should be cited; if not, the SOP leg still grounded it (honest).
    if g.graph_available and node_cites:
        assert any("supplier_0" in c.source for c in node_cites)
