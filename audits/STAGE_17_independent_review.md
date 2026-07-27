# Stage 17 — Independent Review (Functional Safety Wrapper + Agentic Zero-Trust + Self-Healing)

**Reviewer:** independent `task-auditor` persona (a DIFFERENT agent than the Stage-17 implementer).
**Date:** 2026-06-21
**Verification mode:** **DYNAMIC** — infra UP (PG :5544, Neo4j :7687, Mosquitto :1883, Ollama :11434, Groq key).
All tests re-run live; the live audit-chain DB write path exercised; a bypass was actively constructed.
**Scope:** `backend/safety/**`, `backend/security/**`, `scripts/check-safety-trace-pairing.py`,
`backend/agents/runtime/nodes.py` (execute node), `backend/integrations/vda5050/master.py`,
`backend/crypto/software_provider.py`, `backend/tests/{safety,security}/**`, `.github/workflows/ci.yml`,
ADR `2026-06-21_stage17_functional_safety_wrapper.md`, research §27, KB_17/KB_12, risk-register, ledger G-063/G-064.

---

## VERDICT: **PASS** (with one MEDIUM hardening gap ledgered to Stage 18, and two LOW notes)

This is a genuine, honest, depth-appropriate safety stage. Every acceptance criterion is independently confirmed
with runnable evidence. The contracts contain real checks (not `lambda: True`), the validator fails safe on a raising
check, SIL routing is correct, the self-healing loop really detects/repairs/STOs, and the zero-trust controls really
distinguish forged identities, tampered manifests, rogue tools, injection, and rate abuse. No theatre patterns; no
hard-rule violation in any LIVE wired path; honesty discipline is strong (no SIL cert claimed; `sil_bridge` honestly a
placeholder; A2A mTLS honestly deferred to Stage 18).

The one substantive finding (F1) is that the `sil_bridge.execute` **defence-in-depth** claim is **partially
overstated** — the bridge re-checks the *shape* of a `Decision` (allow flag + route string) but not its *authenticity*
or the *contract conditions*, so a forged `Decision` actuates. This is **not a live Rule-3 violation today** (no
production caller reaches `sil_bridge.execute`; the runtime is sim-only and the only real actuator path,
`master.dispatch_order`, is correctly gated). It is a real weakness in the in-code claim that becomes load-bearing
when `sil_bridge` gets a real production caller — ledgered to Stage 18.

---

## Acceptance-criteria evidence table

| # | Criterion | Claimed | Independently confirmed? | Note |
|---|---|---|---|---|
| AC0 | Named ZT framework + per-agent ML-DSA-65 identity + MCP authz + signed manifest + rate-limit (G-063/G-064) | done | **YES** (live) | NIST SP 800-207, 5 pillars mapped; distinct ML-DSA-65 keys; manifest/authz/rate all assert. A2A-mTLS→Stage 18 honestly deferred. |
| AC1 | `contract.py` DSL per KB_17 | done | **YES** | Pydantic Precondition/Invariant/Postcondition/Action/SafetyContract/Decision; matches KB_17 §"Safety contract DSL". |
| AC2 | `validator.validate(action,world_state,contract)->Decision` | done | **YES** (live) | precondition+invariant gate → SIL routing; raising check = fail-safe (`test_check_exception_is_failsafe` PASS). |
| AC3 | `sil_bridge.py` PLC bridge placeholder | done | **YES** | Honest placeholder (`SIL_CONTROLLER` string says "integration point; cert=Stage 23"). Only `actuator.*` emitter besides VDA master. See F1. |
| AC4 | `sto_ss1.py` `trigger_sto`/`trigger_ss1` | done | **YES** (live) | SS1 decelerates → terminal STO; signed audit row persisted to live DB (`test_sto_writes_signed_audit_chain_row` PASS, not skipped). |
| AC5 | ≥5 named contracts with real checks | done | **YES** | All 5 present with genuine preconditions/invariants reading real world_state keys (battery/path/light-curtain/interlocks/zone). |
| AC6 | `sil_pl_map.py` SIL↔PL | done | **YES** (live) | `sil_to_pl(2)=="d"`, `pl_to_sil("e")==3`, ISO 10218-1:2025 class minimums (`test_sil_pl_mapping` PASS). |
| AC7 | `check-safety-trace-pairing.py` fails unpaired actuator span | done | **YES** (live) | Gate ran OK; negative controls assert (`test_unpaired_...`, `test_validate_before_actuator_ordering_enforced`). Real invariant. See F3. |
| AC8 | CI gate `safety-contract-tests` on every PR | done | **YES** | `ci.yml:327-345` runs `tests/safety/ tests/security/` + the trace-pairing gate. |
| AC9 | `pytest backend/tests/safety/ -v` green | done | **YES** (live) | 33 passed (safety+security combined). |
| AC10 | runtime separates planning from execution nodes; execution-only calls sil_bridge | done | **YES (with nuance)** | The runtime `execute` node routes through `validate()` (emits `safety.validate`); it is sim-only and does NOT call `sil_bridge` (no hardware) — honestly documented. The only `sil_bridge` callers are tests. |
| AC11 | Every STO/SS1 writes a signed `audit_chain` row | done | **YES** (live) | DB write verified; `verify_range` confirms hash-chain linkage on the new row. |

---

## Re-run evidence (commands actually executed)

```
$ cd backend && DATABASE_URL=...:5544/manufacturing OMP/MKL=1 python -m pytest tests/safety/ tests/security/ \
    -q --timeout=90 --timeout-method=thread -o asyncio_default_fixture_loop_scope=function
33 passed, 1 warning in 5.02s

$ python -m pytest tests/agents/runtime/test_canned_decision.py -q --timeout=90 ...
7 passed, 3 warnings in 7.89s

$ python -m pytest tests/safety/test_sto_ss1.py -v   (with DATABASE_URL)
test_trigger_sto_returns_triggered PASSED
test_trigger_ss1_decelerates_then_stos PASSED
test_sto_writes_signed_audit_chain_row PASSED        # NOT skipped — real signed row persisted to live DB

$ python scripts/check-safety-trace-pairing.py audits/STAGE_17_traces.json
OK: all 1 actuator span(s) preceded by safety.validate (3 spans checked).   # exit 0

$ bash scripts/audit.sh
TOTAL 364 / Baseline 364  (held — Stage 17 is additive new safety/security code, not a de-mock; Rule 1a)

$ grep -rE "random.uniform|random.choice|Math.random|generateMockState|_get_demo_|RESPONSES = {|MODELS = [" \
    backend/safety/ backend/security/ scripts/check-safety-trace-pairing.py
(no matches — no theatre in new code)
```

---

## Bypass-attempt result (the core safety property, Rule 3)

**Attempt 1 — forge an allowing Decision, skip the validator:**
```python
forged = Decision(allow=True, route="sil_bridge", reason="forged", contract="start_conveyor_segment", sil=2)
sil_bridge.execute(Action(contract="start_conveyor_segment", actuator="conveyor", target="S1"), forged)
# RESULT: executed=True  ← the forged Decision ACTUATED
```
The bridge accepted a hand-built `Decision` that never passed `validator.validate()`. See **F1**.

**Attempt 2 — feed the bridge a Decision the validator genuinely produced as blocked / mis-routed:**
The bridge **correctly refuses** (`SafetyBypassError`) — confirmed by `test_sil_bridge_refuses_blocked_or_misrouted_decision`
and re-derived. So the bridge defends against *validator-produced* bad decisions; it does **not** defend against
*forged* decisions.

**Live-path assessment:** there is **no production caller** of `sil_bridge.execute` in this build (runtime is sim-only;
the only real actuator path is `master.dispatch_order`, which is correctly gated by `validate_order` and is the only
other `actuator.*` emitter). So Attempt 1 is **not a live Rule-3 violation today** — it is a latent weakness in the
in-code "defence-in-depth / no bypass" claim that becomes load-bearing the moment `sil_bridge` is wired to a real PLC.

---

## Findings (severity-ranked)

### F1 — MEDIUM — `sil_bridge.execute` "re-checks" the Decision *shape*, not its *authenticity* or the *contract conditions* (overstated defence-in-depth)
`backend/safety/sil_bridge.py:32-36` gates only on `decision.allow` and `decision.route == "sil_bridge"` — both are
plain, caller-settable fields on the `Decision` pydantic model (`backend/safety/contract.py:57-65`). There is no
provenance binding (no signature/nonce/HMAC tying a `Decision` to a real `validator.validate()` run) and the bridge
does **not** re-evaluate the contract preconditions/invariants against `world_state`. Consequences:
1. **Forgery** — a caller that constructs `Decision(allow=True, route="sil_bridge", ...)` actuates without the validator
   (demonstrated above).
2. **TOCTOU/stale-decision** — even a genuine Decision is trusted later regardless of whether world_state changed since
   validation (e.g. light curtain broken after validate, before execute).

The KB_17 §"Last verified", `backend/safety/__init__.py:6`, the ADR D2, and the risk-register row all assert the bridge
"refuses any non-allowing / mis-routed Decision (defence-in-depth — even a caller that skipped the gate is rejected)".
That is **true only for validator-produced** decisions, not forged ones — the claim should be narrowed, or the bridge
hardened (re-run `validate()` from the contract+world_state inside `execute`, or sign the Decision).
**Why not FAIL:** no live caller reaches `execute` in this build; the only real actuator path (VDA master) is correctly
gated. This is a hardening gap on the API surface, not a live breach. **Ledgered → Stage 18 (when sil_bridge gets a
real caller / the PQC boundary lands).** New gap **G-075**.

### F2 — LOW — `validate_order` (VDA path) is structural-only; it does NOT run the SIL contract
`backend/integrations/vda5050/master.py:131-150` gates a dispatched order via `validate_order` (orderId/header/nodes/
released-first-node/connection-fresh) — a real anti-spoof structural gate that emits the required `safety.validate`
span. But it does **not** invoke the SIL `validate(action, world_state, contract)` path, so a VDA order is not checked
against `move_amr_to_charging_station` / `dispatch_amr_to_zone` preconditions (battery, path-clear, zone speed) before
publish. This is consistent with the documented Stage-16/17 split and the trace-pairing invariant still holds, but the
*contract-level* safety checks are not yet on the real VDA actuator path. Note for Stage 18+ (wire VDA orders to their
named SIL contracts). Not close-blocking; documented scope.

### F3 — LOW — trace-pairing gate enforces "*some* validate before", not "*immediately/matched* before"
`scripts/check-safety-trace-pairing.py:31` flags an actuator span only if **no** `safety.validate*` span started before
it (`any(vt <= t ...)`). KB_17 §"SIL routing" says "IMMEDIATELY before" and per-action. A trace with one early validate
followed by many unmatched actuator spans would pass. This is still a real, non-theatrical invariant (an actuator span
with zero preceding validates genuinely fails — negative tests prove it), but it is weaker than the prose claims. The
docs say "preceded by" elsewhere (accurate). Consider matching by trace/span context or contract attribute later.
Not close-blocking.

---

## Theatre / honesty audit

- **No theatre patterns** in `backend/safety/`, `backend/security/`, or the gate script (grep clean).
- **No Rule-1a dict-literal/synthetic fabrication.** Contracts read real `world_state` keys; the torque detector uses
  real median/MAD robust-Z (genuinely flags a 25.0 spike against a ~10.0 baseline, genuinely passes a stable window);
  per-agent identities are real distinct ML-DSA-65 keypairs from the KeyProvider (different `public_key_b64` confirmed);
  the signed manifest's signature genuinely breaks on tamper (real ML-DSA-65 verify, not a string compare).
- **Honest deferrals:** `sil_bridge` placeholder string is explicit; "no SIL certification" honored across KB_17/ADR/
  risk-register; A2A live mTLS → Stage 18 stated in zero_trust.py PILLARS (Network=PARTIAL, Device=Stage 18), ADR, KB_17,
  ledger. OPC UA "every write" / Sparkplug "every DCMD" task-doc MODIFY items are correctly *not* done because those
  write/DCMD surfaces don't exist yet (subscribe-only / no DCMD emitter) — honest scoping, consistent with code.
- **Research-first (Rule 11):** research §27 dated 2026-06-21 is substantive (27.1 functional safety, 27.2 ZT framework
  decision, 27.3 self-healing) and grounds the depth choices. Compliant.
- **Free/local (Rule 9):** no new deps; dilithium-py (software ML-DSA), robust-Z (stdlib), pyyaml BT. Compliant.
- **Baseline discipline:** held at 364 (additive safety/security code, not a de-mock) — legitimate under Rule 1a.
- **CI:** `safety-contract-tests` genuinely wired on every PR (`needs: [backend]`), runs the suite + the gate.

---

## New gaps (appended to OPEN_GAPS_LEDGER.md)

- **G-075 (MEDIUM → Stage 18):** `sil_bridge.execute` trusts a `Decision`'s `allow`/`route` fields without verifying
  the Decision's provenance (no signature/nonce) or re-checking the contract against current world_state — a forged or
  stale Decision would actuate. Harden before any real PLC caller (re-run `validate()` inside `execute`, or sign the
  Decision and verify in the bridge). Also narrow the "defence-in-depth even if the gate was skipped" claim in
  KB_17/ADR/risk-register to "refuses validator-produced non-allowing/mis-routed decisions" until hardened.

(F2 and F3 are LOW design notes folded into Stage 18+ scope; no separate ledger row required, but called out here.)

---

## Conclusion

Stage 17 is **PASS**. The functional-safety wrapper, STO/SS1 paths, self-healing loop, and agentic zero-trust controls
are real, tested, and honestly documented; the live actuator path is correctly gated and the CI invariant is genuine.
The single MEDIUM finding (F1/G-075) is a hardening gap on a not-yet-live API surface, correctly deferable to Stage 18,
with the only required immediate action being to **narrow the overstated "no-bypass / defence-in-depth" wording** so the
docs match what the code actually enforces today.
