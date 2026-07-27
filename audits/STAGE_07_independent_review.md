# Stage 07 — Independent Review

**Stage**: 07 — RL Intervention: PPO policy over the Stage-6 decision contract
**Task doc**: `tasks/STAGE_07_rl_policy_intervention.md`
**Reviewer**: fresh `task-auditor` (read-only) — did NOT implement Stage 7
**Date**: 2026-06-13
**Verdict**: **PASS**

---

## Independence statement

I did not write, train, or wire any Stage-7 artifact. I read only the files named in the audit brief
(env/ppo/intervention_rl/intervention_policy/train/eval, the metrics + eval JSON, the model card, the ADR, the
test file, the mechanical audit, the task doc), re-ran the named tests and the audit, and re-ran the eval on
**fresh seeds I chose** to test for seed cherry-picking. I fixed nothing. My one output is this file. The
headline claim under audit is a *deliberate negative-vs-rules result* (PPO learns but does not beat the
near-optimal rules); my job was to verify that claim is **honest and reproducible**, not to demand a PPO win.

---

## What I ran (real output)

### 1. Stage-7 RL tests — `pytest tests/test_intervention_rl.py -q`
```
..............                                                           [100%]
14 passed in 7.47s
```
Matches the claimed 14 passed. (The 5 weight-dependent tests did NOT skip — weights are present and load.)

### 2. Stage-6 no-regression — `pytest tests/test_slice_intervene.py tests/test_slice_ab.py tests/test_diagnosis.py -q`
```
21 passed, 1 warning in 4.69s
```
Zero regression on the Stage-6 slice/diagnosis suites.

### 3. Mechanical audit — `bash scripts/audit.sh`
```
  TOTAL                           396
  Baseline (from .audit-baseline): 396
  NO PROGRESS: count is equal to baseline (396).
```
Flat at 396 == baseline. Flat is the declared, justified outcome for an additive ML stage (`--no-baseline-drop`,
ADR D6). No NEW theatrical pattern was introduced (grep of the Stage-7 dir + `intervention_rl.py` for
`random.*|Math.random|generateMockState|_get_demo_|RESPONSES = {|MODELS = [` → **no matches**).

### 4. Fresh-seed eval (cherry-pick check) — `python training/stage_07_rl_intervention/eval.py --seeds 50,51,52,53 --sim-hours 2.0`
```
no_intervention : crack_breakdowns 4.0  ± 0.8
rules_priority  : crack_breakdowns 0.5  ± 0.566
ppo_shield      : crack_breakdowns 0.75 ± 0.49
paired PPO-rules diff: 0.25 +/- 0.49
ppo_beats_rules=False  default_chooser=rules
```
**The negative result reproduces on seeds the implementer never used.** Rules near-optimal (0.5 breakdowns),
PPO does not beat them (0.75), `ppo_beats_rules=False`. Not seed-cherry-picked.

### 5. Reproducibility of the committed numbers — re-ran the canonical 8 seeds (42–49)
```
no_intervention 4.0 ± 0.524 · rules_priority 0.375 ± 0.359 · ppo_shield 0.875 ± 0.245 · diff 0.5 ± 0.37
```
Reproduces the committed `results.json` **exactly**. (Note: running eval.py rewrites `results.json`; I
re-ran the 8-seed canonical set last so the committed file is left in its as-shipped state.)

Three independent seed sets — train-eval 7–12 (`metrics.json`), report 42–49 (`results.json`), my 50–53 —
all show the same direction: rules ≈0.4–0.5, PPO ≈0.75–0.9. The finding is robust.

---

## Findings per acceptance criterion

| AC | Claim | Confirmed? | Evidence |
|---|---|---|---|
| AC1 — RL env (capacity-1 crew, event-driven, shaped reward) | [x] | **YES** | `env.py:74` `InterventionEnv`; capacity in env not SimWorld (`env.py:177` `_crew_busy_count >= crew_capacity`); event-driven decision points (`env.py:175,226`); reward sign/throughput/breakdown/shaping (`env.py:201-224`); determinism + shape + reward asserted in `test_intervention_rl.py:25-64`. |
| AC2 — Real PPO, trained, improves | [x] | **YES** | Genuine PPO-clip + GAE (`ppo.py:84-96` GAE, `ppo.py:131-137` clipped surrogate + value + entropy). Bandit test proves the optimiser learns (`test_intervention_rl.py:78-96`, ran PASS). Metrics record real curve −160.8→−134.0 with `training_learned=True` computed from data (`train.py:181`). |
| AC3 — Inference glue + honest unavailability | [x] | **YES** | `intervention_rl.py:72-92` raises `ModelUnavailableError` if torch OR weights absent — never fabricates. `test_intervention_rl.py:127-132` (ran PASS). `weights_only=True` on load (`ppo.py:157`). |
| AC4 — Safety shield forces maintenance at critical proximity | [x] | **YES** | `env.py:372-389` + `intervention_rl.py:39-54` force highest-risk machine when crew free AND risk ≥ 0.85. `test_shield_forces_maintenance_on_critical_proximity` asserts action overridden to 4 from both 0 and 10 (`test_intervention_rl.py:101-108`, ran PASS); busy-crew + below-critical pass-through also tested (`:111-123`). |
| AC5 — Honest 3-way eval, CRN pairing + CIs (G-046) | [x] | **YES** | `eval.py` runs none/rules/ppo on the SAME paired seeds (`eval.py:50` `base_seed + s`), reports 95% CIs (`eval.py:38-47`) + paired PPO−rules diff (`eval.py:107-119`). Report `results.json` flips default to RL **only** if `ppo_bd <= rules_bd` (`eval.py:123,130`) — it does not, so `default_chooser="rules"`. Reproduced live (above). |
| AC6 — Pluggable chooser, contract unchanged | [x] | **YES** | `intervention_policy.py:125-143` `select_chooser("rules"\|"rl")`; `DEFAULT_CHOOSER="rules"` (`:122`). RL path returns a real `InterventionDecision` (`intervention_rl.py:104-130`); `test_rl_decide_returns_intervention_decision` asserts the shield-forced stage id (`test_intervention_rl.py:162-172`, ran PASS). Granularity difference (per-machine rules vs fleet RL) disclosed honestly in the docstring + ADR D5 — not faked. |
| AC7 — Model card + KB | [x] | **YES** | `compliance/model-cards/rl_intervention_policy.md` is Annex-IV-shaped (intended use, training env, reward+shield design, limitations, seed, eval table, contact). KB_02/05/23/25 show in the working-tree modified set (mechanical audit §2). The card's eval table matches `results.json` numbers. |
| AC8 — Tests green + no regression + zero new theatre | [x] | **YES** | 14 RL + 21 Stage-6 slice tests pass (above); audit flat at 396 with no new pattern. |
| AC9 — Independent audit PASS | [ ]→ | **THIS FILE** | PASS (below). |

---

## Theatrical-work scan

- Grep of `backend/training/stage_07_rl_intervention/` and `backend/ml/intervention_rl.py` for the banned
  fakery patterns → **no matches**. The reward, the PPO update, the eval, and the "learned/beats-rules/default"
  flags are all **computed from measured values** (`train.py:166,181,185-186`; `eval.py:123,130`), not literals.
- The bandit test (`test_intervention_rl.py:78-96`) is a *real* training run with a behavioural assertion
  (`np.mean(hist[-5:]) > np.mean(hist[:5]) + 1.0`) — not a no-op/always-pass. It genuinely proves the optimiser
  learns, decoupled from the hard sim env.
- The 396 audit count is the *whole-repo* fakery total, not Stage-7-introduced fakery. Stage 7 added zero.

## No-bypass / no-regression checks

- `git status` / `git ls-files`: `backend/simulation/sim_world.py` is the only one of {sim_world, slice_runner,
  diagnosis, intervention_policy} tracked in the single commit, and it shows **no modification** — so Stage 7 did
  not touch SimWorld. `slice_runner.py`/`diagnosis.py`/`intervention_policy.py` are Stage-6/7 untracked additions.
  The "sim_world.py / slice_runner.py unchanged by Stage 7" claim (ADR D2/D5, task as-built note) holds.
- No `--no-verify`, no `--force`. The only gate flag is `--no-baseline-drop`, declared up front for an additive
  ML stage, with the justification recorded in the ADR (D6) and the task doc's Audit-target section.
- `weights_only=True` (`ppo.py:157`) — checkpoint holds only tensors + ints; no pickle code-execution surface.

---

## Judgement calls (requested)

**Honest negative-result framing — LEGITIMATE.** The "PPO does not beat rules → rules stay default" result is
reported everywhere and never hidden: `metrics.json` (`ppo_beats_rules_on_crack_prevention:false`),
`results.json` (`default_chooser:"rules"`), `intervention_policy.DEFAULT_CHOOSER="rules"`, the model card's
"Honest finding" section, and ADR D4. The decision is *data-driven* (`eval.py:123` derives it from the measured
breakdown counts), reproduces on three independent seed sets, and the implementer explicitly rejected
"force PPO to beat rules" (ADR alternative #1). This is exactly the "better policy wins, not the fancier one"
discipline the task mandates. I would have failed a stage that buried a marginal contrived "win"; this does the
opposite, honestly.

**`--no-baseline-drop` (leaving `ml/rl_policy.py` + `decision_engine.py` to Stage 11) — HONEST, not dodging.**
Those files are a separate robot-navigation/decision-engine subsystem unrelated to the intervention path Stage 7
extends. Two failure modes were correctly identified and avoided (ADR D6, alt #3): (a) entangling two subsystems,
or (b) deleting grep-counted lines while leaving grep-invisible untrained-model fabrication — i.e. gaming the
metric down without removing real fakery. Deferring with a named target stage (11) and a ledger trail is the more
honest path than a cosmetic baseline drop. I concur. (The deferral is already on the ledger via G-044 / D6.)

**Reward shaping (`risk_exposure_cost`) — LEGITIMATE objective-aligned shaping, NOT answer-baking.** The shaping
term (`env.py:217-223`) penalises the *sum of risk of unattended at-risk machines* — it pushes a free crew not to
idle while machines degrade, but it does **not** encode which machine to pick; prioritisation must still be
learned from the breakdown penalty term. It is dense (per sub-step) and points the same direction as the true
objective (fewer breakdowns), so it does not distort the optimum. Critically, even WITH this shaping PPO still
loses to rules — if the shaping had pre-baked the answer, PPO would have matched/beaten the rules. The shaping is
disclosed in the EnvConfig comment, the model card, and ADR D2. I see no gaming.

---

## Gaps

**None blocking.** No new gaps for the ledger. The honestly-deferred items (full multi-action RL win → Stage 8/11
under G-025; real-telemetry re-fit → Stage 22 under G-035; `rl_policy.py`/`decision_engine.py` de-mock → Stage 11
under ADR D6 / G-044) are already recorded against named target stages in the task doc hand-off and ADR, so the
system will surface them when those stages start. No action required to ship Stage 7.

Minor (non-blocking) note: the train-time observation slot is fed ground-truth `crack_proximity`
(`use_predictor:false`) while inference can feed predictor `p_fail` — this train/inference signal gap is honestly
disclosed in the env docstring (`env.py:16-21`), the model card, and ADR (gated by G-035). Not a defect; flagged
for completeness.

---

## VERDICT: **PASS**

Every acceptance criterion (AC1–AC8) is backed by code I read at the cited lines and tests/commands I re-ran. The
PPO is real (genuine clipped-surrogate + GAE, bandit-verified). The safety shield really overrides the net at
critical proximity. The inference glue raises `ModelUnavailableError` and never fabricates. The "rules stay
default" claim is data-derived, reproduces on fresh seeds I chose, and is reported honestly across metrics/eval/
card/ADR/code. Zero Stage-6 regression; `sim_world.py` provably untouched; `weights_only=True`. The
`--no-baseline-drop` and the reward shaping are both honest, not metric-gaming. This stage may close.
