"""Stage 12.5 — Arize Phoenix eval export (KB_15, research §21).

Phoenix runs as a Docker container in the observability overlay and ingests OTLP from the otel-collector
(`otlp/phoenix`). For Stage 12.5 we wire the **export path** for eval records as OTel spans (`eval.<suite>`), routed
to Phoenix via the collector — the full Phoenix eval-dataset / prompt-injection corpus + CI gate lands at **Stage 20**
(`phoenix-evals`, OWASP-LLM01 + NIST-RMF-Agentic + OWASP-Agentic). Honest: this does not pretend the Stage-20 eval
suites exist yet; it provides the span-emission API they will use.
"""
from __future__ import annotations

from typing import Any, Optional


def log_eval(suite: str, metric: str, value: float, *, baseline: Optional[float] = None,
             passed: Optional[bool] = None, **attrs: Any) -> None:
    """Emit one eval result as an `eval.<suite>` span (routed to Phoenix via the collector).

    `baseline` is encouraged (KB_23 anti-gaming: no metric without a baseline)."""
    from observability.otel_init import traced_span
    span_attrs = {"eval.suite": suite, "eval.metric": metric, "eval.value": float(value)}
    if baseline is not None:
        span_attrs["eval.baseline"] = float(baseline)
    if passed is not None:
        span_attrs["eval.passed"] = bool(passed)
    span_attrs.update(attrs)
    with traced_span(f"eval.{suite}", **span_attrs):
        pass


def status() -> dict[str, Any]:
    import os
    return {
        "export_path": "otlp-collector → phoenix" if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") else "none",
        "eval_suites": "spec — corpora + CI gate land at Stage 20 (phoenix-evals)",
        "note": "Stage 12.5 wires the eval span-export API; OWASP-LLM01 / NIST-RMF-Agentic / OWASP-Agentic "
                "corpora + thresholds are Stage 20 (KB_15 §'Phoenix as CI gate').",
    }


__all__ = ["log_eval", "status"]
