"""Stage 11 — the self-healing LangGraph `StateGraph` + the `run_incident` entry point.

Wires the KB_25 loop as a deterministic, durable graph:

    observe → orient → diagnose → explain → decide → verify ─(hitl_required?)─→ hitl_confirm → execute → log → END
                                                            └────────(no)────────────────────→ execute

Every node wires a REAL Stage-4-10 (depth-hardened) model (see `nodes.py`) and degrades honestly. The graph
compiles with a checkpointer (Postgres if available, else in-memory) keyed by `thread_id`, so a run can pause at
`hitl_confirm` and resume durably.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Optional

from langgraph.graph import StateGraph, START, END

from agents.runtime.state import AgentState
from agents.runtime import nodes
from agents.runtime.hitl import hitl_confirm
from agents.runtime.checkpointer import get_checkpointer


def _route_after_verify(state: AgentState) -> str:
    return "hitl_confirm" if state.hitl_required else "execute"


def _traced_node(name: str, fn):
    """Wrap a node fn so each invocation emits a `langgraph.node.<name>` span (KB_15). No-op-safe without OTel."""
    from observability.otel_init import traced_span

    def _wrapped(state: AgentState):
        with traced_span(f"langgraph.node.{name}", **{"langgraph.node": name}):
            return fn(state)

    _wrapped.__name__ = getattr(fn, "__name__", name)
    return _wrapped


def build_runtime(checkpointer: Optional[Any] = None):
    """Build + compile the self-healing StateGraph. Returns (compiled_graph, backend_name)."""
    backend = "provided"
    if checkpointer is None:
        checkpointer, backend = get_checkpointer()

    g = StateGraph(AgentState)
    # Stage 12.5: each node emits a `langgraph.node.<name>` span (KB_15 observability table).
    g.add_node("observe", _traced_node("observe", nodes.observe))
    g.add_node("orient", _traced_node("orient", nodes.orient))
    g.add_node("diagnose", _traced_node("diagnose", nodes.diagnose))
    g.add_node("explain", _traced_node("explain", nodes.explain))
    g.add_node("decide", _traced_node("decide", nodes.decide))
    g.add_node("verify", _traced_node("verify", nodes.verify))
    g.add_node("hitl_confirm", hitl_confirm)
    g.add_node("execute", _traced_node("execute", nodes.execute))
    g.add_node("log", _traced_node("log", nodes.log))

    g.add_edge(START, "observe")
    g.add_edge("observe", "orient")
    g.add_edge("orient", "diagnose")
    g.add_edge("diagnose", "explain")
    g.add_edge("explain", "decide")
    g.add_edge("decide", "verify")
    g.add_conditional_edges("verify", _route_after_verify, {"hitl_confirm": "hitl_confirm", "execute": "execute"})
    g.add_edge("hitl_confirm", "execute")
    g.add_edge("execute", "log")
    g.add_edge("log", END)

    return g.compile(checkpointer=checkpointer), backend


def run_incident(incident: dict[str, Any], *, thread_id: Optional[str] = None, sil_level: int = 0,
                 telemetry_window: Optional[list[list[float]]] = None,
                 hitl_resolution: Optional[str] = None, app: Optional[Any] = None) -> dict[str, Any]:
    """Run one incident through the self-healing graph. Returns {decisions, trace, interrupted, backend, thread_id}.

    `hitl_resolution` pre-supplies an operator answer (skips the live interrupt — used by tests / replays).
    If the graph pauses at `hitl_confirm` (SIL-1+, no resolution), `interrupted` is True and the run can be resumed
    with the same `thread_id`.
    """
    compiled = app
    backend = "provided"
    if compiled is None:
        compiled, backend = build_runtime()
    thread_id = thread_id or f"incident-{uuid.uuid4().hex[:12]}"
    from agents.runtime.tracing import get_run_callbacks
    config = {"configurable": {"thread_id": thread_id}, "callbacks": get_run_callbacks()}

    init = AgentState(incident=incident, telemetry=incident.get("telemetry", {}),
                      telemetry_window=telemetry_window, sil_level=sil_level, hitl_resolution=hitl_resolution)
    result = compiled.invoke(init, config=config)

    interrupted = bool(result.get("__interrupt__")) if isinstance(result, dict) else False
    decisions = result.get("decisions", []) if isinstance(result, dict) else []
    trace = result.get("trace", []) if isinstance(result, dict) else []
    out = {
        "thread_id": thread_id,
        "backend": backend,
        "interrupted": interrupted,
        "decisions": [d.model_dump() if hasattr(d, "model_dump") else d for d in decisions],
        "trace": [e.model_dump() if hasattr(e, "model_dump") else e for e in trace],
        # Stage-12 memory provenance: audit_chain seqs written + episodic memories recalled this run.
        "audit_seqs": result.get("audit_seqs", []) if isinstance(result, dict) else [],
        "memory_recall": result.get("memory_recall", []) if isinstance(result, dict) else [],
    }
    # Stage 33 (C6-R3): always-on runtime behavioural oversight — feed THIS incident's real behaviour to the
    # Stage-31 monitor on 100% of live runs (gated on, honest-degrading, off the hot path). Emits a signed
    # `behavior.anomaly` row on a real deviation; never breaks the run.
    if os.environ.get("RUNTIME_BEHAVIOR_MONITOR", "0") == "1":
        try:
            from security.behavioral_monitor import get_behavioral_monitor, features_from_run
            verdict = get_behavioral_monitor().observe(features_from_run(out))
            out["behavior_anomaly"] = verdict.to_dict()
        except Exception:  # noqa: BLE001 - oversight is best-effort; a monitor error must never fail the incident
            out["behavior_anomaly"] = None
    return out


__all__ = ["build_runtime", "run_incident", "AgentState"]
