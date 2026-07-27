"""Stage 11 — human-in-the-loop node (LangGraph `interrupt()` primitive).

Research §17: HITL is the SAME `interrupt()` primitive as a clock-pause, compiled INTO the graph. When a decision
affects a SIL-1+ function, the graph PAUSES at this node (writes a checkpoint) and surfaces an approval request;
the operator resumes with `Command(resume="approved"|"rejected")`, which lands in `hitl_resolution` and the graph
continues from the exact checkpoint. The FULL functional-safety wrapper (SIL executor split, contract DSL, STO/SS1)
is Stage 17 — this is the runtime-side hook only.
"""
from __future__ import annotations

from typing import Any

from agents.runtime.state import AgentState, TraceEvent


def hitl_confirm(state: AgentState) -> dict[str, Any]:
    """Pause for human confirmation on SIL-1+ decisions. If a resolution was pre-supplied (resume / config),
    consume it; otherwise raise the LangGraph `interrupt()` so the run durably pauses for an operator."""
    if not state.hitl_required:
        return {}  # not reached via the conditional edge, but safe
    if state.hitl_resolution in ("approved", "rejected"):
        return {"trace": state.trace + [TraceEvent(node="hitl_confirm",
                summary=f"resolution consumed: {state.hitl_resolution}",
                detail={"resolution": state.hitl_resolution})]}
    # Durably pause for a human. On resume, langgraph injects the value here.
    try:
        from langgraph.types import interrupt
        resolution = interrupt({
            "reason": "SIL-1+ decision requires operator confirmation",
            "sil_level": state.sil_level,
            "decision": state.decision,
            "verification": state.verification,
        })
        return {"hitl_resolution": str(resolution),
                "trace": state.trace + [TraceEvent(node="hitl_confirm",
                        summary=f"operator resolved: {resolution}", detail={"resolution": str(resolution)})]}
    except Exception as e:  # interrupt unavailable (older langgraph) — fail safe to "pending" (do NOT auto-approve)
        return {"hitl_resolution": None,
                "trace": state.trace + [TraceEvent(node="hitl_confirm",
                        summary=f"interrupt unavailable ({e}); leaving UNCONFIRMED (fail-safe, no auto-approve)",
                        ok=False)]}


__all__ = ["hitl_confirm"]
