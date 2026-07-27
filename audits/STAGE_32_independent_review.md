# Stage 32 — Independent Review (Pilot-readiness package)

- **Stage:** 32 — Pilot-readiness package (docs-only; charter + capability-readiness matrix + A/B protocol + onboarding-kit §6)
- **Reviewer:** independent `task-auditor` persona — a DIFFERENT agent than the implementer (operator mandate, CLAUDE.md §6)
- **Date:** 2026-07-13
- **Nature:** DOCS-ONLY governance/pilot-prep stage → this is an **honesty / overclaim / number-provenance audit**, not a test re-run.

## TOP-LINE VERDICT: **PASS**

Every headline number in the package traces **exactly** to a closed-stage results file or the recorded Stage close.
No sim/benchmark number is presented as a real-world deployment result. The package repeatedly and explicitly states
that no real-world A/B has been run and that the real pilot is buyer-blocked (G-035/G-043). The charter carries the
predefined success criteria + all four decision gates + both hard gates. Audit holds at 3; no code was touched by this
stage. This is a clean pass — no close-blocking gaps.

---

## 1. Number-provenance spot-checks (the central adversarial test)

Every figure was re-derived from the raw results file or the recorded Stage close — not taken on trust.

| Claimed number (in matrix/charter/explainer) | Cited stage | Independent source checked | Verdict |
|---|---|---|---|
| Repair dispatch downtime **−47.9%, CI [7696,12733]s** | 30 | `repair_ab.json`: `downtime_saved_pct=47.9`, `ci95_saved_seconds=[7696.0, 12733.1]` | **EXACT ✓** |
| Supply-chain **stockouts −51%** | 26 | Recomputed from `supply_ab.json` 10 rows: greedy 106.3 → agentic 52.2 = **−50.9%** | ✓ (rounds to −51%) |
| Supply-chain **bullwhip −98%** | 26 | Recomputed: 74.28 → 1.21 = **−98.4%**; CI matches `paired_diff` bullwhip [48.98, 97.17] | ✓ |
| Supply-chain **material −73% (4918→1305)** | 26 | `paired_diff` orders_placed mean **3612.1**, CI **[3287.78, 3936.42]** ≡ matrix "(4918→1305, CI [3288,3936])"; KB_TASK_LOG L2021 | ✓ (metric = material/orders ordered) |
| Injection detector **0.9935→1.0, FPR 0.0156→0.0** | 31 | `detector_hardening.json`: baseline `0.9935/0.0156`, combined CV `1.0/0.0` (held-out 5-fold) | **EXACT ✓** |
| **C-MAPSS RMSE 13.80** (beats CNN/LSTM) | 8 | `stage08/cmapss_results.json` `test_rmse=13.803`; `model-cards/rul_transformer_cmapss.md` = 13.80 | ✓ |
| **GraphRAG grounded/honest-empty/citation-precision 1.0** | 28 | `graphrag_eval.json`: all three = `1.0` | **EXACT ✓** |
| **RL −125.1 vs −137.4, CI [6.0,18.71]** | 7/30 | `rl_intervention_maskable_ppo.metrics.json`: `-125.06`, `-137.42`, `ci95=[6.0,18.71]` | ✓ |
| **Demand LSTM MAE 32.9, +59% vs persistence** | 5/30 | `demand_forecaster.metrics.json`: `mae=32.909`, `improvement_over_persistence_pct=59.32` | ✓ |
| Active diagnosis **~0.87–0.97 conf in ~3–4 probes** | 29 | Matches recorded Stage-29 close (CLAUDE.md snapshot) | ✓ |

**No number was found that fails to trace to a real closed-stage result.** The one figure whose metric name could
mislead ("material −73%") reconciles precisely: it is the `orders_placed` paired-diff (material ordered), CI matches
the JSON to the digit. RUL is described as "beats CNN/LSTM" (accurate — the model card shows it does NOT beat the best
published Transformer, and the matrix does not claim SOTA). No inflation found.

## 2. No-overclaim audit

| Check | Finding | Verdict |
|---|---|---|
| Every capability row carries a readiness tag + real-data dependency | Matrix legend + per-row `SIM-PROVEN/BENCHMARK-PROVEN/BUILT/REAL-DATA-BLOCKED` tags + G-035 dependency columns | ✓ |
| Docs explicitly state NO real-world A/B has been run | Matrix "The honest bottom line": *"Nothing here is a real-deployment number."*; protocol §6 *"no real A/B has been run"*; explainer §4 *"NO real-world number exists"* | ✓ |
| Real pilot marked buyer-blocked (G-035/G-043) | Stated in every doc + ADR honesty notes; ledger G-043 = *"OPEN (buyer-blocked) — BUILDABLE PREP COMPLETE"*, G-035 = OPEN | ✓ |
| Hard gates framed as production PROPERTIES, not hypotheses | "0 unsafe actuations" + "chain verifies" labelled production-ready properties (they hold today), separated from the A/B hypotheses | ✓ |
| No sim result reads as a shipped/real-customer result | None found — every figure is labelled sim/benchmark and cited to a stage | ✓ |

## 3. Charter discipline

| Requirement | Present? | Location |
|---|---|---|
| Predefined success criteria + thresholds | ✓ | `pilot-charter-template.md §2` (S1–S6, each with a "sim precursor" + a customer-agreed threshold column) |
| Four decision gates (Scale / Iterate / Pivot / Stop) | ✓ | §5 — all four defined, tied to §2 |
| Two hard gates (0 unsafe actuations; chain verifies) | ✓ | §2 S5/S6 + §5 + protocol §3 (G-safety / G-evidence) |
| Guardrail metrics (no regression) | ✓ | §2 (throughput/cycle/quality/energy) |

## 4. Docs-only confirmation

- `bash scripts/audit.sh` → **TOTAL 3** (`mock_detections 0`, `math_random_ts 0`); equal to baseline, correctly closed
  `--no-baseline-drop` per the ADR/task doc (docs-only — markdown cannot introduce fakery patterns).
- Stage-32 deliverables are **all `.md`** (mtime 2026-07-13): `pilot-charter-template.md`, `capability-readiness-matrix.md`,
  `pilot-ab-protocol.md`, `pilot-onboarding-kit.md` (§6), + `research/stage-explainers/STAGE_32/index.html`, KB_26 §13,
  research §43, ledger G-043 note.
- No new code files. The only code files with a 2026-07-13 mtime belong to **Stage 31** (`security/injection_classifier.py`,
  `behavioral_monitor.py`, `prompt_guard.py`, `training/evals/redteam/detector_hardening_eval.py`) and **Stage 30**
  (`scripts/run_repair_ab.py`) — pre-Stage-32 cumulative work, none related to pilot-prep. New deps: none.
- Research-first mandate met: `research/initial-research.md §43` (§43.1 pilot discipline, §43.2 A/B protocol) appended
  before writing; explainer HTML present and honest (all 5 numbers in its table verified above).

## 5. Minor observations (NOT close-blocking, NOT gaps)

- `grep -c "G-035"` on the matrix = 3 (the G-035 dependency appears as a column header in the 3 tables where re-fit is
  the dependency). The Safety/Security and Platform tables use "Pilot gate"/"Notes" columns instead, but every row in
  them still names its real-data dependency inline (e.g. "certified PLC + accredited assessment (G-011)", "production
  node attestation", "real runtime behaviour baseline"). The caveat is present per-row throughout; the literal G-035 tag
  simply isn't on the rows whose blocker is G-011/attestation rather than data re-fit. Correct, if slightly uneven.

## Bottom line

**PASS.** Stage 32 ships exactly the disciplined pilot package it claims: a charter with predefined success criteria +
Scale/Iterate/Pivot/Stop gates + two hard gates, an honest sim-vs-real capability matrix in which every measured number
was independently traced to a closed-stage results file (repair, supply, detector, C-MAPSS, GraphRAG, RL, demand,
active-diagnosis — all confirmed), an A/B protocol reusing the real Stage-6/26/30 harnesses, and an extended onboarding
kit — with no sim number dressed as a real result and the real pilot honestly held OPEN/buyer-blocked (G-035/G-043).
Audit holds 3; no code touched. Cleared to close.
