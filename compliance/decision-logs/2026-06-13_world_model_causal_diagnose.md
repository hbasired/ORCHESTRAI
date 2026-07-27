# ADR — Stage 8: Learned World Model (TTF) + Causal Attribution v1

**Date**: 2026-06-13
**Status**: Accepted
**Stage**: 8 (World model + causal diagnose — KB_25 steps 1–2)
**Author personas**: `ml-engineer` (primary) + `backend-engineer` (diagnosis wiring) + `agentic-governance-engineer` (ADR)
**Relates**: builds on Stage 6 (slice + `diagnosis.py`) and Stage 7 (`2026-06-12_rl_intervention_ppo.md` — the RL that lacked a timing signal). Resolves **G-019**; partially advances **G-020**.

---

## Context

KB_25's self-healing loop step 1 (PREDICT) calls for a learned world model (its example: *"LSTM predicts M fails
in ~8 min"*); step 2 (CAUSALLY REASON) calls for a causal digital twin with counterfactual root-cause. Stage 6
shipped instantaneous failure-risk (`p_fail`) + deterministic rule-based diagnosis; Stage 7's RL intervention
could not exploit *timing* because it had no time-to-failure (TTF) estimate. The `world_model.py` file was a
theatrical stub (`np.random.randn` fallbacks, untrained-random-weights "is_loaded"). The ledger flags G-020 as
research-grade ("research spike before").

## Decisions

**D1 — Learned world model = TTF forecaster (G-019), real + trained + free/local.** `backend/training/stage_08_world_model/`
generates (telemetry-window → ground-truth TTF) data from seeded SimWorld crack rollouts and trains a small LSTM
regressor (`models/world_model_ttf.{pt,metrics.json}`). torch CPU + numpy + the simulator only — no external
dataset, no paid services. **Measured: TTF MAE 0.067 min vs naive mean-TTF baseline 2.979 min (+97.8%)**, and
0.070 vs 3.230 (+97.8%) on disjoint fresh seeds — a genuine, reproducible win.

**D2 — Honest task design (no leakage).** Crack ETA is randomised (8–20 min) so a snapshot under-determines
absolute TTF; the model wins by reading the degradation *rate* across the 6-sample window (revealing the ETA).
This is legitimate temporal inference. The simulator is clean/low-noise, so the 0.067-min figure is a sim number,
not a real-world claim (G-035).

**D3 — `world_model.py` de-mocked.** Rewritten to an honest `WorldModel.predict_ttf(window)` that raises
`ModelUnavailableError` when torch/weights are absent (mirrors `failure_predictor`); the `np.random.randn`
fallbacks and untrained-weights path are removed. `decision_engine`'s legacy `predict()` call is wrapped in
try/except, so it degrades gracefully to its own fallback rather than on fabricated predictions. `weights_only=True`
load (no pickle exec surface). `test_models.py::TestWorldModel` + the integration test updated to the honest
contract.

**D4 — Causal attribution v1 (G-020 partial), behind the same `Diagnosis` interface.** `services/diagnosis.py`
gains `attribute_cause(...)` — a do-operator counterfactual over the KNOWN SimWorld structural causal model
(KB_05): classify the at-risk verdict as `machine_local` vs `externally_influenced` vs `indeterminate`. It rejects
confounders (a genuine wear fault co-occurring with a power_dip stays `machine_local`; a power-anomaly driven by
an active power_dip is `externally_influenced`). Added as a back-compatible `Diagnosis.causal_attribution` field
(existing fields unchanged).

**D5 — Honest scope boundary (no overclaim).** What shipped is a counterfactual over a KNOWN structure + a real
trained TTF model. **NOT** learned causal DISCOVERY, and **NOT** neuro-symbolic VERIFICATION (KB_25 step 3). Those
remain PLANNED — G-020 stays open, targeted at Stage 17 / a research spike. The causal headroom is also limited at
current sim fidelity (external incidents barely perturb the AI4I risk axes), so the attribution is deliberately
bounded and stated as such — not sold as a full causal twin.

**D6 — Audit baseline held at 396 (`--no-baseline-drop`).** Additive ML stage: a trained TTF model + causal
attribution v1. It de-mocks `world_model.py` by removing `np.random.randn`, but those are NOT in the `audit.sh`
grep pattern set (grep-invisible theatre, same class as G-047), so the counted baseline holds flat honestly. No
in-lane grep-counted theatre exists (remaining counted hits live in Stage-9/10/11 files: explainability,
neural_networks, robotics/supply-chain heads, frontend). Justified in `KB_TASK_LOG.md`.

## Why

- TTF is the missing timing signal: it directly feeds smarter intervention (Stage 11) and is a genuine, measurable
  capability gain, unlike forcing an RL win on a near-trivial decision (Stage 7's honest finding).
- A counterfactual over the KNOWN structure is rigorous and honest (the SCM is documented), and it is the right
  v1 before investing in research-grade causal discovery — which the ledger itself flags for a spike.
- De-mocking `world_model.py` removes real (if grep-invisible) theatre — the honest move even when the counter is unaffected.

## Consequences

- New: `backend/training/stage_08_world_model/{rollouts,train,eval,config}.py`,
  `models/world_model_ttf.{pt,metrics.json}`, `backend/tests/test_world_model.py`,
  `compliance/model-cards/world_model_ttf.md`, `research/stage-explainers/STAGE_08/`,
  `training/evals/stage08/results.{json,md}`.
- Modified: `backend/ml/world_model.py` (honest rewrite), `backend/services/diagnosis.py` (+causal attribution,
  back-compatible), `backend/tests/test_models.py` (honest WorldModel contract).
- Audit **396 → 396** (`--no-baseline-drop`). 72 tests pass across world-model/diagnosis/models/slice/RL/predictor.
- **G-019 RESOLVED** (learned world model BUILT + measured). **G-020 PARTIAL** (counterfactual v1 over known SCM;
  learned discovery + neuro-symbolic verify remain → Stage 17 / spike). G-035 still gates real-telemetry claims.

## Alternatives rejected

1. **A full causal digital twin + neuro-symbolic verifier now.** Rejected: research-grade (ledger flags a spike);
   limited headroom at current sim fidelity; would risk Stage-7-style machinery with little real value. Bounded v1 + honest deferral instead.
2. **Keep `world_model.py`'s stub and add a new file.** Rejected: `world_model.py` IS the G-019 file; de-mocking it is the honest, in-scope move.
3. **Train on fixed-ETA cracks (easier, near-perfect TTF).** Rejected as too easy/leaky-looking; randomised ETA makes the task honest temporal inference.
4. **Couple the TTF model into `diagnose()`** (diagnosis only has a snapshot, not a window). Kept separate: world model = `predict_ttf(window)`; diagnosis = snapshot causal attribution. The slice/Stage 11 will combine them.

## References

- Metrics: `models/world_model_ttf.metrics.json` · Eval: `backend/training/evals/stage08/results.json`
- KB_25 (steps 1–2), KB_05 (sim/SCM), KB_23 (eval), KB_02 (model inventory).
- Tests: `backend/tests/test_world_model.py`, `backend/tests/test_diagnosis.py`.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:29+00:00 -->
<!-- signature: mGk5O6XrvK+dppIF719t1dqPs6v+G6zvSYOQcqcr1zIhC/AQNLDwuDG2JUvTH9ntvMOuLIDhlIBPy/RlvXOMwtrVjv4Qes7Ay8Oj5T213N8XDOx6T61xiAJlVoFabbR6JCBnDeKC4stxDPsRCW1ruUe9F2uq74aTgSJ2uYI+WGPGx9VjPNcsKYXUbZhSHzUohCyOhGpxWqGCr4foiV5FZ8GTYxmDf/zj7dIkdpBHRebkax+RoHfPMZwhr2jRXahxshQ4IITvITJgHH/8pDrOBbtWKtRG+Aou2CbsQ81NEn77fD3pfd7ia1SXAC6zaI0+jCap6a4yvVkiGFUXqcZcWxQq3RmhM2Dk6mekkr/9PbzoVwFEr2QMle56KiAonkYvq4DYLiCxJbQxwCL+IpKiYwf1ZSpJ9WpvmaiNoDwePm20f3jvVGOn3MCo6NkC/FASo17yDgpb00ibJ4CzomNF+rgXpqVrAnRuxeET3nfObWeVbWKEd/oAveT2BIgS9ENcZyyDD/3awC+j1YMxgY4UWQtgznjkweG3PX/sQTi3ZbxVDtEieHaZzdHaSXnl8PnnLBLMEh7Nxx1d8Z5GOmSZ2z/FoAS/lpsNWz9pZWDPagb+qCuMCsLiKvx0Zkd010Oc2j/CsrgYxdM6tTPZtsu/OINa+U2qXcK9LoGdi+A+BYDhqnu31KXu9/BoHWolzwB2NiIj/WegyUN63hA+t0TQrnH+3/K7Zrz1XW/tWI4iVLBxUTEzEHaOCZg0L4s7+YG3Vlhz+pOcCFZ14xBooYbZXuJ+4vOuLcksrurY/kJYDWA35/M1fXypVfwrfIP+Ac3a05uo8JwFxecrDweKPlb98iH1MgUKwW0A147Q6fUtD69JG9bxv/w6vAcnmEkBGmn3ck+k/aPddVPJSzlrCkHUE7l1XKnQyiQdzoZ4yFHcX5uuJTVHm6Z0E0HQSZiPLulGkpGGGR5qx5EyEMFvuLrjU5LdbT2ZwyTUoPJsJee2/llDf7S9SSq4K9vh5DRhPRFmPtjIFkYDKO7RYBeZUHErLZqFPxxZBCzM1SFft5ulPfD+Kf6Bu0TWNhq4UChdkWfl/q00IfN6N6WnO4ZcBWlXi1DA3uWeKDxPGL2n2fOyoFS4ltXWP5uG61/vJx1XI+xe6nFPmQtIANqwtkbwf5sNwvPAdaVVCyqpXBfDqU7Tqq1OpV2Kr+QvPiYvF2if8Y4q1a34LlT4igcZvfxkEY0HOvABUCzAcBDabOv/70r5G2nbx9bDMukVnnM+6lJTF20zoOrRdntIL5NcK9WlqAY5dB5RRPU5mBrhkaw0RJ75gLX6dmK3+quu0V9HFniGwdxS6Ddlv9PD0vp9hKqGampvJvXZ/MVj7v+iHvTTkgMu4L2LCPkJqOpZM6KVb2/CHVzOyiCYjRm6E9SSrWdgedL7v92K/2PMObjjy28H0NLfwC6AbO0b0VgUsVSRW+C0mki+gTszBEKztMusEIUqJJFhfjbIXptYAgwDO/IOcdab9OyErma7F4/3E4rChIWZoxp2hztrcWRxRdas3EExnVZogN/SCTZFftqvEGavKgg1OwwAepMGrXypGvzaGSxN9RvRhOdMRVNswowoL7wxG1TanBeQH7npWx/9tZckgBOrBn2zexV9LuZIjG3oavRyOIxIWQsayfaMFrKP3IcB5oH3yyHGLS4fSMA2eZEq79FC0jLpGFkVhxZ7G0X/YAeWA9E0BWx+yN1UuqsvqRyUJmDxOhpPnVWDMjoYSXgQQp6f1fJxi+tNJaR9giM3vHG4AUlE7Nm8vOdRk0+xAdbEw0EHOiYwukQg5hkxKq1W+7F3GWWZL6OM4JMKILXR4ADuL3OYh5LwEP+6KdP9HZQLRPoEIXBeXBfDi7YWIdNGZzvninr4QpiccWmcZEw7L3Ew5zcbuvi9V+NNU/fFrvB639Iy0NqbjaYUKvI9jWLhe6kKRQinZ8HXeVuVqE+sucNJVUhhHA32V5AYRCRbp07+btPY1mJC5j9Cy9ZBD8wAcbXoA61gfQytqWXeduXyAvlUrcDiz8g51zfyd+HRXwua6VOC1YPqkc5cabxuE+7Egj9pSuvT0/KmqI1H8VDdHiu4qNthbelFS0R/m3FEa/RLFILZs2tHh2xFG3S3LxaEZxRZJbNMspFhRdbeDI1JGZmRWK8nfLU8gP0h22mTEyhoL8jb6bT1N+W9fF4SmUMrcMSBQ83bVj9rqUsKHHAKVAvOuop8xgdenlsU6WDj9Oax4XUP+SWHDo1lXJ2zWkAmr4pireAX79x9vz3PEXBw1SGe6TEBUA/rMP9Hv3fHmTZrnNn8xb/ZhXbt6UJ5Q2j9szgHYBYMxq6FHuoIyatQPyuw9s3V0TnseWBfpq/fOxDBNKMoQfuGG0hIy5DGT9Uw1vpSNsoRZqnidlRaJWifYuYg32bOq+tnAYcWwRsFfgOas35RV0Oq6Twuewm7sEZZXIMTJDqfIdtrtJcXUPowd2lmSjqNdqQavmne/PnchVFG5nEO3aUxrKzdvwlouhwv+38SGftYVqiEiSn+ac3JV/7iL1mLLNqYVbN2Kh7Cic3spLcT+U+l9+mkyDKEtDgJUunZRoW1T62MViJh6u2eTYrhkBCXZGbbNBwaRXHfd+uen8i/jyW12kJPr97IhAPk05vYEQJk+J2z/akIz1FmI7yjl7LeP8D4e5o3hrXlX/02XGHosik+DSlkGLp3grlL4ttEpdhnZu/pm2dF9mYydGyczXvLxOPn7S+8c+vqbMXM9QIqoVi3wLkNyun4INTBR3xmAeoHh2g0IAwnTAgEy+ZrG8CYvYnkzQsSDPfPBvVRMG6tbsbS8Wc7aWoT46Db0pRh5og0Il2xqrSLl4rgmkXICiK0QaFLIDkeCuhRkHDC0xrTamtvYpfn/XoKZLJCITXh5IpDxR0ULsgcLY1C+uvxv5861nUi5EQ1t0p4ZvfTT0zUTBGsID1+QAIO/JLTQunrL2u3Qxm1fOGZteG6VIEXhhQClGIA5TBO6GDJTGaBGu0Dfwhbyrz6bovSQSSQ7zcTR8RahzLmsZ0j4fVmCnsfJFHERsXt5fZqOqMaABN64tSiygO9E3RfEbsvtY8P+TEGr2mIMVDJ4kyeq6lEnUjLSyHtSP/P9leMH50jRFja8P7hXovxn4OvtNEfWPEfFg7ycjDnTX7CXvQNMoRPHTg4eX485u25bf2gjV5R1wD/a2LtMKXBgmZ1KztQVIhpQHvFxykYA4BTEP1jglKdsJKAnCKin/7yO7ZTFUX5Le/Zh1Y0rfBICPrqC2cDKu6Tw9Zw8JsRHTU+xdzw7NLBHO3dJwJeKsPwxJ6fOeI4UEDlmgrRZyhxDq7f7NtJ22GeV/qWDgxYFkZJxSiKHIjs0a3NIJm8DI9gqOJ8WSkTSzW9wgJOyx8xPjbgYoN5gKRll+NPHupILPx0igSdYe/OaE4u1bGGA+T4ZyRTv72ffC0AawazyM2lFLmCBQzfDmLMy9rdb/l1kqPioAr4+uNBwJjtPc4sLY+rnKeD5gxBU2i5YmbC+gKcBI1f1gV1xVKqeOb1c5szZnCB6G5vVsSydHm6QEDiEP/ornl79DC/7aAhnVHACSvPL6toTl8nP7qLFkEvN6nTLmsC8W44W2VhrR9y4g+WGmf8dUjY+hBH7x5H5Eunbckmeu8luUWL79o8bslP+9scAVfkRsPmC+mrFEGcuE/quYBUxwWjXS8KZ6OJqOSfUgpDtfxpb+uV5MXNAMBmlUg2dQXqdhNrMX1nPMy8pC1s6Gt7Ois/IuIxX1BmVUaVNtyErbk3xIwTnPRcJj5P/irZzSTPRGtFKy+dWNvpwjR6kV426LxK12Wydbq4GlK5EqirQ5nLJy7iMGXixGxKnBFP49lPtAuFWXzU0fAlIDpxW43xMWrsi54BC4Wh9g0X1/CetmL4U8ReAxXWYGGQBJV1/9wnfn1uq8KXMpSMfICmGXWEAxu4y9zOmrsNHwDslpHOeknE+mkYcTm2H5ZvqAW9JQm8OLzCoHJfL5ndaOpz2Sq5TAOWIdt+d09h7pmNrC9lJFIIho0WhqXcvxqszWjImdlB0fQo8XBhwqdWkwmRTG45kOM76vnbjHyP/dwUMBaWEhZJTaH5XUxnmwQMxdoAgRWq9kwg+8qeGGdUD6nbmzF8pbSxmGWV42Jjt/DbAQ3w0i9e3pGm44aGoxfe7KUv3Ue3wss+9qo+bo4eH1r+PGlRiPRGrLTNlveH4p3anUeiu9P1YGcTmKb2ARciRhifazfmAuGWOnoCeH4uZGJQZdFWUyjpdxiF82T/n3aiZZiSBP58alsDob+iSaNUFFIRKzVM4PL/OGygte0rN4K86SkyXpjFyfU2TYWJtytBa5adqMAAAAAAAAAAAAAAAAAAAAAAAAAABwwRGB0k -->
