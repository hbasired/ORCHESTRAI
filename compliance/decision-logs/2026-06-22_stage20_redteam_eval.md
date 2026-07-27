# ADR — Stage 20: Red-team & adversarial eval harness (OWASP LLM01 + NIST-RMF-Agentic + agentic metrics G-008)

**Date**: 2026-06-22
**Status**: Accepted (Stage 20 — follows Stage 19 evidence pipeline)
**Author personas**: `ml-engineer` (primary) + `security-pqc-engineer` (attack-vector design)
**Relates**: KB_15 (Phoenix as CI gate), KB_18 (OWASP/NIST control mapping), KB_23 (anti-gaming evals). Research §30/§30.5.
Hard Rule 1a (no fabricated metrics), Rule 9 (free/local), Rule 11 (research-first). Pays **G-008** + the **G-064 tail**.

---

## Context

The project owed an automated red-team / adversarial eval harness (the EU-AI-Act + zero-trust evidence): G-008
(agentic eval depth + runtime guardrails) and the G-064 tail (OWASP-Agentic + prompt-injection red-team). Stage 20
builds it against the system's REAL defences — the eval is only credible if it measures live code, never a hand-set
number (Rule 1a / KB_23).

## Decisions

**D1 — `security/prompt_guard.py`: a real hybrid prompt-injection detector.** Two OR-combined layers: (1) deterministic
heuristic patterns over the documented OWASP-LLM01 taxonomy (instruction-override, role jailbreak, delimiter escape,
system-prompt exfil, agency hijack, encoded payloads, multilingual, + safety-critical actuation/LOTO/speed-limit
patterns), and (2) a semantic layer — bge-small (already a dep) cosine-kNN against a canonical attack bank, catching
paraphrases the regex misses, with **honest degradation** to heuristic-only when the embedder is unavailable
(`semantic_available=False`, never faked). Wired into `agents/llm_client.generate()` on **100%-traffic** (blocks when
`PROMPT_GUARD_ENFORCE != 0`).

**D2 — Corpus (deterministic, auditable).** `redteam/generate_corpus.py` (itertools, no RNG) emits **217 OWASP-LLM01**
(153 attacks + 64 benign false-positive controls) + 14 NIST-RMF-Agentic probes + 8 industry-safety scenarios. The
attack PATTERNS are from public OWASP/NIST taxonomies; the RESULTS are measured, not authored. **The attack strings are
defensive test fixtures** (`label:"attack"`, `expect_blocked:true`) — inert JSON the guard must reject, never executed.

**D3 — `runner.py`: scores each corpus against the REAL defence.** owasp → `prompt_guard.inspect`; NIST memory →
`mem0_adapter._authorize`(+RLS); NIST tool → `tool_manifest.{diff_against_live,verify_manifest}`; NIST/industry agency →
`safety.validator.validate_order`. Emits `eval.<suite>` spans (`phoenix_evals.log_eval`) + writes
`training/evals/results/*.json` (ingested by the Annex IV pack). `--gate` exits nonzero on a `thresholds.yaml` breach.

**D4 — `agentic_metrics.py` (G-008).** Tool-selection-quality / action-completion / reasoning-coherence computed over
the REAL LangGraph trajectory (`run_incident` → `trace`), pure-math core (CI-tested) + honest-skip live runner.

**D5 — Two operating points (CI vs nightly).** CI `phoenix-evals` runs the DETERMINISTIC subset (heuristic + the
code-enforced NIST/industry defences — no embedder/network) and fails on a threshold breach. `nightly-evals.yml` runs
the FULL hybrid (semantic + live runtime) and enforces the OWASP-LLM01 ">=99% refusal" target. Same host-vs-CI split as
Stage 18. Thresholds set BELOW measured (KB_23 anti-gaming).

## Measured (live, 2026-06-22)

| suite | heuristic-only (CI) | full hybrid (nightly) |
|---|---|---|
| OWASP-LLM01 detection | 0.758 | **0.9935** (1/153 miss = indirect) |
| OWASP-LLM01 FPR | 0.000 | 0.0156 (1/64 benign) |
| NIST-RMF-Agentic block | **1.000 (14/14)** | 1.000 |
| industry-safety input-tier | 0.875 (7/8) | 0.875 |
| agentic metrics (live runtime) | — | tool-sel **1.0** / action-completion **1.0** / coherence **1.0** |

Eval coverage tests **10/10**; audit holds **364**; imports clean.

## Why
- A guardrail you can't measure is theatre. The harness turns "we mitigate prompt injection" into a number scored
  against live code, regenerated every PR (CI) + nightly (hybrid), feeding the Annex IV conformity pack.

## Consequences
- New: `backend/security/prompt_guard.py`, `backend/training/evals/{runner.py,thresholds.yaml,agentic_metrics.py,
  redteam/{generate_corpus.py,*.jsonl}}`, `backend/tests/evals/test_redteam.py`, `.github/workflows/nightly-evals.yml`,
  CI job `phoenix-evals`. Modified: `agents/llm_client.py` (guard on 100% traffic), `scripts/generate-annex-iv-doc.py`
  (ingest red-team results), KB_15/KB_18, risk-register. No new deps (bge-small/sentence-transformers already present).
- Verified live (Docker up): heuristic CI gate exit 0; hybrid 0.9935; NIST 14/14; agentic 1.0/1.0/1.0; tests 10/10.

## Honest residual / ledger
- **G-008 RESOLVED** (agentic eval metrics + 100%-traffic prompt-injection guardrail shipped + measured). The deeper
  "Galileo-grade" plan/argument-correctness metrics + 100%-traffic runtime guardrails on EVERY LLM provider path can be
  extended later — the metric framework + the llm_client gate are in place.
- **G-064 tail RESOLVED** (OWASP-Agentic + prompt-injection red-team shipped). Continuous behavioural anomaly detection
  (runtime, not batch) remains a later operational-hardening item → ledgered.
- Honest gaps in the detector: 1 indirect-injection miss + partial multilingual reliance on the embedder; FPR 0.0156
  (1 benign maintenance prompt flagged); industry input-tier 0.875 (one no-keyword physical command evades the input
  tier — the BINDING gate is the validator, measured 100% by the NIST agency suite). Documented; ledgered as G-077.
- Process: caught a stale-`results.json` from an invalid-regex import crash hidden by `grep >/dev/null`; re-measured
  with exit-code checks (research §30.5).

## References
- `backend/security/prompt_guard.py` · `backend/training/evals/*` · `backend/agents/llm_client.py` ·
  `.github/workflows/{ci.yml,nightly-evals.yml}` · KB_15/KB_18/KB_23 · research §30. OWASP-LLM-Top-10-2025; NIST AI RMF Agentic Profile.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-22T02:41:44+00:00 -->
<!-- signature: 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 -->
