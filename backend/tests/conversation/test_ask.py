"""Stage 29 (G-022) — ask-the-factory tests: the Verifier honest-empty property + evidence-grounded answers.

The load-bearing property (research §40.1): NO evidence -> "I have no evidence for that", never a fabricated answer.
Evidence gathering reads only real stores; unavailable stores degrade to empty (honest), never invented."""
from __future__ import annotations

import asyncio

from conversation.ask import ask_factory
from conversation.evidence import EvidenceItem, gather_evidence


def test_honest_empty_when_no_evidence_and_no_llm():
    r = asyncio.run(ask_factory("what is the airspeed of an unladen swallow", world=None, use_llm=False))
    assert r["grounded"] is False
    assert r["answer"] == "I have no evidence for that."
    assert r["citations"] == []


def test_answer_is_grounded_and_cites_when_evidence_exists(monkeypatch):
    # Inject a real-shaped evidence bundle (as if the audit store returned a decision trace) — no LLM.
    from conversation import ask as ask_mod

    def fake_gather(question, *, world=None, limit=8):
        from conversation.evidence import EvidenceBundle
        b = EvidenceBundle(question=question)
        b.items = [EvidenceItem(kind="decision_trace", handle="audit:seq=425",
                                summary="preventive_maintenance on stage 3 (torque anomaly)",
                                detail={"incident_id": "inc-1"})]
        b.grounded = True
        b.sources_available = {"audit_chain": True, "graphrag": False, "sim": False}
        return b

    monkeypatch.setattr(ask_mod, "gather_evidence", fake_gather)
    r = asyncio.run(ask_factory("why did stage 3 go down?", world=None, use_llm=False))
    assert r["grounded"] is True
    assert "audit:seq=425" in r["citations"]
    # deterministic (no-LLM) digest must quote the real evidence, not fabricate.
    assert "stage 3" in r["answer"] and "audit:seq=425" in r["answer"]


def test_empty_question_is_handled():
    r = asyncio.run(ask_factory("   ", world=None, use_llm=False))
    assert r["grounded"] is False


def test_gather_evidence_is_well_formed_and_never_raises():
    # Gathering must never raise and must always report which of the 3 stores responded. `grounded` reflects reality:
    # with a live DB/embedder an on-topic query legitimately grounds (real SOP/trace); an off-topic one does not.
    b = gather_evidence("why did stage 2 crack", world=None)
    assert set(b.sources_available) == {"audit_chain", "graphrag", "sim"}
    assert b.grounded == (len(b.items) > 0)                    # grounded iff real evidence was found
    assert all(it.handle for it in b.items)                    # every item is citable
    # A purely off-topic query with no world grounds only if the DB happens to hold decision traces; the handles are
    # still real. The honest-empty guarantee itself is covered by test_honest_empty_when_no_evidence_and_no_llm.
