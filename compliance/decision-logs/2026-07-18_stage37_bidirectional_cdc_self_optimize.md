# ADR — Stage 37: Bidirectional CDC → diagnose the induced problem → self-optimize (G-024)

- **Date:** 2026-07-18
- **Status:** Accepted
- **Stage:** 37 (`tasks/STAGE_37_bidirectional_cdc_self_optimize.md`) — the first of the operator-chosen post-CTO-#6
  free/local build arc (37 bidirectional CDC → 38 new head-agent domain → 39 small gap-closers → consolidated handoff).
- **Roles:** `backend-engineer` (Alembic migration, FastAPI route, ingestion service) + `agentic-governance-engineer`
  (KB_25 loop alignment, ledger, ADR).
- **Research:** `research/initial-research.md §48` (bidirectional CDC / ARGUS-style closed-loop self-optimize;
  AIOps-2026 root-cause diagnosis) — appended BEFORE implementing (Hard Rule 11).

## Context

The Stage-13 CDC is ONE-directional: a change to `incidents` (INSERT) or `stages.status` maps to a **pre-formed**
inject via `change_to_inject`. The operator's original product vision (ledger **G-024**, high, open since 2026-05-31)
is the OTHER direction: an operator edits an arbitrary operational VALUE in the DB (a stage's defect_rate, an inventory
level, a supplier's reliability) and the engine should **reason about the problem that edit induces** — diagnose the
root cause, not just replay a canned incident — then drive the self-healing loop and self-optimize. This is the
ARGUS-style closed loop (research §48.1).

The hard constraints: (a) the reasoner must be honest — a benign edit diagnoses NOTHING (no fabricated problem); (b)
Hard Rule 3 must hold — the reasoner proposes, it never actuates; (c) free-cost, no new deps.

## Decisions & outcomes

1. **A value-change DB trigger (migration `0010_cdc_value_changes`).** A `cdc_emit_value()` plpgsql function + three
   `AFTER UPDATE OF <value columns>` triggers: `stages` (defect_rate/throughput/energy_consumption_kw/utilization),
   `inventory` (current_stock/days_of_supply), `suppliers` (reliability_score/lead_time_days). On a monitored value
   change it emits `jsonb_build_object('table',…, 'column',…, 'old',…, 'new',…, 'target_id', NEW.id)` into the existing
   Stage-13 `cdc_outbox` + `pg_notify('cdc_events', …)`. It reuses the durable outbox + NOTIFY + drain machinery — no
   new ingestion path. Proven reversible (downgrade drops the triggers + function; upgrade restores all three).

2. **A pure, unit-testable root-cause reasoner (`ingestion/cdc_reasoner.py`).** `diagnose_change(table, column, old,
   new, *, target_id, context) -> Optional[InducedProblem]` maps a value edit to a root-cause-labelled problem:
   - `stages.defect_rate` ≥ 0.08 & increased → **defect_surge** (critical ≥ 0.15);
   - `stages.throughput`/`utilization` drop ≥ 30% or below a context floor → **machine_crack** (critical if ≥ 50% drop);
   - `stages.energy_consumption_kw` rise ≥ 50% → **power_dip** (critical ≥ 100%);
   - `inventory.current_stock` < reorder_point (from `context`) → **late_delivery** (critical ≤ 0.5×reorder);
   - `inventory.days_of_supply` ≤ 2 → **late_delivery**;
   - `suppliers.reliability_score` < 0.70 & dropped → **late_delivery** (critical < 0.50);
   - `suppliers.lead_time_days` rise ≥ 50% & ≥ 5d → **late_delivery**.
   Severity is **DERIVED from the edit magnitude**, not a synthetic constant (Rule 1a). A benign or unmonitored edit
   returns `None` — an HONEST "no problem diagnosed", never a fabricated incident. Thresholds encode the same
   documented domain signals the sim's health model uses.

3. **The listener routes value edits FIRST.** `change_to_inject` gains a value-edit branch keyed on the `column` key,
   placed BEFORE the table-specific status/incident branches (both keyed on `table == "stages"`). This was load-bearing:
   the initial placement (after the status branch) let the status branch swallow value edits (returned `None` on a
   missing `new_status`). Caught during live testing, fixed, and pinned by a regression test.

4. **The closed loop + Art-12 audit (`process_value_edit`).** Diagnose → sign the reasoning to `audit_chain`
   ("cdc.diagnose") → optionally drive `run_incident` (the validator-gated LangGraph loop). Benign edits return
   `diagnosed=False` and do NOT run the loop.

5. **API surface `POST /factory/db-edit`** (`api/conversation_routes.py`) calls `process_value_edit` off the event loop
   (`asyncio.to_thread`). The response note affirms the reasoner never actuates.

## Hard Rule 3 (verified)

The reasoner emits a proposed incident that enters the SAME validator-gated self-healing loop as a sensor-fired one;
it adds NO new `actuator.*` emitter — the sole emitter remains `master.dispatch_order` behind `safety/validator.py`.
Confirmed by grep (no actuator call in `cdc_reasoner.py`) and asserted in the route/reasoner tests.

## Honesty notes (Rule 1a — verified)

- **No fabrication:** a benign edit → `None`/`diagnosed=False`. Inventory without a `reorder_point` context → benign
  (we cannot honestly diagnose a stockout without the threshold) — verified by test.
- **Severity is magnitude-derived**, not a hardcoded constant.
- **Honest scope:** this is a documented-threshold DIAGNOSTIC rule engine, not a learned causal model. Deeper learned
  causal discovery over real edit→outcome traces needs pilot data (G-035, buyer-blocked) — recorded, not overclaimed.

## Evidence

- Migration `0010` applied + proven reversible (downgrade -1 → upgrade head restores 3 value triggers).
- Live end-to-end: a real `UPDATE stages SET defect_rate=0.15` writes a `cdc_outbox` value row → drains into the
  SimWorld as a diagnosed `defect_surge/critical` (`test_db_value_edit_drains_into_simworld`).
- 64 tests pass (`tests/ingestion` reasoner rules + listener routing + closed loop + live roundtrip; `tests/conversation`
  route tests incl. `/factory/db-edit`).
- `scripts/verify-audit-chain.py` exit 0 (10,477 rows; all 10,398 post-cutover signatures verify).
- `scripts/audit.sh` = 3 (held; `--no-baseline-drop`: additive real code, no `random.*`/mock/hardcoded fabrication).
- No new dependencies (Rule 9).

## Consequences

- G-024 (open since 2026-05-31) is RESOLVED — the CDC loop is bidirectional; an operator DB edit is diagnosed and drives
  the self-healing loop.
- The next stage (38) extends the KB_25 loop to a new head-agent embodiment domain.

## Alternatives considered

- **Reuse `change_to_inject`'s status path (map value edits to a fixed incident).** Rejected — that is exactly the
  one-directional canned-incident behaviour G-024 asks us to move BEYOND; the point is to REASON about the induced
  problem, not replay a template.
- **A learned causal model over edit→outcome traces.** The honest deep target, but it needs real pilot data (G-035);
  building it on synthetic traces would be theatre. Deferred honestly.
- **A generic `AFTER UPDATE` trigger with `to_jsonb(NEW)` diffing.** Rejected — noisy (fires on every column), and the
  column-scoped `AFTER UPDATE OF` triggers are both cheaper and self-documenting about which signals are monitored.
