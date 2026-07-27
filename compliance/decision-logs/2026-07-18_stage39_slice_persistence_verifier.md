# ADR — Stage 39: Slice decision-log persistence + a non-relaxed, genuinely-rejecting Stage-6 verifier (G-045, G-051)

- **Date:** 2026-07-18
- **Status:** Accepted
- **Stage:** 39 (`tasks/STAGE_39_slice_persistence_verifier.md`) — the last of the operator-chosen post-CTO-#6 free/local
  build arc (37 bidirectional CDC → 38 facilities/energy → 39 small gap-closers → consolidated handoff).
- **Roles:** `backend-engineer` (service edit, DB writer, safety-constraint wiring) + `agentic-governance-engineer`
  (Art-12 traceability, ledger, ADR).
- **Research:** `research/initial-research.md §50` (EU AI Act Art-12 record-keeping / decision provenance; binding plan
  verification) — appended BEFORE implementing (Hard Rule 11).

## Context

Two ledger gaps, both on the Stage-6 slice runner (`backend/services/slice_runner.py`), both surfaced by the Stage-6
independent reviews:

- **G-045** (medium): Stage-6 AC3 claimed slice decisions are "persisted to `decision_logs`", but the shipped
  provenance was the in-memory `SliceTrail` + WS envelopes only — no DB writer existed in the sim path. An honest
  overclaim to correct.
- **G-051** (low, PARTIALLY PAID at Stage 11): the Stage-6 VERIFY step relaxed ALL three rejecting contracts
  (`available_crew=n`, `throughput_floor_frac=0.0`, `max_concurrent_critical_offline=n`), so the plan verifier could
  never reject in the slice path — it only attached provenance. The Stage-11 runtime `verify` node already binds
  (proven), but the Stage-6 `slice_runner` relaxation itself remained open.

Both are completeness/honesty fixes: make a claimed capability actually true, and turn a no-op gate into a real one.

## Decisions & outcomes

1. **G-045 — automatic `decision_logs` persistence (`_persist_decision_log`).** On each live-path intervention the
   slice runner writes a `decision_logs` row: `caller="slice_runner"`, `tool=<decision kind>`, `input_hash`/`output_hash`
   = SHA-256 over the canonical telemetry+prediction (input) and decision+verification+executed (output), `inputs`/
   `outputs` JSONB, and the incident FK when the id is a real UUID (a non-UUID sim tag is stored in `inputs.incident_ref`
   instead, so the FK constraint is never violated). This matches the Art-12 requirement: AUTOMATIC logging of every
   algorithmically-driven decision with full input→output provenance (research §50). Wired ON in the live path
   (`LiveSliceRunner` passes `persist_log=True`) and OFF for the offline A/B (`persist_log=False`, so experiments add no
   DB load and their measured numbers are unchanged).

2. **G-045 — honest degradation (Rule 1a).** No DB reachable → `_persist_decision_log` returns `None`, surfaced as
   `decision_log_id: null` in the intervention payload — never a fabricated id. The in-memory `SliceTrail` + WS
   envelopes remain unchanged.

3. **G-051 — a binding (non-relaxed) `PlantState`.** `_build_plant_state` now supplies REAL binding constraints:
   `throughput_floor_frac=0.6` (≥60% of stages must stay online — the verifier's own default), `max_concurrent_critical_offline=1`
   (the SIL redundancy cap), and `available_crew = crew_total(2) − stages_currently_in_maintenance` (crew contention).
   The plan verifier engine was already genuine (`test_plan_verifier.py`); this brings the Stage-6 slice path to the
   same honesty. The values are conservative, so the normal single-machine maintenance always passes.

## Honesty notes (Rule 1a — verified)

- **A genuinely-rejecting gate is the OPPOSITE of theatre.** The change makes the verifier able to REJECT — proven for
  a throughput-floor breach AND a critical-redundancy breach — where before it could only rubber-stamp.
- **No false-reject regression:** the normal safe single maintenance is still APPROVED (test), and the Stage-6 A/B is
  preserved: unplanned downtime −190.5 min (OFF 470.3 → ON 279.7), 3.67 planned maintenances still fire.
- **No fabrication:** the persistence writes real rows or honestly no-ops (None) without a DB; the hashes are real
  SHA-256; no `random.*`/mock/hardcoded constant.

## Evidence

- 8 new tests (`tests/test_slice_persistence_verifier.py`): binding plant state (floor 0.6 / SIL cap 1 / crew reduced by
  busy), genuine rejection (throughput-floor + critical-redundancy), no false-reject, DB persistence round-trip (real
  64-char hashes + caller/tool/stage_id), honest no-op without DB, non-UUID incident-ref handling.
- Regression: `test_slice_intervene` + `test_slice_events` + `test_slice_ab` + `test_slice_predict_live` +
  `test_plan_verifier` → 31 passed. `scripts/run_slice_ab.py` → unplanned downtime −190.5 min (A/B preserved).
- `scripts/audit.sh` = 3 (held; `--no-baseline-drop`: additive real code, no fabrication). No new dependencies (Rule 9).

## Consequences

- G-045 RESOLVED (Art-12 slice persistence is real); G-051 fully RESOLVED (the Stage-6 slice VERIFY gate genuinely
  rejects). Both close the Stage-6 honesty gaps carried since 2026-06-12/06-14.
- The post-CTO-#6 free/local build arc (37→38→39) is COMPLETE. The next task is the consolidated handoff summary
  (option 1) declaring the disciplined build complete; the highest-leverage remaining move is a real pilot (buyer-blocked).

## Alternatives considered

- **Leave G-051 as an honest deferral** (the runtime already binds). Rejected — the operator chose to close the
  remaining free/local gaps, and the Stage-6 slice path was still an overclaim; binding it is cheap and correct.
- **Route slice persistence through `audit_chain` instead of `decision_logs`.** `decision_logs` is the Stage-1 table
  the Stage-6 AC3 named and its columns (caller/tool/input_hash/output_hash/inputs/outputs) fit exactly; `audit_chain`
  is the signed cross-agent evidence chain (already used by the runtime). Using the named table keeps the fix scoped
  and honest to the original claim.
