---
status: done
stage: 12
slug: agent_memory
created: 2026-05-18
---

# Stage 12 — Agent Memory (Mem0 + pgvector + Neo4j ISA-95 + audit_chain)

> Wire the five-layer memory architecture from KB_14. Mem0 as default episodic backend on PG + pgvector; Letta as opt-in long-horizon; Neo4j for ISA-95 Part 2 graph; DVC for procedural memory; PostgreSQL `audit_chain` (append-only, hash-chained, ML-DSA-signed at Stage 13.5) for evidence.

## Pre-requisites

- Stage 11.5 closed; MCP servers operational.
- Postgres with `pgvector` extension available.
- Neo4j container in compose stack.

## Acceptance criteria

- [ ] Alembic migration `0005_mem0.py` creates `mem0_memories` table + pgvector extension + ivfflat index (per KB_14 schema).
- [ ] Alembic migration `0002_audit_chain.py` creates `audit_chain` table + immutability triggers (UPDATE/DELETE raise).
- [ ] Alembic migration `0003_isa95_metadata.py` creates the relational mirror of Neo4j ISA-95.
- [ ] `backend/memory/mem0_adapter.py` enforces cross-namespace read rejection; test under `backend/tests/memory/test_namespace_isolation.py` proves it.
- [ ] `backend/memory/audit_chain.py` writes append-only rows with SHA-256 chained hash (signature placeholder until Stage 13.5; structure correct).
- [ ] `backend/memory/graph_isa95.py` migrates Neo4j schema idempotently on boot.
- [ ] `backend/memory/letta_adapter.py` exists, feature-flagged off by default.
- [ ] LangGraph runtime (Stage 11) writes to `audit_chain` for every decision.
- [ ] `pgaudit` extension enabled in `docker/docker-compose.yml`.
- [ ] `python scripts/verify-audit-chain.py --quick` clean.
- [ ] `pytest backend/tests/memory/ -v` green.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/memory/__init__.py` | Package marker |
| `backend/memory/mem0_adapter.py` | Mem0 wrapper with namespace isolation |
| `backend/memory/letta_adapter.py` | Letta opt-in adapter |
| `backend/memory/graph_isa95.py` | Neo4j ISA-95 schema migrator |
| `backend/memory/audit_chain.py` | Append-only hash-chained writer |
| `backend/alembic/versions/0002_audit_chain.py` | audit_chain DDL + triggers |
| `backend/alembic/versions/0003_isa95_metadata.py` | ISA-95 PG mirror |
| `backend/alembic/versions/0005_mem0.py` | mem0_memories + pgvector |
| `backend/jobs/mem0_retention_sweep.py` | Nightly purge for expired Mem0 rows |
| `backend/tests/memory/test_namespace_isolation.py` | Cross-namespace read rejection |
| `backend/tests/memory/test_audit_chain_immutable.py` | UPDATE/DELETE rejection |
| `backend/tests/memory/test_graph_isa95.py` | Idempotent migrator |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/agents/runtime/graph.py` | Write to `audit_chain` per decision; query Mem0 in observe node |
| `backend/requirements.txt` | Add `mem0`, `letta` (opt-in), `neo4j`, `pgvector` driver (e.g. `psycopg[binary,pool]`), `text-embeddings-inference` client |
| `docker/docker-compose.yml` | Enable `pgaudit`; add `text-embeddings-inference` for self-hosted embeddings |
| `knowledge-base/KB_14_Agent_Memory_Architecture.md` | Confirm schemas match |
| `knowledge-base/KB_04_Data_Schema.md` | Document new tables |

## KB files this stage updates

- `KB_14_Agent_Memory_Architecture.md`
- `KB_04_Data_Schema.md`
- `KB_01_System_Architecture.md`
- `KB_TASK_LOG.md`

## Verification commands

```bash
cd backend && alembic upgrade head
docker compose exec postgres psql -U postgres -d ai_embodied -c "SELECT to_regclass('audit_chain'), to_regclass('mem0_memories'), to_regclass('isa95_metadata');"
cd backend && pytest tests/memory/ -v
python scripts/verify-audit-chain.py --quick
```

## Audit target

- Strict decrease.

## Role

- Primary: `backend-engineer`
- Secondary: `compliance-engineer` (audit_chain semantics + retention)

## Risks / unknowns

- pgvector index choice (ivfflat vs hnsw): start ivfflat, benchmark in Stage 21.
- Neo4j schema migrations need to be idempotent + safe under concurrent agent boot.

## Hand-off

- What is now true: full five-layer memory operational; audit_chain receiving rows (signed by ML-DSA-65 placeholder until Stage 13.5 replaces with real signatures).
- Next stage (12.5) wires observability so traces show memory I/O.
