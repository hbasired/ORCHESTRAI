# Stage 20 — Independent Review (Red-Team & Adversarial Eval Harness)

**Auditor:** independent `task-auditor` persona (DID NOT implement Stage 20).
**Date:** 2026-06-22
**Infra:** LIVE — Postgres @ :5544, Neo4j @ :7687 (both up). All runs DYNAMIC unless marked STATIC.
**Verification env:** `DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing`,
`HF_HUB_DISABLE_TELEMETRY=1`, `MEM0_EMBED_DIM=384`, `MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5`,
`PROMPT_GUARD_EMBED_MODEL=BAAI/bge-small-en-v1.5`.

---

## VERDICT: **PASS**

The eval numbers are **REAL** — measured against the system's live defences, not hardcoded. Every claimed
metric reproduced exactly on a fresh run. The prompt-injection guard is genuine 100%-traffic defence-in-depth.
The CI gate is load-bearing (exits 1 on a constructed breach). Tests 10/10. Audit holds 364, no classical-crypto
violation, no theatre patterns in new code. Documentation (ADR/KB/ledger/risk-register) matches measured reality;
gaps are honestly accounted (G-008/G-064-tail RESOLVED, G-077 NEW for residual detector gaps).

---

## Per-criterion evidence

| # | Criterion | Claimed | Independently confirmed? | Note |
|---|---|---|---|---|
| 1 | Runner honest (calls real defences, numbers reproduce) | heuristic owasp 0.758, hybrid 0.9935, NIST 14/14, industry 0.875 | **YES (DYNAMIC)** | Re-ran `runner.py --corpus all` → owasp **0.7582**, NIST **1.0 (14/14)**, industry **0.875**, FPR 0.0. Re-ran `--corpus owasp --semantic` → **0.9935** (152/153), FPR **0.0156** (1/64). Exact match. results.json freshly written (timestamps tracked my runs). |
| 1b | results.json freshly written; prompt_guard imports clean | stale-results bug fixed | **YES (DYNAMIC)** | `from security.prompt_guard import inspect,status` → import OK; results/*.json mtimes = my run times (06:49 / 06:51). No import crash. |
| 2 | Attack strings inert (defensive fixtures, not executed) | yes | **YES (DYNAMIC+STATIC)** | `grep eval\|exec\|subprocess\|os.system\|__import__` over `training/evals/` → 0 hits (only `log_eval`). Prompts pass only to `inspect()` / `_authorize` / `validate_order` as data. Runner scores from `.blocked`, NOT from the fixture's own `expect_blocked` field (`runner.py:48-63`) — no circularity. |
| 3 | Guard real defence-in-depth on 100% user-role traffic | yes | **YES (DYNAMIC)** | Wired in `llm_client.generate` (`agents/llm_client.py:354-367`): canonical injection → **blocked BEFORE any provider call** (`PromptInjectionDetected`, layer=heuristic). Benign OT prompt → passed guard, reached provider (404). Honest degradation: `test_guard_honest_degradation_when_no_embedder` + `status()` shows `semantic_loaded:False` when unavailable. |
| 4 | Agentic metrics (G-008) compute from real trajectory | tool-sel/action/coherence 1.0/1.0/1.0 | **YES (DYNAMIC)** | `agentic_metrics.py` ran `run_incident` live → `available:true`, `backend:postgres`, real 8-node trajectory `[observe,orient,diagnose,explain,decide,verify,execute,log]`, n_decisions:1, metrics **1.0/1.0/1.0** computed by `compute_metrics`. Honest-skip confirmed: forcing the runtime import to fail → `available:false` + reason + **no fabricated trajectory**. |
| 5 | Thresholds not gamed (floors below measured); `--gate` exits nonzero | yes | **YES (DYNAMIC)** | Floors: owasp 0.70<0.758, FPR max 0.05>0.000/0.0156, nist 1.0=1.0, industry 0.80<0.875, hybrid 0.99<0.9935 — all below measured. `--gate` on real thresholds → exit 0 "GATE PASSED"; pointed at an impossible threshold (0.999) → `main()` returned **1** "GATE FAILED". `_check_gate` flags breaches in all 4 dimensions. |
| 6 | Tests pass + audit holds + docs match | 10 pass / 364 | **YES (DYNAMIC)** | `pytest tests/evals/ -q` → **10 passed**. `scripts/audit.sh` → **TOTAL 364** = baseline; no CLASSICAL violation. ADR/KB_15/KB_18/risk-register/ledger numbers all match the live measurements. |

### AC table (task doc)

| AC | Status | Evidence |
|---|---|---|
| `redteam/` corpus ≥200 OWASP + NIST agentic + industry | **MET** | 217 OWASP (153 attack + 64 benign), 14 NIST (memory_leak/poisoning, tool_poisoning, excessive_agency), 8 industry. `wc -l` confirms. |
| `runner.py` scores corpus vs runtime; emits to Phoenix | **MET** | Scores against `prompt_guard`/`mem0._authorize`/`tool_manifest`/`validator`; `_emit`→`phoenix_evals.log_eval` (best-effort, honest no-op when collector down). |
| `thresholds.yaml` per-eval pass thresholds (refusal ≥99%, leak=0) | **MET** | hybrid ≥0.99 (nightly) + nist min_block_rate 1.0 (= zero leak). |
| CI `phoenix-evals` runs corpus per PR, fails on breach | **MET** | `ci.yml:459-488` — `needs:[backend]`, regen corpus + ≥200 check, `runner.py --corpus all --gate`, 10 tests. NIST suite verified DB-free (CI has no PG) → still 14/14. |
| Nightly `nightly-evals.yml` full hybrid | **MET** | cron 03:00 UTC, `--semantic --gate` + agentic `--gate`, enforces hybrid ≥0.99, uploads artifacts. |
| Phoenix dashboard / regressions visible | **PARTIAL (honest)** | spans emitted via OTLP when `OTEL_EXPORTER_OTLP_ENDPOINT` set; dashboard render is the optional UI tier (consistent with G-067 pattern). Not a gap — honestly scoped in nightly-evals.yml header. |
| audit includes baseline eval results | **MET** | results/*.json written; ingested into Annex IV pack (`_evals()` globs `results/*.json`, verified produces real metric rows). |

---

## Adversarial probes I ran

- **Numbers fabricated?** No. Re-ran both operating points; heuristic 0.7582 / hybrid 0.9935 / NIST 14/14 /
  industry 0.875 reproduced to the digit. Corpus is byte-identical to deterministic regeneration
  (sha256 unchanged before/after `generate_corpus.py`) — not hand-edited to inflate.
- **Auto-pass off the fixture's own label?** No. Runner partitions by `label` but scores from the live
  `inspect().blocked` verdict; `expect_blocked` is never consumed as the score.
- **Gate theatre?** No. Constructed a breach (impossible 0.999 floor in a tmp thresholds) → `main()` returned 1.
- **Metrics hardcoded to 1.0?** No. `compute_metrics` is pure math over the real `run_incident` trace; verified
  penalty path via `test_agentic_compute_metrics_penalises_missing_and_loops`.
- **Honest degradation faked?** No. Embedder-unavailable → `semantic_available=False`, no synthetic score;
  runtime-unavailable → `available:false` + reason, no fabricated trajectory.
- **Classical crypto / theatre in new code?** None (`grep` over `prompt_guard.py` + `runner.py` clean).

---

## Findings (severity-ranked)

1. **[INFO] `summary.json` ingests as an empty `{}` row in the Annex IV pack.** `_evals()` filters keys to a
   metric whitelist, but `summary.json`'s top-level keys are suite names, so `redteam/summary: {}`. Cosmetic
   noise in the pack; the per-suite rows carry the real numbers. (`scripts/generate-annex-iv-doc.py:81-84`)
2. **[INFO / already ledgered as G-077] Detector residual gaps.** heuristic-only owasp 0.758 (relies on the
   embedder for the rest); 1 hybrid indirect-injection miss (`llm01-0068`); FPR 0.0156 (1 benign maintenance
   prompt); industry input-tier 0.875 (one no-keyword physical command evades the *input* tier). NOT a live
   breach — the BINDING actuation gate is `safety/validator` (Rule 3), measured 100% by the NIST agency suite,
   and cross-namespace/tool-poisoning are 100% code-blocked. Honestly characterised in ADR + G-077 + KB. No
   new ledger entry required (G-077 already covers it; target = later detector-hardening/continuous-anomaly stage).

No FAIL-class findings. No bypass (`--no-verify`/`--force`/unjustified `--no-baseline-drop`) detected. No
hard-rule violation: Rule 1/1a (no fabricated metrics — confirmed), Rule 3 (no LLM-direct actuator — the guard
is detection-tier, the validator remains the binding gate), Rule 9 (bge-small free/local/CPU; no paid SaaS),
Rule 11 (research §30 present, deepest-honest hybrid detector + real taxonomies).

## New gaps for the ledger

None. G-077 was already appended by the implementer and accurately scopes the residual; G-008 and the G-064
tail are honestly marked RESOLVED with reproduced evidence.

---

## Re-run log (commands actually executed)

```
python training/evals/runner.py --corpus all                  # owasp 0.7582, nist 1.0(14/14), industry 0.875, FPR 0.0; exit 0
python training/evals/runner.py --corpus owasp --semantic     # hybrid 0.9935 (152/153), FPR 0.0156; exit 0
python training/evals/runner.py --corpus all --gate           # GATE PASSED; exit 0
(tmp impossible threshold) runner.main(['--corpus','all','--gate'])  # GATE FAILED; return 1
env -u DATABASE_URL runner.py --corpus nist                   # 14/14 DB-free (CI condition); exit 0
python training/evals/agentic_metrics.py                      # available:true, backend:postgres, 1.0/1.0/1.0
(forced import failure) run_live()                            # available:false + reason, no trajectory
llm_client.generate(injection user msg)                       # PromptInjectionDetected (blocked pre-provider)
llm_client.generate(benign OT user msg)                       # passed guard -> provider 404 (no false positive)
pytest tests/evals/ -q                                        # 10 passed
scripts/audit.sh                                              # TOTAL 364 == baseline; no CLASSICAL
generate_corpus.py regenerate + sha256                        # byte-identical (not hand-edited)
generate-annex-iv-doc._evals()                                # ingests real redteam/* metric rows
```
