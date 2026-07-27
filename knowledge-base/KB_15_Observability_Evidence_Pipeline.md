---
name: Observability & Evidence Pipeline
description: OpenTelemetry GenAI semconv + Langfuse self-hosted + Arize Phoenix + separate immutable evidence sink. Why traces and evidence are different stores by design.
type: spec
last-updated: 2026-05-18
---

# KB_15 — Observability & Evidence Pipeline

## Purpose

Specify the two-store split between mutable traces (for debugging / perf / eval review) and immutable evidence (for regulators / auditors). Pin the libraries, ports, retention windows, and the spans every layer must emit.

## Source of truth

- OpenTelemetry GenAI semantic conventions (current state — March 2026 experimental, rapidly stabilising).
- Langfuse v3 self-hosted (Apache 2.0).
- Arize Phoenix (Apache 2.0).
- EU AI Act Article 12 (record-keeping; 6-month minimum retention).
- This file is the contract for `backend/observability/` and `docker/docker-compose.observability.yml`.

## Body

### Two stores by design

| Concern | Store | Mutability | Retention | Purpose |
|---|---|---|---|---|
| Application traces, spans, perf data | **Langfuse v3** self-hosted | mutable; pruning OK | 90 days default | Debugging, eval review, performance |
| Eval results, prompt-injection regression | **Arize Phoenix** | mutable | 90 days | Offline + CI evals, model comparison |
| EU AI Act Art. 12 evidence (every agent action) | **PostgreSQL `audit_chain` table** | **append-only, ML-DSA-65 signed** | indefinite | Regulator-grade record |

Mixing traces and evidence in one store is a compliance own-goal: trace stores get pruned, sampled, lossy. Evidence cannot be lossy.

### Self-hosted, Apache 2.0, EU-residency friendly

No paid SaaS. All run in `docker/docker-compose.observability.yml`. Customer data stays in their cluster.

### Compose stanza shape

```yaml
services:
  langfuse-web:
    image: langfuse/langfuse:3
    environment:
      DATABASE_URL: postgresql://langfuse:${LANGFUSE_PG_PASSWORD}@langfuse-pg:5432/langfuse
      CLICKHOUSE_URL: http://langfuse-clickhouse:8123
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET}
      SALT: ${LANGFUSE_SALT}
      TELEMETRY_ENABLED: "false"
    depends_on: [langfuse-pg, langfuse-clickhouse, langfuse-redis]
    ports: ["3001:3000"]

  langfuse-pg:        { image: postgres:15-alpine, ... }
  langfuse-clickhouse:{ image: clickhouse/clickhouse-server:24.3, ... }
  langfuse-redis:     { image: redis:7-alpine, ... }

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.110.0
    volumes: ["./otel-collector-config.yaml:/etc/otelcol/config.yaml:ro"]
    ports: ["4317:4317", "4318:4318"]

  phoenix:
    image: arizephoenix/phoenix:latest
    ports: ["6006:6006"]
```

### OpenTelemetry collector config shape

```yaml
# docker/otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  batch: { send_batch_size: 1024, timeout: 5s }
  resource:
    attributes:
      - key: service.name
        value: ai-embodied-agent
        action: upsert

exporters:
  otlphttp/langfuse:
    endpoint: http://langfuse-web:3000/api/public/ingestion
    headers: { authorization: "Basic ${LANGFUSE_TOKEN}" }
  otlp/phoenix:
    endpoint: phoenix:4317
    tls: { insecure: true }
  logging: { loglevel: warn }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [resource, batch]
      exporters: [otlphttp/langfuse, otlp/phoenix, logging]
```

### Spans every layer must emit

The instrumentor in `backend/observability/otel_init.py` (Stage 12.5) wraps:

| Surface | Span name | Attributes (GenAI semconv where applicable) |
|---|---|---|
| LangGraph node entry/exit | `langgraph.node.<name>` | `langgraph.run_id`, `langgraph.thread_id` |
| MCP tool call | `mcp.tool.<server>.<tool>` | `mcp.server`, `mcp.tool`, `mcp.input_hash`, `mcp.output_hash` |
| A2A inbound | `a2a.inbound.<peer>.<method>` | `a2a.peer`, `a2a.method`, `a2a.agent_card_fingerprint` |
| A2A outbound | `a2a.outbound.<peer>.<method>` | same |
| LLM completion | `gen_ai.completion` | `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.id`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| Embedding | `gen_ai.embedding` | `gen_ai.request.model`, `embedding.dim` |
| Model inference (non-LLM) | `ml.inference.<model>` | `ml.model.name`, `ml.model.version`, `ml.inference.latency_ms` |
| Safety validator gate | `safety.validate.<contract>` | `safety.contract`, `safety.sil`, `safety.decision` (pass/fail) |
| Actuator command | `actuator.<channel>` | `actuator.channel`, `actuator.command`. **CI gate:** must have a preceding `safety.validate.*` span. |
| Audit chain append | `audit_chain.append` | `audit.actor`, `audit.action`, `audit.seq` |
| Memory read/write | `memory.<backend>.<op>` | `memory.namespace`, `memory.op` |

### Evidence sink — separate from Langfuse

`backend/observability/evidence_sink.py` is a thin wrapper that writes to `audit_chain` (via `backend/memory/audit_chain.py`). Called from the LangGraph node decorators alongside (NOT instead of) OTel span emission. The split:

- OTel span: short-lived debug record.
- audit_chain row: forever evidence record, ML-DSA-65 signed.

Both happen for the same agent action. Loss of trace store doesn't lose evidence; loss of evidence cannot happen (immutable + signed + chained).

### Phoenix as CI gate (Stage 20) — **SHIPPED 2026-06-22**

`backend/training/evals/` (research §30): `runner.py` scores three corpora against the system's REAL defences
(never a hand-set number — Hard Rule 1a / KB_23):

- **OWASP-LLM01** prompt-injection corpus — **217 cases** (153 attacks + 64 benign controls), `redteam/owasp_llm01_corpus.jsonl`,
  scored by `security/prompt_guard.py` (hybrid: heuristic patterns + bge-small semantic kNN). Measured **0.9935** detection
  (full hybrid, 1/153 miss), FPR 0.0156; heuristic-only (CI) 0.758.
- **NIST AI RMF Agentic** vectors (`redteam/nist_rmf_agentic.jsonl`) — cross-session memory leak/poisoning → `mem0_adapter._authorize`+RLS,
  tool-chain poisoning → `security/tool_manifest`, excessive agency → `safety/validator`. Measured **1.000 (14/14)**.
- **Industry-safety** scenarios (`redteam/industry_safety.jsonl`) — unsafe-actuation commands; input-tier 0.875 (binding gate = validator, Rule 3).
- **Agentic metrics (G-008)** — `agentic_metrics.py` computes tool-selection-quality / action-completion / reasoning-coherence over the
  REAL LangGraph trajectory (`run_incident`). Measured **1.0 / 1.0 / 1.0** live (full KB_25 loop, 1 decision).

Thresholds live in `backend/training/evals/thresholds.yaml` (each set BELOW measured). **CI `phoenix-evals`** runs the
deterministic subset every PR + fails on breach; **`nightly-evals.yml`** runs the full hybrid (semantic + live runtime)
and enforces the OWASP-LLM01 ">=99% refusal" target. Results emit via `observability/phoenix_evals.log_eval` → Phoenix
(UI render optional) and feed the Annex IV pack (`scripts/generate-annex-iv-doc.py`). `audits/STAGE_20_audit.md` captures the run.

### Retention

| Store | Retention | Rationale |
|---|---|---|
| Langfuse traces | 90 days | Standard ops debug window; ClickHouse TTL enforces |
| Phoenix evals | 90 days | Comparable to traces |
| `audit_chain` | indefinite | EU AI Act Art. 12; only purge on a legally-mandated subject-access deletion request, which writes a `redaction` row preserving the chain |
| `mem0_memories` | per namespace (see KB_14) | GDPR + Art. 12 alignment |
| `pgaudit` DB-level log | 1 year | independent record of DB activity |

### What NOT to do

- Don't write evidence to Langfuse. It will get pruned.
- Don't query `audit_chain` from product code for debugging. Use Langfuse traces.
- Don't sample OTel spans for safety-critical paths. The safety.validate / actuator pair must always be observable.
- Don't proxy traces through a third-party SaaS. EU-residency story breaks.

### Operator dashboard telemetry contract (added v2.1, 2026-05-31)

The operator dashboard (PRD v2.1 §v2.1.4; page spec in KB_08) consumes a unified **activity stream** that must
cleanly separate **agentic** from **non-agentic** activity. Every activity event carries:

- `actor_class ∈ {agent, human, system, external}` — REQUIRED. `agent` = LLM/agent-runtime action; `human` =
  operator/HITL action; `system` = scheduler/automation/plant process; `external` = A2A peer or upstream system.
- `sil ∈ {0,1,2,3,4}` — safety level of the action (0 for informational).
- `actor_id`, `ts`, `event_type`, `summary`, `correlation_id` (links to OTel trace +, where applicable, an
  `audit_chain` seq), and `severity` for alarmable events.

Sources of the stream (no new lossy store — the dashboard reads from the canonical surfaces):
- agentic events ← OTel `langgraph.node.*`, `mcp.tool.*`, `gen_ai.*` spans + LangGraph HITL `interrupt()`.
- non-agentic events ← simulator/plant telemetry, `actuator.*` spans, MQTT/OPC UA ingest.
- safety events ← `safety.validate.*`, STO/SS1 rows.
- governance/security events ← policy decisions, PII-filter actions, A2A card verify/revoke.

**Alarm model.** Severities: `info | warning | critical | safety_critical`. Each alarm: `id, severity, source,
actor_class, message, raised_at, ack_by, ack_at, cleared_at`. Rules: de-dup by `(source,signature)`;
storm-suppression (rate cap per source); operator acknowledgements are written to `audit_chain` (Art. 12);
**`safety_critical` alarms are never auto-cleared** — they require explicit operator ack and a cleared root cause.
Notification routing is config-driven (UI + optional webhook/email/Slack) with **no hard SaaS dependency**.

**Reporting.** Shift / incident / EU-AI-Act-evidence summaries are generated from `audit_chain` (+ Langfuse for
debug context), exported HTML/PDF/CSV/JSON, signed with the current key, with the audit-chain head hash embedded.
SLOs (event→view p95 ≤ 1 s; alarm p95 ≤ 2 s; export ≤ 10 s) in PRD v2.1 §v2.1.2 §D. Implemented Stage 12.5
(live telemetry) → Stage 19 (signed reporting); rides on the Stage 3 WebSocket broker for live delivery.

## Last verified

2026-06-15 (Stage 12.5): the observability pipeline is **BUILT + verified**. `backend/observability/`: `otel_init.py`
(TracerProvider + env-gated OTLP/HTTP exporter + FastAPI auto-instrumentation + the `traced_span` helper + an
in-memory exporter for tests), `evidence_sink.py` (thin wrapper over `memory/audit_chain` — emits `audit_chain.append`
+ writes the immutable row), `langfuse_sink.py` + `phoenix_evals.py` (honest status + export-path helpers).
Instrumented: `langgraph.node.*` (graph nodes), `mcp.tool.<server>.<tool>` (the runtime mount), `memory.mem0.*`
(recall/remember), `ml.inference.failure_predictor`, `audit_chain.append`. `main.py` calls `otel_init.init(app)` at
startup (honest: no OTLP endpoint → spans created but not exported to a fake sink). Overlay
`docker/docker-compose.observability.yml` + `otel-collector-config.yaml` (langfuse-web/pg/clickhouse/redis +
otel-collector + phoenix; used via `-f`). **Verified:** 7 span tests pass (InMemorySpanExporter asserts the span
table); **live OTLP→collector confirmed** (collector debug exporter logged `langgraph.node.observe` +
`audit_chain.append` with correct attributes); full backend suite 228 passed/2 skipped; audit 364. The
collector→Langfuse/Phoenix UI render is overlay-enabled (Langfuse v3 stack is heavy; the app→collector path is what
was verified live). `gen_ai.*` spans emit when an LLM is used; `safety.validate`/`actuator` at Stage 17; `a2a.*` at
Stage 14; Phoenix eval corpora + CI gate at Stage 20. ADR `2026-06-15_stage12_5_observability.md`.

Prior: 2026-05-18 (base), + 2026-05-31 (operator-dashboard telemetry + alarm + reporting contract added), by
agentic-governance-engineer + devops-sre.

## Stage 28 — grounding citations in the Art-12 trace (2026-07-04)

The runtime `explain` node retrieves GraphRAG grounding (SOP + ISA-95 citations) for each diagnosis and passes it
into `governance/traceability.record_decision_trace` (the `grounding` key of the pre-state snapshot). Every signed
`decision.trace` audit row now records whether the explanation was grounded and which SOP/graph nodes grounded it —
Art-12 record-keeping upgraded from "what was decided" to "what evidence grounded the why".
