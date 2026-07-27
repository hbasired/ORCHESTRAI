# ADR — Stage 38: Facilities / Energy head-agent — KB_25 loop for industrial energy management (G-018)

- **Date:** 2026-07-18
- **Status:** Accepted
- **Stage:** 38 (`tasks/STAGE_38_facilities_energy_agent.md`) — the second of the operator-chosen post-CTO-#6 free/local
  arc (37 bidirectional CDC → 38 new head-agent domain → 39 small gap-closers → consolidated handoff).
- **Roles:** `backend-engineer` (agent module, MILP, FastAPI route) + `agentic-governance-engineer` (KB_25 loop
  alignment, ledger, ADR).
- **Research:** `research/initial-research.md §49` (industrial energy-management SOTA: peak-shaving / load-shifting /
  demand-response, MILP formulation, ToU tariff) — appended BEFORE implementing (Hard Rule 11).

## Context

The KB_25 predict→diagnose→verify→intervene engine is designed for N head-agent domains. Two ran so far: the
production line (Stages 6–11) and supply-chain (Stage 26). Ledger **G-018** asks for a Facilities/Building-energy head
agent as a new embodiment domain. It is a strong choice because the sim ALREADY carries a REAL per-stage energy model
(`simulation/calibration.py::StageCalibration.nominal_kw` — intake 2.0 / press 14.0 / weld 18.0 / machining 22.0 /
wash 8.0 / paint 12.0 kW; the live `manufacturing_agent` reports `energy_consumption = nominal_kw when running`), so
the domain extends real signals, not fabricated ones (Hard Rule 1/1a).

The constraints: pick the DEEPEST honest free/local method (Hard Rule 11 — no toy where a deeper free path exists);
preserve Hard Rule 3 (the agent proposes, it never actuates directly); free-cost (no new deps).

## Decisions & outcomes

1. **A new head-agent domain package `backend/agents/facilities/`, mirroring `agents/supply_chain/`:**
   `signals.py` (observe real per-stage `nominal_kw` → a schedulable-load view + a documented HVAC/lighting baseline),
   `tariff.py` (a documented ToU + demand-charge tariff), `optimizer.py` (the optimiser), `orchestrator.py` (the KB_25
   loop + the `energy_load_shift` contract + the validator gate + audit).

2. **The optimiser is a REAL MILP (the depth Hard Rule 11 demands), not a hand-coded heuristic.**
   `scipy.optimize.milp` (HiGHS — already installed, Rule 9, no PuLP) minimises `Σ_t Σ_j (kw_j·slot_h·price_t)·x[j,t]
   + demand_charge·peak` over binary schedule variables `x[j,t]` (stage j runs in slot t) plus a continuous `peak`,
   subject to: (a) `Σ_t x[j,t] = required_slots[j]` — the **production floor** (every stage delivers its full
   run-hours; shifting NEVER cuts output); (b) `x[j,t]=0` outside each load's window; (c) `peak ≥ base_t + Σ_j
   kw_j·x[j,t]` ∀ t (peak dominates every slot). Two levers in one objective: **load shifting** (move energy off the
   on-peak ToU window) + **peak shaving** (cut the $/kW demand charge). Honest fallback: a deterministic greedy
   cheapest-slots load-shift, LABELLED `method="greedy"`, if `milp` is unavailable — never a fabricated result.

3. **KB_25 loop + Hard Rule 3.** `EnergyOrchestrator.run_cycle`: observe → PREDICT the naive demand curve → DIAGNOSE a
   `demand_charge_breach` (naive peak > the contracted `demand_cap_kw`; no cap ⇒ run proactively — we do NOT invent an
   "anomaly" from peak>process_kw, which is true of any overlapping naive schedule and would be theatre) → optimise →
   VERIFY the load-shift through `safety/validator.validate()` under the code-defined `energy_load_shift` SafetyContract
   (SIL-0, GATED; preconds: production-floor-met, windows-respected, peak-not-increased; invariant: energy-conserved;
   the LLM never edits contracts, KB_17) → INTERVENE by emitting the gated day-ahead schedule + a best-effort signed
   `audit_chain` row (`energy.load_shift`, Art-12). The agent adds NO actuator emitter — the sole codebase emitter
   stays `master.dispatch_order` (grep-verified + a test).

4. **API surface `POST /facilities/optimize-energy`** (`api/facilities_routes.py`, registered in `main.py`), running
   the cycle off the event loop (`asyncio.to_thread`).

## Honesty notes (Rule 1a — verified)

- **Real signals:** the per-stage kW is the sim's real calibrated `nominal_kw`; the HVAC/lighting baseline is an
  explicitly-labelled documented fraction (`BASE_LOAD_FRACTION=0.20`), not a hidden constant.
- **Honest 0% when unshiftable:** a fully-constrained facility (window == required hours) returns 0% reduction, not a
  fabricated saving — verified by test AND recorded as the A/B `min` (0.0%).
- **Tariff numbers are representative, labelled documented constants**, not a real utility schedule; a real pilot swaps
  them (G-035). The optimiser is tariff-agnostic, so this affects only the absolute $ numbers, not the method.
- **The A/B is a deterministic parametric sweep**, summarised as mean/std/min/max — NOT a t-CI (which would
  misrepresent a non-random sample). Stated in the artefact's `honest_label`.

## Evidence

- 15 tests pass (`tests/facilities/test_facilities.py`: tariff, MILP optimiser [peak reduction + production floor +
  determinism + greedy fallback + honest-0%], orchestrator [diagnosis + gate allow/reject + Hard-Rule-3 no-emitter],
  A/B artefact, API route). Regression: safety (33) + health pass.
- A/B (`training/evals/results/energy_ab.json`): peak −22.1% mean (max 58.9%), cost −7.6% mean (max 18.8%), all
  production floors held.
- Live cycle: diagnosed `demand_charge_breach`, MILP peak 130.8→71.8 kW (−45.1%), cost $230.21→$204.05 (−11.4%), gate
  allowed, signed a real `audit_chain` row (seq 10478).
- `scripts/audit.sh` = 3 (held; `--no-baseline-drop`: additive real code — a MILP + documented constants, no
  `random.*`/mock/hardcoded fabrication). No new dependencies (Rule 9).

## Consequences

- G-018 RESOLVED — the KB_25 loop now runs a THIRD embodiment domain (facilities/energy).
- The next stage (39) closes small honest gaps (G-045 decision persistence + G-051 Stage-6 verifier), then the
  consolidated handoff summary.

## Alternatives considered

- **A hand-coded greedy load-shift heuristic only.** Kept as the honest FALLBACK, but rejected as the primary method —
  Hard Rule 11 demands the deepest free path, and a real MILP (HiGHS) is feasible free/local.
- **A learned RL demand-response agent (the multi-agent DRL paper, §49).** Deeper in principle, but honest training
  needs a real tariff + metered-load dataset (G-035); training on synthetic data would be theatre. The MILP is the
  deepest HONEST free/local method against the sim's real signals. Recorded, deferred to a pilot.
- **Wire the optimiser into the live sim tick loop.** The day-ahead planning surface is the honest first cut; live
  tick-loop control is incremental and pilot-relevant (deferred, G-035).
