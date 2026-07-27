# Stage 25 — PQC Key-Rotation Drill (identity key, live local env)

- **Date:** 2026-07-02T18:06Z
- **Command:** `bash scripts/rotate-pqc-keys.sh --key-type identity --grace-hours 24` (dry-run first, then real)
- **Environment (HONEST):** the live local Docker env (PG@5544, the real attestable `audit_chain`) — the task doc says
  "pilot env"; **no customer pilot exists (G-035)**, so this drill exercises the identical machinery on the only live
  environment there is. Re-run on the pilot env at go-live (runbook §4).

## Measured outcome

| Check | Result |
|---|---|
| Chain BEFORE | `verify-audit-chain.py` exit 0 — **427 rows; all 348 post-cutover ML-DSA-65 sigs verify** |
| Dry-run | plan printed (generate → grace(24h, both verify) → revoke(old → revocation list) → verify); no key generated |
| Real rotation | identity key rotated, mode `hybrid`, grace 24h; **rotation marker appended as seq 428** and signed |
| Chain AFTER | exit 0 — **428 rows; all 349 post-cutover sigs verify** (incl. every pre-rotation row under the prior key version → historical verification holds through rotation) |
| Data-plane continuity | the marker append itself succeeded MID-drill (a live signed write during rotation); the preceding operational write (`post_market.sweep`, seq 427) and the marker (seq 428) bracket the drill with zero failed appends. Rotation wall-time **8.4 s**; no signing outage observed |
| Rotation ledger | `key_rotation` rows now: seq 428 (identity, this drill) + the Stage-18-era seq 221 (firmware), 222 (identity), 223 (tls) |

## Honest caveats

- "Zero data-plane downtime" here means: no append failed and the chain verified before/during/after on THIS
  single-node env. A pilot-scale claim needs the drill re-run under concurrent load (see the Stage-25 load test) and on
  the deployed topology.
- The 24-hour grace window (old key remains valid for verify) is asserted by the key_manager overlap logic and the
  post-drill verify of old-key rows; the scheduled revoke-after-grace fires at +24h — confirm the revocation marker in
  the next nightly sweep.

**Verdict: PASS** — rotation is drillable end-to-end on the live chain with continuous verification.
