"""Stage 12.5 — OpenTelemetry setup + the `traced_span` helper (KB_15, research §21).

`init()` installs a `TracerProvider` (resource `service.name=ai-embodied-agent`) + a FastAPI auto-instrumentor + an
OTLP/HTTP span exporter to the collector **when `OTEL_EXPORTER_OTLP_ENDPOINT` is configured**. Honest by design: with
no endpoint, spans are still created (the in-process record + tests) but NOT exported to a fake sink — we never
pretend traces shipped (Rule 1a). `traced_span()` is the single wrapper all instrumentation uses, so the experimental
GenAI semconv churning upstream is a one-file change here.

Span names + attributes follow KB_15 §"Spans every layer must emit" (GenAI semconv attribute names where applicable).
"""
from __future__ import annotations

import contextlib
import os
from typing import Any, Iterator, Optional

_SERVICE = "ai-embodied-agent"
_initialized = False
_backend = "uninitialized"

# A handle to the in-memory exporter when tests install one (so they can read finished spans).
_in_memory_exporter: Any = None


def init(app: Any = None, *, force: bool = False) -> str:
    """Install the global TracerProvider + (env-gated) OTLP exporter + FastAPI instrumentation. Idempotent.

    Returns a backend status string: 'otlp:<endpoint>' | 'local-only (no OTLP endpoint)' | 'already-initialized'.
    """
    global _initialized, _backend
    if _initialized and not force:
        if app is not None:
            _instrument_fastapi(app)
        return _backend

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider(resource=Resource.create({"service.name": _SERVICE}))
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        # OTLP/HTTP traces endpoint (the collector listens on :4318; append the signal path if a base URL is given).
        traces_ep = endpoint if endpoint.rstrip("/").endswith("/v1/traces") else endpoint.rstrip("/") + "/v1/traces"
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=traces_ep)))
        _backend = f"otlp:{traces_ep}"
    else:
        _backend = "local-only (no OTLP endpoint)"

    trace.set_tracer_provider(provider)
    _initialized = True
    if app is not None:
        _instrument_fastapi(app)
    return _backend


def _instrument_fastapi(app: Any) -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except Exception:  # noqa: BLE001 - instrumentation is best-effort; never block app startup
        pass


def status() -> str:
    return _backend


def get_tracer():
    from opentelemetry import trace
    return trace.get_tracer(_SERVICE)


@contextlib.contextmanager
def traced_span(name: str, **attributes: Any) -> Iterator[Any]:
    """Start a span named per KB_15 with the given attributes. Safe to call with or without `init()` (the OTel API
    returns a no-op tracer if no SDK provider is set — no error, no fake export)."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        try:
            for k, v in attributes.items():
                if v is not None:
                    span.set_attribute(k, v)
        except Exception:  # noqa: BLE001 - attribute typing should never break the traced code
            pass
        yield span


# ---- test support ----------------------------------------------------------

def use_in_memory_exporter() -> Any:
    """Install a fresh TracerProvider with an InMemorySpanExporter (SimpleSpanProcessor) and return the exporter.
    Tests call this, run instrumented code, then read `exporter.get_finished_spans()`. Deterministic, no infra."""
    global _initialized, _in_memory_exporter, _backend
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": _SERVICE}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # trace.set_tracer_provider only honours the FIRST call per process; override the internal proxy for tests.
    trace._TRACER_PROVIDER = provider  # type: ignore[attr-defined]
    _in_memory_exporter = exporter
    _initialized = True
    _backend = "in-memory (test)"
    return exporter


__all__ = ["init", "status", "get_tracer", "traced_span", "use_in_memory_exporter"]
