# Stage 37 — Independent Review (bidirectional CDC → diagnose induced problem → self-optimize, G-024)

- **Auditor:** independent `task-auditor` agent (did NOT build this stage).
- **Date:** 2026-07-18
- **Verdict:** **PASS**
- **Scope:** `backend/ingestion/cdc_reasoner.py` (new), `backend/alembic/versions/0010_cdc_value_changes.py` (new),
  `backend/tests/ingestion/test_cdc_reasoner.py` (new), `backend/ingestion/cdc_listener.py` (mod — value-edit branch),
  `backend/api/conversation_routes.py` (mod — `POST /factory/db-edit`), `backend/tests/conversation/test_conversation_routes.py` (mod — 3 route tests),
  ADR `compliance/decision-logs/2026-07-18_stage37_bidirectional_cdc_self_optimize.md`, research §48, KB_07, KB_TASK_LOG, ledger G-024.

## Top-line

The stage is honest, real, and independently reproducible. I read every new/modified file, re-ran the full test
suite against the live Docker Postgres, independently reproduced the live trigger→outbox path with my own `UPDATE`,
inspected the migration's triggers in `information_schema`/`pg_trigger`, and independently proved severity is
magnitude-derived (not a constant). No theatre, no Hard-Rule-3 violation, no bypass. **No blocking gaps.**

## Per-criterion evidence table

| AC | Claimed | Independently confirmed? | Note / evidence |
|---|---|---|---|
| **AC1** value-change DB trigger | migration `0010` adds `cdc_emit_value()` + 3 `AFTER UPDATE OF <cols>` triggers; live `UPDATE defect_rate=0.15` writes an outbox row | **YES** | `alembic current` = `0010_cdc_value_changes (head)`. `pg_get_triggerdef` shows exactly `AFTER UPDATE OF defect_rate, throughput, energy_consumption_kw, utilization ON stages`, `current_stock, days_of_supply ON inventory`, `reliability_score, lead_time_days ON suppliers` — matching the migration byte-for-byte. My own `UPDATE stages SET defect_rate=0.15` wrote outbox `{'new':0.15,'old':0.02,'table':'stages','column':'defect_rate','target_id':…}`. `test_db_value_edit_drains_into_simworld` **passed** (live roundtrip, not skipped). |
| **AC2** root-cause reasoner, severity magnitude-derived, benign→None | `diagnose_change()` maps edits→root-cause labels; severity from magnitude; `None` for benign; no fabrication | **YES** | Read `cdc_reasoner.py` in full. Proved magnitude derivation: `defect_rate` 0.09/0.14→**warning**, 0.15/0.30→**critical**; `throughput` 100→90→**None**, →65→**warning**, →45→**critical**. Benign/unmonitored → `None` (live `utilization` 0.9→0.95 → `None`; `stages.name`/`widgets.color` → `None`; inventory without `reorder_point` → `None`). No `random.*`/mock/hardcoded-response literal (grep NONE). |
| **AC3** listener routes value edits FIRST | `change_to_inject` checks the `column` branch before the `table=="stages"` status branch | **YES** | `cdc_listener.py:38` `if "column" in change:` precedes the `table_name == "stages"` status branch at `:61`. Regression `test_status_change_still_works_after_value_branch` **passed** (`{"stage_id":5,"new_status":"broken"}` → `machine_crack/critical` still fires). |
| **AC4** closed loop + Art-12 audit | `process_value_edit` diagnoses → signs `audit_chain` "cdc.diagnose" → optional `run_incident`; benign → `diagnosed=False`, no loop | **YES** | `cdc_reasoner.py:156-170`: best-effort `audit_chain.append("cdc:reasoner","cdc.diagnose",…)`; `run_loop` → `run_incident(problem.to_incident())`. `run_incident` (`agents/runtime/graph.py:74`) takes a `dict` incident and feeds `AgentState(incident=…)` — the `to_incident()` shape is compatible; the loop return keys (`backend/interrupted/decisions/audit_seqs`) match what the wrapper reads → real wiring, not a stub. `test_process_value_edit_signs_audit_row` (DB) **passed**; benign path returns `diagnosed=False` (tested). |
| **AC5** API surface | `POST /factory/db-edit` → `process_value_edit` via `to_thread` | **YES** | `conversation_routes.py:136-149` `db_edit` → `await asyncio.to_thread(process_value_edit,…)`. 3 route tests pass: `test_db_edit_diagnoses_defect_surge`, `test_db_edit_benign_edit_is_honest`, `test_db_edit_inventory_needs_reorder_context`. |
| **AC6** Hard Rule 3 preserved | reasoner never actuates; sole `actuator.*` emitter unchanged | **YES** | `grep actuator` over `cdc_reasoner.py` / `cdc_listener.py` / `conversation_routes.py` → **NONE**. The only `actuator.*` span emitters remain `safety/sil_bridge.py:69` and `integrations/vda5050/master.py:146` — unchanged by this stage. The diagnosed problem enters solely via the validator-gated `run_incident` loop. |
| **AC7** free-cost + audit-baseline | no new deps; audit holds at 3 (`--no-baseline-drop`, honest) | **YES** | `cdc_reasoner.py` is pure-Python; migration is plpgsql; no import of a new package. `scripts/audit.sh` (no `--baseline`) → **TOTAL 3** = baseline. The 3 residuals are all `_generate_heuristic_actions` in `backend/ml/rl_policy.py` (documented G-052 false-positive) — **zero in Stage 37 code**. `--no-baseline-drop` justification "additive real code, no fabrication removed" is honest (project fabrication already 0 since Stage 28). |

## Commands run (key output)

```
$ alembic current                     → 0010_cdc_value_changes (head)
$ pytest tests/ingestion tests/conversation -q
    → 64 passed, 3 warnings in 62.64s   (0 skipped — live-DB tests exercised, not skipped)
$ (psycopg) live UPDATE stages SET defect_rate=0.15
    → cdc_outbox row {'new':0.15,'old':0.02,'table':'stages','column':'defect_rate','target_id':95029}
    → change_to_inject(...) → ('defect_surge','critical')
    → utilization 0.9→0.95 → None (benign, honest)
$ pg_get_triggerdef: 3 triggers = AFTER UPDATE OF <value cols> on stages/inventory/suppliers  (match migration)
$ scripts/audit.sh (no --baseline)    → TOTAL 3 = baseline (held); 3× heuristic_actions all in ml/rl_policy.py
$ scripts/verify-audit-chain.py       → Audit chain OK (10477 rows; all 10398 post-cutover signatures verify); EXIT 0
```

## Theatre / bypass / Hard-Rule findings

- **None.** No `random.*` / `Math.random` / mock / hardcoded-response literal in any new file. No new actuator
  emitter. No `--no-verify` / `--force`. `--no-baseline-drop` on an additive post-fabrication-zero build stage is the
  established, honest pattern (Stages 29–36 all held at 3 the same way).

## Migration review

- `upgrade()` creates `cdc_emit_value()` + 3 column-scoped `AFTER UPDATE OF` triggers (idempotent `DROP TRIGGER IF EXISTS`
  guards). `downgrade()` drops all 3 triggers + the function — a correct inverse. Verified live: `alembic current` = head
  and all three triggers/the function exist in the DB with the exact column sets from the migration. (I did NOT run
  `downgrade` per the read-only mandate; the code is a valid inverse by inspection and the triggerdefs match.)

## Non-blocking observations (not gaps)

1. The `run_loop=True` branch (`process_value_edit` → `run_incident`) is correctly wired (compatible dict, real
   Stage-11 loop return shape) but is not directly exercised end-to-end by an automated test — route tests use
   `run_loop=False` and the live test covers the CDC-inject path, not `run_incident`. The reasoner→incident conversion
   IS unit-tested (`test_to_incident_shape_and_source`) and `run_incident` is heavily tested elsewhere, so this is a
   coverage nicety, not a defect. No action required for close.
2. The reasoner is a documented-threshold DIAGNOSTIC rule engine, not a learned causal model — this is stated honestly
   in the ADR, task doc, and ledger (learned causal discovery over real edit→outcome traces → G-035, buyer-blocked).
   Correctly scoped, not overclaimed.

## Gaps that must be fixed before close

- **None.** The stage is cleared to close.
