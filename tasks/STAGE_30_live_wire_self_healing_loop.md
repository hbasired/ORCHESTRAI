---
status: done
stage: 30
slug: live_wire_self_healing_loop
created: 2026-07-12
---

# Stage 30 — Live-wire the self-healing loop

> Makes the KB_25 loop fully LIVE end-to-end: (G-005) a real cross-fleet **repair-robot dispatch** — the missing
> KB_25 step-4 recovery action — that cuts machine downtime vs. the passive MTTR timer; (G-025-tail) the Stage-7
> MaskablePPO that beat rules is now consulted by the runtime as a **SHADOW recommender** (logged RL-vs-rule
> agreement, never acts — the SOTA safe-deployment pattern, shielded by the existing verifier); (G-036) the
> operator-facing 7-day demand forecast is now **SERVED by the real model** (LSTM / empirical) with honest labelling,
> replacing a placeholder that carried a fabricated confidence. Research §41; free/local.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_30/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: 29 (conversational), 26 (Contract-Net — reused for repair allocation), 17 (safety validator), 11 (runtime), 7 (MaskablePPO), 5 (demand forecaster)
- Decision logs honoured: `2026-07-12_stage29_conversational_factory_intelligence.md`, `2026-07-03_stage26_supply_chain_automation.md`, `2026-06-14_depth_08_world_model_causal_verify.md`
- KB files at minimum version: KB_25 (self-healing loop, step-4 intervene), KB_05 (sim spec), KB_07 (API)
- Gaps ledger rows pulled in (IDs): **G-005** (cross-fleet repair dispatch), **G-025**-tail (live RL intervention), **G-036** (demand forecaster live path); G-027 (free-cost, ongoing)

## Acceptance criteria

- [x] **AC1 (G-005) — repair-robot dispatch cuts real downtime.** A broken machine's remaining repair time is cut
  by a dispatched repair robot via `Stage.repair_assist` (interruptible SimPy repair) + `SimWorld.request_repair`;
  the coordinator awards the best available robot by a deterministic Contract-Net over REAL robot state
  (`agents/repair/dispatch.py`), safety-gated (`repair_dispatch` contract, Hard Rule 3). **Paired A/B (10 seeds):
  downtime −47.9%, 95% CI [7696, 12733]s, excludes 0** (`training/evals/results/repair_ab.json`). Verified:
  `tests/repair/test_repair_dispatch.py` (incl. a 1-seed A/B + honest no-op on a recovered stage).
- [x] **AC2 (G-005) — honest dispatch gate.** Only idle robots with usable charge bid; min-cost wins; dispatch to a
  non-broken machine is gate-blocked; no available robot → honest no-award; `repair_assist` on a recovered stage is a
  no-op (no fabricated benefit). Verified in `test_repair_dispatch.py`.
- [x] **AC3 (G-025-tail) — RL shadow recommender, logged not acted.** `agents/runtime/rl_shadow.py` runs the Stage-7
  MaskablePPO on its own fleet-scheduling distribution (obs built from real degrading/crack-proximity/broken signals),
  emits an RL recommendation + RL-vs-rule agreement, and NEVER actuates; wired into the runtime `decide` node behind
  `RUNTIME_RL_SHADOW=1` (off by default; the verifier/validator remain the shield). Honest-unavailable when SB3/policy
  absent. Verified: `tests/runtime/test_rl_shadow.py` + live smoke.
- [x] **AC4 (G-036) — demand forecaster SERVED, no fabricated confidence.** `services/demand_forecast_service.py`
  serves the real LSTM (schema history → daily, MAE-derived bounds) or empirical stats (observed daily), else an
  HONESTLY LABELLED planning baseline with `model_loadable` surfaced and NO per-day `confidence`. `state_manager`'s
  operator-facing 7-day forecast now uses it (the legacy fabricated `confidence` is removed). Verified:
  `tests/services/test_demand_forecast_service.py`.
- [x] **AC5 — free-cost + no regression + determinism.** New deps: none. Audit holds 3 (additive real code; also
  removed an audit-invisible fabricated `confidence`). Regression 74 passed / 1 skipped across sim/runtime/supply/
  repair/services; runtime determinism holds (shadow gated off).
- [x] **AC6 — research-first (§41) + explainer + independent review.** Research §41 appended BEFORE implementing;
  `research/stage-explainers/STAGE_30/index.html`; independent review by a DIFFERENT agent = PASS.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/agents/repair/__init__.py` + `dispatch.py` | G-005 repair Contract-Net + `repair_dispatch` safety contract + `dispatch_repair` |
| `backend/agents/runtime/rl_shadow.py` | G-025-tail SHADOW RL recommender (fleet obs → RL vs rule; never acts) |
| `backend/services/demand_forecast_service.py` | G-036 7-day forecast served from the real model / empirical / honest baseline |
| `backend/scripts/run_repair_ab.py` | G-005 paired-seed downtime A/B (dispatch vs passive) |
| `backend/tests/repair/test_repair_dispatch.py` | dispatch + interruptible-repair A/B tests |
| `backend/tests/runtime/test_rl_shadow.py` | shadow recommender tests |
| `backend/tests/services/test_demand_forecast_service.py` | forecast serving + honest-baseline tests |
| `research/stage-explainers/STAGE_30/index.html` | stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/simulation/entities/stage.py` | interruptible repair wait + `repair_assist()` + `repair_dispatch_count` |
| `backend/simulation/sim_world.py` | `request_repair(stage_id, reduction, travel_seconds)` |
| `backend/agents/runtime/nodes.py` | `decide` node attaches the shadow RL recommendation (gated, shadow-only) |
| `backend/services/state_manager.py` | operator-facing 7-day forecast served via the service (fabricated confidence removed) |
| `knowledge-base/KB_25/KB_05/KB_07` + `audits/OPEN_GAPS_LEDGER.md` | intervene step-4 / sim / API + G-005/025/036 RESOLVED |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | additive stage |

## Files to MODIFY

| Path | Change |
|---|---|
| | |

## Files to DELETE

| Path | Reason |
|---|---|
| | |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` (intervene step-4: repair dispatch + RL shadow live)
- `knowledge-base/KB_05_Simulation_Spec.md` (interruptible repair + `repair_assist`)
- `knowledge-base/KB_07_API_Contracts.md` (forecast provenance fields in supply-chain state)

## Verification commands

```bash
bash scripts/audit.sh                    # holds at 3 (additive; --no-baseline-drop)

cd backend && DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing HF_HUB_DISABLE_XET=1 \
  python -m pytest tests/repair/ tests/services/test_demand_forecast_service.py tests/runtime/test_rl_shadow.py -q

# the binding downtime A/B (repair dispatch vs passive MTTR)
cd backend && python scripts/run_repair_ab.py --seeds 10 --hours 6 --out training/evals/results/repair_ab.json

# no regression
cd backend && python -m pytest tests/test_sim_world_smoke.py tests/test_slice_intervene.py tests/agents/runtime/ tests/agents/supply_chain/ -q
```

## Audit target

- Pre-stage baseline: 3
- Target: hold at 3 (`--no-baseline-drop`) — additive real code (repair/RL-shadow/forecast subsystems); zero new
  `random.*`/mock introduced; ALSO removed an audit-invisible fabricated `confidence` synthetic constant (net honesty gain).

## Role

- Primary: `backend-engineer` (sim + runtime wiring) + `ml-engineer` (RL shadow, forecaster serving)
- Secondary: `robotics-integration-engineer` (repair-dispatch safety contract), `agentic-governance-engineer` (traceability)

## Risks / unknowns

- Robots have no physical position in the SimWorld — dispatch cost uses real availability/battery/queue, not a
  fabricated distance (physical-proximity routing = pilot/real-fleet, disclosed).
- The RL shadow maps the real fleet into the model's 9-machine layout (approximate; disclosed) — shadow-only, so the
  point is measuring agreement before ever trusting it.
- Real-data validation of all three (real fleet / real hourly demand) = G-035 (buyer-blocked).

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - The KB_25 loop is live end-to-end: a downed machine gets a real safety-gated repair dispatch (measured −47.9%
    downtime); the RL policy is consulted in shadow; the operator forecast is served from the real model (no fake confidence).
- What the next stage (31 — detector/eval hardening) starts with:
  - A fully-live loop to harden: G-077 prompt_guard learned/LLM-judge tier + G-064-tail continuous runtime anomaly
    detection + CTO #5 R5 deep-eval gate polish.
- Open items deferred to a future stage:
  - RL shadow→active promotion (autonomy-ladder gated) once agreement is validated on real data (pilot).
  - Physical-proximity repair routing + real hourly-demand re-fit (G-035, buyer-blocked).

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-12T15:55:27Z)

### Suggested role (from slug heuristic)

**agentic-governance-engineer** — open `.claude/skills/agentic-governance-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_18_Governance_Evidence.md`
- `knowledge-base/KB_README.md`
- `knowledge-base/KB_TASK_LOG.md`

### Pre-requisites (from previous stage's hand-off — STAGE_29_conversational_factory_intelligence.md)


- What is now true that wasn't before this stage:
  - The factory is INTERACTIVE: `/factory/ask` (grounded, cited QA + honest-empty), `/factory/inject` (NL → validated
    incident → validator-gated loop), `/factory/diagnose` (information-gain active diagnosis over live sim).
  - The self-healing loop can now be interrogated (KB_25 §1b active diagnosis is real, not a no-op) and driven by
    natural language — both feed the same signed Art-12 evidence trail.
  - `audit_chain.read_recent` gives any surface a read-only, honest query over the signed evidence store.
- What the next stage (30 — live-wire the self-healing loop) starts with:
  - The conversational layer will DRIVE a fully-live loop; Stage 30 wires G-005 (cross-fleet repair dispatch),
    G-025-tail (live RL-intervention), G-036 (demand_forecaster into the live path).
- Open items deferred to a future stage:
  - Real-user conversational + adoption validation needs a pilot (G-035/G-043, buyer-blocked).
  - Multi-turn dialogue memory / chat history persistence (incremental; the current endpoints are single-turn).

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
