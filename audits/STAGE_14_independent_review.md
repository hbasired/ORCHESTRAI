# Stage 14 — Independent Review (A2A external federation boundary)

**Reviewer**: `task-auditor` (independent — did NOT implement Stage 14).
**Date**: 2026-06-20
**Stage**: 14 — A2A protocol surface (signed agent cards + JSON-RPC 2.0 federation).
**Verification**: **DYNAMIC** (re-ran the A2A suite, the mechanical audit, the operator-prescribed probe, AND four
extra adversarial crypto probes — all live in this session). The crypto layer is infra-free, so the full logic was
verified without Docker; the two-instance Docker federation + DB-migration apply remain honestly Docker-gated (G-069).

---

## VERDICT: **PASS**

Stage 14 is real, deep, and honest. Agent cards are genuinely signed and verified with FIPS-204 ML-DSA-65 over
JCS-canonicalised bytes via the Stage-13.5 KeyProvider; `verify_card` enforces revocation → pinned-roots → expiry →
signature with any failure → `False` (no partial trust, no always-true path). The KB_16 trust asymmetry is the key
security property and it is **enforced and independently confirmed**: the JSON-RPC dispatch serves ONLY
`a2a.skills.SKILLS` and refuses real MCP tool names (`predict_failure`, `run_inference`, `query_kpi`) with `-32601`.
Tests are honest (two genuinely distinct keypairs; real `TestClient`; Docker path correctly `skipif`). Deferrals
(hybrid ML-KEM TLS → Stage 18; a2a-sdk → G-070; two-instance Docker → G-069) are accurately stated and ledgered.
No theatre, no overclaim that I could find. Two LOW findings (doc drift in KB_16, a ledger-reference overload) and
one informational note — none block close.

---

## Per-criterion evidence (task doc `tasks/STAGE_14_a2a_protocol.md`)

| # | Acceptance criterion | Claimed | Independently confirmed? | Note |
|---|---|---|---|---|
| 1 | `server.py` mounts `/.well-known/agent.json` (signed card) + `/a2a/v1/rpc` (JSON-RPC) | yes | **YES** | `server.py:42` GET card, `server.py:55` POST rpc. Live `TestClient` served a card that `verify_card`→True. |
| 2 | `agent_card.py` Pydantic model; `sign_card`/`verify_card` work end-to-end | yes | **YES** | `agent_card.py:19-74`. Operator probe → `verify True / tamper False`. |
| 3 | `transport_tls.py` configures the oqs-provider hybrid-mTLS sidecar | yes (scaffold) | **YES — honestly deferred** | `transport_tls.py:38` `status()['live_pqc_tls']=False`; config-only, Stage-18 live (KB_13). Not overclaimed. |
| 4 | `revocation.py` polls a configurable URL on a 5-min cycle | yes | **YES** | `revocation.py:17` `poll_seconds=300.0`; fail-safe merge (`load_once` never clears on error, :47); bounded-thread `stop()` :65. |
| 5 | `docker-compose.a2a.yml` runs two instances for federation | yes (Docker-gated) | **PARTIAL — honest** | overlay present (distinct `KEY_STORE_DIR` per peer); host Docker down → G-069. In-process two-identity proof runs instead. |
| 6 | `test_federation.py` — exchange cards, verify, invoke capability, revoke, re-verify | yes | **YES** | `test_federation.py:26-43` two distinct keystores → exchange → verify → revoke → A still trusted. Ran: pass. |
| 7 | CI gate `a2a-conformance` on every PR | yes | **YES** | `ci.yml:231` job installs deps + `pytest tests/a2a/ -q`; `needs:[backend]`. |
| 8 | Alembic peer + agent-card storage | yes (`0007`, not `0004`) | **YES** | `0007_a2a_peers.py` `down_revision="0006_cdc_outbox"` (:19-20); chain 0007→0006→0005 verified. Rename rationale documented in the migration header + ADR. |
| 9 | KB_16 agent-card schema matches code | yes | **YES (with LOW drift)** | KB_16:91-103 field names match `agent_card.py:19-32`. Drift: KB_16:106 still says `sign_card(card, key)` / `verify_card(card_json)` — code is `sign_card(card)` / `verify_card(card,...)`. See F-1. |

---

## Adversarial verification (commands I actually ran this session)

```
# 1) A2A suite
cd backend && python -m pytest tests/a2a/ -q   →  9 passed, 1 skipped  (skip = Docker two-instance, gated by A2A_DOCKER_FEDERATION)

# 2) Mechanical audit
bash scripts/audit.sh   →  TOTAL 364, Baseline 364  (held — Rule-1a audit-invisible: real crypto adds no grep-counted theatre)

# 3) Operator probe (sign/verify/tamper)
verify True
tamper False

# 4) Live trust-boundary + honest-unavailable (fresh TestClient, real MCP tool names)
served_card_verifies True   caps ['forecast_oee']
predict_failure  -32601
run_inference    -32601
query_kpi        -32601
forecast_oee ok  (no world, no snapshot) → {'available': False, 'reason': 'no live SimWorld bound; supply `state` or run the app'}

# 5) Extra crypto adversarial probes
distinct_keys                True    # two keystores → genuinely different ML-DSA-65 public keys
a_not_pinned_under_b         False   # valid signature but key not in pinned_roots → refused
revoked_valid_card_refused   False   # revocation overrides an otherwise-valid card (revocation checked before sig)
cross_key_forge              False   # A's signature presented under B's public key → rejected (no sig confusion)
```

### Finding-by-finding against the prompt's 6 verification targets

**1. Real crypto, not theatre (Rule 1/1a) — CONFIRMED.**
`sign_card` (`agent_card.py:41-46`) sets `public_key_b64` from `pqc_signing.public_key()` and signs
`signing_payload()` = `jcs.canonicalize(card minus signature_b64)` (`:34-38`). `pqc_signing` → `SoftwareKeyProvider`
→ real `dilithium_py.ml_dsa.ML_DSA_65` (`software_provider.py:29-31,80-92`, FIPS-204 sizes documented). `verify_card`
(`:49-71`) checks, in order: missing key/sig → False; `is_revoked` → False; `pinned_roots` membership → False;
expiry → False; then `pqc_signing.verify`. The `except Exception: return False` (:70) is correct honest behaviour
(malformed card = untrusted, not a crash) — NOT an always-true shortcut. The cross-key-forge probe proves the
signature is bound to the embedded key. **No fabricated/always-true verification anywhere in `backend/a2a/`** (grep
for `random.|Math.random|return True|_get_demo|RESPONSES|MODELS|mock|TODO` → no matches).

**2. The trust boundary (KB_16) — CONFIRMED, this is the load-bearing security property.**
`server.py:75-79`: `handler = SKILLS.get(method)`; if `None` → `-32601` "not an A2A-exposed capability". `SKILLS`
(`skills/__init__.py:13-15`) is exactly `{"forecast_oee": ...}`. I verified three *real* MCP tool names
(`predict_failure`, `run_inference`, `query_kpi` — all present in `backend/mcp_servers/`) are refused with `-32601`.
External peers **genuinely cannot** reach the MCP tools through A2A — there is no code path from `/a2a/v1/rpc` to the
MCP surface. The `forecast_oee` capability itself is honest: real OEE = A×P×Q from the SimWorld snapshot
(`skills/forecast_oee.py:13-33`, ideal cycle time from `simulation.calibration.STAGES`), and returns
`{available: False, reason: ...}` when no world is bound — never a fabricated number. `get_sim_world()` exists
(`api/simulation_routes.py:56`), so the live path is real, not a dead import.

**3. Tests real, not theatre — CONFIRMED.**
`test_federation.py:15-43` signs two cards under two separate `KEY_STORE_DIR`s with a provider reset between them and
asserts `card_a.public_key_b64 != card_b.public_key_b64` (:30) — genuinely distinct identities, confirmed by my probe.
The JSON-RPC test (`:63-75`) uses a real `TestClient`, asserts `forecast_oee` returns a real OEE in `[0,1]` AND that
`predict_failure` → `-32601`. The Docker two-instance test (`:83-89`) is correctly `@pytest.mark.skipif(not
A2A_DOCKER_FEDERATION)` — an honest skip, not a silently-passing stub. `test_agent_card.py` covers
sign/verify/tamper/expiry/revoke/pinned-roots, each asserting the real boolean outcome.

**4. Honest deferrals — CONFIRMED.**
- Hybrid ML-KEM TLS is **not** claimed running: `transport_tls.status()['live_pqc_tls'] = False` (`transport_tls.py:41`);
  module docstring + `docker-compose.pqc.yml:1-4` both say "scaffold, live at Stage 18". Accurate.
- Hand-roll-vs-a2a-sdk: `requirements.txt:17` pins `httpx==0.27.2`; `a2a-sdk` is absent; `jcs==0.2.1` already present
  (`requirements.txt:87`). The ADR's "a2a-sdk 1.1.0 needs httpx>=0.28.1, conflicts with our pin" → no new deps is
  accurate. **No new dependencies were added** — confirmed.
- **G-070** (a2a-sdk adoption deferred) and **G-069** (Docker-gated paths owed) are both in `OPEN_GAPS_LEDGER.md`
  (lines 94, 95). Correctly ledgered.

**5. Migration chain + mount — CONFIRMED.**
`0007_a2a_peers` `revision="0007_a2a_peers"`, `down_revision="0006_cdc_outbox"` (:18-19); `0006`'s `down_revision`
is `0005_mem0`. Clean linear chain. Table has a CHECK constraint on `state IN (active,quarantine,revoked)` matching
`PeerState`. `main.py:395-396` imports and includes `a2a.server.router`; `main.py` imports cleanly with routes mounted
(verified live via the TestClient app, which uses the same router).

**6. Overclaims — none material found.** The ADR's "Verified … 9 A2A tests pass / 1 skipped … audit holds 364" is
exactly reproduced. The ADR explicitly labels the live PQC TLS, the Docker federation, and the live mTLS→peer_state
binding as deferred — no capability is claimed that the code does not deliver.

---

## Findings (severity-ranked)

### F-1 (LOW) — KB_16 signature description drifts from the implemented signatures
`KB_16_A2A_MCP_Protocols.md:106` states `sign_card(card, key)` and `:108` `verify_card(card_json) -> bool ... against
the pinned root key set in docker/secrets/a2a_roots/`. The implemented signatures are `sign_card(card)` (the key comes
from the KeyProvider/`agent-identity` alias, not a passed arg) and `verify_card(card, *, pinned_roots=None,
is_revoked=None, now=None)` (pinned roots are passed in by the caller, not auto-read from the secrets dir). The
*schema* block (KB_16:91-103) matches the code; only the prose call-signatures are stale. Cosmetic, non-blocking —
fix the two prose lines for accuracy. (Not a code defect.)

### F-2 (LOW / housekeeping) — G-069 reference is overloaded across two stages
`OPEN_GAPS_LEDGER.md:95` defines **G-069** as the *Stage-13.5* Docker-gated owed work (`audit_chain` row round-trip +
full live suite). The Stage-14 ADR (`2026-06-15_stage14_a2a_protocol.md:43,65`) and `test_federation.py:83` reuse
"G-069" to mean the *Stage-14* two-instance Docker federation run. Both are legitimately "owed when Docker is up," and
the ledger row's `next_step` doesn't yet mention the A2A two-instance run. Recommend either (a) append the A2A
two-instance federation run to the G-069 row's scope/next-step, or (b) open a distinct ledger ID for it, so the
Docker-up follow-up doesn't lose the A2A item. Non-blocking; tracking hygiene only.

### F-3 (INFO) — peer-identity gate is header-based and advisory until Stage 18
`server.py:67-73` gates calls on an `X-A2A-Peer-Key` header against `PeerRegistry`, but only when the header is present
(`if peer_key:`) — an unauthenticated caller without the header is not blocked at this layer. This is **correctly
scoped and stated**: the ADR (:66) and `server.py:6-7` say real peer identity binds at the Stage-18 mTLS sidecar
(client cert → peer_state), and the JSON-RPC surface only ever exposes capabilities (never tools) regardless. So this
is not a trust-boundary hole for the MCP surface — it is an interim, honestly-documented gate. Noted so the Stage-18
implementer wires the mTLS client-cert → `peer_state` binding (already tracked in the ADR's residuals). No new ledger
entry needed beyond the existing Stage-18 scope.

---

## Theatre / bypass scan
- `random.|Math.random|return True|_get_demo|RESPONSES = {|MODELS = [|mock|TODO|FIXME` over `backend/a2a/` → **no matches**.
- No `--no-verify`, no `--force`, no `--no-baseline-drop` (baseline held legitimately under Rule 1a — additive real crypto).
- The `except Exception: return False` blocks (`agent_card.py:70`, `server.py:60,85`, `software_provider.py:91`,
  `revocation.py:47`) are all honest fail-closed / fail-safe behaviour, not swallowed theatre. Verified each leads to a
  rejection / honest-empty / no-op, never a fabricated positive.

## New gaps for the ledger
None required. F-1/F-2 are doc/tracking hygiene fixable in-place; F-3 is already covered by the existing Stage-18 scope
in the ADR. (If the implementer prefers, F-2 can be discharged by editing the G-069 row's scope — but that is the
fixer's call, not an auditor edit.)

## Gaps that must be fixed before close
**None.** All eight acceptance criteria are independently confirmed with real evidence; the trust boundary — the
security property that makes federation safe — is enforced and adversarially verified; deferrals are honest and
ledgered. Verdict stands at **PASS**. (Recommend F-1 be fixed opportunistically for doc accuracy; not close-blocking.)
