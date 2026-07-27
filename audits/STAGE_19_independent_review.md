# Stage 19 — Independent Review (Governance Evidence Pipeline + 4 CTO #3 remediations)

**Auditor:** independent `task-auditor` (did NOT implement Stage 19)
**Date:** 2026-06-21
**Verification mode:** **DYNAMIC** — infra UP (PG :5544, Neo4j :7687, Mosquitto, Ollama). All commands re-run live with
`DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing`, `MEM0_EMBED_DIM=384`,
`MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5`, `HF_HUB_DISABLE_TELEMETRY=1`.

## VERDICT: **PASS-WITH-GAPS**

The four CTO #3 remediations and the Annex IV pack are **real, deep, and honest** — no theatre, no overclaim, no
classical crypto, no bypassed gate. Every claimed capability was independently reproduced live. **One operational gap
blocks a clean close:** the live `audit_chain` does **not currently verify** (2 dev-test-key-polluted rows make
`verify-audit-chain.py` exit 1) — this is the *documented* test-isolation artifact and is fixable by re-running
`scripts/back-sign-legacy-rows.py --confirm`, but it must be done (and the ADR's stale "Audit chain OK (224 rows)"
snapshot reconciled) before `close-task.sh`. Two lower-severity residuals are noted.

---

## Per-criterion evidence

| Acceptance criterion | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| G-073: verify-audit-chain.py LOAD-BEARING (exit 1 on non-verifying post-cutover row) | yes | **YES (dynamic)** | Live run exits **1** on seq 225 (full + `--quick`); not `try/except:pass`. Tamper test (read-only) confirms hash-mismatch detection. Cutover reported explicitly. |
| G-073: cutover honest (placeholders ≠ "all PQ-signed") | yes | **YES** | Prints `placeholder->ML-DSA-65 cutover at seq 80`; pack §8 reports `v0×79, v1×156`. |
| G-073: back-sign-legacy-rows.py honest (re-attests hashes, no fabrication) | yes | **YES** | `--dry-run` reports exactly the 2 non-verifying rows; re-signs unchanged `hash`, refuses prod, requires `--confirm`. |
| G-074: a2a.rpc.<method> span + audit_chain row per call | yes | **YES** | `a2a/server.py:84-92` span + `_audit_a2a` (95-107). Live DB has the real row at seq 225 (`a2a.capability.forecast_oee`, 3309-byte ML-DSA sig). |
| G-074: ml.inference.* spans on world_model/diagnose/explain/decide | yes | **YES** | `nodes.py:142,163,187,209` (+ existing failure_predictor:126); runtime tests 16 pass. |
| G-074: cdc.ingest span | yes | **YES** | `cdc_listener.py:170`. |
| mem0 RLS DB-enforced + fail-closed | yes | **YES (dynamic, key claim)** | See "RLS verification" below — fail-closed proven by direct SQL as `mem0_app`. |
| Python `_authorize` still first gate | yes | **YES** | `mem0_adapter.py:117-126`; `test_python_authorize_still_first_gate` passes. |
| Annex IV pack: 14 sections, real PDF+HTML, ML-DSA-65 footer | yes | **YES** | Generator exits 0; 14 `<h2>` sections; PDF magic `%PDF-`; footer sig **verifies** (alg ML-DSA-65, key v1). |
| Output to dated + latest.{pdf,html} | yes | **YES** | `2026-06-21_annex_iv.{pdf,html}` + `latest.{pdf,html}` written. |
| ai-policy.md authored (ISO 42001 A.6.1) | yes | **YES** | Present; honesty boundary explicit (no certification claim). |
| KB_18 controls marked `shipped` | yes | **YES** | 9 `shipped` markers. |
| CI gate `annex-iv-pack-builds` | yes | **YES** | `ci.yml:429-451`, BLOCKING, `needs:[backend]`, builds pack + runs compliance tests. |
| No conformity overclaim (ADR/KB/policy/pack) | yes | **YES** | "NOT a conformity certificate", "conformity-assessment-ready", "notified body" in pack + ai-policy §3 + ADR D5. |
| Migration 0008 chain correct (after 0007) | yes | **YES** | `0008 → 0007 → 0006`; `alembic_version = 0008_mem0_rls` applied in live DB. |
| Audit holds 364, no CLASSICAL violation | yes | **YES** | `audit.sh` TOTAL 364; no `RSA-`/`ECDSA-` in new files. |

## Test re-runs (all live)

- `pytest tests/a2a/ -q` → **9 passed, 1 skipped** (Docker two-instance gated).
- `pytest tests/compliance/ -q` → **4 passed**.
- `pytest tests/memory/test_mem0_rls.py -q` → **3 passed**.
- `pytest tests/ -k "runtime or nodes" -q` → **16 passed**.
- `scripts/generate-annex-iv-doc.py` → exit 0, signed PDF+HTML, 14 sections.
- `scripts/audit.sh` → TOTAL **364** (= baseline; governance-only stage, `--no-baseline-drop` per task doc).

## RLS verification (the key security claim) — DYNAMIC, INDEPENDENT

Connected directly to PG (not via the test), inserted a known row via the adapter, then probed as `mem0_app`:

```
RLS enabled, FORCE: (True, True)
policy: mem0_namespace_isolation  USING (namespace = current_setting('app.mem0_namespace', true) OR ... = '*ALL*')
roles: aiagent(super=True, bypassrls=True)   mem0_app(super=False, bypassrls=False)
after SET ROLE mem0_app: current_user=mem0_app, bypassrls=False
(a) unset app.mem0_namespace  -> 0 rows   (fail-closed) ✓
    total visible (unset)     -> 0 rows                 ✓
(b) wrong namespace           -> 0 rows                 ✓
(c) correct namespace         -> 1 row                  ✓
```

I also confirmed the **load-bearing dependency**: the app DB user `aiagent` is a **superuser (bypassrls=True)**, so
**without** `SET ROLE mem0_app` it sees all 66 rows — RLS is enforced ONLY because `_connect_ns` drops to the
non-superuser role (`mem0_adapter.py:96`). This is honestly documented in the migration docstring + ADR D3. Verdict:
**RLS is genuinely fail-closed at the DB layer behind the Python `_authorize` first gate** — a real defense-in-depth.

---

## Findings (severity-ranked)

### [BLOCKER-for-close / LOW design] F1 — live audit_chain does not currently verify (2 polluted rows)
`scripts/verify-audit-chain.py` (full + `--quick`) **exits 1** on the live DB:
```
hash-chain: 234 rows; placeholder: 79; ML-DSA-65-verified: 154
placeholder->ML-DSA-65 cutover at seq 80
AUDIT CHAIN BROKEN: seq=225: ML-DSA-65 signature INVALID (key v1)
```
Independent per-row check: only **seq 225** (and seq 235, an annex-iv generator row created during *this* audit) fail.
seq 225 is the **G-074 audit row** (`a2a.capability.forecast_oee`) — written by a *later* test run under an ephemeral
test-isolation keystore, the exact pollution class the implementer already documented and re-attested for the earlier
batch. The hash chain is intact (tamper-evidence preserved); only the signature is unverifiable under the current key.
**This is the load-bearing verify working as designed** (it correctly refuses to pass a non-verifying row) — but it
means the chain is not in a closeable "Audit chain OK" state right now. **Fix before close:** re-run
`DATABASE_URL=... python scripts/back-sign-legacy-rows.py --confirm` (dry-run confirms it would re-attest seqs
[225, 235]), then re-run verify to exit 0. NOT a code defect; an operational re-baseline owed.

### [LOW — overclaim/staleness] F2 — ADR "verified live" snapshot is stale vs. the live DB
ADR D1/Consequences claims `verify-audit-chain → "Audit chain OK (224 rows; cutover seq 80; 145 post-cutover sigs
verify)"`. The live DB now has **235 rows**, cutover seq 80, and **does not verify** (F1). The G-073 ledger row says
"caught 94 dev rows … chain now verifies … 79 placeholders + 145 ML-DSA-verified, exit 0." Neither number matches the
current live state (79 placeholders + 156 v1, 2 non-verifying). The framing of *why* (test-key pollution, not hiding
tampering) is honest, but the specific "verifies, exit 0" assertion is no longer true and should be reconciled when F1
is fixed (Rule 1a: verify, don't assert). Recommend updating the ADR Consequences line to the post-re-attestation
numbers at close.

### [LOW — residual, documented] F3 — RLS strength is gated on `SET ROLE` because the app user is a superuser
Because `aiagent` is a superuser with `bypassrls`, the entire DB-layer isolation depends on the adapter's best-effort
`SET ROLE mem0_app` (`mem0_adapter.py:95-98`, wrapped in `try/except` → silent no-op if the role is absent). This is
honestly documented (migration docstring; ADR D3) and the Python `_authorize` remains the first gate, so it is
acceptable today. A stronger posture (a non-superuser app role by default, or a connection that cannot regain
superuser) is a hardening item for the multi-tenant stage. **Ledger as a forward gap.**

### [INFO] F4 — A2A audit/span emission is not directly asserted by a test
G-074's `a2a.rpc.<method>` span + `audit_chain` row are real (confirmed by the live row at seq 225), but
`tests/a2a/test_federation.py` asserts only the capability boundary, not that a span/audit row is emitted per call. The
evidence is live-verifiable but not regression-guarded by a unit test. Minor — consider a test asserting an audit row
is appended per A2A call.

## No theatre / no bypass
- Grep of new code for `random.uniform|random.choice|Math.random|generateMockState|_get_demo_*|RESPONSES = {|MODELS = [`:
  none. No `RSA-`/`ECDSA-` in new files. `audit.sh` mock_detections = 0.
- No `--no-verify`/`--force`. `--no-baseline-drop` is legitimate (governance-only stage, per task doc Audit target).
- Honest-unavailable paths confirmed: generator footer falls to "(conformity signature unavailable: …)" if signer
  missing; `_authorize` raises `CrossNamespaceAccessError`; verify distinguishes crypto-UNAVAILABLE from verify-FAILURE
  (the precise G-073 fix).

## New ledger gaps
- **F3 → `audits/OPEN_GAPS_LEDGER.md`** (RLS depends on `SET ROLE`; app DB user is superuser) — target a multi-tenant
  hardening stage.

## Required before `close-task.sh`
1. **F1** — re-attest seqs 225/235 (`back-sign-legacy-rows.py --confirm`) so `verify-audit-chain.py` exits 0;
   re-run the live suite if any new rows were written.
2. **F2** — reconcile the ADR Consequences / G-073 ledger "verifies, exit 0 / 224 rows" numbers with the
   post-re-attestation live state.
3. **F3** — append to the open-gaps ledger (forward hardening).
