---
name: Production Hardening
description: Secrets, MLOps, monitoring, CI/CD, drift detection, reliability targets, latency budget, EU AI Act + NIST RMF controls, PQC posture, A2A trust boundary, evidence retention
type: spec
last-updated: 2026-05-18
---

> **Stage 1 close (2026-05-11)** — secrets policy (env vars, no hardcoded
> creds in compose), CI gate (`.github/workflows/ci.yml`: audit + KB-diff
> + gitleaks + model-card + tests), Git LFS rules for weights
> (`.gitattributes`), and the audit baseline (`.audit-baseline = 441`
> initial; 439 post-Stage-1) are all now in effect. Each later stage must
> reduce the audit count (or hold flat only on explicitly-marked
> non-reducing stages with `--no-baseline-drop` justification).

> **2026-05-18 PRD v2.0 expansion.** This file gains three new pillars:
> **(1) PQC posture** — every external boundary uses hybrid TLS
> (ML-KEM-768 + X25519) terminated at an oqs-provider sidecar; every signed
> artefact uses ML-DSA-65; firmware/long-trust artefacts use
> SLH-DSA-SHA2-128s; OT message integrity uses HMAC-SHA-384. CNSA 2.0
> deadline 2027-01-01 drives the rotation plan in `KB_13`.
> **(2) Evidence retention** — `audit_chain` (Postgres, append-only,
> ML-DSA-65 signed) is the EU AI Act Art. 12 evidence sink; Langfuse traces
> (90-day mutable) are debug-only and separate by design. See `KB_15`.
> **(3) A2A trust boundary** — external peers reach the agent only via
> A2A (ML-DSA-signed agent cards, mTLS at sidecar). External peers do
> NOT get MCP-level tool surface access. See `KB_16`.

> **Audit gate extensions (Stage 13.5+):** new forbidden patterns —
> `nacl.signing`, `RSA-`, `ECDSA-` (in new code), `SecureRandom`
> placeholders, `# TODO replace`. Plus: every actuator-bound test must
> show a `safety.validate.*` OTel span before the `actuator.*` span
> (Stage 17 CI gate).

# KB_10 — Production Hardening

## Purpose
Every cross-cutting invariant the build must respect: latency budget, secrets policy, CI gate, observability, compliance scaffolding. If a feature crosses a boundary defined here, this file is consulted before merge.

## Source of truth
- `docker/docker-compose.yml`, `.env.example`, `docker/secrets/`
- `.github/workflows/ci.yml`
- `scripts/audit.sh`
- `compliance/` folder (EU AI Act + NIST RMF scaffolding)

## 1. Latency budget (the critical invariant)

PRD §1.3 SLA: <500 ms decision latency p95. Per-hop budget:

| Hop | Budget (ms) | Notes |
|---|---|---|
| WS ingress | 5 | uvloop + binary frames |
| World-model fwd | 40 | LSTM batch=1 on CPU |
| PPO action | 15 | MlpPolicy CPU inference |
| SHAP cached | 20 | Redis hit; miss = async backfill, don't block decision |
| LLM (Groq) | 120 | streaming first-token; remaining tokens stream async |
| TTS streamed | 0 | perceived; produced async during playback |
| WS egress | 5 | broadcast fanout |
| **Total p95** | **205** | **~295 ms headroom** before SLA breach |

Stages 4–11 each have an acceptance criterion: must not regress p95 latency past budget. Stage 14 adds a load test confirming the budget at 10K concurrent WS clients.

## 2. Secrets policy

- **No secret ever lives in git** (current `aiagent2026` in `docker-compose.yml` is removed Stage 1).
- `.env.example` lists every required variable with `EXAMPLE_VALUE_REPLACE_ME` stubs.
- Local dev: operator copies `.env.example` → `.env.local`, fills in real values, gitignored.
- Docker compose: every credential references `${VAR_NAME}` and is loaded from `.env.local`.
- CI: secrets injected via GitHub Actions encrypted secrets; never echoed to logs.
- Production: secrets manager (1Password CLI, Doppler, or cloud-provider equivalent — TBD pre-pilot).
- `gitleaks detect` runs on every PR; merge blocked on hit.

## 3. CI/CD gate (Stage 1 introduces; tightens every stage)

`.github/workflows/ci.yml` enforces, on every PR to `main`:

1. **Lint** — ruff + black for Python; ESLint + Prettier for TS/TSX.
2. **Types** — mypy (Python; opt-in per module); tsc --noEmit for frontend.
3. **Tests** — pytest backend; vitest/jest frontend; coverage gate ≥60% from Stage 4 onward.
4. **Audit script** — `scripts/audit.sh` returns 0 (mock-fallback count strictly less than prior stage baseline).
5. **Secrets scan** — gitleaks detect.
6. **Docker build** — every service image builds and starts (health check).
7. **KB diff** — if the PR touches `backend/` or `frontend-nextjs/`, at least one file under `knowledge-base/` must also be touched. Enforced via a custom check.
8. **Model card check** — if the PR adds a `*.pt` / `*.pth` / `*.onnx` file under `weights/`, sibling `*.metrics.json` + `*.card.md` must exist.
9. **SBOM generation** (Stage 14) — cyclonedx or syft on every built image.

## 4. Observability (Stage 14 lights up; Stage 1 scaffolds)

- **Metrics** — Prometheus scrape; per-endpoint latency, decision throughput, model inference time, queue lengths.
- **Logs** — `structlog` → Loki.
- **Traces** — OpenTelemetry → Jaeger. Every coordination cycle is one trace; sub-agent proposals are spans.
- **Dashboards** — Grafana, provisioned via code in `docker/grafana/`.
- **Model registry** — MLflow. Every weight ships with a model card; MLflow tracks runs.
- **Drift detection** — rolling KS test on production input distributions vs training; alert when drift > threshold; auto-create a retraining ticket.
- **Circuit breakers** — around every external call (Groq, Gemini, weather, carbon-intensity API).

## 5. Reliability targets

- **Backend uptime** — 99.5% (PRD).
- **WS reconnect** — auto with exponential backoff; resume from current state, not fresh.
- **Postgres** — **SHIPPED Stage 21** (free/OSS/local, research §31): `pg_dump -Fc` + `pg_basebackup` (PITR anchor) via
  `scripts/backup/`; **tested restore** (`scripts/restore/restore-verify.sh` restores to a scratch DB + asserts row-count +
  `audit_chain` head parity — **RTO ~4 s** for the current DB), retention + SHA-256 manifest, 3-2-1 layout
  (`BACKUP_ROOT_2` second medium + config-only off-site). Continuous WAL archiving for PITR (RPO ≤ 60 s) is
  config-provided/OFF (enable per the docker-compose comment at pilot). Multi-node HA/failover = pilot/cloud (Rule 9).
  Full procedure: `compliance/dr-runbook.md`. (Supersedes the earlier "pgBackRest @ Stage 14" placeholder — pgBackRest
  is a heavier install; the built-in `pg_dump`/`pg_basebackup` path is the honest free choice.)
- **Resilience (chaos)** — `scripts/chaos/kill-postgres-drill.sh`: kills PG, asserts HONEST degradation (no fabrication)
  + recovery on restart (G-004). CI gate `dr-backup-restore` runs backup+restore-verify every PR.
- **Model artifacts** — Git LFS retention; pinned by content hash; old weights kept for 90 days then archived.
- **Incident response** — `compliance/incident-playbook.md` (Stage 1 scaffolds; iterated as we learn).
- **Pilot deployment (Stage 22)** — `compliance/pilot-deployment-runbook.md`: SRE production-readiness gate
  (pre-flight checks → shadow/assisted/supervised-autonomous canary → rollback criteria+steps+owner) + the EU-AI-Act
  Art-26 deployer checklist + the go-live wiring of the not-yet-load-bearing safety/identity surfaces (R4/R5). Pairs with
  the DR runbook (recovery half). **Art-72 post-market monitoring**: `compliance/post-market-monitoring-plan.md`
  (ingested into the Annex IV pack). **Pilot onboarding**: `compliance/pilot-onboarding-kit.md` (data-intake + A/B
  protocol + real-fleet re-fit plan; the real customer pilot + published A/B remain deferred — need a buyer, G-035/G-043).
- **DB least-privilege (Stage 22, R8)** — the app connects mem0 as a NON-superuser `mem0_app` LOGIN role (migration
  0009) so Postgres FORCE RLS is enforced by the connection role, not best-effort `SET ROLE`. **Audit-chain test-isolation
  (R1)** — `AUDIT_CHAIN_DATABASE_URL` + a conftest fixture keep test runs off the attestable chain.

## 6. WebSocket production constraints

(Per refresh research finding #9; lands in Stage 3 acceptance):

- **uvloop mandatory** — single worker ≈ 10K concurrent WS without it ≈ half.
- **Multi-worker requires Redis pub/sub broker** — workers fan messages out via Redis; NGINX `ip_hash` keeps clients on the same worker.
- **Async-only inside WS handlers** — CI lint rule forbids any sync DB call. One sync call freezes the whole worker.
- **Backpressure** — drop stale frames when a client is slow; never queue unbounded.

## 7. Data versioning

- **DVC** tracks every dataset under `data/datasets/`.
- Each dataset has a `CARD.md` with license, source URL, size, SHA256, mirror URL, download command, intended model, known limitations.
- CI rejects training runs that reference an un-versioned dataset.
- Mirror policy: if upstream URL has 404'd at any point, pin to HuggingFace Hub mirror.

## 8. EU AI Act compliance scaffolding (Stage 1 creates; Stage 14 fills out)

(Per refresh §6.7.1 in `research/initial-research.md`.)

`compliance/` folder contents:
- `risk-register.md` — Annex III high-risk classification + per-component risk class.
- `model-cards/<model>.md` — Art. 11 technical documentation evidence (Annex IV shape).
- `decision-logs/` — Art. 12 automatic logging output; Postgres-backed; 6-month retention via partitioning.
- `human-oversight.md` — Art. 14 UI hand-off spec; operator override semantics.
- `incident-playbook.md` — Art. 26 deployer incident response; OWASP LLM Top 10 controls.

Hard deadline: **2 Aug 2026** for high-risk systems in scope of an EU customer. Our model: scaffold structure now, fill out as pilots demand.

## 9. NIST AI RMF Agentic Profile controls (Stage 1 scaffolds; Stage 11 + 14 enforce)

(Per refresh §6.7.2.)

- **Prompt-injection sanitizer** on every tool output before LLM context.
- **Cross-session memory namespacing** by `incident_id`; clear on session boundary.
- **Tool-chain provenance** — every action records `(caller, tool, input_hash, output_hash)`. Doubles as Art. 12 evidence.
- **Excessive agency** mitigation — PPO safety-constraint reward shaper (Stage 7); operator override surface (Stage 12); the agent cannot take an action class without explicit human approval (configurable per pilot).

## 10. Failure-mode fallbacks

- **Colab session dies** → notebook is mirrored to Kaggle; same kernel runs without reconfiguration.
- **Dataset URL 404** → HuggingFace Hub mirror per `KB_03`.
- **Groq outage** → Ollama-local LLM (Stage 11).
- **Frontend stack churn** → pinned LTS (Next 15.x / React 18.3 / Tailwind 3); no canaries on `main`.

## Last verified
- 2026-06-21 (Stage 18) — **PQC hardening posture is LIVE** (KB_13): every external boundary fronted by an OpenSSL-3.5
  hybrid-TLS sidecar (X25519MLKEM768 + ML-DSA-65 cert — verified handshake); long-trust artefacts (firmware/policy/all 7
  model cards) SLH-DSA-SHA2-128s signed; 4-key-type crypto-agile rotation drill working; `audit.sh` classical-crypto
  gate; CycloneDX SBOM + documented dependency-exception (G-065). bandit SAST blocking. ADR `2026-06-21_stage18_pqc_wave2.md`.
- 2026-05-11 — Plan-mode session. All bullets here are forward commitments; Stage 1 creates the scaffolding files; Stage 14 finishes the runtime instrumentation.

## Stage 25 — post-GA live-ops invariants (2026-07-03)

- **Art-72 loop:** the nightly anomaly sweep (`jobs/post_market_anomaly_sweep.py`) must write a signed
  `post_market.sweep` audit row per real run; it reports `insufficient_history` (no anomaly claim) below 14 days of
  chain data — a fabricated score is a Rule-1a violation. CLI exits 2 on anomalies (cron-alertable).
- **Exactly-once incident processing:** all concurrent entry goes through `agents/runtime/shard_router.py` —
  PG advisory lock (no concurrent double-run) + `incident_processed` at-most-once ledger (no sequential re-run;
  failed runs release the claim). Load-proven: 8 distinct exactly-once + 4 suppressed, 6 workers (2026-07-02).
  Invariant to protect: heavy model imports must resolve in the MAIN thread first (warm-first) — worker-thread lazy
  imports deadlock on the import lock (Stage-11.5/Stage-25 precedent).
- **pgaudit:** `pgaudit.log='write, ddl, role'` on the manufacturing DB (DB-level defence-in-depth under the signed
  app-level audit_chain); container recreation must use `docker/postgres-pgaudit.Dockerfile`.
- **PQC rotation drillable:** identity rotation verified live 2026-07-02 (marker seq 428, chain green before/after);
  re-run per-quarter and at pilot go-live.
- **Test isolation of the attestable chain:** independently re-proven 2026-07-03 — the real chain head was unchanged
  (428) across a full adversarial suite re-run (AUDIT_CHAIN_DATABASE_URL + throwaway-DB conftest).

## Stage 27 — resilience & anti-fragility invariants (2026-07-04)

- **Durable external effects.** Every external effect (actuator / A2A / OT / order dispatch) should run through the
  durable primitives (`backend/agents/runtime/durable/`): `EffectLedger` (at-most-once claim table — DB-durable
  across workers, replay returns the recorded outcome), `CircuitBreaker` (CLOSED/OPEN/HALF_OPEN per dependency;
  OPEN raises `CircuitOpenError` — HONEST degradation, never a fabricated fallback; every transition = a signed
  audit row), `Saga` (per-step idempotency keys + reverse compensation; a compensation past its retry budget
  surfaces STUCK — named, never swallowed).
- **Workload identity.** SPIRE issues short-lived rotating SVIDs; the A2A boundary authenticates peers by SPIFFE ID
  over mTLS. Rotation is zero-downtime (new serial, constant identity) — re-run `scripts/spire/rotate-svid-drill.py`
  at pilot cadence.
- **Chaos-as-anti-fragility.** `scripts/chaos/circuit-breaker-drill.py` proves graceful degradation + self-recovery;
  the audit chain must verify after any drill (breaker rows are real evidence).
