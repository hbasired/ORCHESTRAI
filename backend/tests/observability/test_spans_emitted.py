"""Stage 12.5 — assert the KB_15 span table is emitted, using OTel's InMemorySpanExporter (no heavy infra).

Deterministic + CI-friendly: install an in-memory exporter, run instrumented code, read the finished spans. The
live collector→Langfuse/Phoenix render is enabled by the observability overlay (smoke-tested separately).
"""
import os
import uuid

import pytest

_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))

_INCIDENT = {
    "incident_id": None,  # set per-test
    "type": "machine_crack", "target_id": 3, "sil_level": 0,
    "telemetry": {"stage_id": 3, "type_": "M", "air_temp_k": 300.0, "process_temp_k": 312.0,
                  "rot_speed_rpm": 1300.0, "torque_nm": 60.0, "tool_wear_min": 210.0,
                  "status": "degraded", "crack_proximity": 0.9},
    "plant": {"available_crew": 1},
}


def _run_incident_collecting_spans():
    from observability.otel_init import use_in_memory_exporter
    from agents.runtime.graph import run_incident
    exporter = use_in_memory_exporter()
    inc = dict(_INCIDENT, incident_id=f"obs-{uuid.uuid4().hex[:8]}")
    run_incident(inc)
    return [s.name for s in exporter.get_finished_spans()]


@pytest.mark.timeout(120)
def test_langgraph_node_spans_emitted():
    names = _run_incident_collecting_spans()
    # Every self-healing node must emit a langgraph.node.<name> span (KB_15).
    for node in ("observe", "orient", "diagnose", "explain", "decide", "verify", "execute", "log"):
        assert f"langgraph.node.{node}" in names, f"missing span langgraph.node.{node}; got {sorted(set(names))}"


@pytest.mark.timeout(120)
def test_ml_inference_span_emitted():
    names = _run_incident_collecting_spans()
    assert "ml.inference.failure_predictor" in names, f"missing ml.inference span; got {sorted(set(names))}"


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL: memory/audit spans need the live DB")
@pytest.mark.timeout(180)
def test_memory_and_audit_spans_emitted_with_db():
    names = _run_incident_collecting_spans()
    assert "memory.mem0.search" in names, f"missing memory.mem0.search; got {sorted(set(names))}"
    assert "audit_chain.append" in names, f"missing audit_chain.append; got {sorted(set(names))}"
    assert "memory.mem0.add" in names, f"missing memory.mem0.add; got {sorted(set(names))}"


@pytest.mark.timeout(60)
def test_traced_span_sets_attributes_and_is_safe_without_init():
    # Fresh process path: traced_span must work even if init() was never called (no-op tracer, no error).
    from observability.otel_init import use_in_memory_exporter, traced_span
    exporter = use_in_memory_exporter()
    with traced_span("mcp.tool.kpi_query_server.oee", **{"mcp.server": "kpi_query_server", "mcp.tool": "oee"}):
        pass
    spans = exporter.get_finished_spans()
    assert spans[-1].name == "mcp.tool.kpi_query_server.oee"
    assert spans[-1].attributes.get("mcp.server") == "kpi_query_server"


def test_otel_init_is_honest_without_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    from observability.otel_init import init
    backend = init(force=True)
    assert "local-only" in backend  # honest: not pretending traces ship to a sink


def test_otel_init_reports_otlp_when_endpoint_set(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    from observability.otel_init import init
    backend = init(force=True)
    assert backend.startswith("otlp:") and "/v1/traces" in backend


def test_phoenix_and_langfuse_sinks_report_honestly():
    from observability import phoenix_evals, langfuse_sink
    assert "spec" in phoenix_evals.status()["eval_suites"].lower()  # Stage-20 corpora honestly not-yet-built
    assert langfuse_sink.status()["active_path"] in ("otlp-collector", "direct-sdk", "none")
