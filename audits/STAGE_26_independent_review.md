# Stage 26 — Independent Review (supply-chain automation)

**Reviewer**: independent task-auditor (DIFFERENT agent than the implementer)
**Date**: 2026-07-03
**Scope**: `tasks/STAGE_26_supply_chain_automation.md` acceptance criteria; all new/modified Stage-26 files;
theatre hunt; dynamic re-runs.

## VERDICT: **PASS-WITH-GAPS**

The implementation is genuinely theatre-free and deep: five real observed-signal agents, a deterministic
Contract-Net with a load-bearing safety gate, a real closed material loop in the sim, an honest A/B whose numbers
reproduce to the digit, 18/18 real tests, audit flat at 364 with a legitimate waiver. **But one headline claim did
not survive adversarial reproduction**: the "6×-median delay on the award-winning supplier was DETECTED live"
drill claim (AC-3) is not reproducible under the stated procedure, and a control experiment shows the exact
claimed detection (`latency_spike@supplier:2`) fires **naturally, without any injection** — the causal attribution
is unverified and plausibly wrong (Rule 1a: unverified capability claim = gap). A second live claim also failed:
AC-4's "verified live post-fix" Neo4j grounding is refuted — the container is still crash-looping (122 restarts;
stale corrupt GDS jar in the /plugins volume survives the compose-only fix). Gaps 1 and 6 below MUST be fixed
before close; Gaps 4–5 must also land before close (mechanical/lifecycle). Gap 2 is ledgered (G-083).

---

## 1. Dynamic re-runs (commands I executed)

| Command | Claim | Result |
|---|---|---|
| `python -m pytest tests/agents/supply_chain/ -q` (DATABASE_URL set) | 18 passed | **REPRODUCED: 18 passed** in 61 s (DB audit-row test executed, not skipped) |
| `bash scripts/audit.sh` | TOTAL 364 flat | **REPRODUCED: TOTAL 364**, baseline 364 |
| `python scripts/run_supply_ab.py --seeds 3 --ticks 120` | direction: agentic better on stockout/bullwhip/orders | **REPRODUCED (direction)**: bullwhip 50.9/159.7/179.2 → 0.78/1.14/1.64; orders 3410/3603/4278 → 993/1008/1202; stockout mean 68 → 48.7 (agentic loses seed 1, 66 vs 53 — consistent with the honest per-seed variance in the 10-seed run). (The JSON write failed only because I passed a bad `--out` path; per-seed rows printed.) |
| 10-seed `supply_ab.json` arithmetic recheck | stockout 106.3→52.2; bullwhip 74.3→1.21; orders 4918→1305; CIs | **REPRODUCED from the committed per-seed rows**: means 106.3/52.2, 74.28/1.211, 4918/1305.9; CIs [12.555,95.645], [48.981,97.167], [3287.78,3936.42]; buffer-frac CI [−0.039,0.029] includes 0. Seed 7 (agentic LOSES stockout 186 vs 93) is committed, not hidden — honest. (Nit: "1305" is a floor of 1305.9.) |
| Disruption drill, spec procedure (seed 42, 60 warm ticks, `delay_next_delivery(6×median)` on the **last award-winning supplier**, 50 post ticks) | `latency_spike` for THAT supplier | **FAILED** — winner = supplier 4 (median 2669 s); no `latency_spike@supplier:4` in 50 ticks, **nor in an extended 140-tick window**, even though the delayed leads (11 878–20 770 s) demonstrably arrived from tick 116 and supplier 4 kept winning 68 post-injection awards. See Gap 1 root cause. |
| Drill control experiment (seed 42, most-awarded supplier 2, injected vs NO-injection control, 140 post ticks each) | — | **Control and injected runs produce byte-identical latency-spike event streams** (18 events across 5 suppliers, incl. `latency_spike@supplier:2` at tick 90 in BOTH). The injection added **zero** attributable detections. Tick 90 is also before any injected order could fulfil (all delayed fulfilments land ≥ tick 126: `_fulfill` computes `extra = delay_until − now` at order time, so fulfilment ≥ delay_until). |
| Drill positive results | starvation cascade | `stockout@stage:8` detected live in my run (claimed "stages 6–9" is seed/procedure-dependent; the stockout detector itself is test-verified) |
| `python scripts/verify-audit-chain.py` | chain OK | **exit 0** — "Audit chain OK (10067 rows; hash chain intact; all 9988 post-cutover signatures verify)". NOTE: the chain grew ~428 → 10 067 because the A/B harness + drills run OUTSIDE pytest (no R1 isolation) and append a signed row per CFP/award — honest rows, chain green, but the harness bloats the dev attestable chain (observation, not a gap). My own drill re-runs also appended such rows (disclosure). |
| `ground_in_graph()` live | "verified live post-fix" (AC-4) | **REFUTED at review time**: returned `graph_grounded=False` (the honest degradation path works). Neo4j is in an active CRASH LOOP — `RestartCount=122`, "Up N seconds (health: starting)" forever. The running container DOES have the new env (`NEO4J_PLUGINS=["apoc"]` — compose change applied), but `docker logs` shows the root cause: `ZipException: Some jar procedure files (graph-data-science.jar) are invalid` — a **stale, corrupt GDS jar left in the /plugins volume** from the earlier interrupted download. Neo4j loads every jar in /plugins regardless of `NEO4J_PLUGINS`, so the compose-only fix is INCOMPLETE. `gds.*` grep over `backend/**/*.py` = zero hits (removal rationale itself is sound). See Gap 6 (now must-fix). |

## 2. Static review — theatre hunt (every new file read line-by-line)

- **No RNG, no sim-config leakage**: grep `SIM_WORLD|calibration|random|rng` over `backend/agents/supply_chain/`
  → sole hit is a docstring in `signals.py:8` saying agents must NOT know it. Agents bid from `SignalObserver`
  stats only (observed fulfilled/failed counters + callback-measured leads). CONFIRMED.
- `signals.py` — `None`-abstention below 3 obs; FIFO-attribution limitation documented (lines 68–72); no invented
  numbers. CLEAN.
- `roles.py` — DemandAgent abstains without history; real `demand_forecaster` used only when history supplied,
  source labelled; `ModelUnavailableError` falls through to labelled empirical stats. (s,S) ROP is the sourced
  textbook form (research §37.3); the `1e6` exploration bid is a labelled policy constant, not a performance claim.
  CLEAN.
- `consensus.py` — deterministic min-cost award, stable tie-break (line 147); counter-based exploration (no RNG,
  lines 141–145); the safety gate `validate(action, world_state, SUPPLY_CHAIN_ORDER_CONTRACT)` at line 160 runs
  BEFORE any order effect (orders are placed only in `orchestrator.tick()` behind `award.allowed`, orchestrator.py:105).
  `_audit` surfaces failure as `(None, False)` — never fabricates a seq. CLEAN.
- `disruption_monitor.py` — sourced thresholds (Iglewicz–Hoaglin 3.5; MIN_OBS abstention); default sink is the real
  Stage-25 `run_incident_guarded` (`agents/runtime/shard_router.py:152`). CLEAN code; behavioural weaknesses in Gap 1/2.
- `orchestrator.py` — honest `graph_grounded=False`; exact callback-measured leads; deterministic failed-order
  reconciliation. CLEAN.
- Sim changes (`entities/supplier.py` `on_fulfil`; `sim_world.py:232` `deliver_material`) — real SimPy effects,
  backpressure via `queue.put`, `on_fulfil` fires only on a genuine reliability-roll success. The sim's own RNG is
  pre-existing sim behaviour (the world model), not agent fabrication. CLEAN.
- `run_supply_ab.py` — paired seeds, same disruption both arms, honest label in the JSON, "if the greedy baseline
  wins a metric, that is the reported result". CLEAN (Gap 3 statistical nit).
- `safety/validator.py::validate` — real precondition/invariant evaluation; `_safe_check` fails CLOSED on
  exceptions; SIL-0 routes "direct" but still blocks on failed checks. The gate is real.
- **Gate-removal counterfactual**: `Award.allowed` defaults False, set only from `decision.allow`
  (consensus.py:161-162). Removing the gate leaves awards disallowed → `test_simworld_loop_orders_deliver_and_feed_buffers`
  fails (`total_orders > 0`); hardcoding `allowed=True` → `test_gate_blocks_order_exceeding_free_capacity` +
  `test_gate_blocks_insane_buffer_reading` fail (they assert the validator-produced `gate_reason` names the failed
  check). The gate is LOAD-BEARING. Caveat: the third claimed "gate block" (quarantined supplier) is enforced at
  CNP bid-eligibility (`collect_bids` skips quarantined, consensus.py:111-112), not at the validator precondition —
  `supplier_not_quarantined` is unreachable via the coordinator path since `world_state["supplier_quarantined"]`
  derives from the same set that already filtered the bids (defence-in-depth, untested at the validator level). Minor.
- **Tests are honest**: 18 tests counted, all assert behaviour; the DB test reads back the exact
  `supply_chain.award` row by seq from the R1-isolated chain. The one weak test is
  `test_normal_leads_do_not_false_positive` (±5 % synthetic leads — far tighter than the sim's real lognormal
  σ_log = 0.4, see Gap 2).

## 3. Acceptance-criteria table

| AC | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| 1. Multi-agent layer, non-fabricating, abstention, audited CFP/award | [x] | **YES** | Code read + tests + live audit rows (seq round-trip test + 9.6k real rows on the dev chain). In-process (not A2A) deviation is HONESTLY noted in the AC itself. |
| 2. Deterministic CNP + safety gate blocks proven | [x] | **YES** (with the quarantine-layer caveat above) | Determinism test + same-seed e2e determinism reproduced; gate load-bearing. |
| 3. Disruption monitoring: 4 detectors, quarantine→eligibility, incidents exactly-once, drill DETECTED | [x] | **PARTIAL — the injected-latency-drill claim did NOT reproduce** | Quarantine, stockout, demand-spike, mid-batch spike detection all verified by tests; stockout cascade seen live; exactly-once router integration real. The "6×-median delay on the award-winning supplier was DETECTED (latency_spike@supplier:2)" claim fails reproduction + control attribution (Gap 1). CDC-not-wired honestly noted. |
| 4. Graph grounding + honest degradation; GDS removal | [x] | **NO — "verified live post-fix" REFUTED** | Honest-degradation path confirmed live (`graph_grounded=False`); upsert code real; GDS-removal rationale sound (zero `gds.*` refs). But Neo4j is STILL crash-looping (122 restarts) — stale corrupt `graph-data-science.jar` in the /plugins volume, which `NEO4J_PLUGINS=["apoc"]` does not remove (Gap 6, must-fix). |
| 5. A/B measured, 10 seeds, honest label | [x] | **YES** | Numbers reproduce from committed rows to the digit; 3-seed re-run direction matches; seed-7 loss honestly committed. |
| 6. 18/18 tests | [x] | **YES** | 18 passed re-run live, DB test included. |
| 7. Explainer | [x] | **YES** (exists, honest notes) | But it repeats the Gap-1 drill claim — must be corrected with AC-3. |

## 4. Gaps (must fix / ledgered)

1. **[MUST FIX BEFORE CLOSE — evidence quality, Rule 1a] The injected-latency-drill claim does not reproduce and
   its causal attribution is refuted by a control.** Claim (task doc AC-3, ADR "Measured outcome" context, explainer
   §5): "a 6×-median delay on the award-winning supplier was DETECTED live (`latency_spike@supplier:2`)".
   Findings (seed 42, the drill procedure as specified):
   (a) last-award-winning supplier (=4): delayed leads arrived (11.9–20.8 ks vs 2.7 ks median) yet NO detection in
   140 post-injection ticks — root causes: the winner had only 3 lead observations at injection (< MIN_OBS=6 →
   detector abstains, by design but undisclosed as a drill limitation) AND the 64-deep `lead_times_s` deque floods
   at ~30 delayed leads/tick so the baseline median shifts to the delayed level before `check()` can test against
   clean history (`disruption_monitor.py:77-93`);
   (b) most-awarded supplier (=2, 115 leads, clean baseline): a NO-INJECTION control produces a byte-identical
   latency-spike event stream — `latency_spike@supplier:2` fires at tick 90 in BOTH runs (a natural lognormal
   outlier: σ_log=0.4 ⇒ P(lead ≥ 2×median) ≈ 4 % per order), and the injection adds zero attributable events
   (the injected supplier received no post-injection awards in this seed → no leads → no signal);
   (c) no drill script was committed (grep `delay_next_delivery` → only `run_supply_ab.py` + sim internals), so the
   claimed detection cannot be reproduced from the repo.
   **Required fix**: commit a reproducible drill script WITH a no-injection control arm; re-measure; then either
   (i) fix the detector so an injected delay is attributably detected (e.g. log-space z, flood-resistant baseline
   snapshot, pending-order age signal — an order older than k×median is detectable BEFORE fulfilment), or
   (ii) correct the AC-3 / ADR / explainer wording to what is actually true (the latency detector fires on observed
   lead outliers; injected-disruption attribution is NOT established; the reliably-detected drill signal is the
   downstream starvation cascade). An unverified "DETECTED live" claim in three documents is exactly the Rule-1a
   class this project forbids.
2. **[LEDGERED → G-083, target Stage 27] Detector episode semantics + natural-outlier noise.** `_raised` (kind,
   subject) de-dup never resets (`disruption_monitor.py:53,109-114`) — "one incident per episode" is actually one
   incident per (kind,subject) PER MONITOR LIFETIME, so the first natural outlier permanently consumes a supplier's
   latency-spike incident and a later REAL disruption can never raise one. Combined with ~4 %/order natural
   2×-median outliers (18 latency events in a 140-tick undisrupted control), the latency incident channel is noisy
   first, then deaf. `test_normal_leads_do_not_false_positive` uses ±5 % synthetic leads and cannot see this.
3. **[MINOR] `paired_ci` hardcodes t=2.262 (dof 9)** for any n (`run_supply_ab.py:147-155`) — correct for the
   committed 10-seed run, wrong for any other `--seeds` (my 3-seed CI would need t=4.303). Compute t from n or
   document the 10-seed assumption.
4. **[BEFORE CLOSE] `audits/STAGE_26_audit.md:149-150` claims the `--no-baseline-drop` waiver is "Justified in
   `knowledge-base/KB_TASK_LOG.md` (Stage 26 entry)" — no Stage-26 entry exists yet** (KB_TASK_LOG ends at Stage 25
   with the `<!-- next entry: Stage 26 -->` placeholder). Forward-dated claim; the entry must actually land before
   close (close-task.sh enforces the entry; the justification text must be in it).
5. **[BEFORE CLOSE] Task-doc "Files to MODIFY" lists `compliance/risk-register.md` ("new supply-chain autonomy
   rows") — no Stage-26 rows exist** (grep: no supply-chain-autonomy row; register's own note defers to "Stage 26
   close"). Add the rows (multi-agent ordering autonomy, detector noise/deafness from Gap 2, CNP monoculture/
   exploration trade-off) before close. (`backend/agents/runtime/graph.py` also listed but unmodified — that one is
   covered by AC-1's honest in-process deviation note.)
6. **[MUST FIX BEFORE CLOSE] AC-4's "verified live post-fix" is REFUTED live: Neo4j is still crash-looping
   (RestartCount=122) and grounding returns False.** The compose change is applied (running env shows
   `NEO4J_PLUGINS=["apoc"]`) but the crash loop's actual root cause survives it: a stale, CORRUPT
   `graph-data-science.jar` remains in the container's `/plugins` volume from the interrupted download, and Neo4j
   loads every jar in `/plugins` regardless of `NEO4J_PLUGINS` — `docker logs`: `Caused by:
   java.util.zip.ZipException: Some jar procedure files (graph-data-science.jar) are invalid`. Fix: delete the
   stale jar from the plugins volume (or recreate the volume), verify the container reaches `healthy` and STAYS up,
   then re-run `ground_in_graph()` and record `graph_grounded=True`. Until then the AC-4 checkbox text (and the
   explainer's "container was re-fetching plugins during much of this build" framing, which implies it recovered)
   overstates what is live. I did not fix it myself (read-only persona).

## 5. What is solid (verified, credit where due)

- Zero fabrication in ~800 new lines: no RNG, no hidden-config reads, no invented stats, abstention everywhere.
- The safety gate is real and load-bearing (counterfactual analysis + 2 gate tests + e2e coupling).
- The closed material loop is a real sim extension (backpressured SimPy put; fulfil-only callbacks).
- The A/B is honest end-to-end: committed per-seed rows reproduce every headline number; an unfavourable seed is
  committed; direction re-reproduced independently; SimWorld-only scope + naive-baseline caveat stated in the JSON
  itself.
- The five in-loop defects narrative (ADR) matches code comments and is credible engineering honesty.
- KB_25 N-domain section, KB_01, KB_16 updates are real (non-trivial, accurate); research §37 predates
  implementation and sources the design; audit chain verifies green.

## 6. Re-run environment

Windows 11 host, system Python 3.11, Docker stack: PG@5544 (up), Redis (up), Neo4j (restarting at review time),
`DATABASE_URL=postgresql://aiagent:***@localhost:5544/manufacturing`. My drill/A-B runs appended real
`supply_chain.cfp`/`supply_chain.award` rows to the dev audit chain (outside pytest isolation, same as the
implementer's harness runs); chain verified green after (exit 0, 10 067 rows).
