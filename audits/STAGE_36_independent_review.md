# Stage 36 — Independent Review (Dependency-refresh feasibility assessment / CTO #6 C6-R2)

- **Reviewer:** independent `task-auditor` agent (NOT the Stage-36 implementer).
- **Date:** 2026-07-18
- **Stage type:** DOCS-ONLY feasibility assessment + honest deferral (no code / requirements / lockfile change).
- **Nature of this review:** an HONESTY / EVIDENCE-REPRODUCIBILITY audit — the deliverable *is* a claim that a
  refresh is unsafe free/local, so the job is to (a) re-run the non-mutating probes and confirm the evidence is real
  and accurate, (b) confirm nothing was actually installed/broken, and (c) confirm nothing is faked as done.

## TOP-LINE VERDICT: **PASS**

The dry-run evidence is real and reproduces to the digit — including the assessment's central claim (the
langchain-core-1.x chain pulls **starlette 1.3.1**, which conflicts with the pinned `fastapi 0.115.6`'s declared
`starlette<0.42`). The working env is verified **unchanged** (all pins intact, nothing installed, the stack still
imports and a safety smoke test passes). The stage is genuinely docs-only, the audit holds at 3, and G-055/G-056/G-070
correctly stay **OPEN** with the assessment attached — nothing is faked as "done." No gaps found. Cleared to close.

## Claim-by-claim evidence table

| # | Claim | What I ran | Verdict |
|---|---|---|---|
| 1a | langchain-core-1.x chain would install lc-1.3.14 / lc-core-1.4.9 / langgraph-1.2.9 / **langgraph-checkpoint-4.1.1** / **starlette-1.3.1** | `pip install --dry-run "langchain-core>=1.0" "langchain>=0.4" "langgraph>=0.3" "langchain-mcp-adapters"` | **CONFIRMED** — output matches the assessment table exactly (see below) |
| 1b | a2a-sdk half would install a2a-sdk-1.1.1 · **httpx-0.28.1** · **protobuf-6.33.6** · json-rpc · culsans · aiologic | `pip install --dry-run "httpx>=0.28.1" "a2a-sdk"` | **CONFIRMED** — output matches assessment table exactly |
| 1c | HARD CONFLICT: `fastapi 0.115.6` requires `starlette<0.42` → starlette 1.3.1 genuinely conflicts, forcing a fastapi major bump | `python -c "import importlib.metadata as m; print(m.requires('fastapi'))"` → `starlette<0.42.0,>=0.40.0` | **CONFIRMED** — real declared metadata conflict, not asserted |
| 2a | Working env UNCHANGED: langchain-core 0.3.28 / httpx 0.27.2 / fastapi 0.115.6 / langgraph 0.2.60 / starlette 0.41.3 | `m.version(...)` **before AND after** all dry-run probes | **CONFIRMED** — identical before/after; a2a-sdk NOT INSTALLED; protobuf still 7.35.1 (nothing pulled in) |
| 2b | Stack still imports + smoke test passes | `pytest tests/safety/test_capability_token.py -q` | **CONFIRMED** — 7 passed |
| 3a | Docs-only — no requirements.txt/lockfile/code change by Stage 36 | mtimes + pin inspection of `backend/requirements.txt` | **CONFIRMED** — requirements.txt mtime `2026-07-11 17:30` (a week BEFORE Stage 36's 2026-07-18 files); pins still at 0.3.28/0.27.2/0.115.6/0.2.60/0.41.3 |
| 3b | Audit holds 3 | `bash scripts/audit.sh` | **CONFIRMED** — TOTAL 3 (all fakery patterns 0; the 3 = documented G-052 `_generate_heuristic_actions` false-positive), baseline 3 |
| 4a | G-055/G-056/G-070 stay OPEN with assessment attached (nothing faked as done) | Read `audits/OPEN_GAPS_LEDGER.md` rows | **CONFIRMED** — all three read "STAYS OPEN, now evidence-backed"; none marked RESOLVED |
| 4b | ADR frames this as a deferral, not a fix; concrete migration plan; accurate "low-value/SBOM-gated" mitigation | Read ADR + assessment §4 + explainer + G-065 ledger row | **CONFIRMED** — ADR: "NOT executed"; §4 is a concrete 6-step branch/CI plan; G-065 is MOSTLY RESOLVED (SBOM + bandit-blocking + `dependency-exceptions.md`), so "not stale-and-vulnerable" is accurate |
| 4c | Research §47 + explainer exist | `research/initial-research.md` L3589 §47.1/§47.2; `research/stage-explainers/STAGE_36/index.html` (7140 B) | **CONFIRMED** — both present, honest, reproduce the evidence |

## Dry-run output I reproduced (verbatim, this session)

```
$ pip install --dry-run "langchain-core>=1.0" "langchain>=0.4" "langgraph>=0.3" "langchain-mcp-adapters"
Would install langchain-1.3.14 langchain-core-1.4.9 langchain-mcp-adapters-0.3.0 langchain-protocol-0.0.18 \
  langgraph-1.2.9 langgraph-checkpoint-4.1.1 langgraph-prebuilt-1.1.0 langgraph-sdk-0.4.2 langsmith-0.10.6 \
  starlette-1.3.1 uuid_utils-0.17.0 zstandard-0.25.0

$ pip install --dry-run "httpx>=0.28.1" "a2a-sdk"
Would install a2a-sdk-1.1.1 aiologic-0.17.1 culsans-0.11.0 httpx-0.28.1 json-rpc-1.15.0 protobuf-6.33.6 wrapt-2.2.2

$ python -c "import importlib.metadata as m; print(m.requires('fastapi'))"
['starlette<0.42.0,>=0.40.0', 'pydantic!=1.8,...,<3.0.0,>=1.7.4', ...]   # ← starlette<0.42 vs the chain's 1.3.1

# env BEFORE probes:      0.3.28 0.27.2 0.115.6 0.2.60 0.41.3
# env AFTER all probes:   0.3.28 0.27.2 0.115.6 0.2.60 0.41.3  | protobuf 7.35.1 | a2a-sdk: NOT INSTALLED
# safety smoke:           7 passed
# audit.sh:               TOTAL 3 (baseline 3)
```

The langchain-core-1.x row matches the assessment's table row byte-for-byte on every load-bearing package
(langchain-core-1.4.9, langgraph-1.2.9, langgraph-checkpoint-4.1.1, starlette-1.3.1, langchain-mcp-adapters-0.3.0). The
a2a-sdk row matches on a2a-sdk-1.1.1 / httpx-0.28.1 / protobuf-6.33.6 / json-rpc / culsans / aiologic.

## Corroboration (independent, beyond re-running the probes)

- **The requirements.txt itself already documents the exact blockers the assessment names** — the pinned file carries
  the comments `pin langgraph-checkpoint <3 — 4.x needs a newer langchain-core and breaks langgraph 0.2.60` and
  `starlette is PINNED <0.42 for fastapi 0.115.6`. The assessment's "load-bearing pin" claims are grounded in the
  actual pin rationale, not invented for this stage.
- **The assessment is honest about the SOFT edge, not overclaiming it.** Blocker #4 (a2a-sdk → protobuf 6.x vs the
  "protobuf<5 for TF" pin note) is self-qualified in the doc: "the installed env has drifted to protobuf 7.35.1 with
  TF 2.15 working, so this specific edge is softer than the pin note." I confirmed protobuf is indeed **7.35.1** — the
  assessment correctly downgrades its own claim rather than overstate the conflict. This is a mark of honesty.

## Theatre / bypass / overclaim scan

- **No theatre introduced** — docs-only; `audit.sh` fakery patterns all 0; the residual 3 is the pre-existing,
  documented G-052 `_generate_heuristic_actions` name-pattern false-positive (not new).
- **No bypass** — `--no-baseline-drop` is the correct and disclosed disposition for a docs-only assessment stage
  (CLAUDE.md §6 allows it for governance/docs-only stages); baseline held, not gamed.
- **No overclaim** — the ADR/assessment/explainer/ledger uniformly frame this as an honest **deferral with evidence +
  plan**, not a fix. G-055/G-056/G-070 remain OPEN. Nothing is presented as executed.

## Gaps

**None (blocking or minor).** The deliverable is truthful, the evidence reproduces exactly, the env was not mutated,
and the affected gaps stay honestly OPEN. The underlying dependency-refresh migration itself remains correctly deferred
to a dedicated branch/staging + CI increment (G-055/G-056/G-070) — that is the intended outcome of C6-R2, not a gap in
this stage.

## Bottom line

Stage 36 does exactly what a rigorous, honest response to "do the dependency refresh" should do when the refresh is
unsafe in the working env: it attempts it **safely** (non-mutating dry-run), **proves** it is a cascading multi-major
migration (langchain/langgraph runtime + fastapi/starlette API + httpx/protobuf) with a **real** metadata conflict
(`fastapi`'s `starlette<0.42` vs the chain's starlette 1.3.1), **documents** the exact blockers + a concrete de-risked
plan, and **defers honestly** — leaving G-055/G-056/G-070 OPEN and evidence-backed rather than faking a "done" or
breaking the verified GA'd stack. Every claim I checked reproduces; the working env is verifiably untouched.

**VERDICT: PASS — cleared to close.**
