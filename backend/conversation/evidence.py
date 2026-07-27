"""Stage 29 (G-022) — the EVIDENCE layer for grounded operational QA.

Every "ask the factory" answer must be traceable to concrete evidence (the SOTA RCA "Verifier" pattern, research
§40.1: demand concrete evidence before an answer reaches a human). This module gathers evidence ONLY from real
stores — it never fabricates — and hands each item back with a citable handle:

  * `audit_chain` decision traces (Art-12 signed rows, Stage 24)  -> handle `audit:seq=<n>`
  * Stage-28 GraphRAG grounding (SOP + ISA-95 graph)              -> handle `sop:<doc-id>` / `graph:<node/edge>`
  * live sim snapshot (SimWorld, via the app state or a fresh world) -> handle `sim:<field>`

When a store is unavailable the corresponding evidence list is simply empty (honest degradation) — the caller then
answers "I have no evidence for that" rather than guessing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class EvidenceItem:
    kind: str                       # "decision_trace" | "sop" | "graph" | "sim" | "kpi"
    handle: str                     # a citable id, e.g. "audit:seq=425", "sop:SOP-001", "sim:throughput"
    summary: str                    # one-line human-readable content
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    question: str
    items: list[EvidenceItem] = field(default_factory=list)
    grounded: bool = False          # True iff at least one real evidence item was found
    sources_available: dict[str, bool] = field(default_factory=dict)  # which stores responded

    def handles(self) -> list[str]:
        return [it.handle for it in self.items]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "grounded": self.grounded,
            "sources_available": self.sources_available,
            "evidence": [{"kind": it.kind, "handle": it.handle, "summary": it.summary, "detail": it.detail}
                         for it in self.items],
        }


def _decision_evidence(question: str, limit: int) -> tuple[list[EvidenceItem], bool]:
    """Real Art-12 decision traces from the signed audit_chain (the 'why did X happen' backbone)."""
    items: list[EvidenceItem] = []
    # Honest grounding: only surface decision-trace evidence when the question actually REFERENCES an incident/stage
    # (a token/keyword match). An off-topic question ("what is the meaning of life") must NOT ground on arbitrary
    # recent traces — that would violate the Verifier honest-empty guarantee (bug found Stage 33: the old unfiltered
    # fallback grounded everything once the DB had traces).
    token = _incident_token(question)
    if token is None:
        return items, True                      # store is reachable, but nothing in the question matches a trace
    try:
        from memory.audit_chain import read_recent
        rows = read_recent(["decision.trace", "decision", "incident"], limit=limit, target_substr=token)
    except Exception:  # noqa: BLE001 - store unavailable -> honest empty
        return items, False
    for r in rows:
        payload = r.get("payload") or {}
        dec = payload.get("decision") or {}
        summ = _summarize_decision(r, dec, payload)
        items.append(EvidenceItem(
            kind="decision_trace",
            handle=f"audit:seq={r.get('seq')}",
            summary=summ,
            detail={"action": r.get("action"), "actor": r.get("actor"),
                    "incident_id": payload.get("incident_id"), "decision": dec},
        ))
    return items, True


def _summarize_decision(row: dict[str, Any], dec: dict[str, Any], payload: dict[str, Any]) -> str:
    inc = payload.get("incident_id") or payload.get("incident") or "?"
    kind = dec.get("kind") or dec.get("action") or row.get("action")
    rationale = dec.get("rationale") or dec.get("reason") or ""
    base = f"[seq {row.get('seq')}] {row.get('action')} for incident {inc}"
    if kind:
        base += f" -> {kind}"
    if rationale:
        base += f": {str(rationale)[:160]}"
    return base


def _graphrag_evidence(question: str) -> tuple[list[EvidenceItem], bool]:
    """Stage-28 GraphRAG grounding (SOP corpus + ISA-95 neighbourhood). Honest-empty off-topic."""
    items: list[EvidenceItem] = []
    try:
        from knowledge_graph.graphrag import retrieve
        g = retrieve(question)
    except Exception:  # noqa: BLE001
        return items, False
    if not getattr(g, "grounded", False):
        return items, True  # store responded, but nothing grounded this question (honest)
    for ctx, cit in zip(g.context, g.citations):
        items.append(EvidenceItem(
            kind="graph" if str(getattr(cit, "source", "")).startswith(("node:", "edge:", "graph:")) else "sop",
            handle=str(getattr(cit, "source", "sop:?")),
            summary=str(ctx)[:200],
            detail={"top_score": getattr(g, "top_score", 0.0)},
        ))
    return items, True


def _sim_evidence(question: str, world: Optional[Any]) -> tuple[list[EvidenceItem], bool]:
    """Live plant state from the running SimWorld (real numbers). Empty if no world is available."""
    items: list[EvidenceItem] = []
    if world is None:
        return items, False
    try:
        snap = world.snapshot()
    except Exception:  # noqa: BLE001
        return items, False
    tput = snap.get("throughput_units_per_hour")
    util = snap.get("amr_utilization")
    items.append(EvidenceItem(kind="sim", handle="sim:throughput",
                              summary=f"current throughput {tput:.1f} units/hr" if isinstance(tput, (int, float)) else "throughput n/a",
                              detail={"throughput_units_per_hour": tput, "amr_utilization": util,
                                      "sim_time_seconds": snap.get("sim_time_seconds")}))
    # Surface any stage/robot that is not in a healthy state — the real fault signal.
    for s in snap.get("stages", []):
        status = str(s.get("status", "")).lower()
        if status and status not in ("running", "idle", "ok", "operational"):
            items.append(EvidenceItem(kind="sim", handle=f"sim:stage={s.get('id', s.get('stage_id'))}",
                                      summary=f"stage {s.get('id', s.get('stage_id'))} status={status}",
                                      detail={k: s.get(k) for k in ("id", "stage_id", "status", "health", "blocked") if k in s}))
    return items, True


def _incident_token(question: str) -> Optional[str]:
    """Extract a cheap filter token (stage number / incident keyword) to target the audit read."""
    import re
    q = question.lower()
    m = re.search(r"stage[ _-]?(\d+)", q)
    if m:
        return f"stage"  # keep broad; the payload filter is a substring match
    for kw in ("crack", "robot", "delivery", "defect", "power", "demand", "stockout", "supplier"):
        if kw in q:
            return kw
    return None


def gather_evidence(question: str, *, world: Optional[Any] = None, limit: int = 8) -> EvidenceBundle:
    """Collect all real evidence relevant to `question`. Never fabricates; unavailable stores -> empty lists."""
    bundle = EvidenceBundle(question=question)
    dec_items, dec_ok = _decision_evidence(question, limit)
    sop_items, sop_ok = _graphrag_evidence(question)
    sim_items, sim_ok = _sim_evidence(question, world)
    bundle.items = dec_items + sop_items + sim_items
    bundle.sources_available = {"audit_chain": dec_ok, "graphrag": sop_ok, "sim": sim_ok}
    bundle.grounded = len(bundle.items) > 0
    return bundle


__all__ = ["EvidenceItem", "EvidenceBundle", "gather_evidence"]
