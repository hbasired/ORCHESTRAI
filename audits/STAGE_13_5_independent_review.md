# Stage 13.5 — Independent Review (PQC Foundations: real ML-DSA-65 + the KeyProvider boundary)

**Reviewer:** independent `task-auditor` persona — a DIFFERENT agent than the Stage-13.5 implementer.
**Date:** 2026-06-19
**Verdict:** **PASS** (with one residual already ledgered as G-069; two task-doc file artefacts honestly deferred to Stage 22 with ADR justification — not gaps).
**Verification mode:** **DYNAMIC** — the crypto layer is infra-free, so every claim below was re-run live on this host (pytest, `scripts/audit.sh`, direct `python -c` probes, ADR-footer signature verification). The ONE DB-gated test (`test_audit_chain_row_is_mldsa_signed_end_to_end`) is `skipif no DATABASE_URL`; Docker Desktop is down on this host, so that single round-trip was NOT exercised (G-069, pre-existing, accurate).

---

## What I ran (commands + observed output)

| Command | Result |
|---|---|
| `cd backend && python -m pytest tests/crypto/ -q` | **8 passed, 1 skipped** (the skip is the DB round-trip, correct without `DATABASE_URL`) |
| `python -c "from crypto import pqc_signing; s=pqc_signing.sign(b'x'); print(len(s), pqc_signing.verify(...))"` | **`3309 True`** |
| `bash scripts/audit.sh` | **TOTAL 364**, baseline 364 — holds (correct: real crypto is Rule-1a audit-invisible, adds no grep theatre) |
| sizes probe (`sig`/`pub`/`sk`) | **sig 3309, pub 1952, sk 4032** — exact FIPS-204 ML-DSA-65 parameter sizes |
| tamper probe | flipped-byte sig → **False**; wrong message → **False** |
| `memory.audit_chain._sign(b'\x11'*32)` | **`('ML-DSA-65', 1, 3309)`** — real, NOT `placeholder-sha256`/`key_version=0` |
| dilithium-py asymmetry probe | two keygens differ; correct-key verify True; **cross-key verify False** (real asymmetric FIPS-204, not a stub) |
| rotation drill (clean tmp keystore) | v1→v2; **old v1 sig still verifies**; v2 sig verifies under v2 pub; **v2 sig under v1 pub False**; `get_public_key_by_version(v1)` matches retained pub |
| `bash scripts/rotate-pqc-keys.sh --dry-run --key-type identity` | dry-run prints the planned `key_manager rotate` invocation, exit 0 |
| ADR footer signature verify | the `2026-06-15_stage13_5_pqc_foundations.md` footer (`ML-DSA-65`, `agent-identity:v1`, 3309 bytes) **verifies True** against the agent-identity v1 public key — genuine signature, not a plausible blob |
| `grep -rnE 'rsa\.generate_private_key\|RSAPrivateKey\|ec\.generate_private_key\|ECDSA\|EllipticCurvePrivateKey\|ed25519\|nacl' backend/crypto/` | **no matches** — no classical keygen anywhere in the crypto dir |
| `git ls-files backend/crypto/.keystore` | empty — keystore NOT tracked; `.gitignore:120` `backend/crypto/.keystore/` |

---

## Adversarial findings against the brief

### 1. Real crypto, not theatre (Rule 1/1a) — CONFIRMED
- `backend/crypto/software_provider.py:29-31,69,84,90,105` calls `dilithium_py.ml_dsa.ML_DSA_65.{keygen,sign,verify}`. I independently probed dilithium-py: randomized keygen (two keypairs differ), correct-key verify True, **cross-key verify False** — this is real asymmetric FIPS-204, not a fixed/faked signer.
- Sizes are exact FIPS-204 ML-DSA-65: **pk=1952, sk=4032, sig=3309** (probed live, and asserted in `tests/crypto/test_pqc_signing.py:28-29` + `test_audit_chain_signing.py:16`).
- Sign/verify/tamper all correct (probed live + `test_pqc_signing.py:7-20`).
- `pkcs11_provider.py` and `vault_provider.py` are **honest stubs**: every method (including `__init__`) `raise NotImplementedError(_MSG)` with actionable guidance (`pkcs11_provider.py:14-28`, `vault_provider.py:13-27`). They do **not** fake HSM/Vault signing. `test_key_manager.py:35-46` proves `CRYPTO_PROVIDER=pkcs11` raises, then `software` works again (the seam is two-way, not a one-shot break).
- No fabricated/placeholder signature is passed off as real. The Stage-12 placeholder path in `audit_chain._sign()` (`audit_chain.py:61-65`) is now superseded: when `crypto.pqc_signing` imports cleanly it returns real ML-DSA-65; placeholder is the labelled fallback only (and `verify_range` explicitly treats placeholder rows as "chain-valid, signature-not-yet-cryptographic" — not as a fake real signature).

### 2. KeyProvider abstraction (KB_13 §"Pluggable KeyProvider") — CONFIRMED
- The ABC `KeyProvider` + `get_key_provider()` factory live in `key_provider.py:16-69`. Selection is config-only via `CRYPTO_PROVIDER ∈ {software, pkcs11, vault}` (`key_provider.py:57-68`); default `software`.
- I grepped every `*.py` under `backend/` for concrete-backend imports. Concrete imports appear **only** inside `key_provider.py:59-66` (the factory — the one place that is *supposed* to know the concretes) and the dilithium import inside `software_provider.py` itself. Callers `pqc_signing.py`, `key_manager.py`, and `audit_chain.py` import **only** `get_key_provider()` / the ABC — never a concrete backend. The HSM swap is genuinely config-only.

### 3. audit_chain wiring — CONFIRMED (infra-free portion)
- `audit_chain._sign(digest)` returns `('ML-DSA-65', 1, 3309)` (probed live), i.e. `algorithm='ML-DSA-65'`, `key_version=1 (≥1)`, real 3309-byte signature — replacing the Stage-12 `placeholder-sha256`/`key_version=0`. The signature verifies under the agent-identity public key (`test_audit_chain_signing.py:7-17`, re-run green).
- The DB round-trip persistence (`test_audit_chain_row_is_mldsa_signed_end_to_end`, `test_audit_chain_signing.py:25-37`) is `skipif not _HAS_DB` and was NOT run (Docker down) — this is **G-069**, already ledgered and accurately scoped: the DB step only persists+reads the *same* signature the infra-free test already proves. The wiring proof (`test_audit_chain_sign_uses_real_mldsa_no_db`) is real and passes.

### 4. Rotation drill — CONFIRMED
- `key_manager.rotate` → `SoftwareKeyProvider.rotate` (`software_provider.py:101-107`) writes the next version, keeps old versions on disk (overlap rotation). Live drill: a signature made under v1 still verifies under the retained v1 public key after rotating to v2; `get_public_key_by_version('agent-identity', 1)` returns the same v1 pub. Historical verification works (`test_key_manager.py:14-32`).

### 5. No classical signatures (Rule 2) — CONFIRMED
- `grep` over `backend/crypto/` for `rsa.generate_private_key|RSAPrivateKey|ec.generate_private_key|ECDSA|EllipticCurvePrivateKey|ed25519|nacl|secp256` → **zero matches**. No real classical keygen; the earlier comment false-positive is not present.
- CI gate `.github/workflows/ci.yml:215-220` (`pqc-crypto-tests` job) greps the same regex in `crypto/` and fails the build on a hit, then runs `pytest tests/crypto/ -q`. The `pre_tool_use.sh:78-86` hook warns (does not block — deliberately conservative for informal stage tracking) on the same patterns in `backend/crypto/` and `backend/a2a/`. Both gates are correct and consistent.

### 6. Acceptance criteria vs. task doc

| Task-doc criterion | Status | Evidence |
|---|---|---|
| Replace placeholder-SHA256 ADR signing with real ML-DSA-65 (CTO remediation) | **MET** | `sign-decision-log.py:27-42` real signer path; the Stage-13.5 ADR footer verifies True (probed) |
| `pqc_signing.py` `sign`/`verify` via ML-DSA-65 | **MET (honest deviation: dilithium-py, not liboqs-python)** | `pqc_signing.py:19-28`; deviation justified in ADR D1 + research §23 (liboqs won't build on Windows) |
| `key_manager.py` `get_signing_key(role)` + `rotate(key_id)` (env-selectable backend) | **MET (env var is `CRYPTO_PROVIDER`, not the doc's `KEY_BACKEND`)** | `key_manager.py:12-30`; selection in `key_provider.py:57` — naming drift only, function delivered |
| `audit_chain.py` signs each row's hash with ML-DSA-65 | **MET (infra-free proof); DB round-trip OWED (G-069)** | `_sign()` returns real ML-DSA-65 live |
| `scripts/sign-decision-log.py` real signer | **MET** | ADR footer verifies True |
| `scripts/verify-audit-chain.py` verifies ML-DSA-65 end-to-end | **CODE PRESENT; DB round-trip OWED (G-069)** | `verify-audit-chain.py:142-152` best-effort ML-DSA verify per row; needs a live DB to exercise |
| SoftHSM init script `docker/secrets/init-softhsm.sh` | **NOT CREATED — deferred to Stage 22 (ADR D2)** | `docker/secrets/` does not exist; provider is an honest stub |
| `pytest backend/tests/crypto/ -v` green (roundtrip + rotation) | **MET** | 8 passed / 1 skipped |
| No new RSA/ECDSA/EdDSA in `backend/crypto/` | **MET** | grep clean + CI gate |

Two listed file artefacts (`docker/secrets/init-softhsm.sh`, `init-vault.sh`) were not created and the `pkcs11`/`vault` providers are stubs. This is an **honest, ADR-documented deferral to the Stage-22 pilot** (ADR D2 + Honest-residual section; KB_13 confirms the swap drill is Stage 22), backed by honest-raising stubs rather than fakes — consistent with Rule 1a. I treat these as deferred-with-justification, not silent drops. Env-var naming drift (`CRYPTO_PROVIDER` vs the doc's `KEY_BACKEND`) and library choice (`dilithium-py` vs `liboqs-python`) are deviations the ADR + research §23 + KB_13 all document; they do not weaken the deliverable.

### 7. Overclaim check — CLEAN
- The ADR's "verified" claims (8 crypto tests pass / 1 skipped; real sizes; rotation; ADR re-signed `ML-DSA-65`; audit holds 364) all reproduced exactly on this host. No overclaim found.
- The G-069 "infra-free wiring proof is real" claim is TRUE: I independently ran `test_audit_chain_sign_uses_real_mldsa_no_db` logic and confirmed `_sign()` returns a real, verifying ML-DSA-65 signature. The ADR correctly does NOT claim the DB persistence was tested — it explicitly ledgers it as owed. This is honest residual disclosure, not a hidden gap.
- Research §23 (`research/initial-research.md:2265+`) exists with the live library-options verification and the dilithium-py decision. KB_13 (`:59-67`) and KB_14 carry the real diffs. KB_TASK_LOG has the Stage-13.5 entry (`:1371`).

---

## Gaps that must be fixed before close

**None that block PASS.** The crypto layer is real, the abstraction is clean, the wiring is proven infra-free, and the one un-run item is a pre-existing, accurately-scoped, lower-tier ledger entry (G-069) whose substance is already proven by the no-DB wiring test.

## Residuals (already ledgered — not introduced by this review)
- **G-069 (medium, OPEN):** DB-gated `audit_chain` row round-trip (`test_audit_chain_row_is_mldsa_signed_end_to_end`) + full live suite re-run owed when Docker is up. Confirmed accurate. **No new ledger row needed** — the existing G-069 fully captures it.
- pkcs11/vault providers are honest stubs; software→pkcs11 swap drill + `docker/secrets/init-*.sh` deferred to Stage 22 (ADR D2, KB_13) — documented, not a gap.
- Agent-card signing (Stage 14), hybrid TLS / SLH-DSA (Stage 18) — out of scope here, correctly deferred.

---

**Independence statement:** I did not implement Stage 13.5. Every PASS criterion above was independently re-run live on this host (the crypto layer needs no infra), not taken from the ADR. The single DB-dependent test could not be exercised (Docker down) and is honestly ledgered as G-069 — its substance is independently proven by the infra-free wiring test, which I re-ran.

**VERDICT: PASS** (DYNAMIC verification; G-069 DB round-trip remains owed per the existing ledger).
