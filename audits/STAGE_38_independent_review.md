# Stage 38 — Independent Review (Facilities / Energy head-agent, G-018)

- **Auditor role:** `task-auditor` (independent — did NOT build this stage).
- **Date:** 2026-07-19
- **Stage:** 38 — `tasks/STAGE_38_facilities_energy_agent.md` (KB_25 loop extended to a THIRD embodiment domain: industrial energy management).
- **Method:** full read of every created/modified file + adversarial re-runs on the live Docker stack (Postgres @5544, ML-DSA-65 audit chain).

## TOP-LINE VERDICT: **PASS**

The stage is honest, deep, and theatre-free. The optimiser is a genuine `scipy.optimize.milp` (HiGHS) model — I read the model construction and re-ran it; it builds a real objective, integrality, bounds, and constraints (including the production-floor equality). The energy signals are the sim's real `nominal_kw`. Hard Rule 3 is preserved (no actuator emitter in the new code; the load-shift is routed through `safety/validator.validate()`). The validator gate genuinely rejects peak-increasing and production-dropping plans (reproduced independently). The A/B numbers reproduce to the digit and are honestly labelled. The `--no-baseline-drop` hold at 3 is justified (additive real code; the residual 3 is the pre-existing `rl_policy.py` G-052 false-positive, not facilities). All 15 tests pass and actually assert behaviour. **No gaps that must be fixed before close.**

## Per-criterion evidence table (AC1–AC8)

| AC | Claim | Independently confirmed? | Evidence |
|---|---|---|---|
| **AC1** | Real energy signals, no fabrication (`observe_from_calibration` reads real `nominal_kw`; labelled `BASE_LOAD_FRACTION=0.20`) | **YES** | `signals.py:54-73` reads `simulation/calibration.py::STAGES`. Grep of `calibration.py:94-103` confirms intake 2.0 / press 14.0 / weld 18.0 / machining 22.0 / wash 8.0 kW etc. Live: total 109 kW → `base_kw=21.8` (=0.20×109); `test_observe_uses_real_nominal_kw` PASS. `BASE_LOAD_FRACTION` is a module constant with a documented comment (`signals.py:16-18`), not hidden. |
| **AC2** | Documented ToU + demand-charge tariff; `bill()` computes energy + demand | **YES** | `tariff.py` — on 0.28 / mid 0.16 / off 0.10 $/kWh + `DEMAND_CHARGE_PER_KW_DAY=0.60`; `bill()` = Σ(kW·h·price) + demand·peak (`tariff.py:49-58`). `test_tariff_periods_and_prices` + `test_tariff_bill_energy_plus_demand` PASS. Numbers explicitly labelled "representative published-structure", not real utility (`tariff.py:1-8`). |
| **AC3** | REAL MILP (`scipy.optimize.milp`/HiGHS); production-floor equality present; deterministic; labelled greedy fallback | **YES** | `optimizer.py::_solve_milp` (l.80-145): builds `c` objective (energy + `demand_charge·peak`), `integrality` (binary x, continuous peak), `Bounds` (window→ub=0), constraints: **(1) `Σ_t x[j,t]=required_slots[j]` equality — production floor, l.120-125**; (2) `peak ≥ base_t + Σ kw·x` per slot, l.126-132. Genuine `milp(...)` call l.134, raises on `not res.success` (no fabricated result). Live re-run: peak 130.8→71.8 kW, every stage exactly 6 slots. `test_milp_reduces_peak_and_holds_production_floor`, `test_milp_is_deterministic`, `test_greedy_fallback_is_labelled_and_valid` PASS. |
| **AC4** | Honest 0% when unshiftable (not a fabricated saving); A/B `min`=0.0% | **YES — and proven genuine, not a bug** | `test_unshiftable_facility_returns_zero_reduction_not_fabricated` PASS. A/B `peak_reduction_pct.min = 0.0`. I independently proved the 0% `day_shift`/req=6 row is the **honest MILP optimum**: the solver concentrates all loads into the 6 cheapest mid-peak slots `[8,9,10,11,18,19]`, cutting total cost 295.6→269.4 (−8.85%) while peak stays 130.8 — energy savings outweigh demand-charge savings from spreading. Correct optimisation of the documented objective. |
| **AC5** | KB_25 loop + validator gate (Hard Rule 3); no actuator emitter | **YES** | `orchestrator.run_cycle` (l.91-149): observe→predict(baseline)→diagnose(`demand_charge_breach`)→optimise(MILP)→VERIFY via `safety.validator.validate()` under `ENERGY_LOAD_SHIFT_CONTRACT`→INTERVENE(`_audit`). Grep of `agents/facilities/*.py` + `facilities_routes.py`: **zero** `actuator.`/`dispatch_order(` calls (only a docstring comment naming `master.dispatch_order`). Independently reproduced gate: peak-increasing → `blocked: precondition:peak_not_increased`; dropped-production → `blocked: precondition:production_floor_met,invariant:energy_conserved`; valid → allow. `test_hard_rule_3_no_actuator_emitter_in_facilities` + `test_contract_rejects_*` PASS. |
| **AC6** | Measured A/B (honest): peak −22.1% mean/max 58.9%, cost −7.6% mean/max 18.8%, all floors held; SimWorld+G-035 label | **YES** | Re-ran `scripts/run_energy_ab.py` → reproduced to the digit: peak mean **22.095** / min 0.0 / max **58.869**, cost mean **7.566** / max 18.828, n=10, `all_floor_ok=true`. `honest_label` contains "SimWorld" + "G-035" + the parametric-sweep/no-t-CI framing. `test_ab_artifact_is_honest_and_floors_hold` PASS. |
| **AC7** | `POST /facilities/optimize-energy` registered; reasoning signed to `audit_chain` (`energy.load_shift`) | **YES** | `facilities_routes.py` route present; `main.py:416-417` registers `facilities_router`. `test_route_optimize_energy` + DB-gated `test_cycle_signs_audit_row` PASS (ran, not skipped, with `DATABASE_URL` set). Live cycle wrote real `audit_seq=10479`, `audited=True`; `verify-audit-chain.py` exit 0 (10479 rows, all 10400 post-cutover sigs verify — includes the new row). |
| **AC8** | Free-cost (no new deps); audit holds at 3 (`--no-baseline-drop` justified) | **YES** | `bash scripts/audit.sh` = TOTAL **3** (baseline 3, held). Only non-zero category is `heuristic_actions=3`, located in `backend/ml/rl_policy.py` (grep-confirmed — the pre-existing G-052 name-pattern false-positive), NOT facilities. Zero `random.*`/mock/hardcoded fabrication in facilities (grep clean). No new dependency (scipy already installed). |

## Commands run (read-only) + key output

```
$ python -m pytest tests/facilities -q          # DATABASE_URL set
15 passed, 2 warnings in 47.01s                 # incl. DB-gated audit-signing test, no skips

$ python -c "...EnergyOrchestrator(demand_cap_kw=100.0).run_cycle().to_dict()..."
method=milp baseline_peak_kw=130.8 optimized_peak_kw=71.8 peak_reduction_pct=45.11
diagnosed=demand_charge_breach allowed=true committed=true audit_seq=10479 audited=true
schedule: every stage-id maps to exactly 6 slots (production floor held)

$ python scripts/run_energy_ab.py --out <scratch>
peak_reduction_pct mean=22.095 min=0.0 max=58.869 ; cost mean=7.566 ; n=10 ; all floors held: True

$ python -c "validate(...peak-increasing...)"   -> allow=False (blocked: precondition:peak_not_increased)
$ python -c "validate(...dropped-production...)" -> allow=False (blocked: precondition:production_floor_met,invariant:energy_conserved)
$ python -c "validate(...valid-improving...)"    -> allow=True

$ python -c "...day_shift req=6 MILP..."         -> peak 130.8 unchanged, total cost 295.608->269.448 (0% peak is the honest optimum)

$ bash scripts/audit.sh                          -> TOTAL 3 (baseline 3, held); heuristic_actions=3 in rl_policy.py only

$ python scripts/verify-audit-chain.py           -> Audit chain OK (10479 rows; hash chain intact; all 10400 post-cutover signatures verify)  [exit 0]
```

## Theatre / bypass / Hard-Rule findings

- **None.** No `random.*` / mock / hardcoded fabrication in `agents/facilities/` or `api/facilities_routes.py` (grep clean). No `--no-verify`/`--force`. Hard Rule 3 intact — no actuator emitter added; the load-shift is validator-gated. Hard Rule 11 satisfied — a real MILP over real signals, grounded in research §49 (dated, sourced with URLs, appended before implementing). Rule 9 satisfied — no new deps. Baseline discipline correct — additive stage held at 3 with an honest `--no-baseline-drop` justification.

## Non-blocking observations (NOT gaps — no fix required before close)

1. `orchestrator.py:117` computes `optimized_kwh = sum(profile.base_by_slot()) * 0.0 + sum(...)`. The `* 0.0` term is a deliberate no-op that documents "base load excluded"; it is harmless and correct (both `optimized_kwh` and `required_kwh` are schedulable-only, so the `energy_conserved` invariant is well-posed). Cosmetic only.
2. The ADR (`2026-07-18_stage38...md:71`) cites the live cycle's `audit_seq` as 10478; my fresh re-run signed 10479. Consistent (monotonic append) — not a discrepancy.
3. The `_greedy` fallback's `feasible` computation (`optimizer.py:62-64`) is convoluted (zip of `schedule.items()` with re-sorted loads) but is only a flag on the non-primary fallback path; the MILP path is the one exercised and is correct.

## Gaps that must be fixed before close

**None.** This stage is cleared to close.

## Honest deferrals confirmed legitimate (ledgered, not dropped)

- Real-utility tariff + metered-load validation, and wiring the optimiser into the live sim tick loop (vs the day-ahead planning surface built here) → a pilot (G-035, buyer-blocked). Labelled everywhere (task doc, ADR §Alternatives, research §49, `honest_label`). Not overclaimed.
- A learned DRL demand-response agent was considered and correctly rejected as the primary method (honest training needs a real tariff/metered dataset = G-035); the MILP is the deepest honest free/local method against the sim's real signals (ADR §Alternatives). Sound.

---

*Independent review by a different agent than the implementer (operator mandate 2026-05-31). Verdict: **PASS** — no close-blocking gaps.*
