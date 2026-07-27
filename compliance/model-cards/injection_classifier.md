# Model Card — injection_classifier (Stage 31, G-077)

## Overview
A learned prompt-injection detection tier: a `LogisticRegression` (class-weight balanced) over `BAAI/bge-small-en-v1.5`
sentence embeddings, forming the **third tier** of `backend/security/prompt_guard.py` (after the deterministic
heuristic must-catch tier, replacing the raw semantic-kNN threshold as the primary calibrated decision; the kNN
remains an honest fallback when the classifier is unavailable). Research §42.1.

## Intended use
- **Defence-in-depth** input screening for the industrial-control LLM assistant — flags prompt-injection / jailbreak /
  system-prompt-exfiltration / safety-bypass attempts before they reach an LLM prompt.
- **NOT the binding gate.** The binding actuation gate remains `backend/safety/validator.py` (Hard Rule 3). No prompt
  detector is fool-proof (OWASP; arxiv 2504.11168) — this raises the bar, it does not guarantee prevention.

## Training data
- `backend/training/evals/redteam/owasp_llm01_corpus.jsonl` — the real Stage-20 OWASP-LLM01 corpus: **153 attacks +
  64 benign controls** (documented OWASP-LLM01 taxonomy; attack strings are inert defensive fixtures).

## Evaluation (held-out — NOT train-on-test)
Stratified **5-fold cross-validation** (`security/injection_classifier.cross_val_eval` / `combined_cv_eval`):

| detector | detection rate | false-positive rate |
|---|---|---|
| Stage-20 baseline (heuristic + kNN) | 0.9935 | 0.0156 |
| **learned tier alone (CV)** | **0.9935** | **0.0** |
| **combined (heuristic OR learned, CV)** | **1.0** | **0.0** |

The learned tier **caught the 1 indirect-injection miss AND removed the 1 benign false-positive** the kNN produced.
Metrics: `models/injection_classifier.metrics.json`.

## Limitations & honest caveats
- **Corpus-scale (217 examples)** — real-traffic + multilingual/obfuscated-attack validation needs a pilot (G-035).
- The **deployment artefact** (`models/injection_classifier.joblib`) is fit on ALL corpus data; the reported numbers
  are the held-out CV (the honest generalisation estimate), not the fit-on-all score.
- **Honest-unavailable:** if sklearn / the bge embedder / the trained model is missing, the tier is skipped
  (`is_available()` False) and `prompt_guard` falls back to heuristic + kNN — it never fabricates a verdict.
- An **ambiguous-band LLM-judge escalation** (free Groq→Ollama) can be enabled (`inspect(..., use_judge=True)`) for
  indirect / no-keyword unsafe-intent inputs; it too is honest-unavailable.

## Provenance
- Trained + evaluated 2026-07-13 (Stage 31). ADR `2026-07-13_stage31_detector_eval_hardening.md`.
- Deps: scikit-learn + sentence-transformers (both already present; no new deps).
