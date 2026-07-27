# ADR — Stage 12.5: observability pipeline (OpenTelemetry → collector → Langfuse + Phoenix)

**Date**: 2026-06-15
**Status**: Accepted (Stage 12.5 — follows Stage 12 `2026-06-15_stage12_agent_memory.md`)
**Author personas**: `devops-sre` (compose stack) + `backend-engineer` (instrumentation)
**Relates**: KB_15 (observability/evidence), KB_10 (hardening), KB_23 (evals). Research §21. Follows Hard Rule 1a
(honest-when-unconfigured — no fake trace export), Rule 9 (free/OSS self-hosted), Rule 11 (research-first).

---

## Context

Stage 12 built the immutable evidence half (`audit_chain`). Stage 12.5 wires the mutable-trace half (KB_15's
two-store split): OpenTelemetry spans → otel-collector → Langfuse (debug, 90-day) + Phoenix (evals), emitted
ALONGSIDE the evidence row for the same action.

## Decisions

**D1 — OTel SDK + the `traced_span` wrapper (`otel_init.py`).** A `TracerProvider` (resource `service.name`) + an
**env-gated OTLP/HTTP exporter** (`OTEL_EXPORTER_OTLP_ENDPOINT`, default the collector `:4318/v1/traces`) + FastAPI
auto-instrumentation. **Honest (Rule 1a):** with no endpoint, spans are still created (in-process record + tests) but
NOT exported to a fake sink — `init()` returns `local-only` and says so. All instrumentation goes through one
`traced_span(name, **attrs)` helper so the **experimental** GenAI semconv churning upstream is a one-file change.
A `use_in_memory_exporter()` gives deterministic, infra-free tests.

**D2 — Span coverage (KB_15 table) emitted from the call sites.** `langgraph.node.<name>` (nodes wrapped at
graph-build time), `mcp.tool.<server>.<tool>` (the runtime MCP mount), `memory.mem0.search`/`memory.mem0.add`
(observe/log), `ml.inference.failure_predictor` (orient), `audit_chain.append` (via `evidence_sink`). `gen_ai.*`
emit when an LLM runs; `safety.validate`/`actuator` are Stage 17; `a2a.*` Stage 14.

**D3 — Evidence sink alongside, not instead of, traces.** `evidence_sink.record()` wraps `memory/audit_chain.append`
(Stage 12) AND emits the `audit_chain.append` span — the runtime `log` node now routes through it, so the same
decision produces both a (prunable) trace and an (immutable, signed) evidence row. Loss of the trace store never
loses evidence (KB_15).

**D4 — Self-hosted overlay (Apache-2.0, no paid SaaS).** `docker-compose.observability.yml` (langfuse-web + its pg +
clickhouse + redis + otel-collector + phoenix) + `otel-collector-config.yaml` (OTLP in → fan-out to Langfuse
`otlphttp` + Phoenix `otlp` + a `debug` exporter so the collector is smoke-testable alone). Used via `-f` overlay
(NOT a forced `include:` in the base compose — the full Langfuse v3 stack is heavy; keep base compose lean; honest
deviation from the task doc's "include" wording). `langfuse-init.sh` documents the first-boot + the `LANGFUSE_TOKEN`.

**D5 — Verification (verified, not asserted).** 7 span tests pass via the InMemorySpanExporter (assert the KB_15
span names + attributes, incl. the memory/audit spans against the live DB). **Live OTLP→collector confirmed:** the
collector's debug exporter logged `langgraph.node.observe` (+ `langgraph.node=observe`) and `audit_chain.append`
(+ `audit.actor`/`audit.action`/`audit.seq=99`) — the app→collector path is real. Full backend suite **228 passed /
2 skipped**; audit **364**. The collector→Langfuse/Phoenix UI render is overlay-enabled (heavy stack); the
app→collector path is what was verified live (honest about the boundary).

**D6 — CI: `observability-smoke` + a fixed regression.** Added the `observability-smoke` CI job (pgvector Postgres +
`pytest tests/observability/`). **Also fixed a regression Stage 12 introduced:** `mcp-conformance` used `postgres:16`
(no pgvector) but `alembic upgrade head` now includes `0005_mem0` (CREATE EXTENSION vector) → its image is corrected
to `pgvector/pgvector:pg16`.

## Why
- A two-store split (mutable traces ≠ immutable evidence) is the KB_15/Art-12 contract; emitting standard OTel GenAI
  spans makes the system observable in any conformant backend (Langfuse/Phoenix/Datadog/...) — and honest-when-
  unconfigured keeps it from ever pretending traces shipped.

## Consequences
- New: `backend/observability/` (5 files), `backend/tests/observability/` (7 tests), `docker-compose.observability.yml`,
  `otel-collector-config.yaml`, `langfuse-init.sh`, the `observability-smoke` CI job, this ADR, the explainer,
  KB_TASK_LOG entry. Modified: `agents/runtime/{graph,nodes}.py` (node + memory/ml spans), `agents/runtime/mcp_mount.py`
  (mcp.tool spans), `main.py` (otel_init at startup), `requirements.txt` (aligned OTel stack), `ci.yml` (mcp-conformance
  image fix + new job), KB_15/KB_10.
- Audit holds 364 (`--no-baseline-drop`; instrumentation wraps real spans, no grep-counted theatre — Rule 1a).

## Honest residual / ledger
- The full Langfuse v3 UI render needs the heavy overlay up — verified the app→collector path live, not the
  Langfuse-UI render (G-067, low — bring up the full overlay + confirm a trace renders in the Langfuse UI).
- Phoenix eval corpora + the `phoenix-evals` CI gate are Stage 20 (the export path is wired now).
- OTel GenAI semconv is experimental — pinned + wrapped via `traced_span`; revisit on the dependency-refresh drill.

## References
- `backend/observability/{otel_init,evidence_sink,langfuse_sink,phoenix_evals}.py` · `backend/tests/observability/
  test_spans_emitted.py` · `docker/{docker-compose.observability.yml,otel-collector-config.yaml,langfuse-init.sh}` ·
  `agents/runtime/{graph,nodes,mcp_mount}.py` · `main.py` · `.github/workflows/ci.yml`. KB_15/10/23. Research §21.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:31+00:00 -->
<!-- signature: 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 -->
