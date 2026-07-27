---
name: PQC Crypto Strategy
description: Post-quantum cryptography placement, library matrix, key lifecycle, rotation policy, CNSA 2.0 timeline
type: spec
last-updated: 2026-05-18
---

# KB_13 — PQC Crypto Strategy

## Purpose

Specify which post-quantum algorithm goes where, which libraries implement them, how keys are stored and rotated, and how the migration roadmap aligns with CNSA 2.0 (2027-01-01 NSS deadline).

## Source of truth

- NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA), finalised 2024-08.
- NIST IR 8547 (PQC migration guidance).
- CNSA 2.0 (NSA / CISA).
- This file is the contract for `backend/crypto/`, `backend/a2a/`, `backend/memory/audit_chain.py`, and the oqs-provider sidecar in `docker/docker-compose.pqc.yml`.

## Body

### Algorithm placement matrix

| Layer | Algorithm | NIST FIPS | Where implemented | Stage |
|---|---|---|---|---|
| Agent ↔ agent TLS (A2A external boundary) | ML-KEM-768 + X25519 hybrid | FIPS 203 | oqs-provider sidecar in `docker/docker-compose.pqc.yml` (haproxy/stunnel front) | Stage 18 |
| Signed agent actions; audit_chain rows; agent cards | ML-DSA-65 | FIPS 204 | `backend/crypto/pqc_signing.py` | Stage 13.5 (audit chain), Stage 14 (agent cards) |
| Firmware / policy bundle signatures (long-trust) | SLH-DSA-SHA2-128s | FIPS 205 | `backend/crypto/pqc_slh_dsa.py` | Stage 18 |
| OT message integrity (Sparkplug B payloads, OPC UA UserTokenPolicy MAC) | HMAC-SHA-384 | (already quantum-resistant at this length) | `backend/crypto/hmac_sha384.py` | Stage 15 |
| Internal session keys / API tokens | secrets.SystemRandom 256-bit | n/a (symmetric, quantum-safe at length) | Python stdlib | always |
| Embedding hashes / non-secret integrity | SHA-256 / SHA-384 | FIPS 180-4 | Python `hashlib` | always |

### What NOT to use after Stage 13.5 (in new code)

- RSA-* (RSASSA-PSS, RSASSA-PKCS1-v1_5) — quantum-vulnerable.
- ECDSA / EdDSA standalone — quantum-vulnerable. (X25519 inside a HYBRID with ML-KEM is OK; EdDSA standalone for new signing is NOT.)
- DH / ECDH standalone — quantum-vulnerable. Use hybrid KEM.
- SHA-1, MD5 — pre-image / collision-broken regardless of quantum.
- AES-128 — too short for long-trust artefacts. Use AES-256 + GCM/SIV.
- DES / 3DES / RC4 / RC5 — never.

The `pre_tool_use.sh` hook warns when these patterns appear in `backend/crypto/` or `backend/a2a/`.

### Library matrix (Docker/Linux only on dev — no Windows-native build)

| Concern | Library | Version pin (target) | Source license |
|---|---|---|---|
| ML-KEM / ML-DSA / SLH-DSA primitives | `liboqs-python` over `liboqs` | `liboqs-python==0.10.*`, `liboqs==0.11.*` | MIT |
| Classical primitives (X25519, HMAC-SHA-384, SHA-256, key serialization) | `cryptography` (Python) | `cryptography==43.*` | Apache 2.0 |
| TLS termination with PQC | OpenSSL 3.5+ with `oqs-provider` | OpenSSL `3.5.*`, oqs-provider `0.8.*` | Apache 2.0 / OpenSSL |
| TLS front (sidecar) | `haproxy` 2.9+ OR `stunnel` 5.7x built against OpenSSL 3.5 | digest-pinned | GPLv2 / GPLv2 |
| Key storage (pilot) | HashiCorp Vault Transit | `vault==1.18.*` server, `hvac==2.3.*` client | BUSL (Vault), MIT (hvac) |
| Key storage (no-budget dev) | SoftHSM v2 (PKCS#11) | `softhsm==2.6.*`, `python-pkcs11==0.7.*` | BSD-2 |
| JSON canonicalization for signing | `jcs` (RFC 8785) | `jcs==0.2.*` | Apache 2.0 |

Windows note: `liboqs-python` does not build cleanly on MSVC without significant effort.

**Stage 13.5 update (2026-06-15) — the software KeyProvider uses `dilithium-py` on Windows-native (research §23).**
`liboqs-python` (Docker/Linux) AND `dilithium-py` (pure-Python, FIPS-204, Windows-native, no build) are BOTH valid
software backends behind the same `KeyProvider` ABC — selected by config, neither imported by callers. The dev/
no-budget tier defaults to `dilithium-py` (real ML-DSA-65: verified FIPS-204 sizes pk=1952/sk=4032/sig=3309), with
the explicit honest caveat that the pure-Python impl is NOT side-channel-hardened — which is fine because production
swaps to `pkcs11`(HSM)/`vault` via `CRYPTO_PROVIDER` (config only), where signing runs in hardened hardware. NOTE:
PyCA `cryptography` 46 ships OpenSSL wheels that do NOT expose ML-DSA (its PQC bindings require AWS-LC/BoringSSL), so
it is not a usable ML-DSA path here despite linking OpenSSL 3.5. Updated library-matrix row: ML-DSA primitives =
`dilithium-py` (Windows/dev software tier) | `liboqs-python` (Linux/Docker) | HSM via PKCS#11 (prod).

### Key inventory and storage

| Key alias | Algorithm | Storage | Rotation | Used by |
|---|---|---|---|---|
| `agent-identity-<env>` | ML-DSA-65 | Vault Transit (pilot) / SoftHSM (dev) | quarterly | A2A agent-card signature, audit_chain row signing |
| `agent-tls-<env>` | ML-KEM-768 + X25519 (hybrid) | Vault Transit / SoftHSM | quarterly | Sidecar TLS (external boundaries) |
| `firmware-policy-<env>` | SLH-DSA-SHA2-128s | Offline HSM (SoftHSM in dev; real HSM at pilot) | annual | Signed policy bundles, model-card attestations |
| `ot-msg-integrity-<env>` | HMAC-SHA-384 (symmetric) | Vault Transit / SoftHSM | monthly | OPC UA + Sparkplug B message MAC |

`<env>` ∈ {dev, staging, pilot, prod}. Keys never share across env boundaries.

### Rotation drill (`scripts/rotate-pqc-keys.sh`)

Overlap rotation pattern (zero-downtime):

1. **Generate.** New keypair version created in Vault Transit / SoftHSM. Old key kept active.
2. **Mark.** Append a special `audit_chain` row of type `key_rotation` signed by BOTH old key (v_n) and new key (v_n+1).
3. **Re-sign.** Agent cards re-emitted with new key signature. Publish both old + new public keys to the A2A discovery endpoint for the grace window.
4. **Grace.** Default 24 h (configurable). Both keys verify; new key signs new artefacts.
5. **Revoke.** Old key added to revocation list at `backend/a2a/revocation.py`'s configured URL. Old key remains in HSM read-only for `audit_chain` historical verification, but is no longer used for signing.
6. **Verify.** `python scripts/verify-audit-chain.py` runs end-to-end and must pass. The rotation marker row anchors the chain across the version boundary.

> **Drill evidence (Stage 25, 2026-07-02):** the identity-key overlap rotation was exercised LIVE on the local env —
> dry-run then real (`--key-type identity --grace-hours 24`); marker **seq 428**; chain verified before (427 rows) and
> after (428 rows, all 349 post-cutover sigs incl. old-key rows — historical verification held through rotation);
> 8.4 s wall, zero failed appends. Full record: `audits/STAGE_25_pqc_drill.md`. Re-run at pilot go-live.

### CNSA 2.0 timeline

| Year | Required posture |
|---|---|
| 2025–2026 | Hybrid (classical + PQC) allowed everywhere. Pilot deployments hybrid by default. |
| 2026-Q4 | Audit chain must be ML-DSA-65 signed (no placeholder). Pilot A2A peers exchange hybrid TLS. |
| 2027-01-01 | NSS-facing surfaces must be PQ-only (no classical fallback). Any customer in NSS supply chain inherits. |
| 2028-2030 | Industry-wide hybrid → PQ-only migration window. Industrial equipment with 10-yr lifecycle must support algorithm-rotation in field. |
| 2035 | All product surfaces PQ-only by default. |

The `--mode={hybrid,pq-only,classical-only}` flag on `scripts/rotate-pqc-keys.sh` supports staged migration.

### Crypto agility (the actual product moat)

Even after NIST's 2024 finalisation, ML-KEM/ML-DSA/SLH-DSA may face cryptanalytic advances in the next decade. The product surface negotiates algorithm identifiers per session:

- A2A agent card lists `supported_kems`, `supported_signatures` arrays.
- Hybrid TLS handshake negotiates the strongest mutually-supported PQC + classical pair.
- audit_chain rows include `key_version` AND `algorithm` columns so chain rebuilds work across algorithm changes.
- Key manager exposes `migrate(old_alg, new_alg)` for emergency algorithm swaps.

A successful "swap ML-DSA-65 for a NIST-PQC-Round-5-finalist" drill is a Stage 25 acceptance criterion.

### Risk register cross-references

- A2A peer compromise → row added 2026-05-18.
- PQC migration rollback → row added 2026-05-18.
- Key-management infra (Vault/SoftHSM) compromise → row to add Stage 13.5 task doc.

### Out of scope

- Quantum-safe HMAC variants (HMAC-SHA-384 already quantum-resistant at this length per NIST guidance).
- TLS 1.3 cipher suite design (we use the standard PQC-hybrid ciphersuites; we don't define new ones).
- HSM hardware selection at pilot — handled in Stage 22 pilot deployment runbook.

### Pluggable KeyProvider / PKCS#11 HSM boundary (added v2.1, 2026-05-31)

**Requirement (PRD v2.1 §v2.1.5):** built-in software key generation/signing must sit behind ONE abstract
boundary so a purchased HSM replaces it as a **configuration change**, not a code change. No caller in
`backend/` imports a concrete crypto backend; callers depend only on the abstract `KeyProvider`.

Market reality validating this (verified 2026-05-31, see research log §11): every serious HSM exposes PQC via
**PKCS#11** — Entrust nShield (ML-DSA in firmware), Utimaco Quantum Protect (ML-KEM+ML-DSA via PKCS#11
vendor-defined mechanisms, in-field firmware upgrade), Thales/Futurex (ML-DSA via firmware, PKCS#11 primary
API). So PKCS#11 is the correct vendor-neutral abstraction.

```
backend/crypto/key_provider.py        # abstract KeyProvider (ABC) + get_key_provider() factory
backend/crypto/software_provider.py   # SoftwareKeyProvider  -> liboqs-python (dev/no-budget)
backend/crypto/pkcs11_provider.py     # Pkcs11KeyProvider     -> python-pkcs11; SoftHSM (dev) AND real HSM (prod), SAME code path
backend/crypto/vault_provider.py      # VaultTransitProvider  -> HashiCorp Vault Transit (pilot)
```

Abstract surface (callers touch only this + the factory):
`generate_keypair(alias, algorithm) · sign(alias, data) · verify(pub, data, sig) · public_key(alias) ·
rotate(alias) · capabilities -> {supported_algorithms, fips_level, attestation}`.

Selection is by config only — `CRYPTO_PROVIDER ∈ {software, pkcs11, vault}` (+ `PKCS11_MODULE`,
`PKCS11_TOKEN/SLOT`, `PKCS11_PIN` via secret). `pqc_signing.py` and `audit_chain.py` call `get_key_provider()`;
they never import a concrete provider.

**Why the swap is fast and undisturbed:**
- `Pkcs11KeyProvider` targets the PKCS#11 standard, so SoftHSM (dev) and a real HSM (prod) are the *same* driver
  with a different token/slot — the buy-an-HSM path is already exercised in dev/CI before a customer ever buys one.
- `audit_chain` rows already carry `key_version` + `algorithm` columns, so historical verification survives a
  provider/key/algorithm swap.

**Crypto-agility acceptance test (Stage 13.5 spec; drilled Stage 22 pilot, re-drilled Stage 25):** a documented
drill swaps `SoftwareKeyProvider`→`Pkcs11KeyProvider` via config only; the running system keeps signing and
`scripts/verify-audit-chain.py` still passes across the boundary. PRD v2.1 §v2.1.2 §C records the SLO.

## Last verified

2026-06-21 (Stage 18 — PQC Wave 2): **hybrid TLS + long-trust SLH-DSA are BUILT + verified live.** Key finding: the
host/container **OpenSSL 3.5.4** ships NATIVE ML-KEM/ML-DSA/SLH-DSA + the `X25519MLKEM768` hybrid group, so the
oqs-provider build in the library matrix above is **no longer needed** (oqs-provider predates the 3.5 release).
- **App-level KEM** — `backend/crypto/pqc_kem.py`: **ML-KEM-768** (FIPS 203) via **kyber-py** (pure-Python, Windows-native,
  the ML-KEM sibling of dilithium-py); `encapsulate`/`decapsulate`/`keygen` + alias-backed keystore. Verified roundtrip,
  FIPS-203 sizes (ek 1184/ct 1088/ss 32), implicit-rejection on tampered ciphertext.
- **Long-trust signing** — `backend/crypto/pqc_slh_dsa.py`: **SLH-DSA-SHA2-128s** (FIPS 205) via the OpenSSL 3.5 CLI;
  real sign/verify (7856-byte sig), honest-unavailable if OpenSSL < 3.5. **All 7 model cards** carry a self-verifiable
  SLH-DSA attestation footer; `scripts/sign-firmware-bundle.py` signs firmware/policy bundles (detached) + model cards.
- **Hybrid TLS** — `docker/docker-compose.pqc.yml` fronts ALL external boundaries (A2A :8443, REST/WS :8444, MQTT-TLS
  :8883, OPC-UA-TLS :4843) with an OpenSSL-3.5 sidecar; `scripts/gen-pqc-tls-cert.sh` emits an **ML-DSA-65** cert chain.
  **Verified live:** `backend/tests/crypto/test_hybrid_tls.py` runs a real `s_server`/`s_client` handshake →
  `Negotiated TLS1.3 group: X25519MLKEM768`, `Peer signature type: mldsa65`.
- **Rotation** — `scripts/rotate-pqc-keys.sh` now drives a real `key_manager` CLI for **all 4 key types**
  (identity ML-DSA-65 / tls ML-KEM-768 / firmware SLH-DSA / hmac) with `--mode={hybrid,pq-only,classical-only}` +
  `--dry-run`; each rotation writes a `key_rotation` audit_chain marker.
- **Gates** — `scripts/audit.sh` now FAILS on real classical-crypto code (`rsa.generate_private_key|ec.generate_private_key|
  EllipticCurvePrivateKey|ec.ECDSA(`) in `backend/crypto`+`backend/a2a` (matches code, not the forbidden-list comments).
  **G-065:** CycloneDX **SBOM** (`sbom.cyclonedx.json`, CI `sbom` job) + `compliance/dependency-exceptions.md` (the
  documented load-bearing-pin exception for pip-audit; bandit SAST is blocking). New deps: `kyber-py==1.2.0`,
  `cyclonedx-bom==7.3.0`. **18 crypto tests pass; audit holds 364.** ADR `2026-06-21_stage18_pqc_wave2.md`.

### Deployment status per surface (Stage 18)

| Surface | KEX | Cert / signature | Status |
|---|---|---|---|
| A2A (`/a2a/v1/rpc`, `/.well-known/agent.json`) | X25519MLKEM768 (sidecar) | ML-DSA-65 agent cards (Stage 14) | sidecar config + live handshake verified; live mTLS-client-cert→peer_state binding = deploy |
| REST `/api/*` + WebSocket `/ws` | X25519MLKEM768 (sidecar) | ML-DSA-65 leaf | sidecar fronts :8444→backend:8000 |
| MQTT (Sparkplug B) | X25519MLKEM768 (sidecar :8883) | ML-DSA-65 leaf + HMAC-SHA-384 payload MAC (Stage 15) | sidecar config |
| OPC UA | X25519MLKEM768 (sidecar :4843) | ML-DSA-65 leaf; Aes256Sha256RsaPss interim direct (Stage 15) | sidecar config |
| audit_chain / ADRs / agent cards | — | ML-DSA-65 (Stage 13.5/14) | LIVE |
| firmware / policy / model-card bundles | — | SLH-DSA-SHA2-128s | LIVE (7 model cards signed) |

Prior: 2026-06-15 (Stage 13.5): `backend/crypto/` is BUILT against this contract. `key_provider.py` (the `KeyProvider` ABC
+ `get_key_provider()` factory, `CRYPTO_PROVIDER ∈ {software,pkcs11,vault}`), `software_provider.py` (real FIPS-204
ML-DSA-65 via `dilithium-py` + a versioned filesystem keystore — rotation + historical verification),
`pkcs11_provider.py`/`vault_provider.py` (honest stubs — the seam is real; full impl + the software→pkcs11 swap drill
= Stage 22 pilot), `pqc_signing.py` (sign/verify/active_key_version/public_key), `key_manager.py`
(get_signing_key/rotate/get_public_key_by_version), `hmac_sha384.py` (OT MAC, Stage 15). `audit_chain` now signs each
row's hash with **real ML-DSA-65** (key_version≥1, algorithm `ML-DSA-65` — replacing the Stage-12 placeholder);
`scripts/sign-decision-log.py` signs ADRs with real ML-DSA-65 (`agent-identity:v1`). No RSA/ECDSA/EdDSA in
`backend/crypto/` (pre_tool_use hook + a `pqc-crypto-tests` CI grep enforce). 8 crypto tests pass (sign/verify/tamper
+ rotation drill + provider-swap agility + audit_chain ML-DSA wiring); audit holds 364. The DB-round-trip + full live
suite re-run await Docker (host Docker Desktop was down at close — G-069). ADR `2026-06-15_stage13_5_pqc_foundations.md`.

Prior: 2026-05-18 (base), + 2026-05-31 (KeyProvider/PKCS#11 boundary added; HSM-PQC market reality verified).

## Stage 27 — SPIFFE/SPIRE workload identity (dual-identity model, 2026-07-04)

Two identities, each doing what it is for (research §38.1/§38.2):
- **SPIFFE X509-SVID = TRANSPORT authentication.** Short-lived (1h TTL), auto-rotated by SPIRE; proves *who is
  calling* on the wire (mutual TLS). LIVE: `docker/docker-compose.spire.yml` (SPIRE server + agent, join-token
  node attestation, trust domain `ai-agent.local`); `backend/security/spiffe_identity.py` (X509Source containerised
  path + dev-host SVID fetch + `authenticate_peer` gate). VERIFIED: a real SVID-mTLS handshake authenticates a
  valid client and REFUSES an anonymous one (6/6 tests); SVID rotation drill shows a NEW cert serial with the SAME
  SPIFFE identity (`scripts/spire/rotate-svid-drill.py`).
- **ML-DSA-65 = EVIDENCE signing.** Post-quantum, long-trust: audit rows, agent cards, ADRs (Stage 13.5+).
The AgentCard binds BOTH (`backend/a2a/agent_card_cnstyle.py`: SPIFFE ID + ML-DSA public key in one signed card),
so a consumer verifies transport identity (SVID) AND evidence signatures (ML-DSA) belong to the same agent.
Honest scope: Istio Ambient mesh mTLS = pilot/K8s; the LOCAL load-bearing path is direct SVID-mTLS at the A2A
boundary (`a2a/server.py` XFCC authentication — R4/G-4 CLOSED on that path).
