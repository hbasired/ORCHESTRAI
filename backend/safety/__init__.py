"""Functional safety wrapper (KB_17). LLM/planner proposes; the classical validator gates; the SIL bridge executes.

- `contract.py` — the Pydantic safety-contract DSL (preconditions / invariants / postconditions + `sil` + `iso_clauses`
  + `fail_safe_path`); `contracts/` — the static per-action contracts.
- `validator.py` — `validate(action, world_state, contract) -> Decision` (SIL routing) + the Stage-16 `validate_order`.
- `sil_bridge.py` — the ONLY emitter of `actuator.*` spans. It actuates ONLY via a forgery/TOCTOU-resistant path
  (G-075 CLOSED, Stage 33): (a) authoritative RE-VALIDATION when passed contract+world_state, OR (b) a valid, fresh,
  action-bound **capability token** minted by `validate()` (`capability_token.py`). A forged/stale/wrong-action
  `Decision(allow=True)` is REJECTED — the bridge no longer trusts caller-set `allow`/`route`.
- `sto_ss1.py` — STO / SS1 safe-motion paths (signed `audit_chain` rows).
- `sil_pl_map.py` — IEC 61508 SIL ↔ ISO 13849-1 PL mapping.
- `self_healing/` — joint-torque anomaly detection + behaviour-tree self-repair (self-repair still passes the validator).

CI invariant (`scripts/check-safety-trace-pairing.py`): every `actuator.*` span is preceded by a `safety.validate.*`
span. The architecture is *amenable* to certification; actual SIL cert = Stage 23 + external assessor (no SIL claim).
"""
