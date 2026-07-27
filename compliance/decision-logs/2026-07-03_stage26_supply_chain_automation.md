# ADR — Stage 26: Complete Supply-Chain Automation (multi-agent CNP + disruption monitoring)

- **Date:** 2026-07-03
- **Status:** Accepted
- **Stage:** 26 (`tasks/STAGE_26_supply_chain_automation.md`) — first roadmap-extension build stage (ADR
  `2026-07-02_strategic_audit_and_post_ga_roadmap.md`).
- **Roles:** `backend-engineer` (agents) + `agentic-governance-engineer` (coordination/safety/audit).
- **Research:** `research/initial-research.md §37` (CNP as the deterministic binding protocol; the IJPR
  consensus-seeking bullwhip result; the full stochastic-lead ROP form; disruption signals) — appended BEFORE
  implementing (Hard Rule 11).

## Context

The self-healing loop covered one production line; the 2026-07-02 strategic reset committed Stage 26 to widening it
into an end-to-end supply-chain layer — the neutral, certifiable answer to the supply-chain-agent category (IBM
watsonx Orchestrate's flagship domain) built on OUR spine: deterministic, safety-gated, signed-audit-trailed.

## Decisions

1. **Coordination = deterministic Contract-Net** (announce → sealed bids → award; min-cost, stable tie-break;
   every 10th round a counter-based exploration award to the least-observed supplier). LLM consensus-seeking (IJPR)
   is NOT the binding path — determinism and auditability are our constraints; adopted from the paper instead: the
   role decomposition and the bullwhip metric. (research §37.1/§37.2)
2. **Inventory policy = (s,S) with the full stochastic-lead ROP:** s = μ_d·μ_L + z·√(μ_L·σ_d² + μ_d²·σ_L²),
   S = s + μ_d·μ_L, z=2.33 (declared 99% service target); inventory POSITION (on-hand + on-order); bounded by
   PHYSICAL free capacity; labelled bootstrap-exploration orders for cold start; abstention (never invention) when
   signal is missing. Demand from the real `demand_forecaster.pt` when schema-compatible history is supplied
   (proxy model, G-035), else labelled empirical statistics.
3. **Every order is safety-gated (Hard Rule 3 at the supply-chain boundary):** the static `supply_chain_order`
   SafetyContract (SIL-0, preconditions qty-bounded/supplier-known/not-quarantined, invariant buffer-sane,
   fail-safe no_action) validates through `safety/validator.validate()` BEFORE any `supplier.order()` effect.
   Every CFP and award writes a signed `audit_chain` row + OTel span (best-effort, surfaced-failure pattern).
4. **Disruption monitoring** (detectors: supplier-failure→quarantine; latency via OVERDUE-PENDING expediting +
   a placement-windowed median-shift complement — see the defects section for the 4-iteration design history;
   persistent-starvation stockout; demand spike) raises incidents into the runtime via the **Stage-25 exactly-once
   router** — the runtime-facing integration.
5. **The material loop was closed IN THE SIM** (the honest place): `Supplier.order(on_fulfil=…)` fires only on a
   genuine fulfilment; `SimWorld.deliver_material()` feeds the unit into the stage buffer with real backpressure.
   Without this, no ordering policy could affect stockouts (found by running the loop).

## Measured outcome (10 paired seeds × 160 ticks, mid-run disruption; `supply_ab.json`)

| metric | greedy | agentic | paired 95% CI (g−a) |
|---|---|---|---|
| stockout-ticks | 106.3 | **52.2 (−51%)** | [12.6, 95.6] |
| bullwhip ratio | 74.3 | **1.21 (−98%)** | [49.0, 97.2] |
| units ordered | 4918 | **1305 (−73%)** | [3288, 3936] |
| mean buffer fill | ≈ equal | ≈ equal | [−0.039, 0.029] (includes 0) |

**HONEST LABEL:** SimWorld study, not real supply-chain evidence (G-035 buyer-blocked). The greedy baseline is
deliberately naive; the bullwhip + cost gaps are structural, the service gap partly baseline-naivety.

## Defects found by running the loop + the independent review (all fixed in-stage)

(1) open-circuit material loop; (2) winner-take-all supplier monoculture → deterministic exploration;
(3) capacity clamp on position instead of on-hand → 1-unit trickle starvation; (4) FIFO lead attribution smearing a
delayed order's lead onto other suppliers → exact callback-measured leads; (5) **the latency detector took FOUR
refuted-and-redesigned iterations** — v1 last-element robust-Z (missed mid-batch spikes); v2 per-lead log-space
outlier test (REFUTED by the independent review's no-injection control: natural lognormal tails × hundreds of draws
= multiple-testing false fires; and structurally LATE for the sim's freeze-type delay, whose fulfilments only become
observable after the freeze ends); v3 placement-windowed median-shift (killed the fulfilment-order ramp artifact —
same-placement batches fulfil shortest-first — but still post-hoc); v4 **OVERDUE-PENDING** (the operational
expediting rule: orders placed but unfulfilled past median·e^(3.5σ̂_log) age, ≥3 simultaneous; fleet-pooled threshold
basis when the supplier's own lead history is thin — the freeze starves its own detector). Registry-integrity fixes
en route: failure pruning consumes oldest entries → exact-match resolve falls back to oldest (leaked phantom
pendings drove persistent false overdue events).

**Drill verdict (CONTROLLED, injection vs same-seed no-injection control — the review's methodology):** a 10×-median
freeze on the award-winning supplier is detected DURING the freeze with a clean control on seeds 42/7/13
(`training/evals/results/supply_drill.json`). Honest sensitivity bound: freezes ≲ median·e^(3.5σ̂_log) (≈6.4× median
at the observed σ̂≈0.53) sit below the detection floor implied by the 3.5σ false-positive standard — stated, not
hidden. The first drill's claimed detection (`latency_spike@supplier:2`, 6×) was a NATURAL tail draw — refuted by
the reviewer's control arm and corrected here.

## Consequences

- New package `backend/agents/supply_chain/` (signals/roles/consensus/disruption_monitor/orchestrator) +
  `backend/scripts/run_supply_ab.py` + `backend/scripts/run_supply_drill.py` (controlled drill with a no-injection
  control arm) + 19 tests. SimWorld gains `deliver_material` + `on_fulfil` (real sim extension,
  task-doc-sanctioned). New deps: **none** (Rule 9 holds).
- Audit baseline: hold at 364 expected (`--no-baseline-drop`: additive real code, no de-mock surface — legacy
  de-mock remains Stage 28). KB_25 gains the supply-chain N-domain section; KB_01/KB_16 updated.
- **Neo4j grounding VERIFIED LIVE** (`ground_in_graph: True`; 6 supplier Enterprise nodes queried back via
  cypher-shell). Root cause of the session-long crash loop (742+ restarts): a CORRUPT partially-downloaded
  `graph-data-science.jar` persisted in the plugins VOLUME — Neo4j hard-fails on an invalid plugin zip at startup;
  the unused GDS plugin (zero `gds.*` references in backend code) was removed from the dev compose and the corrupt
  jar deleted from the volume (documented in `docker/docker-compose.yml`).
- Deferred honestly: real-supply-chain validation (G-035); LLM consensus annotation layer; RL replenishment third
  A/B arm (SB3 available — a depth option, ledgered); G-083 (detector episode-reset + noise polish → Stage 27,
  ledgered by the independent review).

## References
- research §37 · `research/stage-explainers/STAGE_26/index.html` · `backend/training/evals/results/supply_ab.json` ·
  arxiv 2411.10184 / IJPR 10.1080/00207543.2025.2604311 (consensus-seeking) · en.wikipedia.org/wiki/Contract_Net_Protocol ·
  ADR `2026-07-02_strategic_audit_and_post_ga_roadmap.md`.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-04T12:52:58+00:00 -->
<!-- signature: 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 -->
