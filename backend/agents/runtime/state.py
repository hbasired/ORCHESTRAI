"""Stage 11 — the LangGraph runtime state (minimal Pydantic schema) + the Decision output type.

Best practice (research §17): keep state MINIMAL so checkpoint diffs stay small and the graph is easy to reason
about. The state carries the incident, the telemetry under analysis, and the per-step outputs of the self-healing
loop. Each node returns a partial dict update; LangGraph merges it into a fresh state instance (so the schema is
effectively immutable per super-step). Every node also appends a `trace` event — the provenance the Annex IV pack
(Stage 19) + audit_chain (Stage 13.5) will consume.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Decision(BaseModel):
    """One coordinator decision for one machine/incident — the public `coordinate()` output element."""

    stage_id: int
    kind: str                       # preventive_maintenance | wait_external | monitor | (future recovery kinds)
    rationale: str
    approved: bool = True           # gated by the neuro-symbolic verifier
    hitl_required: bool = False
    executed: bool = False
    provenance: dict[str, Any] = Field(default_factory=dict)  # prediction/ttf/diagnosis/explanation/verification


class TraceEvent(BaseModel):
    node: str
    summary: str
    ok: bool = True
    detail: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """Minimal runtime state flowing through the self-healing StateGraph."""

    # ---- input ----
    incident: dict[str, Any] = Field(default_factory=dict)   # {type, target_id, telemetry, recent_incidents, sil}
    telemetry: dict[str, Any] = Field(default_factory=dict)
    telemetry_window: Optional[list[list[float]]] = None     # (window_len, 5) for the TTF world model, if available
    sil_level: int = 0                                       # SIL of the affected function (HITL gate at >=1)

    # ---- per-step outputs of the loop (predict -> orient -> diagnose -> explain -> decide -> verify) ----
    prediction: dict[str, Any] = Field(default_factory=dict)
    ttf_forecast: Optional[dict[str, Any]] = None
    diagnosis: dict[str, Any] = Field(default_factory=dict)
    explanation: Optional[dict[str, Any]] = None
    grounding: Optional[dict[str, Any]] = None            # Stage 28: GraphRAG citations for the explanation (Art-12)
    decision: dict[str, Any] = Field(default_factory=dict)
    verification: Optional[dict[str, Any]] = None
    hitl_required: bool = False
    hitl_resolution: Optional[str] = None                    # "approved" | "rejected" | None (pending)
    executed: bool = False

    # ---- memory (Stage 12) ----
    memory_recall: list[dict[str, Any]] = Field(default_factory=list)  # prior Mem0 memories for this incident
    audit_seqs: list[int] = Field(default_factory=list)                # audit_chain seqs written this run

    # ---- provenance ----
    trace: list[TraceEvent] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


__all__ = ["AgentState", "Decision", "TraceEvent"]
