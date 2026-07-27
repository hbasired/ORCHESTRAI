# ADR — Stage 31: Detector / eval hardening (learned injection tier + continuous behavioural monitor)

- **Date:** 2026-07-13
- **Status:** Accepted
- **Stage:** 31 (`tasks/STAGE_31_detector_eval_hardening.md`) — third of the operator-chosen post-Stage-28 arc
  (29 conversational → 30 live-wire → **31 detector hardening** → 32 pilot-prep → CTO #6).
- **Roles:** `ml-engineer` (learned classifier + held-out eval + model card) + `security-pqc-engineer` /
  `agentic-governance-engineer` (detector wiring + behavioural oversight).
- **Research:** `research/initial-research.md §42` (embedding-classifier + LLM-judge injection detection; trajectory /
  behavioural anomaly detection SOTA) — appended BEFORE implementing (Hard Rule 11).

## Context

Stage 20 shipped a hybrid prompt-injection detector (heuristic regex + semantic kNN) measuring 0.9935 detection /
0.0156 FPR, with a residual indirect-injection miss + a benign false-positive (G-077), and CONTINUOUS runtime
behavioural anomaly detection was ledgered but not built (G-064-tail; CTO-#5 R5). Stage 31 hardens both — honestly,
free/local, on the now-richer (Stages 29–30) live system.

## Decisions & outcomes (every number a live command this session)

1. **G-077 — a LEARNED injection-detection tier.** `security/injection_classifier.py`: a `LogisticRegression`
   (class-weight balanced) over `bge-small` embeddings, trained on the real Stage-20 corpus (153 attacks + 64 benign),
   becomes the PRIMARY calibrated semantic decision in `prompt_guard.inspect()` (replacing the raw kNN single-threshold;
   the kNN stays an honest fallback when the classifier/embedder is unavailable). An optional free-LLM judge
   (`inspect(use_judge=True)`, Groq→Ollama) escalates the uncertain probability band + no-keyword unsafe intent.
   **Measured by STRATIFIED 5-fold cross-validation (NOT train-on-test): combined detector detection 0.9935 → 1.0,
   FPR 0.0156 → 0.0** — the learned tier caught the 1 indirect miss AND removed the 1 benign FP. Deployment artefact
   `models/injection_classifier.joblib` (fit on all data) + `.metrics.json` + `compliance/model-cards/injection_classifier.md`.
2. **G-064-tail — CONTINUOUS runtime behavioural anomaly monitor.** `security/behavioral_monitor.py`: the ONLINE
   counterpart of the Stage-25 nightly sweep — rolling **robust-Z (median/MAD)** over the runtime's REAL per-incident
   behavioural features (decision count / tool calls / actuation attempts / verifier rejections / node revisits /
   duration) + explicit **trajectory checks** (loops, redundant actions, invalid tool args, actuation>decisions),
   emitting a signed `behavior.anomaly` row; honest `insufficient_history` below warmup (no fabricated baseline).
   `features_from_run()` maps a real `run_incident` result into the feature set (so it consumes live output). Labelled
   eval: detection 1.0 / FPR 0.0.
3. **CTO-#5 R5 — honest deep-eval artefact.** `training/evals/redteam/detector_hardening_eval.py` writes the held-out
   CV numbers + the behavioural eval to `training/evals/results/detector_hardening.json`.

## Honesty notes (Rule 1a — verified)

- **The reported lift is held-out CV, not train-on-test.** `cross_val_eval` / `combined_cv_eval` train the classifier
  on k-1 folds and score the held-out fold; the deployment model (fit on all data) is separate and its metrics.json
  says so. This is the specific circularity a reviewer would check — it is avoided by construction.
- **The learned tier REDUCES the detector's real FPR** (0.0156 → 0.0) — a genuine defence improvement, not just an
  additional OR-tier (which could only raise FPR): the classifier REPLACES the kNN as the primary semantic decision.
- **Honest degradation everywhere:** classifier/embedder/LLM absent → tier skipped (never a fabricated verdict); the
  learned + kNN tiers share one embedder gate so they degrade together. The binding actuation gate remains
  `safety/validator` (Rule 3) — detectors are defence-in-depth; no detector is fool-proof (OWASP; arxiv 2504.11168).

## Consequences

- New: `backend/security/{injection_classifier,behavioral_monitor}.py` +
  `backend/training/evals/redteam/detector_hardening_eval.py` + `backend/tests/security/{test_injection_classifier,
  test_behavioral_monitor}.py` (12 new tests) + `models/injection_classifier.{joblib,metrics.json}` +
  `compliance/model-cards/injection_classifier.md`. Modified: `backend/security/prompt_guard.py` (tiered inspect).
  **New deps: none** (scikit-learn + sentence-transformers already present). KB_23 updated; G-077 + G-064-tail RESOLVED.
- **Audit holds 3** (`--no-baseline-drop`: additive real code; the learned tier reduces the real FPR). 30 security +
  red-team tests pass; the Stage-20 eval floors still hold. `verify-audit-chain.py` exit 0.
- Deferred honestly: real-traffic / multilingual detector validation + threshold tuning on live data (pilot, G-035);
  always-on runtime hook for the behavioural monitor (currently consumes results post-hoc via `features_from_run`).

## References
- research §42 · `research/stage-explainers/STAGE_31/index.html` · `backend/security/injection_classifier.py` ·
  `backend/security/behavioral_monitor.py` · `training/evals/results/detector_hardening.json` ·
  `compliance/model-cards/injection_classifier.md` · G-077 / G-064 (`audits/OPEN_GAPS_LEDGER.md`) ·
  ADR `2026-06-22_stage20_redteam_eval.md` · arxiv 2410.22284 (embedding classifiers) · 2602.06443 (TrajAD) ·
  doi 10.3390/a19010092 (indirect-injection embedding+XGBoost).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-13T06:02:11+00:00 -->
<!-- signature: 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 -->
