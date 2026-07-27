# ADR — Stage 18: PQC Migration Wave 2 (hybrid TLS everywhere + SLH-DSA long-trust + G-065 SBOM)

**Date**: 2026-06-21
**Status**: Accepted (Stage 18 — follows Stage 17 functional safety wrapper)
**Author personas**: `security-pqc-engineer` (primary) + `devops-sre` (sidecar/SBOM)
**Relates**: KB_13 (PQC), KB_16 (A2A transport), KB_10 (production hardening). Research §28. Hard Rule 1a (real crypto,
honest deferrals), Rule 9 (free/local), Rule 11 (research-first), Rule 2 (PQC, no classical).

---

## Context

Stage 13.5 gave us ML-DSA-65 signing; Stage 14 the A2A boundary; Stage 15 OT boundaries. Stage 18 puts every external
boundary on **hybrid ML-KEM-768+X25519 TLS**, adds **SLH-DSA-SHA2-128s** for long-trust artefacts, makes the system
crypto-agile for the **CNSA 2.0** 2027-01-01 deadline, and pays the CTO #3 **G-065** (SBOM + dependency hygiene).

## Decisions

**D1 — OpenSSL 3.5 native PQC replaces the oqs-provider build (research §28.1).** The host/container OpenSSL **3.5.4**
ships native ML-KEM/ML-DSA/SLH-DSA + the `X25519MLKEM768` hybrid group — verified live (a real `s_server`/`s_client`
handshake negotiates `X25519MLKEM768` with an ML-DSA-65 cert; SLH-DSA-SHA2-128s sign/verify works). So the KB_13
library-matrix oqs-provider row is obsolete (it predates the 3.5 release); the sidecar is a stock OpenSSL-3.5 terminator.

**D2 — App-level KEM = ML-KEM-768 via kyber-py.** `backend/crypto/pqc_kem.py` (`encapsulate`/`decapsulate`/`keygen` +
alias-backed keystore) for when the sidecar is off-path. kyber-py is pure-Python + Windows-native (the ML-KEM sibling of
the Stage-13.5 dilithium-py signer); same honesty caveat (not side-channel-hardened → HSM in prod by config).

**D3 — Long-trust signing = SLH-DSA-SHA2-128s via OpenSSL 3.5.** `backend/crypto/pqc_slh_dsa.py` (CLI-backed; honest
`SlhDsaUnavailable` if OpenSSL < 3.5). SLH-DSA (hash-based, most conservative PQC) is correct for 10-yr-lifecycle
firmware/policy. `scripts/sign-firmware-bundle.py` signs bundles (detached `.slhdsa.sig` + attestation) + model-card
footers; **all 7 model cards** now carry a self-verifiable SLH-DSA attestation footer.

**D4 — Hybrid TLS sidecar on every boundary.** `docker/docker-compose.pqc.yml` fronts A2A/REST/WS/MQTT/OPC-UA with an
OpenSSL-3.5 sidecar; `scripts/gen-pqc-tls-cert.sh` emits the ML-DSA-65 cert chain. The live X25519MLKEM768 handshake is
verified by `backend/tests/crypto/test_hybrid_tls.py`. (Live mTLS-client-cert→`peer_state` binding for A2A is the deploy
wiring on top of this — the ZT Network pillar from Stage 17 G-064; the cert/KEX layer is now real.)

**D5 — Crypto-agility + 4-key-type rotation.** `key_manager` gains a `rotate` CLI driving `scripts/rotate-pqc-keys.sh`
for ALL 4 key types (identity ML-DSA-65 / tls ML-KEM-768 / firmware SLH-DSA / hmac) × `--mode={hybrid,pq-only,
classical-only}` × `--dry-run`; each rotation writes a `key_rotation` audit_chain marker (KB_13 overlap-rotation drill).
**Fixed a real defect:** the rotate script referenced a `key_manager` CLI that did not exist (it was never runnable
before) — the CLI + per-type rotation are now implemented + verified for all 4 types.

**D6 — Classical-crypto gate.** `scripts/audit.sh` now FAILS on real classical-crypto API calls in `backend/crypto`+
`backend/a2a` (`rsa.generate_private_key|ec.generate_private_key|EllipticCurvePrivateKey|ec.ECDSA(`) — matching CODE,
not the forbidden-list comments (which caused a Stage-13.5 false positive).

**D7 — G-065 supply-chain.** CycloneDX **SBOM** (`sbom.cyclonedx.json`, blocking CI `sbom` job — 69 components) is the
attestable frozen set; `bandit` SAST stays blocking; `pip-audit` stays informative ONLY under the **documented
load-bearing-pin exception** (`compliance/dependency-exceptions.md`: langgraph/starlette/mcp/protobuf<5↔TF/httpx) — the
AC's "OR document the exception" path, since hard-blocking would fail on a frozen-pin advisory we've consciously accepted.

## Why
- CNSA 2.0 mandates hybrid now → PQ-only by 2027 for NSS surfaces. Doing this on stock OpenSSL 3.5 (no fragile
  oqs-provider build) + pure-Python kyber-py makes it real, free, and reproducible. SLH-DSA gives firmware/policy a
  hash-based long-trust anchor independent of the lattice assumption. The SBOM + exception doc make the deliberately
  frozen dependency set attestable (Annex IV) rather than a silent liability.

## Consequences
- New: `backend/crypto/{pqc_kem,pqc_slh_dsa}.py` + `key_manager` CLI; `backend/tests/crypto/{test_pqc_kem,
  test_pqc_slh_dsa,test_hybrid_tls}.py`; `scripts/{sign-firmware-bundle.py,gen-pqc-tls-cert.sh}`;
  `compliance/dependency-exceptions.md`; `sbom.cyclonedx.json`; CI `sbom` job. Modified: `docker/docker-compose.pqc.yml`
  (all boundaries), `scripts/{rotate-pqc-keys.sh-driven key_manager CLI, audit.sh classical gate}`, `requirements.txt`
  (kyber-py, cyclonedx-bom), `compliance/model-cards/*.md` (SLH-DSA footers), KB_13, risk-register.
- New deps: `kyber-py==1.2.0` (runtime), `cyclonedx-bom==7.3.0` (build-time). SLH-DSA + hybrid TLS = host OpenSSL 3.5.
- Verified live: 18 crypto tests (KEM roundtrip + SLH-DSA sign/verify + **real X25519MLKEM768 handshake** + the
  Stage-13.5 suite); all 4 key-type rotations; SBOM generates (69 components); audit holds **364** + classical gate clean.

## Honest residual / ledger
- The sidecar handshake is verified on the host (OpenSSL 3.5); the containerised haproxy-3.1/OpenSSL-3.5 deployment +
  live mTLS-client-cert→peer_state binding (A2A) are deploy wiring on top of the verified KEX/cert layer.
- **G-075** (Stage-17 sil_bridge forgeable Decision): the self-validation hook is wired; the first real PLC caller
  (which must pass contract+world_state) is still a later stage — Stage 18 added no real PLC caller.
- kyber-py / dilithium-py software tier is not side-channel-hardened → HSM/Vault by config (CRYPTO_PROVIDER) at pilot.

## References
- `backend/crypto/{pqc_kem,pqc_slh_dsa,key_manager}.py` · `backend/tests/crypto/*` · `scripts/{sign-firmware-bundle.py,
  gen-pqc-tls-cert.sh,rotate-pqc-keys.sh,audit.sh}` · `docker/docker-compose.pqc.yml` · `compliance/dependency-exceptions.md`
  · `sbom.cyclonedx.json` · `.github/workflows/ci.yml`. KB_13/16/10. Research §28. FIPS 203/204/205; OpenSSL 3.5; CNSA 2.0.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:32+00:00 -->
<!-- signature: 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 -->
