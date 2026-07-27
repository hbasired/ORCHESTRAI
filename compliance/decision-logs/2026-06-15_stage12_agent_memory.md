# ADR — Stage 12: agent memory (audit_chain + Mem0/pgvector + Neo4j ISA-95)

**Date**: 2026-06-15
**Status**: Accepted (Stage 12 — follows Stage 11.5 `2026-06-15_stage11_5_mcp_servers.md`)
**Author personas**: `backend-engineer` (primary) + `compliance-engineer` (audit_chain semantics + retention)
**Relates**: KB_14 (memory architecture), KB_04 (schema), KB_01 (topology). Research §19. Follows Hard Rule 1a
(honest-unavailable, no fabricated embeddings/audit rows), Rule 9 (free/OSS/local), Rule 11/11a (deepest honest
path; full depth first pass), Rule 11b (finish completely; verify live; ledger-and-fix). **Partially addresses G-059**
(see D4 — Stage 12 wires the *memory* layer into the graph nodes; G-059's literal intent, routing through the
mounted MCP *tools*, remains OPEN and re-targeted).

---

## Context

Stage 12 wires KB_14's five-layer memory: working (LangGraph checkpointer, Stage 11 — done), **episodic/semantic**
(Mem0/pgvector), **semantic graph** (Neo4j ISA-95), procedural (DVC — future), and **audit** (append-only
hash-chained, the EU-AI-Act Art-12 evidence). It also **partially addresses G-059** (Stage 11.5): the runtime graph
nodes now consume an external capability layer (memory), so decisions are audited + memory-mediated — though G-059's
literal ask (routing the runtime's *model/tool* calls through the mounted MCP `StructuredTool`s) remains OPEN.

## Decisions

**D1 — `audit_chain`: append-only, SHA-256 hash-chained, DB-enforced.** Migration `0003_audit_chain` +
`backend/memory/audit_chain.py`: each row `hash = SHA-256(prev_hash ‖ canonical(payload))` (research §19.4); BEFORE
UPDATE/DELETE triggers RAISE → append-only at the DB level (the app role inserts+reads only). Appends serialize on a
Postgres advisory lock so the chain links deterministically under concurrency. `verify_range()` recomputes + checks
linkage. The signature is a **structurally-correct placeholder** (`algorithm='placeholder-sha256'`, `key_version=0`)
— Stage 13.5 swaps in real ML-DSA-65 via `backend/crypto/pqc_signing.py` (the signer is resolved dynamically, so
13.5 is a drop-in). Honest: no DB → `AuditChainUnavailable` (never a dropped/faked audit record). `scripts/verify-
audit-chain.py` (pre-existing, psycopg2, same canonical form) verifies the live chain.

**D2 — `mem0_adapter`: direct pgvector store, HNSW, namespace-isolated, real embeddings.** Migration `0005_mem0`
(`mem0_memories`, `vector(MEM0_EMBED_DIM)`, **HNSW** cosine — research §19.2, a deviation from the KB's ivfflat
because the store is insert-as-you-go) + `backend/memory/mem0_adapter.py`. A **direct pgvector store** on KB_14's own
schema, NOT the `mem0ai` library (research §19.1: it needs an LLM for fact-extraction + imposes its own schema).
Real **sentence-transformers** embeddings (env-configurable; default bge-large/1024, verified live with bge-small/384
for download feasibility — dim is env-driven so the column matches). **Namespace isolation** (NIST RMF, KB_14): the
adapter binds to an incident (+ operator) context and may read its own `incident:`/`operator:` namespaces + the
shared `semantic:`/`procedural:`/`agent:` — a foreign tenant namespace raises `CrossNamespaceAccessError` (checked
BEFORE any I/O). Honest: no embedder → `EmbedderUnavailable` (never a random/fabricated embedding). Retention by
namespace; `jobs/mem0_retention_sweep.py` purges expired rows nightly + audits the purge.

**D3 — `graph_isa95`: idempotent Neo4j ISA-95 + PG mirror.** `backend/memory/graph_isa95.py::run_migrations()` is
idempotent (`CREATE CONSTRAINT IF NOT EXISTS` per ISA-95 Part-2 label) — safe on every boot. `upsert_node()` MERGEs
a node (+ parent edge) into Neo4j AND mirrors it into `isa95_metadata` (migration `0004`). Honest: no Neo4j →
`Neo4jUnavailable`. **`letta_adapter`** is the opt-in long-horizon backend — feature-flagged OFF by default
(`LETTA_ENABLED`); `is_enabled()`/`status()` never pretend it's active (default episodic backend stays Mem0).

**D4 — Runtime wiring (graph consumes the memory layer; partially addresses G-059).** `agents/runtime/nodes.py`:
`observe` recalls prior Mem0 memories for the incident; `log` writes each decision to `audit_chain` + remembers it in
Mem0. Best-effort + honest — the loop still completes (traced, not faked) when the DB/embedder is absent (the runtime
must run under MemorySaver/no-DB). `run_incident` now surfaces `audit_seqs` + `memory_recall`. AgentState gains
`memory_recall` + `audit_seqs`. **Scope note (honesty):** this makes the graph nodes consume an *external capability
layer* (memory) — but G-059's literal ask is to route the runtime's *model/tool* calls through the mounted MCP
`StructuredTool`s, which Stage 12 does NOT do (the nodes still import the Stage-4-10 models directly, for latency).
G-059 therefore stays **OPEN**, re-targeted to Stage 14 (A2A) / a runtime-MCP-routing increment.

**D5 — Infra: pgvector image on the same volume.** The episodic layer needs the `vector` extension, absent from
`postgres:15-alpine`. The Docker PG image is swapped to **`pgvector/pgvector:pg15`** (same PG-15 major → the existing
`docker_postgres-data` volume is preserved: manufacturing DB + decisions + checkpoint tables intact). docker-compose
updated. `pgaudit` is NOT bundled → DB-level audit logging is **deferred/ledgered**; the immutability triggers + the
app-level hash chain are the Art-12 evidence now.

## Why
- A regulator-grade, tamper-evident decision ledger + a real (non-fabricated) episodic/semantic memory are the
  deepest-honest Stage-12 build and the substrate for the Annex-IV pack (Stage 19) + self-improving agents — not a
  stub. SQL-not-NoSQL + namespace isolation are KB_14-locked; HNSW + direct-pgvector are research-grounded refinements.

## Consequences
- New: `backend/memory/` (5 files), migrations `0003/0004/0005`, `jobs/mem0_retention_sweep.py`, `backend/tests/
  memory/` (3 files, 13 tests), this ADR, the explainer, KB_TASK_LOG entry. Modified: `agents/runtime/{state,nodes,
  graph}.py` (memory wiring + provenance), `requirements.txt` (pgvector, sentence-transformers), `docker-compose.yml`
  (pgvector image), KB_14/KB_04/KB_01.
- Verified live (Docker `pgvector/pgvector:pg15`@5544 + Neo4j@7687): migrations applied (head `0005_mem0`, vector
  ext + immutability triggers present, data intact); Mem0 real semantic search (score 0.744) + isolation enforced;
  ISA-95 idempotent migrate (16 constraints) + hierarchy + PG mirror; audit append+verify OK; **runtime run-2 recalls
  run-1's memory + writes audit seqs**. 13 memory tests; full backend suite **221 passed / 2 skipped**; audit **364**.
- Audit holds 364 (`--no-baseline-drop`; the memory layer wraps real DB/embedder/graph, adds no grep-counted theatre
  — Rule 1a). G-059 stays OPEN (memory wired, but MCP-tool routing not done — see D4).

## Honest residual / ledger
- Real ML-DSA-65 audit-chain signing replaces the placeholder at Stage 13.5 (already structured for the drop-in).
- `pgaudit` (DB-level activity log) deferred — needs a Postgres image bundling it (G-060).
- DVC procedural-memory layer (KB_14) not built this stage — future (the loop doesn't yet load DVC skills) (G-061).
- Live verification used bge-small/384; production default is bge-large/1024 (env-driven, both real).

## References
- `backend/memory/{audit_chain,mem0_adapter,graph_isa95,letta_adapter}.py` · `backend/jobs/mem0_retention_sweep.py`
  · `backend/alembic/versions/{0003_audit_chain,0004_isa95_metadata,0005_mem0}.py` · `agents/runtime/{state,nodes,
  graph}.py` · `backend/tests/memory/*` · `scripts/verify-audit-chain.py` · `docker/docker-compose.yml`.
  KB_14/04/01. Research §19.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:31+00:00 -->
<!-- signature: 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 -->
