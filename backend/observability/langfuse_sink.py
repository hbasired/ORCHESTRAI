"""Stage 12.5 — Langfuse trace sink (KB_15).

In the KB_15 design the app emits **OTLP → otel-collector → Langfuse** (the collector's `otlphttp/langfuse`
exporter); the app itself only needs the OTLP exporter (configured in `otel_init`), NOT a direct Langfuse client on
the trace path. This module is therefore a thin **status + optional direct-client** helper, honest about which path
is active — it never claims traces reached Langfuse when they didn't.

(The Stage-11 runtime `agents/runtime/tracing.py` separately supports env-gated direct Langfuse callbacks for the
LangGraph run; that remains the alternative path when the collector overlay isn't running.)
"""
from __future__ import annotations

import os
from typing import Any


def status() -> dict[str, Any]:
    """Honest report of how traces reach Langfuse in this process."""
    otlp = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    direct = bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))
    try:
        import langfuse  # noqa: F401
        sdk = True
    except Exception:  # noqa: BLE001
        sdk = False
    path = ("otlp-collector" if otlp else ("direct-sdk" if direct else "none"))
    return {
        "active_path": path,
        "otlp_endpoint": otlp,
        "direct_sdk_configured": direct,
        "langfuse_sdk_installed": sdk,
        "note": "traces reach Langfuse via the otel-collector otlphttp/langfuse exporter (KB_15); "
                "the app only needs OTEL_EXPORTER_OTLP_ENDPOINT set + the observability overlay running.",
    }


def direct_client() -> Any:
    """Return a Langfuse SDK client IF directly configured (LANGFUSE_PUBLIC_KEY+SECRET_KEY), else raise honestly."""
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        raise RuntimeError("Langfuse direct client not configured (set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY); "
                           "the default trace path is OTLP → collector → Langfuse (KB_15).")
    from langfuse import Langfuse
    return Langfuse()


__all__ = ["status", "direct_client"]
