# ADR — Stage 25: Post-GA Operations (Art-72 loop live, PQC drill, scale foothold, ledger closures)

- **Date:** 2026-07-02
- **Status:** Accepted
- **Stage:** 25 (`tasks/STAGE_25_post_ga.md`) — first post-GA build increment; carries CTO #5 remediations R5/R6/R7.
- **Roles:** `agentic-governance-engineer` (coordination) + `compliance-engineer` (Art-72) + `security-pqc-engineer`
  (rotation drill) + `devops-sre` (pgaudit/Langfuse/scale).
- **Research:** `research/initial-research.md §36` (Art-72 template status, lightweight anomaly detection, pgaudit
  policy, PgBouncer/worker-scaling guidance) — appended BEFORE implementing (Hard Rule 11).

## Context

GA v1.0.0 closed the build (CTO #5: "GA is real and honest", zero must-fix). Stage 25 converts the released platform
into an OPERATED one: the EU-AI-Act Article-72 post-market loop must actually run, the crypto lifecycle must be
drillable, concurrent load must be safe, and the long-carried low-severity ledger items (G-021/055/060/061/066/067/070)
must be paid or honestly re-ledgered with evidence. The buyer-blocked ACs (real pilot R1, go-live wiring R2, external
federation partner) are DEFERRED by design, not faked — they need a customer.

## Decisions & outcomes (every number produced by a live command this session)

1. **Art-72 post-market loop OPERATIONAL (rehearsed honestly on the live dev env — no deployed customer exists):**
   `backend/jobs/post_market_anomaly_sweep.py` — per-day audit_chain feature matrix (counts/action, distinct actors,
   governance deny-rate) → robust-Z (Iglewicz–Hoaglin |z|≥3.5) + sklearn IsolationForest; **honest-empty below 14 days
   of history**; each run appends a signed `post_market.sweep` row + JSON report. Live: **10/10 tests; real sweep wrote
   seq 427; verdict `insufficient_history` (6-day chain) — the honest output, not a fabricated score.** Quarterly report
   `compliance/post-market-monitoring/2026-Q3.md` (labelled REHEARSAL). CLI exit 2 on anomalies for cron alerting.
2. **pgaudit (G-060 RESOLVED):** live on the Docker PG (`pgaudit.log='write, ddl, role'`, parameters on; persisted in
   `postgresql.auto.conf`); PROVEN — probe CREATE/INSERT/DROP produced 3 `AUDIT:` lines; durable via
   `docker/postgres-pgaudit.Dockerfile`. DB-level defence-in-depth under the app-level signed audit_chain.
3. **PQC identity-rotation drill (local live env):** dry-run then real (`--key-type identity --grace-hours 24`);
   **marker seq 428; chain verified before (427) and after (428, all 349 post-cutover sigs incl. old-key rows); 8.4s
   wall; no append failed.** `audits/STAGE_25_pqc_drill.md` (PASS with single-node caveats).
4. **Scale foothold (G-066 FOOTHOLD; tail deferred):** `agents/runtime/shard_router.py` — deterministic sha256
   sharding + PG advisory lock (no CONCURRENT double-run) + **at-most-once `incident_processed` ledger** (no SEQUENTIAL
   re-run; failed runs release the claim → retryable) + warm-first fan-out + per-future timeouts. **Live load test 7/7:
   8 distinct incidents processed exactly once, 4 duplicates suppressed, 6 workers, 50s, 0.16 incidents/s (a laptop
   measurement, not an SLA).** The test's FIRST run CAUGHT two real defects, fixed in-stage: (a) worker-thread
   import-lock deadlock on the lazy model imports (same class as the Stage-11.5 FastMCP deadlock) → warm-first;
   (b) sequential re-processing after lock release → the at-most-once ledger. Multi-node HA/read-replicas → pilot/cloud.
5. **Ops cascade view (G-021 RESOLVED):** `api/ops_routes.py` — `/ops/cascade` (per-incident decision cascades with
   REAL inter-row latencies) + `/ops/post-market` + self-contained HTML; reads ONLY the signed audit_chain (never the
   G-082 legacy path); honest-503 without DB; 4/4 tests incl. live legs.
6. **Nightly deep-crypto gate (R5):** `crypto-deep-openssl35` job appended to `nightly-evals.yml` (debian:trixie-slim,
   OpenSSL 3.5.6) — the FULL crypto suite runs nightly and **a skip of the deep tests on that runner is a failure**;
   complements the per-PR job (Stage 22 R6) + the existing nightly ≥99% hybrid eval gate. The learned/LLM-judge
   detector tier (G-077) stays OPEN.
7. **Procedural memory (G-061 RESOLVED):** first DVC-versioned skill `data/skills/bearing_overheat_response/skill.yaml`
   (a real playbook naming the live module per step); pointer git-tracked; `dvc status` clean. Trade recorded:
   `pathspec` pinned 0.12.1 for dvc 3.58 — breaks the locally-installed `black` (dev-only, unused by CI).
8. **Langfuse UI (G-067 RESOLVED):** v3.203.3 VERIFIED LIVE — health `{status:OK}` + UI HTTP 200 on :3001. The overlay
   had never been started; the first live run surfaced 4 real config gaps, fixed in `docker-compose.observability.yml`:
   `CLICKHOUSE_MIGRATION_URL`, `CLICKHOUSE_CLUSTER_ENABLED=false`, `ENCRYPTION_KEY`, and the v3-mandatory S3 blob store
   (new MinIO container) + `langfuse-worker`.
9. **Dep-refresh drill (G-055/56 + G-070, both remain OPEN with evidence):** a2a-sdk 1.1.0 still requires
   `httpx>=0.28.1` vs frozen 0.27.2; langchain-core 1.x is **ResolutionImpossible** against pinned langchain 0.3.13 +
   langgraph 0.2.60 → both need one dedicated, coordinated dependency-refresh increment.
10. **Ops-environment honesty fixes:** the mem0 default embedder (bge-large) had a corrupted/incomplete HF cache blob
    that stalled any embedder-touching test via the flaky xet transport → purged + re-fetched with
    `HF_HUB_DISABLE_XET=1`; load/scale tests run HF-offline-hermetic so a network stall can never masquerade as a
    concurrency defect.

## Consequences

- Audit baseline **holds 364** (`--no-baseline-drop`: ops/compliance/infra stage; additive real code; no de-mock
  surface — the legacy de-mock is Stage 28's job per ADR `2026-07-02_strategic_audit_and_post_ga_roadmap.md`).
- New deps: **none** (pathspec re-pin only). Rule 9 (free/local/OSS) held — MinIO/Langfuse/pgaudit all free OSS.
- Deferred honestly (buyer/pilot-blocked): R1 real pilot + A/B (G-035/G-043), R2 go-live mTLS + sil_bridge wiring
  (G-4/G-075), R3 accredited cert (G-011), R4 EU provider obligations, external federation partner, G-077 detector tier.
- Next executable: **Stage 26 — complete supply-chain automation**, then 27/28 per the strategic-reset ADR.

## References
- `tasks/STAGE_25_post_ga.md` · research §36 · `audits/STAGE_25_pqc_drill.md` ·
  `research/stage-explainers/STAGE_25/index.html` · `audits/OPEN_GAPS_LEDGER.md` (G-021/055/060/061/066/067/070 rows
  updated) · `compliance/post-market-monitoring/2026-Q3.md` · CTO #5 remediation map (R5/R6/R7 paid; R1–R4 deferred).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v2 -->
<!-- signed_at: 2026-07-03T12:51:15+00:00 -->
<!-- signature: 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 -->
