---
status: done
stage: 13.5
slug: pqc_foundations
created: 2026-05-18
---

# Stage 13.5 — PQC Foundations (ML-DSA-65 + Key Management)

> First PQC milestone. ML-DSA-65 signing wired into the `audit_chain` table. Key management via Vault Transit (pilot) or SoftHSM (dev no-budget). Other PQC algorithms (ML-KEM hybrid TLS, SLH-DSA firmware) ship in Stage 18.

## Pre-requisites

- Stages 11–13 closed.
- `liboqs` available in the backend Docker image.

## Acceptance criteria

- [ ] (CTO remediation) Replace placeholder-SHA256 ADR/decision-log signing with real ML-DSA-65 signatures

- [ ] `backend/crypto/pqc_signing.py` exposes `sign(payload_bytes, key) -> sig_bytes` and `verify(payload, sig, public_key) -> bool` using `liboqs-python` ML-DSA-65.
- [ ] `backend/crypto/key_manager.py` provides `get_signing_key(role) -> SigningKey` + `rotate(key_id)` with Vault Transit OR SoftHSM backend (env-var `KEY_BACKEND`).
- [ ] `backend/memory/audit_chain.py` updated to sign each row's hash with ML-DSA-65 via `pqc_signing.py` (replacing the Stage 12 placeholder).
- [ ] `scripts/sign-decision-log.py` uses the real signer (replacing the placeholder).
- [ ] `scripts/verify-audit-chain.py` verifies the ML-DSA-65 signatures end-to-end.
- [ ] SoftHSM init script in `docker/secrets/init-softhsm.sh` for no-budget dev path.
- [ ] `pytest backend/tests/crypto/ -v` green (sign/verify roundtrip, key rotation drill).
- [ ] No new RSA / ECDSA / EdDSA signature code in `backend/crypto/`.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/crypto/__init__.py` | Package marker |
| `backend/crypto/pqc_signing.py` | ML-DSA-65 sign/verify |
| `backend/crypto/key_manager.py` | Vault/SoftHSM abstraction |
| `backend/crypto/hmac_sha384.py` | OT MAC helper (used at Stage 15) |
| `backend/tests/crypto/test_pqc_signing.py` | Roundtrip + tampering tests |
| `backend/tests/crypto/test_key_manager.py` | Vault + SoftHSM paths |
| `backend/tests/crypto/test_audit_chain_signing.py` | Audit chain end-to-end |
| `docker/secrets/init-softhsm.sh` | SoftHSM bootstrap |
| `docker/secrets/init-vault.sh` | Vault Transit engine bootstrap (pilot) |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/memory/audit_chain.py` | Use real signer |
| `scripts/sign-decision-log.py` | Use real signer |
| `backend/requirements.txt` | Add `liboqs-python`, `hvac`, `python-pkcs11`, `jcs` |
| `backend/Dockerfile` (or equivalent) | Install `liboqs` system package |
| `.github/workflows/ci.yml` | Add `pqc-crypto-tests` job |
| `compliance/risk-register.md` | Update PQC-related rows with implementation status |
| `knowledge-base/KB_13_PQC_Crypto_Strategy.md` | Confirm implementation matches spec |

## KB files this stage updates

- `KB_13_PQC_Crypto_Strategy.md`
- `KB_14_Agent_Memory_Architecture.md` (audit_chain now signed)
- `KB_TASK_LOG.md`

## Verification commands

```bash
cd backend && pytest tests/crypto/ -v
python scripts/verify-audit-chain.py
bash scripts/rotate-pqc-keys.sh --dry-run --key-type identity
```

## Audit target

- Strict decrease. Plus new gate: `scripts/audit.sh` should flag any new RSA / ECDSA usage in `backend/crypto/`.

## Role

- Primary: `security-pqc-engineer`
- Secondary: `backend-engineer` (audit_chain wiring), `compliance-engineer` (ADR for crypto choices)

## Risks / unknowns

- `liboqs-python` build on the backend Docker image — pin distro version that has `liboqs` packaged or build from source.
- SoftHSM PKCS#11 driver path varies; document for the dev README.

## Hand-off

- What is now true: every audit chain row is ML-DSA-65 signed; key rotation drill works.
- Next stages: 14 (A2A protocol — agent cards signed by `agent-identity` key), 18 (PQC Wave 2 — hybrid TLS everywhere).
