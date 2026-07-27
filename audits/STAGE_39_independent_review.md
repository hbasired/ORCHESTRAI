# Stage 39 — Independent Review (slice decision-log persistence + non-relaxed Stage-6 verifier; G-045, G-051)

- **Auditor:** independent `task-auditor` agent (did NOT build this stage).
- **Date:** 2026-07-20
- **Scope:** `backend/services/slice_runner.py` (`_persist_decision_log`, rewritten `_build_plant_state`, `persist_log`
  param + `LiveSliceRunner` wiring); `backend/tests/test_slice_persistence_verifier.py`; the ADR, explainer, research
  §50, KB_18/KB_25 diffs; audit-baseline discipline.
- **Method:** read every changed file; re-ran the stage tests, the full slice regression suite, and the A/B **against
  the live Docker stack** (Postgres@5544 / Neo4j@7687 / Redis@6379); independently wrote a `decision_logs` row and
  hand-recomputed its SHA-256 provenance hash; re-ran `scripts/audit.sh`.

## TOP-LINE VERDICT: **PASS**

Both gap-closers are real, honest, and independently reproduced. The make-or-break check — **is the Stage-6 A/B still
preserved now that the verifier genuinely binds?** — is **YES**: the A/B was re-run with the binding verifier active
(`enable_verify` defaults `True`, so the A/B exercises the new binding `PlantState`) and it still shows unplanned
downtime **−190.53 min** with **3.67 planned maintenances still firing** — i.e. the binding gate does NOT false-reject
the normal maintenance. Persistence writes real SHA-256-hashed rows or honestly no-ops (`None`) without a DB. No
theatre, no fabrication, no bypass. Audit holds at 3. No new dependencies.

---

## Commands run + key output

### 1. Stage-specific tests (Docker Postgres up) — 8 passed, none skipped
```
cd backend; DATABASE_URL=postgresql://aiagent:***@localhost:5544/manufacturing \
  python -m pytest tests/test_slice_persistence_verifier.py -v
```
```
test_plant_state_is_not_relaxed PASSED
test_available_crew_reduced_by_busy_maintenance PASSED
test_verifier_rejects_when_throughput_floor_breached PASSED
test_verifier_rejects_second_critical_offline PASSED
test_verifier_still_approves_safe_single_maintenance PASSED
test_persist_is_honest_noop_without_db PASSED
test_persist_writes_real_decision_log_row PASSED           <- ran (not skipped; DB present)
test_persist_stores_non_uuid_incident_ref_in_inputs PASSED <- ran (not skipped; DB present)
8 passed in 7.62s
```
Both DB round-trip tests actually executed (DATABASE_URL was set), so the `skipif` did not hide them.

### 2. Regression — existing slice + verifier suites — 31 passed
```
python -m pytest tests/test_slice_intervene.py tests/test_slice_events.py tests/test_slice_ab.py \
  tests/test_slice_predict_live.py tests/test_plan_verifier.py -q
-> 31 passed, 2 warnings in 27.36s
```

### 3. **A/B (make-or-break) — measured result preserved**
```
python scripts/run_slice_ab.py
seeds=[42, 43, 44] sim_hours=8.0
OFF: unplanned=470.27 min, crack_breakdowns=4.33, thr=6.96 u/h
ON : unplanned=279.74 min, crack_breakdowns=1.33, planned_maint=3.67, thr=6.92 u/h
MEASURED delta (OFF-ON): unplanned_downtime 190.53 min, total_downtime 150.87 min
```
`planned_maint=3.67` proves the binding verifier is **not** silently rejecting the maintenances that make Stage 6 work.
The A/B loop runs `run_slice_step` with `enable_verify=True` (default) → the binding `PlantState` **is** in the loop
during the A/B, and the normal single-machine maintenance still passes. The "A/B preserved" claim is TRUE.

### 4. Independent G-045 DB round-trip (hand-verified hashes)
```
_persist_decision_log(caller="slice_runner", tool="preventive_maintenance",
   inputs={"stage_id":7,"telemetry":{"torque_nm":60.0},"prediction":{"p_fail":0.8}},
   outputs={...}, incident_id="not-a-uuid-xyz")
-> decision_id 42f34316-...  row=('slice_runner','preventive_maintenance', <ih>, <oh>, None, 'not-a-uuid-xyz')
hand-recomputed input_hash == stored input_hash : True   (SHA-256 over canonical JSON, incident_ref folded into inputs)
hash lengths 64/64, distinct: True
incident_id FK is None (non-uuid), incident_ref='not-a-uuid-xyz' stored in inputs JSONB
```
The stored `input_hash` **matches my independent SHA-256 recomputation** → the provenance hashes are real, not
fabricated. Non-UUID incident tags are correctly kept out of the FK and stored in `inputs.incident_ref`.

### 5. Mechanical audit — holds at 3
```
bash scripts/audit.sh   ->  TOTAL 3   (heuristic_actions 3, all others 0)   Baseline 3
```
The residual 3 is the documented G-052 `_generate_heuristic_actions` name-pattern false-positive (untouched).
`.audit-baseline` = 3. No new theatre introduced (`random.*`/mock/hardcoded grep on `slice_runner.py` → NONE).

### 6. Free-cost — no new deps
`slice_runner.py` imports only stdlib (`hashlib`, `json`, `uuid`, `os`, …) + `psycopg` (already pinned
`psycopg[binary]==3.3.4`, requirements line 48). No Stage-39 line added to `backend/requirements.txt`.

---

## Per-criterion evidence table

| AC | Claim | Independently confirmed? | Evidence |
|---|---|---|---|
| **AC1** — G-045 automatic `decision_logs` persistence | `_persist_decision_log` writes each live decision (caller/tool + SHA-256 in/out hashes + JSONB), wired into live path via `LiveSliceRunner(persist_log=True)`, off for A/B | **YES** | `slice_runner.py:100-137` writer; `:420` `persist_log=True` (only caller); `:288-295` wired in loop. DB round-trip test + my hand-recomputed hash match. `decision_logs` schema columns all exist (`0001_init.py:286-298`). |
| **AC2** — G-045 honest degradation | No DB → returns `None`, never a fabricated id | **YES** | `:108-110` early `return None` when no DSN; `:136-137` `except → return None`. `test_persist_is_honest_noop_without_db` passes (env unset). |
| **AC3** — G-051 binding (non-relaxed) `PlantState` | floor `0.6`, SIL cap `1`, `crew = 2 − busy` | **YES** | `slice_runner.py:144-174`; `test_plant_state_is_not_relaxed` + `test_available_crew_reduced_by_busy_maintenance` pass. Values are real & bind (not `0.0`/`n`). |
| **AC4** — G-051 verifier genuinely REJECTS | rejects throughput-floor breach AND second-critical breach | **YES** | Both tests assert `approved is False` **and the right constraint** (`throughput_floor` / `critical_redundancy`). Traced verifier logic (`plan_verifier.py:132-167`) — rejections are correctly derived, not asserted. |
| **AC5** — G-051 no false-reject + A/B preserved | safe single maintenance still APPROVED; A/B −190.5 min, ~3.67 planned maint | **YES (make-or-break)** | `test_verifier_still_approves_safe_single_maintenance` passes; A/B re-run **−190.53 min, planned_maint=3.67** with binding verifier active; 31 regression tests pass. |
| **AC6** — free-cost + audit-baseline | no new deps; audit holds 3 (`--no-baseline-drop`) | **YES** | No new dep (psycopg pre-existing, rest stdlib). `audit.sh` = 3. Justification honest: additive real code; a genuinely-rejecting gate is the opposite of theatre. |

---

## Theatre / regression / overclaim findings

**None blocking.** Specifically checked and cleared:

- **No fabrication.** grep of `slice_runner.py` for `random.*`/mock/`generateMockState`/hardcoded-response patterns →
  NONE. Persistence hashes are genuine SHA-256 (hand-verified). No-DB path honestly returns `None`.
- **No bypass.** No `--no-verify`/`--force`. `--no-baseline-drop` is legitimate here (additive real code; nothing
  grep-visible to remove — the win is a real DB writer + a gate that can now reject).
- **Ledger honesty is accurate.** "G-051 **fully** RESOLVED" correctly discloses the runtime-vs-slice distinction:
  the Stage-11 runtime `verify` node was already binding (PARTIALLY PAID); Stage 39 closes the remaining Stage-6
  `slice_runner` half. "G-045 RESOLVED" is TRUE — the Stage-6 AC3 "persisted to decision_logs" claim, previously
  in-memory `SliceTrail` only, is now a real DB write on the live path.

### Minor, non-blocking observations (not gaps; recorded for completeness)
1. `_persist_decision_log` opens a fresh `psycopg.connect` per decision (no pooling). Acceptable for the low-cadence
   (~5s) live loop and disclosed as best-effort; a shared session would be a future optimisation, not a correctness
   issue.
2. A **valid-format** UUID `incident_id` that is not an existing `incidents` FK would fail the INSERT (FK constraint)
   and honestly return `None` (that decision would not persist). This is a very narrow edge — real incident ids come
   from the DB — and the behaviour is honest no-op, not fabrication. No action required.

## Gaps that must be fixed before close

**None.** All six acceptance criteria are backed by evidence I independently reproduced. Cleared to close.
