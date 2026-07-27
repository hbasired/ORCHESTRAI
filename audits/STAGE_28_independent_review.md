# Stage 28 — Independent Review

- **Reviewer:** Independent task-auditor (a DIFFERENT agent than the Stage-28 implementer).
- **Date:** 2026-07-11/12
- **Scope:** GraphRAG grounding + adoption UX + the G-082 de-mock + the G-085 audit-hygiene baseline change (364 → 3).
- **VERDICT: PASS-WITH-GAPS.** The 364→3 baseline change is **LEGITIMATE** (genuine venv-scoping hygiene PAIRED with a
  real de-mock — NOT gaming). Real project fabrication is genuinely 0 in both languages. GraphRAG + adoption reproduce
  to the number. No regression. The gaps below are all MINOR and LEDGERABLE — **none is close-blocking.**

## Gaps found (all minor / ledgerable — none blocks close)

1. **ADR doc inaccuracy (not gaming).** The decomposition-TABLE line in
   `2026-07-04_stage28_graphrag_adoption_ux.md` reads "**~271 (venv/third-party, G-085)**", but 271 was the *total
   remaining python `random.*` hits* at that intermediate step; the **venv portion is ~209-212** (I measured **209**).
   The ADR's own point #5 ("~212") and the ledger G-085 entry have it right. Fix the table figure to ~209-212. This
   does NOT affect the legitimacy of the baseline change.
2. **Rule-1a synthetic constant in the adoption UX (`backend/api/adoption_routes.py:118-119`).** The *grounded*-path
   `confidence: 0.85` + `uncertainty_band: [0.75, 0.95]` are HARDCODED constants, not derived from the retrieval cosine
   score (which the retriever computes). This is the "fixed confidence + fake uncertainty band" pattern Rule 1a names.
   MITIGATED: the load-bearing anti-hallucination property (off-topic → confidence **0.0** + `hitl_required=True` + no
   fabricated grounding) is genuine and tested; the citations are real; the layer is an explicitly-labelled adoption-UX
   surface, not claimed as a model output. RECOMMEND: tie the grounded confidence to the real top cosine score / citation
   count. Ledgerable (real-pilot calibration = G-035).
3. **Trivial nit:** `backend/pipeline/api_integrations.py:252` still has a now-unused `import random` (the jitter it fed
   was removed). Does not match the audit grep; harmless dead import. One-line cleanup.
4. **Note (not a gap):** the full **8/8** knowledge_graph + **5/5** adoption counts require the embedder env var
   (`RUN_EMBEDDER_TESTS=1` / `MEM0_EMBED_MODEL`). Without it the embedder-dependent tests SKIP (3+5, 3+2). This is
   legitimate environment gating consistent with the project's heavy-embedder test pattern — the tests DO pass and assert
   real behaviour when the embedder is enabled (verified below). The ADR's "8/8"/"5/5" is accurate under that condition.

## The single most important question: is the 364 → 3 baseline change LEGITIMATE or GAMING?

**VERDICT ON THE BASELINE: LEGITIMATE.** It is genuine audit-hygiene (venv-scoping) PAIRED with a real de-mock,
not gaming. Evidence:

| Component | ADR claim | Independently measured | Legit? |
|---|---|---|---|
| G-085 venv/third-party (audit-scoping fix) | ~271 (table) / ~212 (point #5) | **209** lines `random.(uniform\|choice\|choices)` in `backend/venv/**.py` | YES — venv is gitignored + untracked + third-party (numpy/scipy/redis/pip), absent on a clean CI checkout |
| Real Python de-mock (G-082) | ~59 | project python `random.*` (excl venv/tests/training) = **0** now; git diff removed **119** `random.*` lines from tracked `.py` | YES — real |
| Real frontend de-mock | ~87 | `Math.random` in `frontend-nextjs/src` = **0** now; git diff removed **83** `Math.random` + **6** `generateMockState/Robots` | YES — real |
| Residual | 3 | `bash scripts/audit.sh` TOTAL = **3**, all `heuristic_actions` false-positive | YES — documented G-052 |

- **`git check-ignore backend/venv` → `backend/venv` (exit 0); `git ls-files backend/venv` → 0 tracked files.** The venv is
  genuinely gitignored/untracked third-party code. Whitelisting `backend/venv/`, `backend/.venv/`, `/node_modules/`,
  `/site-packages/` in `scripts/audit.sh` is **legitimate hygiene**, NOT gaming — the audit's stated purpose is PROJECT
  theatre, and a clean checkout never has these dirs.
- **Reconciliation:** 209 (venv) + 59 (python) + 87+6 (frontend Math.random+generators) + 3 (residual) = **364**. The
  decomposition holds when using the ADR's *point-#5* venv figure (~212 ≈ measured 209).
- **Minor doc gap (not gaming):** the ADR's decomposition-TABLE figure "~271 (venv)" is inconsistent with its own point #5
  ("~212") and with the measured 209 — an over-statement of the venv portion by ~60. The direction/legitimacy is sound;
  the table number should read ~209-212. Ledgerable, not close-blocking.
- **Crucially: real project fabrication is genuinely 0** (grep-confirmed both languages). The venv fix alone would leave
  the count at 212; the de-mock is what takes it to 3. Both halves are real.

## Verification log (commands I actually ran)

### 1. Baseline decomposition — the most important check
- `git check-ignore backend/venv` → `backend/venv` (exit 0); `git ls-files backend/venv | wc -l` → **0** tracked. venv is
  genuinely gitignored + untracked.
- `grep -rlE 'random\.(uniform|choice)' backend/venv --include=*.py` → numpy/scipy/redis/pip/cachetools (third-party).
  `grep -rnE 'random\.(uniform|choice|choices)' backend/venv --include=*.py | wc -l` → **209** lines.
- **Project python:** `grep -rnE 'random\.(uniform|choice|choices|randint|random)' backend --include=*.py` excl
  venv/tests/training → **0**. git diff removed **119** `random.*` lines from tracked `.py`.
- **Frontend:** `grep -rn 'Math.random' frontend-nextjs/src | wc -l` → **0** (total, incl. comments). git diff removed
  **83** `Math.random` + **6** `generateMockState/Robots` lines. `detRand()` (factory/page.tsx:15) is a genuine
  mulberry32-style seeded PRNG (fixed seed `0x2f6e2b1`), NOT an alias of Math.random.
- **Residual 3:** `bash scripts/audit.sh` → TOTAL **3**, all `heuristic_actions`; all 3 hits are in `ml/rl_policy.py`
  (2 call sites + the def). `_generate_heuristic_actions` (rl_policy.py:267) is a documented deterministic
  battery/queue-threshold rule policy (G-052) — a name-pattern false-positive, not fabrication. `audit.sh` prints
  "OK: count decreased from 364 to 3."
- **Reconciliation:** 209 (venv) + 59 (python) + 87 (frontend Math.random+generators) + 3 (residual) ≈ **364**. Legit.
- **Spot-read de-mocked files:** `ml/neural_networks.py` → real `defect_classifier` or honest-`{"available": False,
  "defect_class": None, "confidence": None}` (Rule 1a — no invented class/confidence). `services/state_manager.py` →
  deterministic id/step math.sin-cos drift + deterministic alert rotation (labelled demo). `pipeline/api_integrations.py`
  → honest-unavailable weather, honest-empty IoT `[]`, labelled deterministic carbon estimate.
- **VERDICT on the baseline: LEGITIMATE hygiene + real de-mock. Not gaming.**

### 2. GraphRAG
- `python knowledge_graph/graphrag_eval.py` → grounded_answer_rate **1.0**, honest_empty_rate **1.0**,
  graph_citation_precision **1.0** (6 in-domain + 4 out-of-domain). Matches the stored `graphrag_eval.json`.
- `python -m pytest tests/knowledge_graph/ -q` (RUN_EMBEDDER_TESTS=1) → **8 passed**. (Without the flag: 3 passed / 5
  skipped on embedder gating.)
- `graphrag.py`: honest-empty via `grounded = bool(context)` (grounded ONLY if a real citation found); citations are real
  SOP doc-ids (4 SOPs in `sop_corpus/`) + real Neo4j node/edge ids via Cypher; honest degradation when embedder/Neo4j
  absent.
- Runtime wiring: `agents/runtime/nodes.py:199-208` explain node calls `retrieve(q)` → `state.grounding`; the log node
  (`nodes.py:363-368`) passes `"grounding": state.grounding` into `record_decision_trace` → the Art-12 signed trace
  carries the grounding. Confirmed.

### 3. Adoption UX
- `python -m pytest tests/api/test_adoption_routes.py -q` (MEM0_EMBED_MODEL set) → **5 passed**. (Without: 3 passed / 2
  skipped on embedder gating.)
- `adoption_routes.py`: `/recommendation` off-topic → `confidence: 0.0`, `uncertainty_band: None`,
  `hitl_required: True`, no fabricated grounding (honest). `/wiifm` reads the REAL Stage-26
  `training/evals/results/supply_ab.json` (paired_diff stockout_ticks), honest-empty (`available: False`) otherwise.
  `/autonomy` defaults to the safest `shadow`; `/personas` role-shaped. (See gap #2 re: the grounded-path confidence
  constant.)

### 4. No regression
- `python scripts/verify-audit-chain.py` → "Audit chain OK (10076 rows; hash chain intact; all 9997 post-cutover
  signatures verify)", **exit 0**.
- `python -m pytest tests/test_health.py tests/test_websocket_smoke.py -q` → **4 passed** (legacy demo path intact after
  the de-mock).

### 5. ADR framing honesty
- The ADR transparently decomposes the drop into 4 parts and explicitly states the venv-scoping is "audit-hygiene, not
  baseline-gaming ... paired with the REAL de-mock." The residual-3 false-positive is honestly disclosed. G-082 marked
  RESOLVED + G-085 ledgered. The only framing defect is the "~271 (venv)" table figure (gap #1) — an over-statement of
  the venv portion; the correct ~209-212 appears in the ADR's own point #5 and the ledger.

## Bottom line
The 364 → 3 baseline change is **honest and legitimate**: ~209 was gitignored third-party venv code that never belonged
in a project-theatre count (a clean CI checkout has no venv), and the remaining drop is a REAL de-mock that takes project
`random.*`/`Math.random` fabrication to a genuine **0** in both backend and frontend. GraphRAG and the adoption UX are
real (not theatre) and reproduce to the number; the audit chain is intact; the legacy demo path still passes. **PASS-
WITH-GAPS** — the enumerated gaps are minor and ledgerable, none blocks `close-task.sh`.
