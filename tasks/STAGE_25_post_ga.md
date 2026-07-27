---
status: done
stage: 25
slug: post_ga
created: 2026-05-18
---

# Stage 25 — Post-GA (PQC Rotation Drill + A2A Federation Test + EU AI Act Post-Market Monitoring)

> Live ops. Three exercises that prove the system survives production: (1) full PQC rotation drill on the pilot env with zero data-plane downtime; (2) A2A federation test with a second vendor's agent; (3) EU AI Act Article 72 post-market monitoring loop operational.

## Pre-requisites

- Stage 24.5 (CTO #5) closed with `production-grade` verdict.

## Acceptance criteria

- [x] (CTO remediation) Low-severity ledger: **G-060 RESOLVED** (pgaudit live, `AUDIT:` lines proven, durable Dockerfile); **G-061 RESOLVED** (DVC-versioned `data/skills/bearing_overheat_response/skill.yaml`, dvc status clean); **G-067** Langfuse v3 overlay fixed live (CLICKHOUSE_MIGRATION_URL + CLUSTER_ENABLED=false + ENCRYPTION_KEY + MinIO S3 + worker — the overlay had never been started; render verification completed in-stage); **G-070 re-checked, still OPEN** (a2a-sdk 1.1.0 needs httpx>=0.28.1 vs frozen 0.27.2); **G-055/56 drill DONE, still OPEN** (langchain-core 1.x ResolutionImpossible vs pinned langchain 0.3.13 + langgraph 0.2.60 → dedicated dep-refresh increment).

- [x] (CTO remediation) **G-066 FOOTHOLD** — `agents/runtime/shard_router.py`: deterministic sha256 sharding + PG advisory lock (no concurrent double-run) + at-most-once `incident_processed` ledger (no sequential re-run; failed runs release the claim) + warm-first fan-out; LIVE load test 7/7: **8 distinct processed exactly once, 4 dupes suppressed, 6 workers, 50s, 0.16/s**. The test CAUGHT two real defects (worker-thread import-lock deadlock; sequential re-processing) — fixed in-stage. Read-replicas/partitioning/multi-node HA honestly deferred (pilot/cloud, Rule 9).

- [x] (CTO remediation) Deep legs + observability: **nightly `crypto-deep-openssl35` job** added to nightly-evals.yml (debian:trixie OpenSSL 3.5.6; a skip of the deep tests there = FAILURE; the >=99% hybrid eval nightly gate already existed); **G-021 RESOLVED** (`api/ops_routes.py` — /ops/cascade + /ops/post-market + HTML, real audit_chain only, honest-503, 4/4 tests); **continuous behavioural anomaly detection SHIPPED as the Art-72 nightly sweep** (robust-Z + IsolationForest over the live chain); the learned/LLM-judge detector tier for prompt_guard (G-077) remains OPEN → detector-hardening increment.

- [ ] **DEFERRED (buyer-blocked, by design)** — (CTO remediation) Wire the two go-live safety/identity surfaces AS the pilot deploys (pilot-deployment-runbook.md §4): R4 = live containerised hybrid-mTLS client-cert→peer_state binding for A2A to make the endpoint AUTHENTICATED, not just RBAC-confined (close G-4/G-064 Network pillar); R5 = re-run validate() from contract+world_state inside sil_bridge.execute (or verify a signed Decision) for the FIRST real PLC caller + wire the VDA dispatch path to its named SIL contract (battery/path/zone) not just the structural gate (close G-075).

- [ ] **DEFERRED (buyer-blocked — the single biggest credibility gap, carried honestly)** — (CTO remediation) Run a REAL reference pilot + publish an A/B (G-035/G-043): re-fit all proxy/benchmark models on real site telemetry per compliance/pilot-onboarding-kit.md; convert the Stage-6 sim A/B to real-world evidence. The single biggest fundability/credibility gap. Buildable half (onboarding kit) done in Stage 22.

- [x] **PQC rotation drill (LOCAL live env — no pilot exists, honestly labelled):**
  - [x] `rotate-pqc-keys.sh --key-type identity --grace-hours 24` succeeded (dry-run then real; marker seq 428).
  - [x] No append failed during the drill (seq 427 pre / 428 mid — signing continuity held; 8.4s wall; single-node caveat recorded).
  - [x] Chain verified before (427 rows) and after (428 rows, all 349 post-cutover sigs incl. old-key rows).
  - [x] `audits/STAGE_25_pqc_drill.md` written (PASS, with honest caveats).
- [ ] **DEFERRED (needs a non-internal partner; two-instance federation over real HTTP was already proven at Stage 14/CTO #4)** — A2A federation with a second vendor:
  - A non-internal partner agent (vendor, customer, or LF Agentic AI Foundation reference peer) successfully exchanges signed cards with our pilot.
  - At least one capability invoked successfully across the federation.
  - Documented in `audits/STAGE_25_a2a_federation.md`.
- [x] **EU AI Act Article 72 post-market monitoring loop (rehearsed on the live dev env — no deployed customer):**
  - [x] `/ops/post-market` + `/ops/cascade` surface chain head/rows, sweep verdicts, rotation cadence, per-incident cascades with real latencies (incident-severity + eval-rate panels grow as history accrues).
  - [x] `jobs/post_market_anomaly_sweep.py` — robust-Z + IsolationForest per-day features; 10/10 tests; live run wrote signed `post_market.sweep` seq 427; honest `insufficient_history` on the young (6-day) chain.
  - [x] `compliance/post-market-monitoring/2026-Q3.md` (labelled REHEARSAL — not field evidence).

## Files to CREATE

| Path | Purpose |
|---|---|
| `audits/STAGE_25_pqc_drill.md` | Drill outcome |
| `audits/STAGE_25_a2a_federation.md` | Federation test outcome |
| `compliance/post-market-monitoring/2026-Q4.md` | First post-market report |
| `backend/jobs/post_market_anomaly_sweep.py` | Nightly anomaly detection on audit_chain |
| `frontend-nextjs/src/app/post-market/page.tsx` | Live ops dashboard |

## Files to MODIFY

| Path | Change |
|---|---|
| `compliance/risk-register.md` | Quarterly refresh; new rows for live-ops findings |
| `knowledge-base/KB_18_Governance_Evidence.md` | Article 72 row marked `shipped` |
| `knowledge-base/KB_10_Production_Hardening.md` | Live ops invariants captured |

## KB files this stage updates

- `KB_18_Governance_Evidence.md`
- `KB_10_Production_Hardening.md`
- `KB_13_PQC_Crypto_Strategy.md` (rotation drill evidence)
- `KB_16_A2A_MCP_Protocols.md` (federation evidence)
- `KB_TASK_LOG.md`

## Verification commands

```bash
# PQC drill
bash scripts/rotate-pqc-keys.sh --key-type identity --grace-hours 24
python scripts/verify-audit-chain.py

# A2A federation
docker compose -f docker/docker-compose.a2a.yml up partner-peer
cd backend && pytest tests/a2a/test_federation_external.py -v

# Post-market dashboard
docker compose up -d frontend-nextjs
# Visit http://localhost:3000/post-market
```

## Audit target

- Strict decrease (any lingering theatrical patterns surfaced during live ops drill must be cleaned).

## Role

- Primary: `agentic-governance-engineer` (coordination), `security-pqc-engineer` (rotation drill), `compliance-engineer` (post-market loop)

## Hand-off

- **What is now true:** the Art-72 post-market loop is OPERATIONAL on the live env (nightly signed anomaly sweep +
  quarterly report + /ops dashboards); the PQC identity rotation is drillable end-to-end with continuous chain
  verification (seq 428); pgaudit gives DB-level audit defence-in-depth (G-060); concurrent incident processing is
  exactly-once on a single node (sharding + advisory lock + at-most-once ledger; live load test 8/8 + 4 suppressed);
  the deep crypto suite is nightly-gate-enforced on OpenSSL 3.5; procedural memory is DVC-versioned (G-061); the
  Langfuse v3 overlay is live-startable (G-067 fixes: migration URL, single-node clickhouse, encryption key, MinIO S3,
  worker). Dep-refresh drill recorded: a2a-sdk (G-070) + langchain-core 1.x (G-055/56) both remain pin-blocked ->
  dedicated dep-refresh increment.
- **Honest deferrals (buyer/pilot-blocked, unchanged):** real pilot + published A/B (R1/G-035/G-043); go-live mTLS +
  sil_bridge wiring (R2/G-4/G-075); accredited certification (R3/G-011); EU provider obligations (R4); external
  federation partner. G-077 learned-detector tier open.
- **Next:** Stage 26 — complete supply-chain automation (`tasks/STAGE_26_supply_chain_automation.md`), then 27
  (resilience & anti-fragility), 28 (GraphRAG + adoption UX) per ADR `2026-07-02_strategic_audit_and_post_ga_roadmap.md`.
  CTO-checkpoint cadence continues (next around Stage 30).
