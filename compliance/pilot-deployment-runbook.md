# Pilot Deployment Runbook (Stage 22)

> Production-readiness-review (PRR) + EU-AI-Act **deployer** runbook for a first closed pilot. Free/OSS/local through
> build (Rule 9); the actual customer engagement (real fleet, published A/B) is the post-build pilot — see
> `compliance/pilot-onboarding-kit.md`. Pairs with the DR/recovery half in `compliance/dr-runbook.md` (Stage 21).
> Research §32; ADR `2026-06-22_stage22_pilot_deployment_runbook.md`. KB_10/KB_15/KB_18.

## 0. Pre-flight gate (must ALL be green before a pilot deploy)

| Gate | How to check | Owner |
|---|---|---|
| Audit chain green | `python scripts/verify-audit-chain.py` → exit 0 | security-pqc |
| Backups + tested restore | `bash scripts/backup/backup-all.sh && bash scripts/restore/restore-verify.sh` → PASS | devops-sre |
| Red-team gate | `cd backend && python training/evals/runner.py --corpus all --gate` → PASS (+ nightly hybrid ≥0.99) | ml-eng |
| Safety trace-pairing | CI `safety-contract-tests` green (every `actuator.*` preceded by `safety.validate.*`) | robotics-int |
| SBOM + SAST | CI `sbom` (blocking) + `bandit` green | security-pqc |
| Annex IV pack builds | `python scripts/generate-annex-iv-doc.py` → 14 sections + PMM plan + signed footer | compliance |
| DB least-privilege | app connects as a non-superuser role; mem0 RLS fail-closed (Stage 22 R8) | backend |
| Full suite | `cd backend && pytest -q` green | all |

A red gate blocks the pilot. **G-1 (chain green) and G-2 (register refreshed) are hard pre-pilot gates** (CTO #4).

## 1. Deployment strategy (SRE PRR)

- **Topology:** the `docker/docker-compose.yml` stack (Postgres pgvector, Neo4j, Redis, MQTT, backend, simulation) +
  overlays as needed (`docker-compose.observability.yml`, `.pqc.yml`, `.a2a.yml`). Single-node for the pilot (multi-node
  HA = G-066, post-pilot).
- **Staged rollout (canary):** deploy to a **shadow/observation** posture first — the agent runs the full
  predict→diagnose→verify loop and RECORDS recommended decisions WITHOUT actuating (HITL approval required; no live
  actuator wired yet, §4). Promote to **assisted** (operator approves each action) only after the shadow A/B looks sane,
  then to **supervised-autonomous** for low-SIL actions. Never skip straight to actuation.
- **Verification checks after deploy:** `/health` + `/ready` 200; `verify-audit-chain.py` exit 0; a synthetic incident
  through `run_incident` produces a full trajectory + a signed audit row; OTel spans flowing to the collector.
- **Rollback criteria:** any safety-validate bypass, any audit-chain verify failure, sustained SLO breach (below), or a
  red-team regression in nightly. **Rollback steps:** `docker compose down` the new tag → restore the pre-deploy DB
  snapshot (`scripts/restore/restore-verify.sh` then the §5 recovery in the DR runbook) → redeploy the prior image tag →
  re-run the pre-flight gate. **Named decision owner:** the on-call SRE (below) decides go/rollback.

## 2. SLOs (pilot draft)

| SLO | Target | Source |
|---|---|---|
| Backend API availability | 99.5% (PRD) | `/health` probe |
| Decision-loop p95 latency | < 5 s per incident | `ml.inference.*` + `langgraph.node.*` spans |
| Audit-chain integrity | 100% (verify exit 0, continuous) | `verify-audit-chain.py` (scheduled) |
| Red-team OWASP-LLM01 refusal | ≥ 0.99 (nightly hybrid) | `nightly-evals.yml` |
| RPO / RTO | ≤ 60 s (PITR) / < 5 min | DR runbook (Stage 21) |

## 3. EU AI Act — Deployer obligations checklist (Article 26)

The pilot operator is a **deployer** of a high-risk AI system. Binding for high-risk: **2 Aug 2026**.

- [ ] **Use per instructions-for-use** — operate within the documented operating envelope (Annex IV §intended-purpose).
- [ ] **Human oversight by competent persons** — HITL approval on SIL-1+ decisions is wired (`runtime/hitl.py`,
      Stage 17); name + train the overseers.
- [ ] **Monitor operation** — the post-market-monitoring plan (`compliance/post-market-monitoring-plan.md`, Art-72) is
      active; spans + `audit_chain` are the monitoring data.
- [ ] **Input-data governance** — ensure pilot input data is relevant/representative for the intended purpose; log it.
- [ ] **Keep logs ≥ 6 months** — the append-only `audit_chain` (Art-12) + OTel evidence sink satisfy this; confirm
      retention config.
- [ ] **Incident + risk reporting** — on a serious incident or a risk identified in use, **suspend use**, inform the
      provider + market-surveillance authority without undue delay (`compliance/incident-playbook.md`).
- [ ] **Inform affected workers / their representatives** before putting the system into service at the workplace.
- [ ] **Cooperate with authorities** + keep the auto-generated logs available.

## 4. Go-live wiring of the not-yet-load-bearing surfaces (CTO #4 R4/R5 — do AS you go live)

Both are honest placeholders today (no real peer/PLC exists) and flip to **load-bearing the moment the pilot connects a
real one** — they MUST be wired as part of go-live, not deferred again:

- **R5 — `sil_bridge` first-real-PLC hardening (G-075).** Before the first real actuator caller: in
  `backend/safety/sil_bridge.py::execute`, require the self-validating path — re-run `validator.validate()` from
  `contract` + current `world_state` inside `execute` (or verify a signed Decision), so a forged/stale `Decision` cannot
  actuate. Wire the VDA dispatch (`integrations/vda5050/master.dispatch_order`) to its NAMED SIL contract
  (battery/path/zone), not just the structural gate. Acceptance: a forged `Decision(allow=True)` is rejected live.
- **R4 — A2A live mTLS binding (G-4/G-064 Network pillar).** Before EXPOSING the A2A endpoint: run the containerised
  hybrid-mTLS path (`docker-compose.a2a.yml` + `.pqc.yml`) so the client cert binds to `peer_state` on the wire (not
  just compose config); keep the exposed capability set read-only (`skills/forecast_oee`; MCP tools refused) until then.
  Acceptance: an unauthenticated/omitted-cert caller is rejected at the transport, not just the app gate.

## 5. On-call & escalation

- **On-call SRE** (deploy/rollback decision owner) — primary + secondary; escalation to the platform lead.
- **Safety escalation** — any STO/SS1 trip or safety-validate failure pages the robotics-integration owner immediately;
  the line goes to a safe state (Stage 17) before diagnosis.
- **Compliance escalation** — a serious incident triggers the Art-26 reporting path (compliance owner) within the
  regulatory window.
- **Runbook drift** — re-validate this runbook's links + commands each pilot milestone (it is in the Annex IV evidence set).

## 6. Honest scope boundary

- This runbook makes the system pilot-DEPLOYABLE in shadow/assisted posture on a single node, free/local. **Not yet
  done (need a buyer/real fleet / post-build):** the real customer pilot + published A/B (G-035/G-043 — onboarding kit),
  multi-node HA + auto-failover (G-066), live off-site backup replication, and the go-live wiring in §4 (done AS the real
  pilot connects). Conformity is NOT certified — the Stage-23 dry-run + a notified body come next. Nothing here is faked.
