# Stage 6 — Vertical Slice v0 A/B (measured)

Generated: 2026-07-20T05:36:40.638648+00:00 · seeds [42, 43, 44] · 8.0 sim-hours/arm
Scenario: machine_crack campaign (rotating stages, calibrated defaults)

| metric | loop OFF | loop ON | delta (OFF−ON) |
|---|---|---|---|
| unplanned downtime (min, mean) | 470.27 | 279.74 | 190.53 |
| total downtime incl. planned (min, mean) | 470.27 | 319.4 | 150.87 |
| crack-induced breakdowns (mean) | 4.33 | 1.33 | — |
| throughput (units/hr, mean) | 6.96 | 6.92 | -0.04 (ON−OFF) |

## Paired bootstrap 95% CIs (richer A/B — CRN-paired over seeds)

| metric (OFF−ON, throughput ON−OFF) | mean | 95% CI | significant? |
|---|---|---|---|
| unplanned_downtime_min | 190.53 | [68.91, 346.03] | True |
| total_downtime_min | 150.87 | [48.91, 301.03] | True |
| crack_breakdowns | 3 | [0, 5] | False |
| throughput_units_per_hour | -0.04 | [-0.37, 0.24] | False |

Loop pipeline (ON arm): `predict→forecast_ttf→causal_diagnose→shap_explain→neuro_symbolic_verify→intervene` — the Stage-6 depth-hardened loop wires the Stage-8 TTF forecast + learned-causal diagnosis + Stage-10 SHAP explanation + the neuro-symbolic plan verifier (which approves the single-machine maintenance, so the measured numbers are preserved).

Honesty: measured output of seeded simulation runs; both arms share seeds and code, differing only by the SliceLoop process. With few seeds the CIs are wide (truthfully). Accounting caveats in the script docstring.