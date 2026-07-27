# Stage 18 — PQC Migration Wave 2 — Independent Review

**Auditor:** independent `task-auditor` (a DIFFERENT agent than the Stage-18 implementer)
**Date:** 2026-06-21
**Scope:** `backend/crypto/{pqc_kem,pqc_slh_dsa,key_manager}.py`; `scripts/{sign-firmware-bundle.py,gen-pqc-tls-cert.sh,rotate-pqc-keys.sh,audit.sh}`; `docker/docker-compose.pqc.yml`; `compliance/{model-cards/*.md,dependency-exceptions.md}`; `sbom.cyclonedx.json`; `backend/tests/crypto/{test_pqc_kem,test_pqc_slh_dsa,test_hybrid_tls}.py`; `.github/workflows/ci.yml`; ADR `2026-06-21_stage18_pqc_wave2.md`; KB_13/KB_10; risk-register; ledger G-065.
**Host capability:** OpenSSL **3.5.4** (native ML-KEM / ML-DSA / SLH-DSA + `X25519MLKEM768`) + kyber-py + Postgres :5544 — all crypto claims verified **LIVE** (DYNAMIC).

---

## VERDICT: **PASS** (with 1 MEDIUM CI defect + minor doc nits to fold in; none crypto-correctness)

The crypto in this stage is **real, not theatre**. I independently reproduced every load-bearing claim with my own commands (not just the stage's tests): a genuine ML-KEM-768 roundtrip with FIPS-203 sizes and implicit rejection; a genuine SLH-DSA-SHA2-128s sign/verify with tamper rejection; a **real `s_server`/`s_client` X25519MLKEM768 hybrid handshake with an ML-DSA-65 cert**; a model-card footer that self-verifies against its body and rejects a tampered body; all 4 key-type rotations writing real `key_rotation` audit_chain rows; and the classical-crypto gate firing on an injected real classical call while not false-positiving on docstrings. Hard Rules 1/1a (no theatre), 2 (no classical in new crypto), 9 (free/local), 11 (research-first) are honoured.

The single non-trivial finding is a **CI YAML defect** (duplicate `sbom:` job key) that means the *specific Stage-18 blocking SBOM job described in the ADR is not the one CI actually runs* — but the SBOM artefact itself is real and reproducible, and an (older) SBOM job survives. It does not affect crypto correctness; it is a fold-in fix, not a crypto-honesty failure. I therefore rate PASS rather than FAIL, but the SBOM-job claim in the ADR/KB/ledger is currently **slightly overstated** and should be corrected or the YAML de-duplicated.

---

## Per-criterion evidence

| Acceptance criterion | Claimed | Independently confirmed? | Note / command |
|---|---|---|---|
| G-065: promote/triage pip-audit + bandit; CycloneDX SBOM | done (exception + SBOM) | **YES (with CI caveat — see F1)** | SBOM real (CycloneDX 1.6, **69 components**); regenerated with the Stage-18 command → 69 components; bandit job has NO `continue-on-error` (blocking); pip-audit `continue-on-error: true` under documented exception. BUT duplicate `sbom:` job key → the Stage-18 blocking job is dropped by last-wins parsing (F1). |
| Sidecar terminates hybrid TLS on every boundary (A2A/REST/WS/MQTT/OPC UA) | sidecar config for all 5 | **YES (config); honest that it's deploy-wiring not a live containerised run** | `docker-compose.pqc.yml` fronts :8443/:8444/:8883/:4843; ADR "Honest residual" + KB_13 status table state the containerised haproxy deploy is "deploy wiring on top of the verified KEX/cert layer" — honest distinction. |
| `pqc_kem.py` encapsulate/decapsulate (FIPS-203) | real ML-KEM-768 | **YES (DYNAMIC)** | `pytest tests/crypto/test_pqc_kem.py` 5/5 pass; my own kyber-py run: ek=1184/dk=2400/ct=1088/ss=32, roundtrip matches, tampered ct → different secret (implicit reject), wrong dk → different secret. |
| `pqc_slh_dsa.py` for long-trust signing | real SLH-DSA-128s; honest-unavailable | **YES (DYNAMIC)** | `pytest tests/crypto/test_pqc_slh_dsa.py` 3 pass / 1 skip (unavailability path skips *because OpenSSL 3.5 is present* — honest); my own OpenSSL run: 7856-byte sig, verifies good, rejects tampered. `SlhDsaUnavailable` raised (never faked) if OpenSSL<3.5. |
| Signed bundles: model cards + policy + firmware SLH-DSA-signed | all 7 cards + detached bundle signer | **YES (DYNAMIC)** | 7/7 model cards carry footers; I extracted `rul_transformer_cmapss.md`'s footer and **independently verified** sig+pubkey against the body via OpenSSL (good=verified, tampered=rejected); footer sha256 == recomputed body sha256. `sign-firmware-bundle.py` detached sign→verify→tamper-reject reproduced on a temp file. |
| `rotate-pqc-keys.sh` supports all 4 key types + `--mode` | identity/tls/firmware/hmac | **YES (DYNAMIC)** | `--dry-run --key-type tls` works (CLI exists — fixing the ADR-claimed broken-script defect); real firmware/hmac/identity/tls rotations into a **temp** KEY_STORE_DIR each created the right keys (`.key/.pub`, `.dk/.ek`, `v1.sk/v1.pk`, hmac 48-byte key) and wrote real `key_rotation` audit_chain rows (seq 221/222/223 confirmed in PG). |
| Audit-script extension: classical crypto fails in new backend code | new gate in `audit.sh` | **YES (DYNAMIC, adversarial)** | `bash scripts/audit.sh` → 364, **no CLASSICAL VIOLATION**. Injected a real `rsa.generate_private_key(...)` into a throwaway `backend/crypto/` file → the exact gate grep fired; removed it. Gate matches CODE not the `# new SLH-DSA` comment / docstrings (no false positive). |
| CI gate `pqc-crypto-tests` covers KEM/SLH-DSA/TLS | yes | **YES (with CI-runner caveat F4)** | Job runs `pytest tests/crypto/` (all 3 files). On `ubuntu-latest` (OpenSSL 3.0) the SLH-DSA + hybrid-TLS tests **skip**; only KEM runs in CI. Locally on the 3.5 host all run. Honest skipif design; CI does not exercise the handshake. |
| `KB_13` updated with deployment status per surface | yes | **YES** | KB_13 §"Deployment status per surface" table is accurate + honestly caveated (sidecar config vs LIVE). |

---

## Findings (severity-ranked)

### F1 — MEDIUM — Duplicate `sbom:` job key in CI: the Stage-18 blocking SBOM job is silently dropped
`.github/workflows/ci.yml` defines **two** jobs both keyed `sbom:` — the new Stage-18 one at **line 404** (`cyclonedx-bom==7.3.0`, blocking, with a JSON `assert bomFormat=='CycloneDX'` gate) and a pre-existing one at **line 445** (`cyclonedx-bom==4.5.0`, emits `sbom-backend.json`). YAML mapping keys must be unique; duplicate keys are last-wins in permissive parsers and a hard error in strict ones. PyYAML keeps only the **older** job (verified: `jobs['sbom']` install line = `cyclonedx-bom==4.5.0`). So either GitHub rejects the workflow as invalid, or the new blocking Stage-18 SBOM job never runs.
**Impact:** the ADR/KB_13/ledger claim of a "blocking CI `sbom` job — 69 components / cyclonedx-bom 7.3.0 + JSON assertion" is not what CI executes. The SBOM *artefact* is genuine (I regenerated it: CycloneDX 1.6, 69 components), so G-065's substance holds, but the CI-gate claim is overstated.
**Fix:** rename/merge the duplicate so exactly one `sbom` job exists (keep the Stage-18 blocking 7.3.0 one), or correct the docs to describe the surviving job. `file:.github/workflows/ci.yml:404` + `:445`.

### F2 — LOW — `cyclonedx-bom` version drift across artefacts (7.3.0 vs 4.6.1 vs 4.5.0)
ADR D7/consequences + KB_13 line 184 + the new CI job (line 413) say **7.3.0**; `backend/requirements.txt:94` pins **4.6.1**; the surviving CI job (line 454) installs **4.5.0**. Three different pins for the same tool. The SBOM still generates (verified locally), but the attestable build set should agree. `file:backend/requirements.txt:94`.

### F3 — LOW — KB_13 line 176 overclaims what `test_hybrid_tls.py` asserts
KB_13 says the test verifies "`Negotiated TLS1.3 group: X25519MLKEM768`, `Peer signature type: mldsa65`." The test (`test_hybrid_tls.py:66-67`) asserts only the negotiated group + `TLSv1.3`; it does **not** assert `Peer signature type: mldsa65` (it does separately assert the cert text contains `ML-DSA-65` at line 49). The claim is *true in reality* — I independently confirmed an ML-DSA-65 cert in the handshake — but the named test does not assert that exact string. Rule-1a "verify the claim against the code path" nit; trim the wording. `file:knowledge-base/KB_13_PQC_Crypto_Strategy.md:176`.

### F4 — LOW — CI runner OpenSSL < 3.5 → SLH-DSA + hybrid-TLS tests SKIP in CI
`pqc-crypto-tests` runs on `ubuntu-latest` (OpenSSL 3.0.x). The SLH-DSA and hybrid-TLS tests `skipif` on OpenSSL<3.5, so in CI only the (infra-free, kyber-py) KEM tests actually execute; the handshake + SLH-DSA paths are verified only on the OpenSSL-3.5 host (which I did, live). Honest skipif design, but the CI gate does not exercise the AC's "sidecar TLS handshake" or SLH-DSA. Consider an OpenSSL-3.5 container/setup step in CI, or document that those paths are host/pilot-verified. `file:.github/workflows/ci.yml:201-223`.

### F5 — LOW — risk-register row 107 says pip-audit is "BLOCKING" — contradicts the Stage-18 decision
`compliance/risk-register.md:107` (the frozen-dependency-drift row, dated 2026-06-15) says G-065's mitigation is "BLOCKING `pip-audit`/`bandit` CI." Stage 18's actual decision (ADR D7 + `dependency-exceptions.md`) makes pip-audit **non-blocking** under a documented exception. Pre-existing row not corrected during Stage 18. Append a corrective note. `file:compliance/risk-register.md:107`.

---

## Honesty / overclaim assessment (prompt items 6, 8)

- **"OpenSSL 3.5 replaces oqs-provider" (ADR D1):** SOUND. I confirmed OpenSSL 3.5.4 natively lists `ML-KEM-768`, `SLH-DSA-SHA2-128s`, `ML-DSA-65`, and negotiates the `X25519MLKEM768` group — no oqs-provider build needed. KB_13's obsolete-row note is correct.
- **Sidecar-deploy vs host-handshake distinction:** STATED HONESTLY. The ADR "Honest residual" and the KB_13 status table both mark surfaces as "sidecar config" / "live handshake verified" and explicitly defer the containerised haproxy deployment + live mTLS-client-cert→`peer_state` binding to deploy-wiring (the Stage-17 G-064 Network pillar). No false "live in production" claim.
- **No Rule-1a theatre:** the new crypto files contain no fabrication; the only "faked" string is a docstring stating it is *never* faked. Honest-unavailable (`SlhDsaUnavailable` raise) is real, not a silent fake sig.
- **No Rule-2 violation:** `audit.sh` classical gate clean; no `rsa/ec/dsa.generate_private_key`/`EllipticCurvePrivateKey`/`ec.ECDSA(` in `backend/crypto`+`backend/a2a`; adversarial injection proves the gate works.
- **G-065 not an excuse to skip security:** the pip-audit exception is legitimate — `dependency-exceptions.md` enumerates the actual load-bearing pins with bump paths and 5 concrete compensating controls; bandit is genuinely blocking; the SBOM is real and reproducible. This is the AC's "OR document the exception" path, done honestly (subject to F1's CI-wiring fix).

---

## Re-run log (commands I executed)

```
openssl version → OpenSSL 3.5.4 30 Sep 2025
openssl list -signature-algorithms → ML-DSA-65, SLH-DSA-SHA2-128s present; -kem-algorithms → ML-KEM-768 present
cd backend && DATABASE_URL=...:5544/manufacturing pytest tests/crypto/test_pqc_kem.py tests/crypto/test_pqc_slh_dsa.py tests/crypto/test_hybrid_tls.py -v
   → 9 passed, 1 skipped
cd backend && DATABASE_URL=... pytest tests/crypto/ -q → 18 passed, 1 skipped
# independent ML-KEM-768 (kyber-py): ek1184/dk2400/ct1088/ss32; roundtrip OK; tamper→diff; wrong-dk→diff
# independent SLH-DSA (openssl genpkey/pkeyutl): 7856-byte sig; Verified Successfully; tampered → Verification Failure
# independent hybrid TLS: s_server -groups X25519MLKEM768 (ML-DSA-65 cert) ↔ s_client
   → "Negotiated TLS1.3 group: X25519MLKEM768", TLSv1.3, TLS_AES_256_GCM_SHA384
# independent model-card footer verify (rul_transformer_cmapss.md): sha256 match; Signature Verified Successfully; tampered → Failure
bash scripts/rotate-pqc-keys.sh --dry-run --key-type tls → JSON summary, CLI present
# rotate_key_type firmware/hmac/identity/tls into temp KEY_STORE_DIR → real keys + audit rows seq 221/222/223 (PG)
bash scripts/audit.sh → TOTAL 364, baseline 364, NO classical-crypto violation
# adversarial: injected rsa.generate_private_key into a throwaway backend/crypto file → gate grep FIRED; file removed
python -m cyclonedx_py requirements backend/requirements.txt → CycloneDX 1.6, 69 components
# bandit job: no continue-on-error (blocking); pip-audit job: continue-on-error: true (documented exception)
git status --short → no stray probe/temp files (all throwaway artefacts removed)
```

---

## Gaps to fold in (none block crypto correctness)

- **F1 (MEDIUM)** — de-duplicate the `sbom:` CI job so the Stage-18 blocking SBOM gate is the one that runs (or correct the ADR/KB/ledger SBOM-job wording). This is the one finding that meaningfully diverges doc-from-reality.
- **F2–F5 (LOW)** — version-pin drift; trim the KB_13 test-assertion wording; document/CI-enable the OpenSSL-3.5-gated tests; correct risk-register row 107's "BLOCKING pip-audit."

These are documentation/CI-wiring corrections, appropriately fixable in-stage before close; none require a later stage, so no new ledger row is opened. (G-075 and G-070 remain correctly open per the ledger; Stage 18 added no real PLC caller, consistent with the ADR.)
