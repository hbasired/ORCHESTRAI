# ADR — Stage 33: Safety & runtime-oversight hardening (capability tokens close G-075)

- **Date:** 2026-07-13
- **Status:** Accepted
- **Stage:** 33 (`tasks/STAGE_33_safety_oversight_hardening.md`) — the first post-CTO-#6 increment, paying the in-house
  hardening remediations CTO #6 routed (C6-R1 / C6-R3 / C6-R4).
- **Roles:** `robotics-integration-engineer` (sil_bridge / functional safety) + `agentic-governance-engineer`
  (behavioural oversight + risk register) + `security-pqc-engineer` (token design).
- **Research:** `research/initial-research.md §44` (unforgeable actuation capability tokens; runtime behavioural
  oversight SOTA) — appended BEFORE implementing (Hard Rule 11).

## Context

CTO #6 named **G-075** as the standout in-house item to "do as code NOW, do NOT keep deferring to the first PLC
caller" — the longest-lived open safety gap (open through CTO #4/#5/#6): `sil_bridge.execute` trusted a caller-settable
`Decision.allow`/`route`, so a FORGED `Decision(allow=True, route="sil_bridge")` could actuate, and a stale genuine
Decision was a TOCTOU risk. CTO #6 also routed C6-R3 (wire the Stage-31 behavioural monitor as an always-on runtime
hook) and C6-R4 (risk-register refresh for Stages 29–32).

## Decisions & outcomes

1. **G-075 (C6-R1) — unforgeable actuation capability tokens.** `backend/safety/capability_token.py`: `validate()`
   MINTS a token on every ALLOW — `HMAC-SHA-256(per-process secret, canonical{allow, route, contract, sil,
   action_hash, nonce, issued_at})`, where `action_hash = sha256(canonical(action))` binds it to the EXACT action
   (SOTA capability-token pattern, research §44.1). `sil_bridge.execute()` now actuates ONLY via **(a)** authoritative
   RE-VALIDATION (given `contract` + `world_state`, it re-runs `validate()` against CURRENT state and ignores the
   passed verdict — forgery- AND TOCTOU-proof) or **(b)** a valid, FRESH token bound to THIS action. A forged (no
   token), stale (replay/TOCTOU), wrong-action, or tampered `Decision(allow=True)` is REJECTED (`SafetyBypassError`).
   The `Decision` model gained `token`/`nonce`/`issued_at`. **7 dedicated tests + the full 26-test safety suite pass.**
2. **C6-R3 — always-on runtime behavioural oversight.** `agents/runtime/graph.py::run_incident` now feeds every live
   incident's real behavioural features to the Stage-31 `BehavioralMonitor` (via `features_from_run`) when
   `RUNTIME_BEHAVIOR_MONITOR=1` — off by default, off the hot path, honest-degrading (a monitor error never fails the
   run). Emits a signed `behavior.anomaly` row on a real deviation. Runtime determinism holds with it off (verified).
3. **C6-R4 — risk register refreshed for Stages 29–33** (`compliance/risk-register.md`): the conversational NL→action
   Rule-3 posture, the repair-dispatch + RL-shadow gates, the detector single-corpus caveat, the oversight hook, and
   **G-075 CLOSED**. The overstated defence-in-depth wording in `safety/__init__.py` + the `sil_bridge` docstring is
   narrowed to the now-accurate guarantee.

## Honesty notes (Rule 1a — verified)

- **The token is defence-in-depth, not the sole gate.** The authoritative check remains re-running `validate()` from
  the contract + current world_state; the token makes the no-contract path forgery/replay-resistant instead of
  blindly-trusting. The wording now states exactly this — no overclaim.
- **A latent Stage-29 honesty bug found + fixed in regression (Rule 11b working):** `conversation/evidence.py`
  grounded an OFF-TOPIC question on arbitrary recent decision traces once the DB filled (the honest-empty guarantee
  was DB-state-dependent — the Stage-29 review missed it because the DB had few traces then). Fixed: an off-topic
  question with no incident/stage reference no longer grounds on unrelated traces (25 conversation tests pass).
- **No fabrication:** the token uses stdlib `hmac`/`os.urandom` (NOT the theatrical-fallback `random`); the monitor
  hook reports real features or honest-degrades.

## Consequences

- New: `backend/safety/capability_token.py` + `backend/tests/safety/test_capability_token.py` (7 tests). Modified:
  `safety/validator.py` (mint), `safety/contract.py` (Decision fields), `safety/sil_bridge.py` (redeem/re-validate),
  `safety/__init__.py` (wording), `agents/runtime/graph.py` (monitor hook), `conversation/evidence.py` (honest-empty
  fix), `compliance/risk-register.md` (refresh). **New deps: none.** KB_17 updated; G-075 marked RESOLVED.
- **Audit holds 3** (`--no-baseline-drop`: additive safety hardening; no new fakery pattern). Safety (33), runtime
  (13/1skip), security (30), conversation (25) tests pass; `verify-audit-chain.py` exit 0 (10,469 rows).
- Deferred honestly: C6-R2 dependency-refresh (langchain-core 1.x + a2a-sdk, pin-blocked — its own increment); the
  real-world items (pilot G-035/G-043, cert G-011, scale G-066) stay buyer/accredited-body-blocked.

## References
- research §44 · `research/stage-explainers/STAGE_33/index.html` · `backend/safety/capability_token.py` ·
  `backend/safety/sil_bridge.py` · `backend/tests/safety/test_capability_token.py` · KB_17 · G-075
  (`audits/OPEN_GAPS_LEDGER.md`) · `audits/CTO_6_review.md` (C6-R1/R3/R4) · arxiv 2605.25632 (Authority-Frontier
  capability tokens) · a2aproject/A2A #1404 (capability-based authz).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-13T15:40:53+00:00 -->
<!-- signature: 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 -->
