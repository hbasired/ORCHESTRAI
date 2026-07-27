---
status: complete
stage: 37
slug: bidirectional_cdc_self_optimize
created: 2026-07-18
---

# Stage 37 — Bidirectional CDC → diagnose induced problem → self-optimize (G-024)

> The Stage-13 CDC is one-directional: an `incidents` INSERT or a `stages.status` change maps to a **pre-formed** inject.
> Stage 37 closes the loop the OTHER way (the operator's original product vision, ledger **G-024**): an operator EDITS an
> arbitrary operational VALUE in Postgres (a stage's `defect_rate`/`throughput`/`energy`/`utilization`, an inventory level,
> a supplier's reliability/lead-time) → a new value-change DB trigger emits the diff → the backend **REASONS about the
> induced problem** (root-cause diagnosis, NOT a canned incident) → the diagnosed problem enters the SAME validator-gated
> self-healing loop (KB_25 predict→diagnose→verify→intervene) → the system self-optimizes. This is the ARGUS-style
> closed-loop pattern (research §48.1). Hard Rule 3 is preserved end-to-end: the reasoner PROPOSES; the sole actuator
> emitter stays `master.dispatch_order` behind `safety/validator.py`. Builds directly on Stage-13
> (`ingestion/cdc_listener.py`, `cdc_emit` trigger, `change_to_inject`) + the runtime `run_incident`.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_37/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: Stage 13 (CDC ingestion — `cdc_outbox` + `cdc_emit` trigger + listener), Stage 29 (active diagnosis + the `/factory/*` conversational surface), Stage 11 (LangGraph `run_incident` self-healing loop), Stage 17 (safety validator — Hard Rule 3 seam).
- Decision logs honoured: `2026-06-15_stage13_cdc_ingestion.md` (transactional outbox + NOTIFY + drain), `2026-07-12_stage29_conversational_factory_intelligence.md` (validator-gated NL inject).
- Gaps ledger rows pulled in (IDs): **G-024** (this stage's target — bidirectional CDC-triggers-problem); G-027 (free-cost, ONGOING — satisfied: no new deps, reasoner is pure-Python + optional Groq/Ollama).

## Acceptance criteria

- [x] **AC1 — value-change DB trigger.** A migration (`0010_cdc_value_changes`) adds a `cdc_emit_value()` plpgsql function + `AFTER UPDATE OF <value columns>` triggers on `stages` (defect_rate/throughput/energy_consumption_kw/utilization), `inventory` (current_stock/days_of_supply), `suppliers` (reliability_score/lead_time_days) that emit `{table, column, old, new, target_id}` into `cdc_outbox` + `pg_notify('cdc_events', …)`. Verified: a real `UPDATE stages SET defect_rate=0.15` writes an outbox row (`test_db_value_edit_drains_into_simworld`).
- [x] **AC2 — root-cause reasoner (pure, unit-testable).** `ingestion/cdc_reasoner.py::diagnose_change()` maps a value edit → a root-cause-labelled `InducedProblem` (defect_surge / machine_crack / power_dip / late_delivery) with severity **DERIVED from the edit magnitude** (not a synthetic constant), or `None` for a benign edit. Documented domain thresholds; no fabrication. 19 rule tests.
- [x] **AC3 — listener routes value edits.** `cdc_listener.change_to_inject` checks the value-edit branch FIRST (a `column` key) so value rows are diagnosed instead of being swallowed by the status branch; the Stage-13 status/incident paths still work (regression test).
- [x] **AC4 — closed loop + Art-12 audit.** `process_value_edit()` diagnoses → signs the reasoning to `audit_chain` ("cdc.diagnose") → optionally drives `run_incident` (the validator-gated loop). Benign edits return `diagnosed=False` and do NOT run the loop (honest).
- [x] **AC5 — API surface.** `POST /factory/db-edit` calls `process_value_edit` (off the event loop via `to_thread`). Route tests: defect_surge diagnosed, benign honest, inventory needs reorder context.
- [x] **AC6 — Hard Rule 3 preserved.** The reasoner never actuates; the diagnosed problem enters the same validator-gated loop; the sole `actuator.*` emitter remains `master.dispatch_order`. Asserted in the route note + reasoner docstring; no new actuator emitter added (grep-verified in independent review).
- [x] **AC7 — free-cost + audit-baseline.** No new dependencies (Rule 9). Audit holds at 3 (`--no-baseline-drop`: additive real code; the reasoner uses documented thresholds + real magnitudes, no `random.*`/mock).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/ingestion/cdc_reasoner.py` | The G-024 root-cause reasoner: `diagnose_change()` (pure) + `process_value_edit()` (closed loop + audit). |
| `backend/alembic/versions/0010_cdc_value_changes.py` | `cdc_emit_value()` plpgsql + value-column UPDATE triggers on stages/inventory/suppliers. |
| `backend/tests/ingestion/test_cdc_reasoner.py` | 22 tests: reasoner rules + listener routing + closed loop + live DB roundtrip. |
| `research/stage-explainers/STAGE_37/index.html` | Stage explainer. |
| `compliance/decision-logs/2026-07-18_stage37_bidirectional_cdc_self_optimize.md` | ADR. |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/ingestion/cdc_listener.py` | `change_to_inject` gains a value-edit branch (checked FIRST) that routes to `cdc_reasoner.diagnose_change`. |
| `backend/api/conversation_routes.py` | Add `POST /factory/db-edit` → `process_value_edit`. |
| `backend/tests/conversation/test_conversation_routes.py` | 3 route tests for `/factory/db-edit`. |
| `research/initial-research.md` | §48 (SOTA: ARGUS closed-loop, AIOps-2026). |
| `knowledge-base/KB_05_*` / `KB_07_API_Contracts.md` / `KB_TASK_LOG.md` | CDC bidirectional loop + new endpoint. |
| `audits/OPEN_GAPS_LEDGER.md` | G-024 → RESOLVED. |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | Additive stage. |

## KB files this stage updates

(The KB-diff CI gate enforces these. Every listed file must have a non-trivial diff in the closing PR.)

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_NN_<topic>.md`

## Verification commands

```bash
# Audit baseline holds at 3 (additive stage, --no-baseline-drop)
bash scripts/audit.sh

# Migration applies + is reversible
cd backend && DATABASE_URL=… python -m alembic upgrade head
DATABASE_URL=… python -m alembic downgrade -1 && DATABASE_URL=… python -m alembic upgrade head

# Stage-specific tests (reasoner rules + listener routing + closed loop + live DB roundtrip + routes)
cd backend && DATABASE_URL=… python -m pytest tests/ingestion tests/conversation -q
# -> 64 passed

# Audit chain still green
python scripts/verify-audit-chain.py   # -> exit 0
```

## Audit target

- Pre-stage baseline: 3.
- Target: hold at 3 (`--no-baseline-drop`). This is an additive, honest subsystem — the reasoner uses documented
  domain thresholds and real edit magnitudes; there is no `random.*`/mock/hardcoded-fabrication to remove.

## Role

- Primary: `backend-engineer` (FastAPI route, Alembic migration, ingestion service).
- Secondary: `agentic-governance-engineer` (KB_25 loop alignment, ledger, ADR).

## Risks / unknowns

- The value-edit branch must precede the table-specific status/incident branches in `change_to_inject` (both are keyed
  on `table == "stages"`); getting this wrong silently swallows value edits. Caught during live testing, fixed, and
  pinned by a regression test (`test_status_change_still_works_after_value_branch`). **RESOLVED.**
- Honest scope: the reasoner encodes documented domain thresholds (the same signals the sim health model uses); it is a
  DIAGNOSTIC rule engine, not a learned causal model — deeper learned causal discovery over real edit-outcome traces is
  a pilot-data item (G-035, buyer-blocked). Recorded honestly, not overclaimed.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - **G-024 is RESOLVED — the CDC loop is now BIDIRECTIONAL.** An operator's edit of an operational VALUE in Postgres
    (stage defect_rate/throughput/energy/utilization, inventory level, supplier reliability/lead-time) fires a
    value-change trigger → `cdc_reasoner.diagnose_change` DIAGNOSES the induced root-cause problem → the diagnosed
    incident enters the same validator-gated self-healing loop (`run_incident`). Verified live: a real
    `UPDATE stages SET defect_rate=0.15` drains into the SimWorld as a diagnosed `defect_surge/critical`.
  - New surface `POST /factory/db-edit` (diagnose + optional self-optimize); the reasoning is signed to `audit_chain`
    ("cdc.diagnose"), Art-12.
  - Hard Rule 3 held end-to-end (reasoner proposes; `master.dispatch_order` remains the sole actuator emitter).
  - Migration `0010_cdc_value_changes` applied + proven reversible; audit chain green (10,477 rows); 64 CDC+conversation
    tests pass; audit holds 3; no new dependencies.
- What the next stage starts with:
  - **Stage 38 — a new head-agent domain** (extend the KB_25 predict→diagnose→verify→intervene loop to a new embodiment
    domain — Facilities/Energy G-018 preferred, since the sim already emits real per-stage energy signals, or
    Workforce-Safety G-017). Same pattern as supply-chain in Stage 26.
- Open items deferred to a future stage (name the stage if known):
  - Learned causal discovery over real edit→outcome traces (deeper than the current documented-threshold diagnostic
    engine) needs pilot data → G-035 (buyer-blocked). Recorded honestly, not overclaimed.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-18T14:10:04Z)

### Suggested role (from slug heuristic)

**backend-engineer** — open `.claude/skills/backend-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_TASK_LOG.md`
- `knowledge-base/KB_01_System_Architecture.md`
- `knowledge-base/KB_04_Data_Schema.md`
- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_07_API_Contracts.md`
- `knowledge-base/KB_14_Agent_Memory_Architecture.md`
- `knowledge-base/KB_15_Observability_Evidence_Pipeline.md`
- `knowledge-base/KB_16_A2A_MCP_Protocols.md`

### Pre-requisites (from previous stage's hand-off — STAGE_36_dependency_refresh.md)


- What is now true that wasn't before this stage:
  - C6-R2 is honestly resolved as far as is safe free/local: attempted (dry-run), proven a cascading stack-breaking
    migration, and documented with hard evidence + a de-risked plan. The working env is unchanged; nothing faked.
  - **All routed CTO-#6 in-house items are now addressed (C6-R1 G-075 ✓ Stage 33, C6-R3 hook ✓ Stage 33, C6-R4 ✓
    Stage 33, C6-R5 ✓ Stage 34, C6-R3-tail ✓ Stage 35, C6-R2 assessed ✓ Stage 36).**
- What the next stage starts with:
  - Only real-world engagement remains (pilot G-035/G-043, cert G-011, scale G-066 — buyer/accredited-body-blocked) OR
    the actual dep-refresh migration when a dedicated branch/staging + CI exists.
- Open items deferred to a future stage:
  - The dep-refresh migration itself (G-055/G-056/G-070) → a dedicated branch/CI increment per the plan; G-065 hygiene.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
