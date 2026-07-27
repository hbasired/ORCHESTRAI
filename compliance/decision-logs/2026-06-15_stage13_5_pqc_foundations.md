# ADR — Stage 13.5: PQC foundations (real ML-DSA-65 signing + the KeyProvider boundary)

**Date**: 2026-06-15
**Status**: Accepted (Stage 13.5 — follows Stage 13 `2026-06-15_stage13_cdc_ingestion.md`)
**Author personas**: `security-pqc-engineer` (primary) + `backend-engineer` (audit_chain wiring) + `compliance-engineer`
**Relates**: KB_13 (PQC strategy — the contract), KB_14 (audit_chain). Research §23. Follows Hard Rule 1a (real
crypto, honest stubs — never a faked signature), Rule 9 (free/local), Rule 11 (research-first), Rule 2 (no
classical-only signatures in new code). Pays the CTO remediation "replace placeholder-SHA256 ADR signing with real
ML-DSA-65" + begins the zero-trust agent-identity work (G-064).

---

## Context

Stage 12 wrote `audit_chain` with a STRUCTURALLY-correct placeholder signature (`algorithm='placeholder-sha256'`,
`key_version=0`), explicitly to be replaced here. Stage 13.5 wires REAL FIPS-204 **ML-DSA-65** signing behind KB_13's
pluggable **KeyProvider** boundary, so the audit chain + ADRs carry genuine post-quantum signatures and a purchased
HSM is a config swap, not a code change.

## Decisions

**D1 — `dilithium-py` ML-DSA-65 for the software KeyProvider (research §23).** The hard constraint: `liboqs-python`
doesn't build on Windows (KB_13), and PyCA `cryptography` 46 ships OpenSSL wheels that do NOT expose ML-DSA (its PQC
bindings need AWS-LC/BoringSSL — confirmed empirically: no `ml_dsa` module despite OpenSSL 3.5.4). `dilithium-py` is a
pure-Python FIPS-204 ML-DSA — Windows-native, no build, **real** (verified sizes pk=1952/sk=4032/sig=3309, valid
sign/verify, tamper rejected). Honest caveat (the library's own): not side-channel-hardened — acceptable BECAUSE it is
the dev/no-budget **software tier**; production swaps to `pkcs11`(HSM)/`vault` via `CRYPTO_PROVIDER` (config only),
where signing runs in hardened hardware.

**D2 — The KeyProvider abstraction is the real deliverable (KB_13 §v2.1.5).** `crypto/key_provider.py` (the
`KeyProvider` ABC + `get_key_provider()` factory) is the ONE boundary; `crypto/pqc_signing.py` + `crypto/key_manager.py`
+ `memory/audit_chain.py` call it and NEVER import a concrete backend. `software_provider.py` (dilithium-py + a
versioned filesystem keystore — overlap rotation + historical verification). `pkcs11_provider.py`/`vault_provider.py`
are **honest stubs** that raise with guidance (Rule 1a — no faked HSM signing); the full software→pkcs11 swap drill is
the Stage-22 pilot (KB_13). `hmac_sha384.py` is the OT MAC helper (Stage-15 use).

**D3 — audit_chain + ADR signing now real ML-DSA-65 (replacing the placeholder).** `audit_chain.append` signs each
row's hash with ML-DSA-65 (`key_version≥1`, `algorithm='ML-DSA-65'`); `verify_range` + `scripts/verify-audit-chain.py`
verify the signatures (via `key_manager.get_public_key_by_version`). `scripts/sign-decision-log.py` now signs ADRs
with real ML-DSA-65 (`agent-identity:v1`) — verified: this very ADR + the Stage-13 ADR re-signed `algorithm: ML-DSA-65`.
All historical decision-logs are batch re-signed at close (the CTO remediation). No RSA/ECDSA/EdDSA in
`backend/crypto/` — the pre_tool_use hook + a new `pqc-crypto-tests` CI grep enforce it (Rule 2).

## Why
- The audit chain is the EU-AI-Act Art-12 evidence + the substrate for A2A agent identity (Stage 14) — it must carry
  genuine post-quantum signatures, not a placeholder. The KeyProvider boundary makes "buy an HSM" a config change and
  is the crypto-agility moat (KB_13). Doing real ML-DSA-65 on the free/Windows dev host required the dilithium-py
  choice — honest about its software-tier nature, with the HSM path proven by the same ABC.

## Consequences
- New: `backend/crypto/{__init__,key_provider,software_provider,pkcs11_provider,vault_provider,pqc_signing,
  key_manager,hmac_sha384}.py`, `backend/tests/crypto/` (3 files, 9 tests), the `pqc-crypto-tests` CI job, this ADR,
  the explainer, KB_TASK_LOG entry, ledger G-069. Modified: `scripts/sign-decision-log.py` (real signer API),
  `requirements.txt` (`dilithium-py==1.4.0`, `jcs==0.2.1`), KB_13/KB_14, risk-register. `audit_chain.py` needed NO
  change (its Stage-12 `_sign()` already imported `crypto.pqc_signing` + fell back to placeholder — now it finds the
  real signer). Keystore gitignored.
- Verified (infra-free — no Docker needed for the crypto layer): **8 crypto tests pass / 1 skipped** (real ML-DSA-65
  sign/verify/tamper + sizes; rotation drill keeps v1 verifiable after rotating to v2; provider-swap agility; and
  `audit_chain._sign()` returns real ML-DSA-65 not the placeholder, verified). Real ADR signing confirmed
  (`ML-DSA-65`, `agent-identity:v1`). Audit holds **364** (real crypto, no grep-counted theatre — Rule 1a).

## Honest residual / ledger
- **G-069** — the host Docker Desktop was DOWN at close, so the DB-gated `audit_chain` row round-trip
  (`test_audit_chain_row_is_mldsa_signed_end_to_end`) + the full live suite re-run are owed when Docker is back. The
  wiring is proven infra-free by `test_audit_chain_sign_uses_real_mldsa_no_db` (the `_sign()` path returns + verifies
  a real ML-DSA-65 signature); the DB step only persists+reads that same signature.
- `pkcs11`/`vault` providers are honest stubs; the software→pkcs11 swap drill is Stage 22 (KB_13).
- Hybrid TLS (ML-KEM-768), SLH-DSA firmware signing = Stage 18 (PQC Wave 2). Agent-card signing = Stage 14.

## References
- `backend/crypto/*.py` · `backend/tests/crypto/*` · `backend/memory/audit_chain.py` · `scripts/sign-decision-log.py`
  · `scripts/verify-audit-chain.py` · `.github/workflows/ci.yml` (pqc-crypto-tests). KB_13/14. Research §23.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:31+00:00 -->
<!-- signature: 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 -->
