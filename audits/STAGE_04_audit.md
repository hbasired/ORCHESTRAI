# Audit report — Stage 04

**Date**: 2026-06-01T04:50:28Z
**Task doc**: tasks/STAGE_04_predictive_maintenance.md
**Baseline**: 411
**Audit total**: 404

## 1. Audit script

```
Audit report (2026-06-01T04:50:24Z)
=============================================
  mock_predictions                  0
  hardcoded_responses_ts            0
  generate_mock_state               3
  hardcoded_models_ts               0
  random_uniform_py               148
  heuristic_actions                 3
  random_choices_py                 4
  random_choice_py                153
  generate_robots                   3
  get_demo_metrics                  0
  math_random_ts                   84
  mock_detections                   6
---------------------------------------------
  TOTAL                           404
---------------------------------------------
Baseline (from .audit-baseline): 411
OK: count decreased from 411 to 404.
```

Gate: total (404) must be **<=** baseline (411). Strictly **<** unless stage is flagged `--no-baseline-drop`.

## 2. KB diff coverage

Working-tree modified KB files:
knowledge-base/

Cross-check this against the task doc's "KB files this stage updates" block. Every listed KB file must have a non-trivial diff.

## 3. Missing artefacts

### Model cards / metrics
  (none)

### New ADRs (untracked decision logs)
compliance/decision-logs/

## 4. Vulnerabilities

### Gitleaks
```
(gitleaks not run — install gitleaks for secret scanning)
```

### Classical-crypto in backend/crypto/ (after Stage 13.5+)
  (none)

### Actuator paths without safety.validator reference (Stage 17+)
  (none)

## 5. Audit chain integrity

OK (quick verify passed)

## 6. Gaps (action items)

(Rectify each before `scripts/close-task.sh`. The closure script refuses if this section is non-empty.)

- [ ] (auto-generated from the checks above where applicable; populate manually otherwise)

