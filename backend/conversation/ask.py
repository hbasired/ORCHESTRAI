"""Stage 29 (G-022) — "ask the factory": grounded operational QA + "why did X happen?".

Design (research §40.1 — the RCA Verifier pattern + RAG grounding):
  1. Gather REAL evidence (`evidence.gather_evidence`) — Art-12 decision traces + Stage-28 GraphRAG + live sim.
  2. If nothing grounds the question -> **honest-empty** ("I have no evidence for that"), never a guessed answer.
  3. If a free LLM is reachable (Groq -> Ollama, Rule 9), synthesize a natural-language answer that is CONSTRAINED
     to the evidence and MUST cite the evidence handles; low temperature for factual grounding. The original
     question is re-appended to anchor attention (SOTA anti-drift, §40.1).
  4. If no LLM is reachable, return a deterministic templated digest of the SAME real evidence (honest degradation)
     — the answer is still 100% real evidence, just not prose.

The answer ALWAYS carries its evidence handles, so a human/assessor can verify every claim against the signed store.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from conversation.evidence import EvidenceBundle, gather_evidence

_SYSTEM = (
    "You are the factory's operations assistant. Answer the operator's question USING ONLY the EVIDENCE provided "
    "below — never invent facts, numbers, or causes. Cite the evidence you use with its handle in square brackets, "
    "e.g. [audit:seq=425] or [sop:SOP-001]. If the evidence does not answer the question, say exactly: "
    "'I have no evidence for that.' Be concise (2-4 sentences)."
)


def _format_evidence(bundle: EvidenceBundle) -> str:
    lines = []
    for it in bundle.items:
        lines.append(f"- [{it.handle}] ({it.kind}) {it.summary}")
    return "\n".join(lines) if lines else "(no evidence found)"


def _templated_answer(bundle: EvidenceBundle) -> str:
    """Deterministic honest digest used when no LLM is reachable — real evidence, no prose fabrication."""
    if not bundle.grounded:
        return "I have no evidence for that."
    head = f"Based on {len(bundle.items)} evidence item(s):"
    body = "; ".join(f"{it.summary} [{it.handle}]" for it in bundle.items[:5])
    return f"{head} {body}."


async def ask_factory(question: str, *, world: Optional[Any] = None,
                      use_llm: bool = True, session_id: Optional[str] = None) -> dict[str, Any]:
    """Answer an operator question, grounded in real evidence. Returns the answer + the evidence + provenance.

    Stage 35 (C6-R3 tail): if `session_id` is given, the last N turns are loaded as DIALOGUE HISTORY and passed to the
    LLM for phrasing/coreference — but GROUNDING stays per-CURRENT-question (the Verifier honest-empty still fires when
    nothing grounds this question; history is NEVER cited as evidence). The Q + answer are appended to the session."""
    question = (question or "").strip()
    if not question:
        return {"question": question, "grounded": False, "answer": "Please ask a question.",
                "evidence": [], "citations": [], "llm": None, "sources_available": {}}

    # Gather evidence in a worker thread: the reads are blocking (DB, embedder) and `graphrag.retrieve` runs its own
    # asyncio loop for the graph leg — which can only run OFF the request event loop. This also keeps the loop free.
    bundle = await asyncio.to_thread(gather_evidence, question, world=world)

    # Verifier pattern: no evidence -> honest-empty, regardless of the LLM (and regardless of any dialogue history).
    if not bundle.grounded:
        if session_id:
            await asyncio.to_thread(_record_turns, session_id, question, "I have no evidence for that.")
        return {"question": question, "grounded": False, "answer": "I have no evidence for that.",
                "evidence": [], "citations": [], "llm": None, "session_id": session_id,
                "sources_available": bundle.sources_available,
                "note": "No decision trace, SOP, or live-state evidence matched — abstaining (Verifier pattern, §40.1)."}

    citations = bundle.handles()
    llm_used: Optional[str] = None
    answer: Optional[str] = None

    # Sliding-window dialogue history (coreference/phrasing only — never evidence).
    history_block = ""
    if session_id:
        from conversation.session_store import recent_turns, format_history
        history_block = await asyncio.to_thread(lambda: format_history(recent_turns(session_id)))

    if use_llm:
        try:
            from agents.llm_client import get_llm_client, LLMMessage
            client = get_llm_client()
            prompt = (
                (f"{history_block}\n\n" if history_block else "")
                + f"EVIDENCE:\n{_format_evidence(bundle)}\n\n"
                f"QUESTION: {question}\n\n"
                f"Answer using ONLY the evidence above and cite handles (the history is for phrasing/coreference, not "
                f"a source). QUESTION (again): {question}"
            )
            resp = await client.generate(
                [LLMMessage(role="system", content=_SYSTEM), LLMMessage(role="user", content=prompt)],
                temperature=0.1, max_tokens=400, fallback=True)
            content = getattr(resp, "content", None)
            if content and content.strip():
                answer = content.strip()
                llm_used = getattr(resp, "provider", "llm")
        except Exception:  # noqa: BLE001 - LLM unreachable -> honest deterministic digest below
            answer = None

    if answer is None:
        answer = _templated_answer(bundle)  # honest degradation: real evidence, deterministic prose

    if session_id:
        await asyncio.to_thread(_record_turns, session_id, question, answer)

    return {
        "question": question,
        "grounded": True,
        "answer": answer,
        "evidence": bundle.to_dict()["evidence"],
        "citations": citations,
        "llm": llm_used,
        "session_id": session_id,
        "multi_turn": bool(history_block),
        "sources_available": bundle.sources_available,
        "note": "Every claim is grounded in the cited evidence handles (audit_chain seqs / SOP ids / live sim). "
                "Dialogue history aids phrasing/coreference only and is never cited as evidence.",
    }


def _record_turns(session_id: str, question: str, answer: str) -> None:
    """Persist the user Q + assistant answer (best-effort; honest no-op if the store is down)."""
    try:
        from conversation.session_store import append_turn
        append_turn(session_id, "user", question)
        append_turn(session_id, "assistant", answer)
    except Exception:  # noqa: BLE001
        pass


__all__ = ["ask_factory"]
