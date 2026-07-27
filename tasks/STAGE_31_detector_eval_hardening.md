---
status: done
stage: 31
slug: detector_eval_hardening
created: 2026-07-13
---

# Stage 31 — Detector / eval hardening

> Hardens the Stage-20 red-team defences on the now-richer system: (G-077) a LEARNED third tier for the
> prompt-injection detector (bge-embedding logistic-regression trained on the real corpus) that lifts recall AND cuts
> the false-positive, measured by held-out CV — plus an optional free-LLM judge escalation; (G-064-tail) a CONTINUOUS
> runtime behavioural anomaly monitor (online robust-Z + trajectory checks), the streaming counterpart of the
> Stage-25 nightly sweep; (CTO-#5 R5) the honest deep-eval numbers persisted to a results artefact + model card.
> Research §42; free/local; the binding actuation gate stays `safety/validator`.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_31/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: 30 (live-wire loop), 20 (red-team eval harness + corpus), 25 (post-market robust-Z sweep), 17 (safety validator = binding gate)
- Decision logs honoured: `2026-07-12_stage30_live_wire_self_healing_loop.md`, `2026-06-22_stage20_redteam_eval.md`, `2026-07-02_stage25_post_ga_ops.md`
- KB files at minimum version: KB_23 (evals & benchmarks), KB_18 (governance/security)
- Gaps ledger rows pulled in (IDs): **G-077** (prompt_guard residual gaps), **G-064**-tail (continuous runtime anomaly detection), CTO-#5 **R5** (deep-eval gate + detector polish); G-027 (free-cost, ongoing)

## Acceptance criteria

- [x] **AC1 (G-077) — a LEARNED injection tier lifts recall AND cuts FPR, measured held-out.** `security/injection_classifier.py`
  (logistic-regression over bge-small embeddings, trained on the real 217-example OWASP corpus) becomes the primary
  calibrated semantic decision in `prompt_guard.inspect()`. **Stratified 5-fold CV (NOT train-on-test): combined
  detector detection 0.9935 → 1.0, FPR 0.0156 → 0.0** (`training/evals/results/detector_hardening.json`). Verified:
  `tests/security/test_injection_classifier.py`.
- [x] **AC2 (G-077) — the benign FP is gone + heuristic must-catch still holds + honest fallback.** `inspect()` passes
  the previously-false-positived benign maintenance question; the deterministic heuristic still catches a safety-bypass
  command with no embedder; the learned+kNN tiers degrade together on a shared embedder gate (honest); an optional
  free-LLM judge escalates the uncertain band. Verified in `test_injection_classifier.py` + `tests/evals/test_redteam.py`.
- [x] **AC3 (G-064-tail) — continuous runtime behavioural anomaly detection.** `security/behavioral_monitor.py` — online
  robust-Z (median/MAD) over real per-incident behavioural features + trajectory checks (loops/redundant/invalid-tool-args/
  actuation>decisions); signed `behavior.anomaly` row; honest `insufficient_history` below warmup; `features_from_run()`
  consumes a real `run_incident` result. Labelled eval: detection 1.0 / FPR 0.0. Verified: `tests/security/test_behavioral_monitor.py`.
- [x] **AC4 (CTO-#5 R5) — honest deep-eval artefact + model card.** `detector_hardening_eval.py` writes the held-out CV
  numbers to `training/evals/results/detector_hardening.json`; `models/injection_classifier.metrics.json` +
  `compliance/model-cards/injection_classifier.md` document the trained model with its held-out metrics + honest caveats.
- [x] **AC5 — free-cost + no regression.** New deps: none (sklearn/sentence-transformers present). Audit holds 3.
  30 security+red-team tests pass; the Stage-20 eval floors still hold.
- [x] **AC6 — research-first (§42) + explainer + independent review.** Research §42 appended BEFORE implementing;
  `research/stage-explainers/STAGE_31/index.html`; independent review by a DIFFERENT agent = PASS.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/security/injection_classifier.py` | G-077 learned tier (bge+LR) + held-out CV eval + deployment fit/save |
| `backend/security/behavioral_monitor.py` | G-064-tail continuous online behavioural anomaly monitor |
| `backend/training/evals/redteam/detector_hardening_eval.py` | persists the honest held-out detector metrics |
| `backend/tests/security/test_injection_classifier.py` + `test_behavioral_monitor.py` | tests (11) |
| `models/injection_classifier.{joblib,metrics.json}` + `compliance/model-cards/injection_classifier.md` | trained-model artefacts + card |
| `research/stage-explainers/STAGE_31/index.html` | stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/security/prompt_guard.py` | learned tier as the primary semantic decision (kNN fallback) + LLM-judge escalation + shared embedder gate |
| `knowledge-base/KB_23_Evals_and_Benchmarks.md` + `audits/OPEN_GAPS_LEDGER.md` | detector-hardening numbers + G-077/G-064-tail RESOLVED |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | additive stage |

## Files to MODIFY

| Path | Change |
|---|---|
| | |

## Files to DELETE

| Path | Reason |
|---|---|
| | |

## KB files this stage updates

(The KB-diff CI gate enforces these. Every listed file must have a non-trivial diff in the closing PR.)

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_NN_<topic>.md`

## Verification commands

```bash
bash scripts/audit.sh                    # holds at 3 (additive; --no-baseline-drop)

# Stage-31 detector tests + the honest held-out CV lift
cd backend && DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing \
  MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5 MEM0_EMBED_DIM=384 HF_HUB_DISABLE_XET=1 \
  python -m pytest tests/security/ tests/evals/test_redteam.py -q

# regenerate the honest metrics artefact
cd backend && python training/evals/redteam/detector_hardening_eval.py --out training/evals/results/detector_hardening.json
```

## Audit target

- Pre-stage baseline: 3
- Target: hold at 3 (`--no-baseline-drop`) — additive real code (learned detector + behavioural monitor); zero new
  `random.*`/mock introduced; the learned tier REDUCES the detector's real FPR (a genuine defence improvement).

## Role

- Primary: `ml-engineer` (learned classifier, held-out eval, model card)
- Secondary: `security-pqc-engineer` / `agentic-governance-engineer` (detector wiring + behavioural oversight)

## Risks / unknowns

- Corpus-scale (217 examples) — real-traffic + multilingual/obfuscated-attack validation needs a pilot (G-035).
- The deployment classifier is fit on all data; the REPORTED numbers are the held-out CV (the honest estimate).
- No detector is fool-proof (OWASP) — the binding actuation gate remains `safety/validator` (Rule 3).

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - The injection detector has a learned tier (detection 0.9935→1.0, FPR 0.0156→0.0, held-out CV) + an LLM-judge
    escalation; a continuous runtime behavioural anomaly monitor exists and consumes real `run_incident` output.
- What the next stage (32 — pilot-prep) starts with:
  - A hardened, honestly-measured defence surface + a fully-live loop — ready to package the pilot onboarding kit +
    A/B protocol against a real buyer's incidents (G-035/G-043, buyer-blocked).
- Open items deferred to a future stage:
  - Real-traffic / multilingual detector validation + threshold tuning on live data (pilot, G-035).
  - Wiring the behavioural monitor as an always-on runtime hook (currently consumes results post-hoc via `features_from_run`).

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-13T05:02:34Z)

### Suggested role (from slug heuristic)

**ml-engineer** — open `.claude/skills/ml-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_TASK_LOG.md`
- `knowledge-base/KB_02_Models_Inventory.md`
- `knowledge-base/KB_03_Datasets_Catalog.md`
- `knowledge-base/KB_10_Production_Hardening.md`
- `knowledge-base/KB_17_Functional_Safety_Wrapper.md`
- `knowledge-base/KB_18_Governance_Evidence.md`

### Pre-requisites (from previous stage's hand-off — STAGE_30_live_wire_self_healing_loop.md)


- What is now true that wasn't before this stage:
  - The KB_25 loop is live end-to-end: a downed machine gets a real safety-gated repair dispatch (measured −47.9%
    downtime); the RL policy is consulted in shadow; the operator forecast is served from the real model (no fake confidence).
- What the next stage (31 — detector/eval hardening) starts with:
  - A fully-live loop to harden: G-077 prompt_guard learned/LLM-judge tier + G-064-tail continuous runtime anomaly
    detection + CTO #5 R5 deep-eval gate polish.
- Open items deferred to a future stage:
  - RL shadow→active promotion (autonomy-ladder gated) once agreement is validated on real data (pilot).
  - Physical-proximity repair routing + real hourly-demand re-fit (G-035, buyer-blocked).

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
