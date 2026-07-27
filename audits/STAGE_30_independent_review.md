# Stage 30 — Independent Review (Live-wire the self-healing loop)

- **Reviewer:** independent `task-auditor` agent (did NOT implement Stage 30)
- **Date:** 2026-07-13
- **Scope:** G-005 repair dispatch · G-025-tail RL shadow · G-036 demand-forecaster serving
- **Method:** adversarial code read + re-ran the tests, the A/B, the audit, and the chain verifier myself.

## TOP-LINE VERDICT: **PASS** (one minor, non-close-blocking statistical nit; ledgered)

The stage is honest and real. All three claimed subsystems are genuinely wired, the safety gate is
load-bearing, the RL shadow never actuates, the fabricated `confidence` constant is genuinely removed,
and the headline downtime reduction reproduces independently. No theatre, no bypass, no Hard-Rule-3 breach.

---

## Claim-by-claim table

| # | Claim | What I measured | Verdict |
|---|---|---|---|
| 1 | G-005 repair A/B is real (−47.9% downtime, CI excludes 0), mechanism = interruptible `repair_assist` | Re-ran `run_repair_ab.py --seeds 3 --hours 4`: seed42 saved 6681s, seed43 11031s, seed44 8558s → **mean 8757s (48.2%), 95% CI [5986,11528], excludes 0**. Real dispatches per arm (16/12/9). Mechanism confirmed in `stage.py::_failure_loop` (interruptible while-loop) + `repair_assist` cutting `remaining`. | **CONFIRMED** |
| 1b | Passive (no-dispatch) downtime unchanged from legacy | Read the `stage.py` diff: with no interrupt the loop does one `yield timeout(remaining)` for the full `t_repair` and adds all of it to `time_broken_seconds`; `_repair_pending_reduction` defaults 0.0. Byte-equivalent to a plain MTTR timeout. | **CONFIRMED** |
| 1c | `repair_assist` is a no-op on a non-broken stage (no fabricated benefit) | `stage.py:125` guards `if self.status != "broken" or not self._awaiting_repair: return False`. Test `test_repair_assist_is_noop_on_a_recovered_stage` asserts it returns False on a nominal/degraded stage. | **CONFIRMED** |
| 2 | Hard Rule 3 — award routes through `safety/validator.validate()` under `repair_dispatch` contract BEFORE any effect; non-broken → gate-blocked; no-robot → honest no-award; no actuator bypass | `dispatch.py::award` calls `validate(action, world_state, REPAIR_DISPATCH_CONTRACT)` and sets `allowed=decision.allow`. `dispatch_repair` only calls `world.request_repair(...)` when `aw.allowed and robot_id is not None`. Precondition `stage_is_broken` blocks non-broken (test `test_gate_blocks_dispatch_to_a_healthy_machine`). No-bid path returns `robot_id=None` honest no-award (test `test_honest_no_award_when_no_robot_available`). Sole effect path is gated; no direct actuator emitter. | **CONFIRMED** |
| 3 | G-025 RL shadow NEVER actuates; logged-not-acted; gated by `RUNTIME_RL_SHADOW` (off by default); honest-unavailable when SB3 absent; doesn't change the runtime decision | `nodes.py::decide` keeps the rule `dec` as `decision`; shadow only appended to `decision["provenance"]["rl_shadow"]`, behind `shadow_enabled()`. `rl_shadow.py` returns `available=False` when SB3/policy absent (no fabricated action). Ran `test_rl_shadow.py -v`: all 3 **PASSED (not skipped)** — SB3 present, shadow genuinely runs and asserts `"NOT drive actuation" in note`. Determinism test passes with shadow off. | **CONFIRMED** |
| 4 | G-036 removed the fabrication — legacy `confidence = max(0.7, 0.92 - i*0.03)` GONE; served from real LSTM/empirical/honest baseline (`lower_bound: None` in baseline) | `git diff` shows the `confidence` line and the whole placeholder block **deleted** (`-` lines). Grep of `state_manager.py` finds `confidence` only in a comment. `demand_forecast_service.py` path 3 returns `lower_bound: None`, `served: False`, no confidence key. Tests assert no `confidence` key + `None` bounds + provenance surfaced in live state. | **CONFIRMED** |
| 5 | No fabrication / free-cost; new deps = none | Grep for `random.*`/`np.random`/mock in `agents/repair/` → **no matches**. `git diff requirements.txt` → no additions (only a CRLF warning). Audit constants in `dispatch.py` are documented modelling constants, not RNG. | **CONFIRMED** |
| 6 | Audit holds 3; chain verifies; determinism holds; 13 stage tests pass | `audit.sh` TOTAL **3** (= baseline; 3 residual `heuristic_actions` are the documented G-052 name-pattern false-positive). `verify-audit-chain.py` **exit 0** (10469 rows; all 10390 post-cutover sigs verify). `test_runtime_determinism.py` 1 passed. Stage suite **13 passed / 0 skipped**. | **CONFIRMED** |

---

## Commands I ran (real outputs)

```
$ python -m pytest tests/repair/ tests/services/test_demand_forecast_service.py tests/runtime/test_rl_shadow.py -q
13 passed, 3 warnings in 36.33s

$ python scripts/run_repair_ab.py --seeds 3 --hours 4 --out /tmp/rev_repair.json
seed 42: control 20878s  dispatch 14197s  saved 6681s  (16 dispatches)
seed 43: control 19322s  dispatch  8292s  saved 11031s (12 dispatches)
seed 44: control 14274s  dispatch  5716s  saved 8558s  (9 dispatches)
mean downtime saved 8757s (48.2%), 95% CI [5986, 11528]  (excludes 0: True)

$ bash scripts/audit.sh
  heuristic_actions                 3
  TOTAL                             3
Baseline (from .audit-baseline): 3

$ python scripts/verify-audit-chain.py
Audit chain OK (10469 rows; hash chain intact; all 10390 post-cutover signatures verify)
EXIT=0

$ python -m pytest tests/agents/runtime/test_runtime_determinism.py -q
1 passed in 71.63s

$ python -m pytest tests/runtime/test_rl_shadow.py -v
test_empty_fleet_is_honest_unavailable PASSED
test_shadow_recommendation_is_logged_not_acted PASSED
test_rule_baseline_targets_the_highest_risk_zone PASSED

$ git diff HEAD -- backend/services/state_manager.py | grep confidence
-                "confidence": max(0.7, 0.92 - i * 0.03)      # (deleted)

$ grep -r "random\.|np.random|Math.random" backend/agents/repair/
(no matches)

$ git diff HEAD -- backend/requirements.txt   → no dependency additions
```

## Gaps found

| ID | Severity | Close-blocking? | Note |
|---|---|---|---|
| — | **Minor** | **No** | `run_repair_ab.py::_ci95` hardcodes `t = 2.262 if n==10 else 2.2`. For a non-default seed count the 2.2 constant understates the Student-t critical value (n=3 → t≈4.303), so a small-n CI is optimistically narrow. The **headline claim uses n=10 with the correct t=2.262**, so the reported result is unaffected; and even the widened n=3 interval still excludes 0. Cosmetic/methodological only. |
| — | Info | No | The repair effect is SimWorld-internal (`request_repair` emits no `actuator.*` OTel span), so the CI trace-pairing invariant is not triggered — correct, and honestly disclosed (robots have no physical position; real actuator dispatch = pilot). The safety gate still fires (`safety.validate`) before the effect. |

No theatre, no faked tests, no gate bypass, no Hard-Rule-3 violation, no fabricated constants found.

## Bottom line

**PASS.** Every Stage-30 claim reproduces against the real code and live commands: the repair A/B genuinely
reduces downtime (48.2% on my 3-seed re-run, CI excludes 0) via an interruptible-repair mechanism whose
passive path is byte-equivalent to legacy; the award is safety-gated before any effect (Hard Rule 3 intact);
the RL shadow genuinely runs yet never actuates and is off by default; and the fabricated per-day `confidence`
constant is genuinely removed in favour of an honest served/baseline forecast. Audit holds 3, chain verifies
(exit 0), determinism holds, 13/13 stage tests pass, no new deps. The single finding (small-n CI t-value) is
minor and does not affect the reported n=10 result — **not close-blocking. Cleared to close.**
