# Stage 12.5 — Independent Review (Observability pipeline, KB_15)

**Auditor**: independent `task-auditor` persona (did NOT implement Stage 12.5).
**Date**: 2026-06-15
**Verification mode**: **DYNAMIC** — live Docker infra was up (Postgres `pgvector/pgvector:pg15` @5544, Neo4j @7687, otel-collector @4318 with debug exporter). I ran the span tests, the audit, and drove a real OTLP→collector incident myself.

## VERDICT: **PASS**

Stage 12.5 is honest, real, and meets its acceptance criteria within the explicitly-ledgered deviations (G-067, low). Span coverage matches KB_15 exactly; the two-store split genuinely writes both an OTel span and an immutable `audit_chain` row for the same action; tests run instrumented code and read finished spans (not mock-asserting); and the honest-when-unconfigured contract (Rule 1/1a) holds in code and at runtime. No theatre found in the new code. Audit holds at 364 (justified `--no-baseline-drop` — instrumentation wraps real spans, zero grep-counted fakery added).

---

## What I ran (dynamic evidence)

| Command | Result |
|---|---|
| `bash scripts/audit.sh` | TOTAL **364** == baseline 364 (held; instrumentation-only stage) |
| `pytest tests/observability/ -q` (live DB env) | **7 passed** in 68s |
| `pytest …::test_memory_and_audit_spans_emitted_with_db -v` | **PASSED** (ran, NOT skipped — `_HAS_DB` True) |
| `pytest tests/agents/runtime/ tests/memory/ -q` (live DB) | **20 passed** (instrumentation in-path didn't break the runtime/memory loops) |
| Real OTLP run → `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` + `run_incident(...)` + `force_flush()` | `backend=otlp:http://localhost:4318/v1/traces`; 1 decision; `audit_seqs=[49]`; backend=postgres (durable) |
| `docker logs ai-agent-otel-collector` after the run | **All KB_15 spans received over the wire** (see below) |

### Collector received over the wire (decisive end-to-end proof)
```
memory.mem0.search          memory.namespace=incident:audit-otlp-001 memory.op=search
langgraph.node.observe      langgraph.node=observe
ml.inference.failure_predictor  ml.model.name=failure_predictor
langgraph.node.orient / diagnose / explain / decide / verify / execute
audit_chain.append          audit.actor=agent:embodied audit.action=decision.monitor audit.seq=49
memory.mem0.add             memory.namespace=incident:audit-otlp-001 memory.op=add
langgraph.node.log
```
`audit.seq=49` in the span matches the `audit_seqs=[49]` row written to durable Postgres this same run — proving the two-store split is real (one action → one span **and** one immutable chained row), not a span pretending to be evidence.

---

## Per-criterion evidence

| # | Acceptance criterion | Claimed | Independently confirmed? | Note |
|---|---|---|---|---|
| 1 | `docker-compose.observability.yml` boots Langfuse+PG+ClickHouse+Redis+collector+Phoenix | yes | **Partial / by inspection** | Compose file defines all 6 services correctly (`docker-compose.observability.yml:11-85`). Only the collector subset was UP live; full Langfuse-v3 render not brought up → **G-067 (low)**, honestly ledgered. |
| 2 | `otel_init.py` installs SDK + GenAI semconv instrumentor at FastAPI startup | yes | **Yes** | `main.py:150-156` calls `otel_init.init(app)` at startup; `otel_init.py:25-56` installs TracerProvider + env-gated OTLP exporter + FastAPI auto-instrument. |
| 3 | `langfuse_sink.py` exports traces to Langfuse | yes | **Yes (honest path)** | App emits OTLP→collector→Langfuse `otlphttp` (not a direct client on the trace path). `langfuse_sink.py` is a status/optional-direct helper that never claims traces shipped when they didn't (`status()` returns `active_path` honestly). Correct per KB_15 design. |
| 4 | `phoenix_evals.py` exports eval data to Phoenix | yes | **Yes (honestly scoped)** | `phoenix_evals.log_eval()` emits `eval.<suite>` spans routed via collector; `status()` says corpora + CI gate are **Stage 20**, not pretending the eval suites exist. |
| 5 | `evidence_sink.py` writes `audit_chain` parallel to span | yes | **Yes** | `evidence_sink.record()` (`evidence_sink.py:14-25`) emits `audit_chain.append` span AND calls the real `memory.audit_chain.append` (append-only SHA-256 chain, raises `AuditChainUnavailable` when no DB — `audit_chain.py:9-11,27-28`). Confirmed live: seq 49 written + span emitted. Routed from the runtime `log` node (`nodes.py:222-230`). |
| 6 | Spans emitted per KB_15 §"Spans every layer must emit" | yes | **Yes** | All emitted from real call sites: `langgraph.node.*` (`graph.py:29-57`), `ml.inference.failure_predictor` (`nodes.py:68`), `memory.mem0.search`/`add` (`nodes.py:47,240`), `audit_chain.append` (`evidence_sink.py:18`), `mcp.tool.<server>.<tool>` (`mcp_mount.py:115,124`). Names + attributes match KB_15:108-118. |
| 7 | Canned LangGraph run visible in Langfuse UI (`:3001`) | yes | **No (overlay-enabled, not live)** | Honest deviation, ledgered **G-067**: app→collector path verified live; Langfuse-UI render needs the heavy overlay (not brought up). The export path is configured (`otel-collector-config.yaml:21-23`). |
| 8 | Phoenix UI accessible (`:6006`) | yes | **No (overlay-enabled, not live)** | Same as #7 — Phoenix container defined (`docker-compose.observability.yml:25-31`) but not UP this session. Part of G-067. |

---

## Adversarial checks (per the brief)

1. **Honesty (Rule 1/1a) — PASS.** `otel_init` with no endpoint sets `_backend="local-only (no OTLP endpoint)"` (`otel_init.py:49-50`); spans are created via the no-op tracer but **never exported to a fake sink**. Confirmed by `test_otel_init_is_honest_without_endpoint`. `langfuse_sink.status()` and `phoenix_evals.status()` both report the real active path and honestly mark Stage-20 eval suites as `"spec — corpora + CI gate land at Stage 20"`. **No fabricated/no-op span passed off as real export anywhere.** Grep of `backend/observability/` for `random.*|Math.random|_get_demo_|RESPONSES =|MODELS =|# Generate mock|fallback|importance_score|confidence = 0.9` → **No matches**.

2. **Span coverage vs KB_15 — PASS.** Verified each span at its claimed call site (file:line above) AND received them all over the wire at the live collector. The `mcp.tool.*` span is the only one not exercised by `run_incident` (the loop doesn't call MCP tools), but it is emitted from a real call site (`mcp_mount.py:115,124`), unit-asserted by `test_traced_span_sets_attributes_and_is_safe_without_init`, and exercised by `tests/mcp/test_runtime_mount.py`.

3. **Two-store split — PASS.** `evidence_sink.record` does both (span + real append), not instead-of. The runtime `log` node routes decisions through `evidence_sink.record` (`nodes.py:222-230`). Live proof: span `audit.seq=49` ↔ durable PG row 49.

4. **Tests real, not theater — PASS.** `test_spans_emitted.py` installs a real `InMemorySpanExporter` (`use_in_memory_exporter`, `otel_init.py:93-111`), runs the actual `run_incident(...)` graph, and asserts over `exporter.get_finished_spans()` span **names + attributes** — genuine behavioural assertions, no mocks. The DB-gated test is correctly `skipif(not _HAS_DB)` and **ran (PASSED) here**, not silently skipped.

5. **Acceptance criteria deviations — honest & ledgered.** (a) `-f` overlay instead of a forced `include:` in base compose — disclosed in ADR D4 and justified (heavy Langfuse-v3 stack; keep base lean). (b) Langfuse/Phoenix UI render verified-as-overlay-enabled, not live — **G-067 (low)**, correctly recorded in `OPEN_GAPS_LEDGER.md:94`.

6. **CI regression fix — PASS.** Both `mcp-conformance` (`ci.yml:113`) and the new `observability-smoke` (`ci.yml:159`) use `pgvector/pgvector:pg16`. Confirmed `mcp-conformance` runs `alembic upgrade head` (`ci.yml:138`) which now pulls `0005_mem0` (CREATE EXTENSION vector) — plain `postgres:16` would have failed; the image fix is correct and necessary. New `observability-smoke` job is real (pgvector PG + `pytest tests/observability/`, `ci.yml:154-192`).

7. **Overclaims — none material.** The ADR D5 carefully scopes the live boundary ("app→collector path is what was verified live") and does not claim the Langfuse-UI render. I independently reproduced the live app→collector evidence. The one cosmetic mismatch (below) is not an overclaim.

---

## Findings (severity-ranked)

- **(none — blocking)**

- **LOW / cosmetic — test count drift in the ADR/KB.** ADR D5 and KB_15 say *"8 tests"* in the file-list (ADR `Consequences`) but *"7 span tests pass"* in D5; the file `test_spans_emitted.py` contains exactly **7** test functions and `pytest` reports **7 passed**. The "8" is a stale/miscount in prose only — no functional impact, no fabricated evidence. Recommend correcting "8 tests" → "7 tests" in the ADR `Consequences` line on the next doc touch. (Not close-blocking; not a new gap.)

- **LOW — `arize-phoenix` not added to `requirements.txt` despite the task doc's "Files to MODIFY" listing it.** This is actually **correct and honest**: Phoenix runs as a Docker container (`docker-compose.observability.yml:25`), and `phoenix_evals.py` only emits OTLP spans (no `import arize`/`import phoenix` anywhere in `backend/` — grep confirmed). The app never needs the Phoenix client lib on the trace path (matches research §21.2: "the app needs ONLY an OTLP exporter"). The deviation from the task doc's dep list is a sound design choice, well-documented in the ADR. No action needed; noted for completeness.

## New gaps
- **None.** G-067 (Langfuse/Phoenix UI render not verified live, low → Stage 12.5 follow-up / pilot) already exists and correctly captures the only real residual.

## Bottom line
Verified dynamically end-to-end against the live stack: spans are emitted from the real call sites, ship over the wire to the collector with correct attributes, and the same action lands an immutable `audit_chain` row — the KB_15 two-store contract is genuinely implemented, honest-when-unconfigured, and free/OSS/self-hosted. **PASS.**
