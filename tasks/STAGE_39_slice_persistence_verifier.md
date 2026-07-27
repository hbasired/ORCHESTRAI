---
status: complete
stage: 39
slug: slice_persistence_verifier
created: 2026-07-19
---

# Stage 39 — Slice decision-log persistence + a non-relaxed, genuinely-rejecting Stage-6 verifier (G-045, G-051)

> Two small honest gap-closers on the Stage-6 slice runner (`backend/services/slice_runner.py`), both surfaced by the
> Stage-6 independent reviews and carried in the ledger. **G-045:** Stage-6 AC3 claimed slice decisions are "persisted
> to `decision_logs`", but the shipped provenance was in-memory `SliceTrail` + WS envelopes only — no DB writer existed.
> **G-051:** the Stage-6 VERIFY step relaxed ALL three rejecting contracts (`available_crew=n`,
> `throughput_floor_frac=0.0`, `max_concurrent_critical_offline=n`), so the plan verifier could never reject — only
> attach provenance. This stage makes both claims TRUE: an AUTOMATIC `decision_logs` writer (Art-12, with input/output
> provenance hashes) in the live path, and a BINDING `PlantState` (limited crew, 60% throughput floor, SIL redundancy
> cap) so the verifier genuinely REJECTS an unsafe plan — while the normal safe maintenance still passes (the measured
> Stage-6 A/B is preserved). Research §50; KB_18 (Art-12), KB_25 (VERIFY). Last of the post-CTO-#6 build arc before the
> consolidated handoff.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_39/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: Stage 6 (slice loop — `slice_runner.py`, `SliceTrail`, the verify seam), Stage 8 (plan_verifier), Stage 1 (the `decision_logs` table, `alembic/0001_init`).
- Decision logs honoured: `2026-06-01_stage06_slice_v0.md` (ADR D2 disclosed both relaxations), the Stage-6 depth-hardening ADR.
- Gaps ledger rows pulled in (IDs): **G-045** (slice decision persistence to `decision_logs`), **G-051** (non-relaxed Stage-6 verifier). G-027 (free-cost, ONGOING — satisfied: no new deps).

## Acceptance criteria

- [x] **AC1 — G-045: automatic `decision_logs` persistence.** `slice_runner._persist_decision_log()` writes each live-path decision to Postgres `decision_logs` (caller=`slice_runner`, tool=decision kind, `input_hash`/`output_hash` = SHA-256 of the canonical telemetry/prediction (in) and decision+verification (out), `inputs`/`outputs` JSONB, incident FK when a real UUID). Wired into the live path (`LiveSliceRunner` passes `persist_log=True`); OFF for the offline A/B (`persist_log=False`). Verified: `test_persist_writes_real_decision_log_row` (DB round-trip, real 64-char hashes), `test_persist_stores_non_uuid_incident_ref_in_inputs`.
- [x] **AC2 — G-045: honest degradation.** No DB reachable → `_persist_decision_log` returns `None` (surfaced as `decision_log_id: null`), never a fabricated id. Verified: `test_persist_is_honest_noop_without_db`.
- [x] **AC3 — G-051: a binding (non-relaxed) `PlantState`.** `_build_plant_state` now sets `throughput_floor_frac=0.6`, `max_concurrent_critical_offline=1` (SIL), and `available_crew = crew_total(2) − stages_in_maintenance` (crew contention). Verified: `test_plant_state_is_not_relaxed`, `test_available_crew_reduced_by_busy_maintenance`.
- [x] **AC4 — G-051: the verifier genuinely REJECTS.** With the binding state the slice verify gate rejects an unsafe plan — a throughput-floor breach (too many stages offline) and a critical-redundancy breach (a second critical machine). Verified: `test_verifier_rejects_when_throughput_floor_breached`, `test_verifier_rejects_second_critical_offline`.
- [x] **AC5 — G-051: no false-reject regression.** The normal safe single maintenance is still APPROVED, and the Stage-6 A/B is preserved (unplanned downtime −190.5 min, 3.67 planned maintenances still fire). Verified: `test_verifier_still_approves_safe_single_maintenance` + `run_slice_ab.py` + the existing slice suite (31 passed).
- [x] **AC6 — free-cost + audit-baseline.** No new dependencies (Rule 9). Audit holds at 3 (`--no-baseline-drop`: additive real code — a DB writer + binding constraints, no `random.*`/mock/hardcoded fabrication; a genuinely-rejecting gate is the OPPOSITE of theatre).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/tests/test_slice_persistence_verifier.py` | 8 tests: binding plant state, genuine rejection, no false-reject, DB persistence + honest no-op. |
| `research/stage-explainers/STAGE_39/index.html` | Stage explainer. |
| `compliance/decision-logs/2026-07-18_stage39_slice_persistence_verifier.md` | ADR. |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/services/slice_runner.py` | Add `_persist_decision_log` (G-045); rewrite `_build_plant_state` to bind (G-051); add `persist_log` param + wire `LiveSliceRunner`. |
| `research/initial-research.md` | §50 (Art-12 record-keeping + binding plan verification SOTA). |
| `knowledge-base/KB_18_*` / `KB_25_*` / `KB_TASK_LOG.md` | Art-12 slice persistence + the non-relaxed VERIFY. |
| `audits/OPEN_GAPS_LEDGER.md` | G-045 → RESOLVED; G-051 → fully RESOLVED (Stage-6 half). |

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
# Audit holds at 3 (additive stage, --no-baseline-drop)
bash scripts/audit.sh

# Stage-specific tests (binding plant state / genuine rejection / no false-reject / DB persistence)
cd backend && DATABASE_URL=… python -m pytest tests/test_slice_persistence_verifier.py -q      # -> 8 passed

# Regression: the existing slice + verifier suites + the A/B (measured result preserved)
cd backend && DATABASE_URL=… python -m pytest tests/test_slice_intervene.py tests/test_slice_events.py \
  tests/test_slice_ab.py tests/test_slice_predict_live.py tests/test_plan_verifier.py -q         # -> 31 passed
cd backend && python scripts/run_slice_ab.py     # unplanned downtime −190.5 min, planned maint still fire
```

## Audit target

- Pre-stage baseline: 3.
- Target: hold at 3 (`--no-baseline-drop`). Additive real code — a DB writer + binding safety constraints; no
  `random.*`/mock/hardcoded-fabrication to remove or add. A genuinely-rejecting verify gate is the OPPOSITE of theatre.
  Residual 3 = the documented `_generate_heuristic_actions` G-052 false-positive (untouched).

## Role

- Primary: `backend-engineer` (service edit, DB writer, safety-constraint wiring).
- Secondary: `agentic-governance-engineer` (Art-12 traceability, ledger, ADR).

## Risks / unknowns

- **Making the verifier bind could false-reject the normal Stage-6 maintenance and change the measured A/B.** Guarded:
  a no-false-reject test AND a full A/B re-run (unplanned downtime −190.5 min, 3.67 planned maintenances still fire —
  consistent with the original Stage-6 result). The binding values are conservative (crew 2, floor 0.6, SIL cap 1) so
  the normal single-machine case always passes. **RESOLVED.**
- Persistence writes one `decision_logs` row per live intervention. It is best-effort + honest-degrading (no DB → no-op)
  and OFF for the offline A/B, so it adds no load to the experiments and never blocks the live loop.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - **G-045 RESOLVED** — live slice decisions are AUTOMATICALLY persisted to Postgres `decision_logs` with SHA-256
    input/output provenance hashes (Art-12); the Stage-6 "persisted to decision_logs" claim is now TRUE (was in-memory
    only). Honest no-op without a DB.
  - **G-051 fully RESOLVED (Stage-6 half)** — the Stage-6 VERIFY step is no longer a no-op: `_build_plant_state` binds
    (limited crew / 60% throughput floor / SIL redundancy cap), so the plan verifier genuinely REJECTS an unsafe slice
    plan (proven) while the safe case still passes and the A/B is preserved.
  - No new deps; audit holds 3; 8 new tests + 31 regression pass.
- What the next stage starts with:
  - **The consolidated handoff summary (option 1)** — the post-CTO-#6 free/local build arc (37 bidirectional CDC →
    38 facilities/energy → 39 gap-closers) is COMPLETE. Produce a state-of-system + pilot-readiness + real-world-path
    summary declaring the disciplined build complete; the highest-leverage remaining move is a real pilot (buyer-blocked).
- Open items deferred to a future stage (name the stage if known):
  - None new. The standing real-world items (pilot G-035/G-043, cert G-011, scale G-066) remain buyer/accredited-body-blocked.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-19T14:20:01Z)

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

### Pre-requisites (from previous stage's hand-off — STAGE_38_facilities_energy_agent.md)


- What is now true that wasn't before this stage:
  - **G-018 is RESOLVED — the KB_25 loop now runs in a new embodiment domain (Facilities/Energy).** A Facilities/Energy
    head-agent (`backend/agents/facilities/`) observes the sim's REAL per-stage `nominal_kw`, diagnoses a demand-charge
    breach, and runs a REAL MILP (scipy/HiGHS) peak-shaving/load-shifting optimisation against a documented ToU +
    demand-charge tariff, validator-gated (`energy_load_shift` contract, Hard Rule 3) and audit-signed (Art-12).
  - New surface `POST /facilities/optimize-energy`; new signed audit event `energy.load_shift`.
  - Measured (SimWorld): peak −22.1% mean (max 58.9%), cost −7.6% mean (max 18.8%), all production floors held; a
    live cycle diagnosed `demand_charge_breach` and signed a real audit row. 15 tests pass; audit holds 3; no new deps.
- What the next stage starts with:
  - **Stage 39 — small honest gap-closers**: G-045 (persist slice decisions to Postgres `decision_logs` — Stage-6 said
    "persisted" but shipped in-memory `SliceTrail`) + G-051 (supply a non-relaxed `PlantState` so the Stage-6 verifier
    can actually REJECT, not a no-op). Then the consolidated handoff summary (option 1).
- Open items deferred to a future stage (name the stage if known):
  - Real-utility tariff + metered-load validation, and wiring the energy optimiser into the live sim tick loop (vs the
    day-ahead planning surface built here) → a pilot (G-035, buyer-blocked). Recorded, not overclaimed.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
