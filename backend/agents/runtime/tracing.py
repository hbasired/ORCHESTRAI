"""Stage 11 — observability tracing for the LangGraph runtime (Langfuse / LangSmith), env-gated + honest.

Two layers, no fabrication:
  1. **Always-on, dependency-free:** every run already builds `AgentState.trace` — a per-node provenance list
     (the EU-AI-Act Art-12 record). This needs no external server and is the source of truth for "every decision
     produces a trace".
  2. **Optional external observability:** if Langfuse is configured (`LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`)
     and/or LangSmith (`LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY`), the graph invoke is given the matching
     callback handler so the run renders in the dashboard. If neither is configured we attach NOTHING and say so —
     we never pretend a trace was shipped.
"""
from __future__ import annotations

import os
from typing import Any


def get_run_callbacks() -> list[Any]:
    """Return the LangChain callback handlers to attach to a graph invoke (empty list if none configured)."""
    cbs: list[Any] = []
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        try:
            from langfuse.langchain import CallbackHandler  # langfuse>=3 LangChain integration
            cbs.append(CallbackHandler())
        except Exception:
            try:  # older langfuse layout
                from langfuse.callback import CallbackHandler  # type: ignore
                cbs.append(CallbackHandler())
            except Exception:
                pass
    # LangSmith needs no callback object — it auto-traces when LANGCHAIN_TRACING_V2=true + LANGCHAIN_API_KEY set.
    return cbs


def tracing_status() -> dict[str, Any]:
    """Honest report of which tracers are active (for startup logging + the canned test)."""
    return {
        "always_on_trace": "AgentState.trace (per-node provenance; no external dependency)",
        "langfuse_configured": bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")),
        "langsmith_configured": os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
        and bool(os.environ.get("LANGCHAIN_API_KEY")),
    }


__all__ = ["get_run_callbacks", "tracing_status"]
