---
status: complete
stage: 38
slug: facilities_energy_agent
created: 2026-07-18
---

# Stage 38 — Facilities / Energy head-agent: KB_25 loop for industrial energy management (G-018)

> A NEW embodiment domain for the KB_25 predict→diagnose→verify→intervene loop (ledger **G-018**), the same
> "new head-agent domain" pattern Stage 26 used for supply-chain. The sim already carries a REAL per-stage energy
> model (`simulation/calibration.py::StageCalibration.nominal_kw` — intake 2.0 → machining 22.0 kW; the live
> `manufacturing_agent` reports `energy_consumption = nominal_kw when running`), so this extends real signals, not
> fabricated ones. The agent observes the facility's per-stage kW → PREDICTs the naive demand curve → DIAGNOSEs an
> approaching demand-charge breach → REASONs via a **real MILP** (`scipy.optimize.milp`/HiGHS) that does peak-shaving +
> load-shifting against a documented ToU + demand-charge tariff → VERIFYs the load-shift through `safety/validator.py`
> under a code-defined `energy_load_shift` contract (Hard Rule 3 — the agent proposes; `master.dispatch_order` stays the
> sole actuator emitter) → INTERVENEs by emitting the gated plan + a signed `audit_chain` row (Art-12). Research §49;
> KB_25 (loop), KB_17 (contract DSL). Follows the Stage-37 hand-off (post-CTO-#6 free/local arc: 37→38→39→handoff).

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_38/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: Stage 26 (supply-chain — the "new head-agent domain" pattern: signals/roles/consensus/orchestrator + inline contract + validator gate + audit), Stage 17 (safety validator + contract DSL — the Hard Rule 3 seam), Stage 12 (audit_chain).
- Decision logs honoured: `2026-07-03_stage26_supply_chain_automation.md` (new-domain pattern), `2026-06-21_stage17_functional_safety_wrapper.md` (contract DSL / Hard Rule 3).
- Gaps ledger rows pulled in (IDs): **G-018** (this stage's target — Facilities/Building-energy embodiment domain); G-027 (free-cost, ONGOING — satisfied: scipy already installed, no new deps).

## Acceptance criteria

- [x] **AC1 — real energy signals, no fabrication.** `agents/facilities/signals.py::observe_from_calibration` reads the sim's REAL per-stage `nominal_kw` (intake 2.0 / weld 18.0 / machining 22.0 …) into a schedulable-load view + a documented, explicitly-labelled HVAC/lighting baseline (`BASE_LOAD_FRACTION=0.20`). Verified: `test_observe_uses_real_nominal_kw`.
- [x] **AC2 — documented ToU + demand-charge tariff.** `agents/facilities/tariff.py::Tariff` — on/mid/off-peak $/kWh + a $/kW-day demand charge (representative published-structure numbers, labelled; the optimiser is tariff-agnostic). `bill()` computes the true energy + demand cost. Verified: `test_tariff_periods_and_prices`, `test_tariff_bill_energy_plus_demand`.
- [x] **AC3 — a REAL MILP optimiser (depth, Hard Rule 11).** `agents/facilities/optimizer.py::optimize_energy` minimises `Σ(kW·h·ToU_price) + demand_charge·peak` via `scipy.optimize.milp` (HiGHS), subject to the production floor (`Σ_t x[j,t] = required_slots[j]`) + per-load windows + `peak ≥` every slot's aggregate. Genuine optimisation, deterministic, with an honest labelled greedy fallback. Verified: `test_milp_reduces_peak_and_holds_production_floor`, `test_milp_is_deterministic`, `test_greedy_fallback_is_labelled_and_valid`.
- [x] **AC4 — honest 0% when unshiftable.** A fully-constrained facility (window == required hours) returns 0% reduction, never a fabricated saving. Verified: `test_unshiftable_facility_returns_zero_reduction_not_fabricated`; and the A/B sweep records `min` peak-reduction 0.0%.
- [x] **AC5 — KB_25 loop + validator gate (Hard Rule 3).** `agents/facilities/orchestrator.py::EnergyOrchestrator.run_cycle` runs observe→predict→diagnose(demand_charge_breach)→optimise→VERIFY via `safety/validator.validate()` under the code-defined `energy_load_shift` contract→INTERVENE(signed audit row). The agent adds NO actuator emitter (sole emitter stays `master.dispatch_order`). Verified: `test_cycle_diagnoses_demand_breach_and_gate_allows`, `test_contract_rejects_a_peak_increasing_plan`, `test_contract_rejects_dropped_production`, `test_hard_rule_3_no_actuator_emitter_in_facilities`.
- [x] **AC6 — measured A/B (honest).** `scripts/run_energy_ab.py` → `training/evals/results/energy_ab.json`: MILP vs naive-baseline over a parametric scenario sweep. **peak −22.1% mean (max 58.9%), cost −7.6% mean (max 18.8%), all production floors held**; labelled a SimWorld study (real-utility validation → G-035). Verified: `test_ab_artifact_is_honest_and_floors_hold`.
- [x] **AC7 — API surface + audit signing.** `POST /facilities/optimize-energy` (`api/facilities_routes.py`, registered in `main.py`) returns the gated plan; the reasoning is signed to `audit_chain` (`energy.load_shift`, Art-12). Verified: `test_route_optimize_energy`, `test_cycle_signs_audit_row` (DB-gated, live audit_seq).
- [x] **AC8 — free-cost + audit-baseline.** No new dependencies (scipy present, Rule 9). Audit holds at 3 (`--no-baseline-drop`: additive real code — a MILP + documented thresholds, no `random.*`/mock/hardcoded fabrication).

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/agents/facilities/__init__.py` | Package exports. |
| `backend/agents/facilities/tariff.py` | Documented ToU + demand-charge tariff + `bill()`. |
| `backend/agents/facilities/signals.py` | Facility energy observation from the sim's real per-stage `nominal_kw`. |
| `backend/agents/facilities/optimizer.py` | The MILP peak-shaving/load-shifting optimiser (scipy/HiGHS) + baseline + greedy fallback. |
| `backend/agents/facilities/orchestrator.py` | The KB_25 loop head-agent + `energy_load_shift` contract + validator gate + audit. |
| `backend/api/facilities_routes.py` | `POST /facilities/optimize-energy`. |
| `backend/scripts/run_energy_ab.py` | The deterministic A/B sweep → `training/evals/results/energy_ab.json`. |
| `backend/tests/facilities/test_facilities.py` | 15 tests (tariff/optimizer/orchestrator/gate/AB/route). |
| `research/stage-explainers/STAGE_38/index.html` | Stage explainer. |
| `compliance/decision-logs/2026-07-18_stage38_facilities_energy_agent.md` | ADR. |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/main.py` | Register `facilities_router`. |
| `research/initial-research.md` | §49 (energy-management SOTA). |
| `knowledge-base/KB_25_*` / `KB_07_API_Contracts.md` / `KB_TASK_LOG.md` | New energy domain + endpoint. |
| `audits/OPEN_GAPS_LEDGER.md` | G-018 → RESOLVED. |

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

# Stage-specific tests (tariff / MILP optimiser / orchestrator gate / A/B / route)
cd backend && DATABASE_URL=… python -m pytest tests/facilities -q          # -> 15 passed

# Regenerate + inspect the A/B artefact
cd backend && python scripts/run_energy_ab.py --out training/evals/results/energy_ab.json

# Live orchestrator cycle (real audit signing)
cd backend && DATABASE_URL=… python -c "from agents.facilities.orchestrator import EnergyOrchestrator; \
  print(EnergyOrchestrator(demand_cap_kw=100.0).run_cycle().to_dict())"

# Audit chain still green
python scripts/verify-audit-chain.py   # -> exit 0
```

## Audit target

- Pre-stage baseline: 3.
- Target: hold at 3 (`--no-baseline-drop`). Additive real subsystem — a MILP optimiser + documented tariff/thresholds;
  no `random.*`/mock/hardcoded-fabrication to remove or add. The residual 3 is the documented `_generate_heuristic_actions`
  G-052 name-pattern false-positive (untouched).

## Role

- Primary: `backend-engineer` (agent module, MILP, FastAPI route) / `agentic-governance-engineer` (KB_25 loop, ledger, ADR).
- Secondary: `robotics-integration-engineer` (the `energy_load_shift` SafetyContract sits in the `backend/safety` DSL).

## Risks / unknowns

- **The tariff numbers + the HVAC baseline fraction are representative documented constants, not a real utility schedule
  or metered load.** Labelled as such everywhere; a real pilot swaps them for the customer's actual tariff + meter
  (G-035, buyer-blocked). The optimiser is tariff-agnostic, so this does not affect the method's validity — only the
  absolute $ numbers. Recorded honestly, not overclaimed.
- The A/B is a SimWorld parametric sweep (deterministic MILP), NOT random seeds — summarised as mean/std/min/max, not a
  t-CI (a t-CI would misrepresent a non-random sample). Stated in the artefact's `honest_label`.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

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

## Pre-populated by start-task.sh (2026-07-18T15:06:23Z)

### Suggested role (from slug heuristic)

**agentic-governance-engineer** — open `.claude/skills/agentic-governance-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_18_Governance_Evidence.md`
- `knowledge-base/KB_README.md`
- `knowledge-base/KB_TASK_LOG.md`

### Pre-requisites (from previous stage's hand-off — STAGE_37_bidirectional_cdc_self_optimize.md)


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

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
