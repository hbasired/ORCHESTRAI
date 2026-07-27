---
name: Agent Memory Architecture
description: Working/episodic/semantic/procedural/audit memory layers — Mem0 + pgvector + Neo4j ISA-95 + append-only audit_chain. SQL not NoSQL.
type: spec
last-updated: 2026-05-18
---

# KB_14 — Agent Memory Architecture

## Purpose

Define the five memory layers of the agent runtime, the backends behind each, the namespacing rules, the retention policy, and the (locked) SQL-not-NoSQL choice.

## Source of truth

- Mem0 docs + AWS Bedrock AgentCore exclusivity announcement.
- Letta (MemGPT) docs.
- LangGraph checkpointer docs (`langgraph.checkpoint.postgres`).
- ISA-95 Part 2 information model (IEC 62264-2).
- This file is the contract for `backend/memory/`.

## Body

### The five layers

| Layer | Lifespan | Backend | Why this choice |
|---|---|---|---|
| Working | per-task (<8 k tokens) | LangGraph `AgentState` (Pydantic, frozen) + `langgraph.checkpoint.postgres.PostgresSaver` | In-process by design; checkpointed for HITL interrupt resume |
| Episodic (default) | per-shift, per-incident | **Mem0** on PostgreSQL + pgvector | Smallest token footprint (~1.7k/conversation vs Zep ~600k); AWS Bedrock AgentCore exclusive provider |
| Episodic (opt-in, per-pilot) | shift-persistent, multi-day | **Letta** (MemGPT) | Better long-horizon coherence; reserve for customers who need shift-persistent identity |
| Semantic | persistent | pgvector (`namespace=semantic:*`) + **Neo4j 5** for ISA-95 Part 2 graph | Vector for free-text; graph non-negotiable for equipment hierarchy queries |
| Procedural | versioned | DVC-tracked `data/skills/<name>/skill.yaml` | Reuses existing DVC pipeline; reproducible recipes |
| Audit | append-only, indefinite | PostgreSQL `audit_chain` (immutable + ML-DSA-65 signed) + `pgaudit` extension | Regulator-grade. Auditors know SQL. |

### SQL vs NoSQL — locked SQL

The user asked. Verdict: **SQL** (PostgreSQL) for everything except the graph layer.

1. EU AI Act conformity assessors, ISO/IEC 42001 internal audit, SOC 2 reviewers all know how to query PostgreSQL — none of them want to learn Mongo / Cassandra / DynamoDB.
2. PostgreSQL + pgvector handles relational schema AND vector embeddings without a second datastore.
3. `pgaudit` + immutability triggers on `audit_chain` give the legal-grade evidence Art. 12 requires.
4. Mem0 backs naturally onto PG + pgvector (no second operational story).
5. Neo4j is the one exception — graph queries on ISA-95 hierarchy are genuinely better in Cypher than recursive SQL.

### Mem0 schema (Alembic `0005_mem0.py`)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE mem0_memories (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  namespace       text NOT NULL,
  content         text NOT NULL,
  embedding       vector(1024) NOT NULL,
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  retained_until  timestamptz
);

CREATE INDEX mem0_memories_ns  ON mem0_memories (namespace);
CREATE INDEX mem0_memories_vec ON mem0_memories
  USING hnsw (embedding vector_cosine_ops);   -- HNSW, not ivfflat (Stage 12; research §19.2)
```

> **Stage-12 implementation note (2026-06-15).** Index is **HNSW** (`vector_cosine_ops`), not the ivfflat shown in
> the original draft: the store is insert-as-you-go (a memory per incident/decision), and HNSW handles incremental
> inserts + needs no training step + has higher recall, whereas ivfflat must train its `lists` on existing data and
> degrades under inserts (research §19.2; pgvector docs). The embedding dimension is **env-configurable**
> (`MEM0_EMBED_DIM`, default 1024) so the `vector(dim)` column matches the active embedder; migration `0005_mem0`
> reads it. Implemented as a **direct pgvector store** on this schema (`backend/memory/mem0_adapter.py`), NOT the
> `mem0ai` library (research §19.1: that library needs an LLM for fact-extraction + imposes its own schema, which
> conflicts with this contract + the offline/free constraint). The chain is `0003_audit_chain → 0004_isa95_metadata
> → 0005_mem0` (the draft's "0002/0003/0005" names predate Stage 11's `0002_langgraph_checkpoints`).

Embedding dim 1024 — `BAAI/bge-large-en-v1.5` self-hosted via **sentence-transformers** (Apache 2.0, runs on the
project's torch, CPU). No paid embedding API. (A smaller real model, e.g. `BAAI/bge-small-en-v1.5`/384-dim, is
selectable for resource-constrained / CI runs; the dim is env-driven so the column matches.)

### Namespacing rules

Namespaces (string column):
- `agent:<role>` — agent-level (rare; mostly for system prompts learned across incidents).
- `incident:<incident_id>` — default for run-time decisions.
- `operator:<operator_id>` — operator preferences and overrides.
- `semantic:<topic>` — knowledge base content (SOPs, equipment specs).
- `procedural:<skill_name>` — learned skills (separately also DVC-versioned).

Cross-namespace reads are **forbidden** in `backend/memory/mem0_adapter.py`. Any callsite asking for memories with a different namespace than the current incident context raises `CrossNamespaceAccessError`. Tests under `backend/tests/memory/test_namespace_isolation.py` enforce this — NIST RMF Agentic mitigation against cross-tenant memory leakage.

### Retention policy

- `retained_until` column on every Mem0 row.
- Default retention by namespace:
  - `incident:*` — 6 months minimum (EU AI Act Art. 12 alignment), 12 months default.
  - `operator:*` — until operator account closure + 30 days (GDPR Art. 17 alignment).
  - `semantic:*` — indefinite.
  - `procedural:*` — indefinite (versioned in DVC).
- Sweep job (`backend/jobs/mem0_retention_sweep.py`) runs nightly; purges rows where `retained_until < now()`. Tracked in `audit_chain` as `action=memory_purge` with row count.

### Neo4j ISA-95 schema

Node labels (one per ISA-95 Part 2 object class):

- `Enterprise`, `Site`, `Area`, `WorkCenter`, `WorkUnit`
- `EquipmentClass`, `Equipment`
- `MaterialClass`, `MaterialLot`, `MaterialSublot`
- `ProcessSegment`, `OperationsDefinition`, `OperationsRequest`, `OperationsResponse`
- `Personnel`, `PersonnelClass`

Relationships:

- `HAS_SITE`, `HAS_AREA`, `HAS_WORK_CENTER`, `HAS_WORK_UNIT`
- `CONTAINS` (Equipment hierarchy)
- `INSTANCE_OF` (Equipment → EquipmentClass)
- `CONSUMES`, `PRODUCES` (ProcessSegment → MaterialClass)
- `PERFORMED_BY` (ProcessSegment → EquipmentClass / PersonnelClass)
- `PART_OF_SEGMENT` (OperationsRequest → ProcessSegment)

Migrator: `backend/memory/graph_isa95.py:run_migrations()` idempotent on boot. Relational mirror: `isa95_metadata` PostgreSQL table (Alembic `0003_isa95_metadata.py`) for SQL joins that need it.

### Procedural memory (DVC-versioned)

Each "skill" is a directory under `data/skills/<name>/`:

```
data/skills/expedite_supplier_order/
  skill.yaml         # name, version, inputs, outputs, preconditions, postconditions
  prompt.md          # the system prompt for the LLM planning step
  examples.jsonl     # few-shot examples
  weights/           # optional, fine-tuned weights if applicable
```

DVC tracks the directory; the LangGraph `procedural_memory` node loads skills by name and version. Stage advancement bumps DVC versions.

### Audit chain — append-only hash-chained

Alembic `0002_audit_chain.py`:

```sql
CREATE TABLE audit_chain (
  seq          bigserial PRIMARY KEY,
  ts           timestamptz NOT NULL DEFAULT now(),
  actor        text NOT NULL,        -- e.g. "agent:embodied", "operator:abc123"
  action       text NOT NULL,        -- e.g. "decision.accept", "policy.override", "memory.purge"
  payload      jsonb NOT NULL,       -- the action's structured payload
  prev_hash    bytea NOT NULL,
  hash         bytea NOT NULL,       -- SHA-256(prev_hash || canonical(payload))
  sig_mldsa    bytea NOT NULL,       -- ML-DSA-65 signature over hash
  key_version  int NOT NULL,
  algorithm    text NOT NULL DEFAULT 'ML-DSA-65'
);

CREATE UNIQUE INDEX audit_chain_seq_uniq ON audit_chain (seq);

CREATE OR REPLACE FUNCTION audit_chain_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_chain is append-only';
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER no_update BEFORE UPDATE ON audit_chain
  FOR EACH ROW EXECUTE FUNCTION audit_chain_immutable();
CREATE TRIGGER no_delete BEFORE DELETE ON audit_chain
  FOR EACH ROW EXECUTE FUNCTION audit_chain_immutable();
```

API: `backend/memory/audit_chain.py` exposes:

- `append(actor: str, action: str, payload: dict) -> int` (returns seq) — signs with ML-DSA-65 via `backend/crypto/pqc_signing.py`.
- `verify_range(start_seq: int = 1, end_seq: int | None = None) -> Report` — used by `scripts/verify-audit-chain.py`.

`pgaudit` extension is enabled in `docker/docker-compose.yml` so DB-level activity is also logged independently of the application.

### How the layers compose during a decision

Example: an incident triggers a planning cycle.

1. **Working:** LangGraph creates a fresh `AgentState`; embeds the incident envelope.
2. **Episodic (Mem0):** queries `incident:<id>` namespace for prior events on this incident; also `operator:<id>` for the active operator's preferences.
3. **Semantic:** pgvector lookup over `semantic:*` for related SOPs; Neo4j Cypher query for affected equipment hierarchy.
4. **Procedural:** loads named skill (e.g., `expedite_supplier_order`) from DVC-pinned version.
5. **Planning:** LLM produces a plan.
6. **Safety:** `backend/safety/validator.py` gates each actuator-bound step.
7. **Audit:** EACH step writes to `audit_chain` with `actor`, `action`, `payload`. The chain row is the EU AI Act Art. 12 evidence.
8. **Mem0 write:** the final decision (and operator override, if any) writes to `incident:<id>` for future retrieval.

### What this design refuses to do

- **No NoSQL primary store.** See SQL-vs-NoSQL section above.
- **No cross-namespace Mem0 reads.** Enforced by `mem0_adapter.py`.
- **No mutable audit memory.** `audit_chain` is append-only; corrections are new rows referencing the corrected seq via payload.
- **No memory writes from the LLM directly.** All writes go through `backend/memory/*.py` adapters, which validate, namespace-check, and log to `audit_chain`.

## Last verified

2026-06-15 (Stage 12): the memory layer is **BUILT + verified live**. `backend/memory/`: `audit_chain.py`
(append-only SHA-256 hash chain + placeholder sig + `verify_range`), `mem0_adapter.py` (pgvector HNSW +
`CrossNamespaceAccessError` + retention), `graph_isa95.py` (idempotent Neo4j ISA-95 migrator + PG mirror),
`letta_adapter.py` (opt-in, flagged off). Migrations `0003_audit_chain` / `0004_isa95_metadata` / `0005_mem0`
applied to the Docker PG (image swapped to `pgvector/pgvector:pg15`, data preserved). The LangGraph runtime writes
`audit_chain` per decision + recalls/remembers via Mem0 (`observe`/`log` nodes — verified: run-2 recalled run-1's
memory; audit seqs written; graph now consumes the memory layer — partially addresses G-059, but its literal
MCP-tool routing stays OPEN). 13 memory tests pass; full backend suite 221 passed / 2 skipped; audit
364. **Stage 13.5 (2026-06-15): the placeholder is REPLACED — `audit_chain` rows are now signed with real FIPS-204
ML-DSA-65** (key_version≥1, algorithm `ML-DSA-65`) via `backend/crypto/pqc_signing.py` → the `KeyProvider` (software
tier = `dilithium-py`; HSM/Vault by config). NEW-row ML-DSA-65 signatures are cryptographically verified by
`test_audit_chain_row_is_mldsa_signed_end_to_end`; **NOTE (CTO #3, G-073):** the `verify-audit-chain.py` script today
attests the SHA-256 hash-CHAIN linkage (its per-row signature verify is not yet fail-closed, and 79 legacy rows are
pre-PQC placeholder-sha256) — making the script's signature verify load-bearing + back-signing the legacy rows is
Stage 19. `pgaudit` deferred (image lacks it; the immutability triggers + app chain are the Art-12 evidence).
ADRs `2026-06-15_stage12_agent_memory.md` + `2026-06-15_stage13_5_pqc_foundations.md`.

**Stage 15 (2026-06-20): the Neo4j ISA-95 graph is now POPULATED from live OT telemetry** —
`graph_isa95.populate_from_ot_event(source, equipment_id, name, telemetry, work_center_id=…)` MERGEs Equipment nodes
(under a WorkCenter) from inbound **OPC UA** datachanges + **Sparkplug B** DBIRTH/DDATA (idempotent; honest-unavailable
without Neo4j). Verified over a real Neo4j (`tests/integrations/test_isa95_population.py`). The formal different-agent
independent review of Stage 12 owed as **G-062** was also run at Stage 15 (`audits/STAGE_12_independent_review.md`).

Prior: 2026-05-18, agentic-governance-engineer + backend-engineer review (contract only; no code existed yet).

## Stage 28 — GraphRAG semantic-retrieval path (2026-07-04)

`backend/knowledge_graph/graphrag.py` adds a lean VectorCypher-style GraphRAG retriever (research §39.1): bge-small
semantic match over an SOP corpus (`sop_corpus/*.md`) + a 1-2-hop ISA-95 graph neighbourhood, returning grounded
context with EXPLICIT citations (SOP doc-ids + Neo4j node/edge ids). Honest-empty on off-topic (bge threshold 0.6).
Wired into the runtime `explain` node → the Art-12 `record_decision_trace` snapshot carries the grounding, so the
signed audit trail records WHAT grounded each explanation — the trust/explainability moat. Eval (grounded-answer 1.0,
honest-empty 1.0, citation-precision 1.0 at SOP/SimWorld scale). This is the SEMANTIC retrieval layer atop the
Mem0/pgvector (episodic) + Neo4j ISA-95 (structural) memory.

## Stage 35 — Multi-turn dialogue memory (conversational layer, 2026-07-18, CTO-#6 C6-R3 tail)

`backend/conversation/session_store.py` adds a DURABLE (Postgres `conversation_turns`) **sliding-window** dialogue
memory keyed by `session_id` (research §46) — the conversational counterpart of the other memory layers, distinct
from Mem0 (per-incident episodic) and GraphRAG (semantic). The `/factory/ask` + `/factory/inject` endpoints take an
optional `session_id`: the last N turns are loaded as DIALOGUE HISTORY and passed to the LLM for **phrasing +
coreference resolution** ("welding cell 3 is overheating" → "it is getting worse" → still target 3, verified live).
**The Stage-29 grounding/Verifier invariant is strictly preserved:** history helps phrasing/coreference but is NEVER
evidence — each answer's evidence is gathered per-current-question, honest-empty still fires, prior turns are never
cited. Honest-degrading (no DB → single-turn no-op, never fabricates history). Sliding window over summarization
(§46.1: over-summarization risk); summarization for 20+-turn sessions deferred. No new deps. ADR
`2026-07-13_stage35_multi_turn_dialogue_memory.md`.
