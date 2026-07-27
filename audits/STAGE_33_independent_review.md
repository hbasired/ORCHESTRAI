# Stage 33 — Independent Review (Safety & runtime-oversight hardening / G-075)

- **Reviewer:** `task-auditor` (independent agent — did NOT implement Stage 33)
- **Date:** 2026-07-13
- **Scope:** CTO #6 C6-R1 (G-075 capability tokens), C6-R3 (behavioural-monitor runtime hook), C6-R4 (risk-register
  refresh + wording narrowing); the `conversation/evidence.py` honest-empty fix.
- **Method:** read every changed file; re-ran the safety + runtime suites; **wrote my OWN adversarial bypass harness
  (17 attack/control cases) and tried hard to make a forged Decision actuate**; re-ran audit + audit-chain verify;
  smoke-tested the monitor path.

## TOP-LINE VERDICT: **PASS**

The central safety claim holds under adversarial testing: **a forged `Decision(allow=True, route="sil_bridge")` can no
longer actuate via `sil_bridge.execute`.** I could not bypass the capability-token / re-validation gate through any of
15 distinct forgery, replay, action-swap, field-mutation, or key-forgery attacks. No theatre, no bypass, no overclaim.
Audit holds at 3; chain verifies exit 0. No close-blocking gaps.

---

## Adversarial bypass harness (my own — I wrote and ran this, NOT the stage's tests)

Full script: `scratchpad/bypass_attack.py`. It exercises `safety.validator.validate` → `safety.sil_bridge.execute`
directly. A case PASSES iff a bypass is BLOCKED (`SafetyBypassError`); the two CONTROLs must actuate. Real output:

```
=== SECRET PROVENANCE ===
len(_SECRET) = 32 (expect 32)
_SECRET is bytes from os.urandom, per-process module global.
mint uses hmac: True | random module used: False

=== RESULTS ===
[PASS] CONTROL: genuine validate->execute actuates            executed=True
[PASS] ATTACK1: forged allow=True, no token/contract          blocked (missing capability token)
[PASS] ATTACK2: token for A redeemed for B (action-hash bind) blocked (invalid — different action)
[PASS] ATTACK2b: token reused on same actuator, mutated params blocked (invalid — action hash differs)
[PASS] ATTACK3a: stale token (freshness=0)                    blocked (stale token)
[PASS] ATTACK3b: replay after freshness window elapses (TOCTOU) blocked (stale token)
[PASS] ATTACK3c: future-date issued_at to evade staleness     blocked (token issued in the future)
[PASS] ATTACK4: tampered token (flip a byte)                  blocked (invalid capability token)
[PASS] ATTACK5a: valid token, mutate decision.sil             blocked (invalid — bound field differs)
[PASS] ATTACK5b: sil0 direct token, route flipped to sil_bridge blocked (invalid — bound field differs)
[PASS] ATTACK5c: valid token, mutate decision.contract        blocked (invalid — bound field differs)
[PASS] ATTACK6a: fabricated all-zero token+nonce (no secret)  blocked (invalid capability token)
[PASS] ATTACK6b: HMAC computed with attacker key              blocked (invalid capability token)
[PASS] ATTACK7a: re-validate ignores forged verdict, unsafe->block blocked (ALLOWING Decision required)
[PASS] CONTROL: re-validate safe live state actuates          executed=True
[PASS] ATTACK8: sil1 operator_confirm decision at sil_bridge  blocked (route != sil_bridge)
[PASS] ATTACK9: blocked (allow=False) decision                blocked (ALLOWING Decision required)

17/17 attacks handled correctly.
BYPASSED/FAILED: NONE — G-075 holds.
```

### What each attack proves
- **ATTACK1** — the core G-075 hole: a hand-forged `Decision(allow=True, route="sil_bridge")` with **no token and no
  contract** is rejected (`sil_bridge.py:54-65`). The old blind trust of `decision.allow`/`route` is gone.
- **ATTACK2 / 2b** — the HMAC covers `action_hash = sha256(canonical(action))`, so a token minted for action A (or the
  same actuator with mutated params) cannot redeem a different action. Action-hash binding is real and load-bearing.
- **ATTACK3a/3b/3c** — freshness is enforced both directions: past the window (`age > freshness_s`) AND future-dated
  (`age < -1.0`). Replay / TOCTOU of a stale-but-genuine Decision is blocked; forging `issued_at` into the future does
  not help (the HMAC also covers `issued_at`, and future-skew is caught first).
- **ATTACK4** — a single flipped byte fails `hmac.compare_digest` (constant-time).
- **ATTACK5a/5b/5c** — the HMAC covers `{allow, route, contract, sil, action_hash, nonce, issued_at}`, so copying a
  valid token onto a Decision with **any** mutated bound field (escalate `sil`, flip `route` direct→sil_bridge, swap
  `contract`) fails verification. There is no field-substitution escape.
- **ATTACK6a/6b** — I confirmed `_SECRET = os.urandom(32)` (32 bytes, per-process module global, `hmac` not `random`).
  A fabricated token and an HMAC computed with an attacker-chosen key both fail. The key is not derivable across the
  trust boundary; you cannot forge a valid token without the in-process secret.
- **ATTACK7a + CONTROL** — the authoritative re-validation path (`contract`+`world_state` given) **ignores the passed
  verdict** and re-runs `validate()` against live state: blocks when unsafe, actuates when safe. Forgery- and
  TOCTOU-proof independent of the token.
- **ATTACK8/9** — mis-routed (SIL-1 `operator_confirm`) and blocked (`allow=False`) decisions are rejected *before* the
  token check, so the pre-existing SIL gate is intact.

---

## Claim-by-claim evidence table

| # | Acceptance criterion | Claimed | Independently confirmed? | Evidence |
|---|---|---|---|---|
| AC1 | G-075: forged Decision can no longer actuate | closed via mint/redeem + re-validate | **YES** | my 15/15 bypass attempts all blocked; `test_capability_token.py` 7/7 pass |
| AC2 | No regression to the safety gate | full `tests/safety/` (33) pass; blocked/mis-routed still rejected | **YES** | `pytest tests/safety/` → **33 passed**; ATTACK8/9 blocked |
| AC3 | Continuous behavioural oversight, gated/off-hot-path/honest-degrading; determinism holds off | `RUNTIME_BEHAVIOR_MONITOR=1`, additive after graph, try/except | **YES** | `graph.py:111-117` gated + wrapped, appends after `result`; `features_from_run` yields real features + `insufficient_history:True` below warmup; runtime suite **13 passed/1 skip** (monitor off by default; determinism test present, does not set the flag) |
| AC4 | Risk register refreshed + G-075 CLOSED + wording narrowed | Stage 29–33 rows, defence-in-depth narrowed | **YES** | `risk-register.md:178-193` (G-075 "high → CLOSED"), ledger G-075 `RESOLVED 2026-07-13`; `safety/__init__.py:6-9` + `sil_bridge` docstring now say "actuates ONLY via a forgery/TOCTOU-resistant path… no longer trusts caller-set allow/route" + "defence-in-depth; binding gate remains safety.validator" — accurate, not overstated |
| AC5 | Free-cost, no new deps, audit holds 3, Stage-29 honest-empty bug fixed | stdlib hmac; audit 3 | **YES** | `capability_token.py` imports only `hashlib/hmac/json/os/time`; `bash scripts/audit.sh` → **3**; `evidence.py:52-60,134-144` off-topic → `_incident_token`=None → no grounding; `read_recent(...target_substr=)` signature valid |
| AC6 | Research §44 first + explainer + independent review PASS | present | **YES (this doc)** | ADR + task doc reference research §44; explainer path seeded; this review = PASS |

---

## Re-run log (commands I actually executed)

- `pytest tests/safety/ -q` → **33 passed** (incl. 7 capability-token tests)
- `pytest tests/agents/runtime/ -q` → **13 passed, 1 skipped** (no regression; determinism holds with monitor off)
- `python scratchpad/bypass_attack.py` → **17/17 handled; 0 bypassed** (output above)
- `bash scripts/audit.sh` → baseline **3**, count **3** (holds; `--no-baseline-drop` legitimate — additive safety
  hardening, zero new fakery pattern; `capability_token` uses `hmac`/`os.urandom`, no `random.*`)
- `python scripts/verify-audit-chain.py` → **exit 0**: `Audit chain OK (10477 rows; hash chain intact; all 10398
  post-cutover signatures verify)` (row count grew vs ADR's 10,469 because my genuine-actuation controls + safety tests
  wrote new signed rows — chain still intact)
- Monitor smoke: `features_from_run` → real features; `observe` → `{'anomalous':False, ..., 'insufficient_history':True}`
  (honest degradation below warmup, not fabricated)

## Honesty / theatre check
- **No theatre.** The token is real HMAC-SHA-256 over a canonical payload; `random.*`/`Math.random`/mock patterns absent
  from the new code. `sil_bridge` remains the sole `actuator.*` emitter; Hard Rule 3 intact.
- **No overclaim.** The docs state the token is defence-in-depth and the binding gate remains `safety.validator` — which
  matches the code (re-validation path ignores the token entirely; ATTACK7a confirms). This is the exact wording the
  G-075 ledger row asked to narrow.
- **Latent Stage-29 bug genuinely fixed.** `conversation/evidence.py` no longer grounds an off-topic question on arbitrary
  recent traces (`_incident_token` gate). The `read_recent(target_substr=...)` call is against a real signature — not a
  latent crash.

## Observations (all NON-blocking — honestly disclosed by the implementer, not gaps)
1. **In-process threat is out of scope by design.** A caller already executing in-process could import
   `capability_token.mint` or read `_SECRET`. This is a strictly higher-privilege threat than passing a forged Decision
   dict across a boundary (the actual G-075 threat), and it is acknowledged verbatim in the module docstring + task-doc
   Risks ("a same-process caller could in principle read the key, but that is a far higher bar than forging a dict; the
   re-validation path does not depend on the token at all"). Correctly scoped; the authoritative re-validation path is
   the real backstop. **Not a gap.**
2. **No real production `sil_bridge` caller yet** — the live actuator path is `master.dispatch_order`→`validate_order`.
   The hardening is defence-in-depth readied for the first SIL≥2 PLC caller, done as code NOW per CTO #6 (not deferred).
   Honestly disclosed. **Not a gap.**
3. **Tokens are per-process / non-persistent** — correct for single-actuation, sub-second-lived tokens; re-validation
   doesn't depend on them. **Not a gap.**

## Bottom line
**PASS.** G-075 — the longest-lived open safety item — is genuinely closed. I attacked the capability token from 15
angles (no-token forgery, action swap, param mutation, staleness both directions, byte tamper, four bound-field
mutations, two key-forgery attempts) and every one was rejected; the two legitimate paths (genuine round-trip + live
re-validation) actuate. Behavioural-monitor hook (C6-R3) is gated/off-hot-path/honest-degrading with determinism held;
risk register + wording (C6-R4) are refreshed and now accurate; the evidence.py honest-empty fix is real. No new deps,
audit 3, chain exit 0. **Cleared to close.**
