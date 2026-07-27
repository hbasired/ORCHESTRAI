"""Stage 11 — LangGraph self-healing agent runtime.

A durable, deterministic LangGraph `StateGraph` that runs the KB_25 self-healing loop over one incident —
observe → orient (predict + TTF forecast) → diagnose (learned-causal) → explain (SHAP) → decide → verify
(neuro-symbolic) → hitl-confirm (interrupt) → execute → log — wiring the REAL Stage 4-10 (depth-hardened)
models as direct Python imports. Honest by design: every node degrades gracefully + records what actually ran
(no fabrication); models that are unavailable are reported, never faked.

This package is the runtime core. The full Stage-11 migration of the bespoke `EmbodiedAgent` to a thin wrapper,
the Postgres checkpointer + alembic table, Langfuse tracing, and the decision-engine de-mock (G-052) build on it.
"""
from agents.runtime.state import AgentState, Decision
from agents.runtime.graph import build_runtime, run_incident

__all__ = ["AgentState", "Decision", "build_runtime", "run_incident"]
