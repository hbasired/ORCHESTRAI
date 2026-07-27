---
status: done
stage: 18
slug: pqc_wave2
created: 2026-05-18
---

# Stage 18 — PQC Migration Wave 2 (Hybrid TLS Everywhere + SLH-DSA Firmware)

> All external boundaries on hybrid TLS (ML-KEM-768 + X25519). SLH-DSA-SHA2-128s for firmware / policy / model-card bundles. Crypto-agility plumbing for the 2027-01-01 CNSA 2.0 deadline.

## Pre-requisites

- Stage 13.5 closed (ML-DSA-65 + key manager).
- Stage 14 closed (A2A — first hybrid TLS deployment).
- Stage 15 closed (OPC UA + Sparkplug B — second batch of external boundaries).

## Acceptance criteria

- [ ] (CTO remediation) Promote pip-audit (and confirm bandit) to BLOCKING CI gates (pip-audit is currently continue-on-error:true / warn-only despite its 'flip to required when Stage 11 deps clean' comment), or document the load-bearing-pin exception; generate a CycloneDX SBOM (G-065)

- [ ] oqs-provider sidecar terminates hybrid TLS on every external boundary: A2A, REST `/api/*`, WebSocket `/ws`, MQTT-over-TLS, OPC UA.
- [ ] `backend/crypto/pqc_kem.py` exposes `encapsulate(peer_public) -> (ciphertext, shared_secret)` / `decapsulate(ciphertext, key_id) -> shared_secret` for application-level KEM (when sidecar is off-path).
- [ ] `backend/crypto/pqc_slh_dsa.py` for firmware/long-trust artefact signing.
- [ ] Signed bundles: model-card attestations + policy bundles + firmware images all SLH-DSA signed.
- [ ] `scripts/rotate-pqc-keys.sh` supports all four key types (identity, tls, firmware, hmac) with `--mode` flag.
- [ ] Audit-script extension: any new `RSA-` / `ECDSA-` / classical-only signature code in `backend/` fails the new pattern.
- [ ] CI gate `pqc-crypto-tests` covers KEM roundtrip, SLH-DSA sign/verify, sidecar TLS handshake.
- [ ] `KB_13_PQC_Crypto_Strategy.md` updated with deployment status per surface.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/crypto/pqc_kem.py` | ML-KEM-768 KEM operations |
| `backend/crypto/pqc_slh_dsa.py` | SLH-DSA-SHA2-128s signatures |
| `backend/tests/crypto/test_pqc_kem.py` | KEM roundtrip |
| `backend/tests/crypto/test_pqc_slh_dsa.py` | Long-trust sign/verify |
| `backend/tests/crypto/test_hybrid_tls.py` | Sidecar handshake |
| `scripts/sign-firmware-bundle.py` | SLH-DSA sign helper |

## Files to MODIFY

| Path | Change |
|---|---|
| `docker/docker-compose.pqc.yml` | Sidecar fronts ALL external boundaries (not just A2A) |
| `backend/crypto/key_manager.py` | Add `firmware-policy-<env>` SLH-DSA key type |
| `scripts/rotate-pqc-keys.sh` | Support all four key types fully |
| `scripts/audit.sh` | Extend forbidden patterns: `rsa\.generate_private_key|ec\.generate_private_key|ECDSA|EllipticCurvePrivateKey` in NEW backend/crypto code |
| `compliance/model-cards/*.md` | Add SLH-DSA signed attestation footer |
| `compliance/risk-register.md` | PQC migration rollback row marked implemented |

## KB files this stage updates

- `KB_13_PQC_Crypto_Strategy.md`
- `KB_10_Production_Hardening.md`
- `KB_TASK_LOG.md`

## Verification commands

```bash
cd backend && pytest tests/crypto/ -v
bash scripts/rotate-pqc-keys.sh --dry-run --key-type tls
# Verify hybrid TLS handshake
openssl s_client -connect localhost:8443 -groups X25519MLKEM768 -tls1_3
```

## Audit target

- Strict decrease + zero new classical-only crypto in new code.

## Role

- Primary: `security-pqc-engineer`
- Secondary: `devops-sre` (sidecar deployment)

## Hand-off

- What is now true: CNSA 2.0 posture met for hybrid migration; product is "crypto-agile" with rotation drill working end-to-end.
- Next stage (19) wires the governance evidence pipeline that depends on these signed artefacts.
