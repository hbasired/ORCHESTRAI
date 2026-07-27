# Stage 35 — Independent Review (Multi-turn dialogue memory, CTO #6 C6-R3 tail)

- **Reviewer:** independent `task-auditor` (a DIFFERENT agent than the implementer), CLAUDE.md §6.
- **Date:** 2026-07-18
- **Scope:** `backend/conversation/session_store.py` (new), `conversation/ask.py` + `nl_inject.py` (session wiring),
  `api/conversation_routes.py` (session_id in request bodies), `tests/conversation/test_session_store.py` (6 tests),
  ADR `2026-07-13_stage35_multi_turn_dialogue_memory.md`, research §46.
- **Environment:** Postgres @5544 (`ai-agent-postgres` UP 17 min), system `python` 3.11.9, `DATABASE_URL` set per task.

---

## TOP-LINE VERDICT: **PASS**

The central grounding invariant is **preserved** — proven both by code structure and by an adversarial live experiment
that seeded a session with fake-citation "answers" and still could not make an off-topic question ground. Hard Rule 3
is intact. No fabrication, no new deps, no regression. All six acceptance criteria independently confirmed.

---

## Claim-by-claim

| # | Claim | Measured (independently) | Verdict |
|---|-------|--------------------------|---------|
| 1 | **Grounding/Verifier invariant PRESERVED** (the #1 thing) | `ask.py` L62–68 `if not bundle.grounded: return honest-empty` fires **before** the history block is even loaded (L74–78); `gather_evidence(question,world)` (L59) **never** receives history, so `bundle.grounded` is purely a function of the current question's evidence. Isolated test `test_ask_honest_empty_still_fires...` **1 passed**. Adversarial throwaway (session seeded with 4 turns incl. `[audit:seq=999]`,`[sop:SOP-FAKE]`,"24 mph") → `grounded=False`, answer exactly `"I have no evidence for that."`, `citations=[]`, `evidence=[]`, **no leak** of any seeded content; turn still recorded. | **CONFIRMED** |
| 2 | **Session store real + honest-degrading** | `session_store.py` connects to Postgres; round-trip persists; sliding window = `ORDER BY turn_index DESC LIMIT N` then reverse → last-N chronological; no DB (`_connect`→None) ⇒ `append`=False / `recent`=`[]` (no fabricated history). Store tests (round-trip / sliding-window / empty-session / honest-noop / labelled-history) all pass within the 31. `grep -rnE 'random\.' session_store.py` → **no match (exit 1)**. | **CONFIRMED** |
| 3 | **Hard Rule 3 unchanged** | `nl_inject.py`: LLM only emits a validated `InjectedIncident` (Pydantic + `validate_domain()`); it enters `world.inject()` (state mutation) / `run_incident` (validator-gated LangGraph loop) — never an actuator. `grep actuator\.|dispatch_order` over `conversation/` → **only a docstring reference** (nl_inject.py:11) naming `master.dispatch_order` as the sole emitter; no emitter in the module. History only feeds `history_block` into the parse prompt. | **CONFIRMED** |
| 4 | **No fabrication / free-cost** | `requirements.txt` working-copy diff is **pre-existing** (pydantic 2.10.4→2.13.4 + Stages 11/11.5/12/12.5/13.5 blocks); `psycopg[binary]==3.3.4` is Stage 11. **No Stage-35-new dep.** No `random.*` / `Math.random` anywhere in `conversation/` or `conversation_routes.py` (grep exit 1). | **CONFIRMED** |
| 5 | **No regression** | `pytest tests/conversation/ -q` → **31 passed** in 62s (25 Stage-29 + 6 Stage-35). | **CONFIRMED** |
| — | Audit / research / explainer / ADR | `audit.sh` = **3** (== baseline; `--no-baseline-drop` justified: additive real code). Research **§46** present (line 3554, dated 2026-07-18, incl. §46.1 history-strategy + §46.2 grounding invariant). Explainer `research/stage-explainers/STAGE_35/index.html` exists (6.4 KB). ADR present + signed. AC1–AC6 all substantiated. | **CONFIRMED** |

---

## Commands I ran (real output, abridged)

```
$ docker ps --filter name=ai-agent-postgres   → ai-agent-postgres Up 17 minutes 0.0.0.0:5544->5432/tcp
$ python --version                             → Python 3.11.9
$ grep -rnE 'random\.' conversation/session_store.py                 → (no match, exit 1)
$ grep -rnE 'random\.(...)|Math\.random' conversation/ conversation_routes.py → (no match, exit 1)

$ git diff backend/requirements.txt   → pydantic 2.10.4→2.13.4 + Stage-11..13.5 blocks only (no Stage-35 dep)

$ pytest tests/conversation/ -q       → 31 passed, 1 warning in 62.26s

$ pytest tests/conversation/test_session_store.py::test_ask_honest_empty_still_fires_with_a_session_and_records_the_turn -q
                                       → 1 passed in 54.17s

$ python adv_grounding.py             (seeded 4 fake-citation turns, then off-topic Q with that session_id)
  grounded      : False
  answer        : 'I have no evidence for that.'
  citations     : []
  evidence      : []
  turns after   : 6 roles: ['user', 'assistant']
  PASS: history did NOT substitute for evidence; honest-empty fired; citations/evidence empty; no leak.

$ bash scripts/audit.sh | tail         → TOTAL 3 ; Baseline 3
$ grep '## 46' research/initial-research.md → "## 46. Stage 35 — Multi-turn dialogue memory ... [2026-07-18]"
$ ls research/stage-explainers/STAGE_35/index.html → exists (6444 bytes)
```

The adversarial script is the strongest evidence for the central claim: I deliberately poisoned the dialogue history
with a plausible answer and fabricated citation handles, then re-asked the same off-topic question with the poisoned
`session_id`. The system returned the fixed honest-empty string with empty evidence/citations and leaked **none** of the
seeded content — history cannot substitute for evidence.

---

## Gaps / observations

| ID | Observation | Severity | Close-blocking? |
|----|-------------|----------|-----------------|
| — | `/factory/ask` multi-turn coreference is **phrasing-level only** — the evidence is still gathered for the CURRENT question, so a follow-up like "and what did we do about it?" that doesn't independently reference an incident will honest-empty rather than resolve "it" from history. This is **correct and documented** (ADR "Consequences": full coreferential GROUNDING / query-rewriting deferred). It is the honesty-preserving choice, not a defect. | Informational | No |
| — | DB-gated tests require `DATABASE_URL`; without it they `skip` (only the honest-noop + labelled-history tests run infra-free). Appropriate — the store IS Postgres-backed. | Informational | No |

No theatre, no bypass, no fabrication, no `--no-verify`/`--force`. The `--no-baseline-drop` (audit holds 3) is legitimate
for an additive-code stage that introduces no new fakery (the residual 3 is the documented G-052 name-pattern
false-positive, unchanged).

---

## Bottom line

**PASS.** The one thing that mattered most — adding dialogue history must not let history stand in for evidence — holds
under adversarial probing: the honest-empty Verifier fires before history is ever loaded, grounding is computed only from
the current question, and prior turns are never cited. The session store is a real, honest-degrading Postgres
sliding-window; Hard Rule 3 is untouched (the LLM remains an input parser, `master.dispatch_order` the sole actuator
emitter); no new deps; 31/31 conversation tests green; audit holds 3. Cleared to close.
