---
status: not-started
stage: 21
slug: dr_ha_backups
created: 2026-06-26
---

# Stage 21 — Disaster Recovery, HA posture & backups (free-cost, OSS/local)

> Harden the stateful tier (Postgres source-of-truth + audit_chain, Neo4j ISA-95 graph, Redis cache) with a tested
> backup→restore→verify DR path before the Stage-22 pilot. Free/OSS/local only (Rule 9): Postgres PITR (base backup +
> WAL archiving, built-in) + portable `pg_dump`; Neo4j Community **offline** `neo4j-admin database dump`; Redis RDB
> snapshot; a **restore-verification drill** (restore into a scratch DB + assert row counts + audit_chain head — "never
> trust an untested backup"); a chaos drill (kill PG, assert honest degradation + recovery); a DR runbook with measured
> RPO/RTO. Full multi-node HA + live off-site replication are honestly deferred to the pilot/cloud (Rule 9). Research §31;
> KB_10 (production hardening) + KB_15. Prior: Stage 20 (red-team evals) closed.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_21/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: (list of prior stages this depends on)
- Decision logs honoured: (list of ADRs)
- KB files at minimum version: (list)
- Gaps ledger rows pulled in (IDs): (from `audits/OPEN_GAPS_LEDGER.md`)

## Acceptance criteria

(Folded gaps: **G-066** DR/HA [primary], **G-004** chaos engineering, **G-060** pgaudit/DR, **G-027** free-cost,
CTO #3 remediation = runtime determinism regression test.)

- [x] **AC1 — Postgres backup.** `scripts/backup/backup-postgres.sh` (`pg_dump -Fc` + `pg_restore --list` integrity) + `scripts/backup/pg-basebackup.sh` (PITR anchor: base.tar.gz + pg_wal.tar.gz). WAL-archive/`archive_timeout=60` config-provided in `docker-compose.yml` (OFF by default — bad `archive_command` → full WAL disk). 3-2-1 via `BACKUP_ROOT_2` + config-only off-site. VERIFIED live.
- [x] **AC2 — Neo4j + Redis backup.** `backup-neo4j.sh` offline `neo4j-admin database dump` (`neo4j`+`system`, `--volumes-from`); `backup-redis.sh` BGSAVE→`dump.rdb`; `backup-all.sh` orchestrates + SHA-256 manifest + retention. VERIFIED live (both dumps + RDB produced).
- [x] **AC3 — Tested restore (binding).** `scripts/restore/restore-verify.sh` restores to a SCRATCH DB + asserts per-table row-count parity + `audit_chain` head parity; exits nonzero on mismatch. **PASS live (22 tables; RTO ~4 s).** Neo4j load-verify documented in the runbook.
- [x] **AC4 — Chaos drill (G-004).** `scripts/chaos/kill-postgres-drill.sh` kills PG → asserts honest degradation (probe + `verify-audit-chain.py` FAIL, no fabrication) → recovery on restart. **PASS live.**
- [x] **AC5 — DR runbook.** `compliance/dr-runbook.md` — RPO (≤60 s w/ PITR) / RTO targets, recovery steps, 3-2-1(-1-0) layout, honest single-node scope boundary.
- [x] **AC6 — Runtime determinism (CTO #3).** `backend/tests/agents/runtime/test_runtime_determinism.py` — identical trajectory + decisions across two runs. **1 passed live.**
- [x] **AC7 — CI gate `dr-backup-restore`.** Named-PG container → seed schema → backup + restore-verify; fails on mismatch. Path simulated PASS on a generic schema.
- [x] **AC8 — Tests + audit.** Determinism test passes; full suite green (333 passed/10 skipped at the progress re-check); `bash scripts/audit.sh` holds **364** (additive scripts + 1 test; `--no-baseline-drop` justified).

## Files to CREATE

| Path | Purpose |
|---|---|
| `scripts/backup/backup-all.sh` | Orchestrate pg+neo4j+redis backup + retention |
| `scripts/backup/backup-postgres.sh` | `pg_dump -Fc` + base-backup/WAL-archive config |
| `scripts/backup/backup-neo4j.sh` | Offline `neo4j-admin database dump` (Community) |
| `scripts/backup/backup-redis.sh` | BGSAVE + copy `dump.rdb` |
| `scripts/restore/restore-verify.sh` | Restore to scratch DB + assert row counts + audit_chain head |
| `scripts/chaos/kill-postgres-drill.sh` | Chaos drill: kill PG → assert honest degradation + recovery |
| `compliance/dr-runbook.md` | DR runbook: RPO/RTO, recovery steps, 3-2-1 layout, scope boundary |
| `backend/tests/agents/runtime/test_runtime_determinism.py` | CTO #3: deterministic trace+decisions for same incident+thread_id |
| `.github/workflows/` (job in `ci.yml`) | `dr-backup-restore` gate |

## Files to MODIFY

| Path | Change |
|---|---|
| `docker/docker-compose.yml` | `archive_command`/`archive_timeout` + a backups volume; `restart: unless-stopped` + healthchecks where missing |
| `.github/workflows/ci.yml` | add `dr-backup-restore` job |
| `compliance/risk-register.md` | DR/data-loss row → mitigated + tested (RPO/RTO) |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | additive infra/scripts stage |

## KB files this stage updates

(The KB-diff CI gate enforces these. Every listed file must have a non-trivial diff in the closing PR.)

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_NN_<topic>.md`

## Verification commands

```bash
# Audit baseline strictly decreases (or hold with explicit --no-baseline-drop justification)
bash scripts/audit.sh

# Tests pass
cd backend && pytest -q
cd frontend-nextjs && npm test && npm run build

# Stage-specific
```

## Audit target

- Pre-stage baseline: (capture from `.audit-baseline` at stage open)
- Target: (strictly less than pre-stage; specify expected drop and which patterns fall)

## Role

- Primary: (per CLAUDE.md §3 decision tree — `backend-engineer` / `ml-engineer` / ... )
- Secondary (hand-offs): (list)

## Risks / unknowns

(Append-only as the stage progresses. Convert resolved items to ADRs in `compliance/decision-logs/`.)

-

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-06-26T08:15:02Z)

### Suggested role (from slug heuristic)

**devops-sre** — open `.claude/skills/devops-sre/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_TASK_LOG.md`
- `knowledge-base/KB_10_Production_Hardening.md`
- `knowledge-base/KB_15_Observability_Evidence_Pipeline.md`

### Pre-requisites (from previous stage's hand-off — STAGE_20_redteam_eval.md)


- What is now true: red-team posture verified by automated eval gate; results feed Annex IV pack.
- Next stage (21) hardens DR/HA/backups before the pilot deployment runbook in Stage 22.

### CTO checkpoint remediations targeting this stage (auto-routed)

- (from CTO_3_remediation_map.json) Add a runtime determinism regression test: assert two runs of the same incident/thread_id produce identical traces + decisions, pinning the structural determinism the durable LangGraph runtime relies on (today determinism is only indirectly tested)


These items MUST appear as acceptance criteria above.

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
