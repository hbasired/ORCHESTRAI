---
status: done
stage: 12.5
slug: observability
created: 2026-05-18
---

# Stage 12.5 — Observability (OTel GenAI semconv + Langfuse + Phoenix)

> Wire the observability stack per KB_15. OpenTelemetry collector emits to Langfuse (mutable, 90-day) AND to Phoenix (evals). The separate immutable evidence sink (`audit_chain`) was wired in Stage 12.

## Pre-requisites

- Stages 11, 11.5, 12 closed.

## Acceptance criteria

- [x] `docker/docker-compose.observability.yml` boots Langfuse + Postgres + ClickHouse + Redis + OTel collector + Phoenix. — DONE (used via `-f` overlay, NOT a forced base `include:` — keep base compose lean; honest deviation). otel-collector brought up + verified live.
- [x] `backend/observability/otel_init.py` installs the SDK + GenAI semconv instrumentor at FastAPI startup. — DONE (`init(app)` in `main.py` lifespan; FastAPI auto-instrumentation; `traced_span` wrapper; honest-when-unconfigured).
- [x] `backend/observability/langfuse_sink.py` exports traces to Langfuse. — DONE (honest path: app → OTLP → collector → Langfuse `otlphttp`; the module reports the real active path; the app needs only the OTLP exporter).
- [x] `backend/observability/phoenix_evals.py` exports eval data to Phoenix. — DONE (eval span-export API `log_eval`; full Phoenix eval corpora + CI gate honestly deferred to Stage 20).
- [x] `backend/observability/evidence_sink.py` writes to `audit_chain` (parallel to OTel span emission). — DONE (wraps `memory/audit_chain` + emits `audit_chain.append`; runtime `log` node routed through it — verified `audit.seq` matches the durable PG row).
- [x] Spans emitted per KB_15 §"Spans every layer must emit" table. — DONE for the currently-applicable rows (`langgraph.node.*`, `mcp.tool.*`, `memory.mem0.*`, `ml.inference.*`, `audit_chain.append`); `gen_ai.*`/`safety.validate`/`actuator`/`a2a.*` emit at their owning stages (17/14). 7 span tests pass; **live OTLP→collector confirmed**.
- [~] Canned LangGraph run produces visible traces in Langfuse UI (`http://localhost:3001`). — app→collector path VERIFIED LIVE; the Langfuse v3 UI render needs the heavy overlay up → **G-067** (low, ledgered).
- [~] Phoenix UI accessible (`http://localhost:6006`). — overlay provides it; UI render bundled with G-067.
- [x] Independent review PASS (Rule 11b) — `audits/STAGE_12_5_independent_review.md` (**DYNAMIC**: a different agent re-ran the suite + the live OTLP→collector proof + audit 364).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/observability/__init__.py` | Package marker |
| `backend/observability/otel_init.py` | OTel SDK + GenAI semconv setup |
| `backend/observability/langfuse_sink.py` | Langfuse exporter |
| `backend/observability/phoenix_evals.py` | Phoenix exporter |
| `backend/observability/evidence_sink.py` | Thin wrapper to `audit_chain` |
| `docker/docker-compose.observability.yml` | Self-hosted stack |
| `docker/otel-collector-config.yaml` | OTLP receiver + Langfuse/Phoenix exporters |
| `docker/langfuse-init.sh` | Langfuse first-boot setup |
| `backend/tests/observability/test_spans_emitted.py` | Asserts spans reach collector |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/main.py` | Call `otel_init.init()` at startup |
| `backend/agents/runtime/graph.py` | Decorate nodes with span emission |
| `backend/mcp_servers/*.py` | Emit `mcp.tool.<server>.<tool>` spans |
| `backend/memory/*.py` | Emit `memory.<backend>.<op>` spans |
| `backend/requirements.txt` | Add `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp`, `langfuse`, `arize-phoenix` |
| `docker/docker-compose.yml` | `include:` directive for observability overlay |
| `.github/workflows/ci.yml` | Add `observability-smoke` job |

## KB files this stage updates

- `KB_15_Observability_Evidence_Pipeline.md`
- `KB_10_Production_Hardening.md`
- `KB_TASK_LOG.md`

## Verification commands

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.observability.yml up -d
cd backend && pytest tests/observability/ -v
# Open Langfuse UI and verify a canned LangGraph run produces traces
```

## Audit target

- Strict decrease.

## Role

- Primary: `devops-sre` (compose stack), `backend-engineer` (instrumentation)

## Hand-off

- What is now true: every agent action produces an OTel trace and an `audit_chain` row.
- Next stages (13–13.5) consume this for CDC ingestion and PQC signing.
