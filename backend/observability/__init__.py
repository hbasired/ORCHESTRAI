"""Stage 12.5 — observability & evidence pipeline (KB_15).

Two stores by design: **mutable traces** (OpenTelemetry → collector → Langfuse + Phoenix, 90-day) and **immutable
evidence** (`audit_chain`, append-only + signed, indefinite — built Stage 12). This package emits OTel spans per the
KB_15 span table using the GenAI semantic conventions where applicable; `evidence_sink` writes evidence ALONGSIDE
(never instead of) span emission, so losing the trace store never loses evidence.

Public surface:
- `otel_init.init(app=None)` — set the TracerProvider + OTLP exporter (env-gated) + FastAPI instrumentation.
- `otel_init.traced_span(name, **attrs)` — the one helper all instrumentation uses (wraps the SDK so an
  experimental-semconv rename is a one-file change).
- `evidence_sink.record_decision(...)` — thin wrapper over `memory.audit_chain`.
"""
