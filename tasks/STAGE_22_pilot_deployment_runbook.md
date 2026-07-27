---
status: not-started
stage: 22
slug: pilot_deployment_runbook
created: 2026-06-26
---

# Stage 22 — Pilot deployment runbook + post-market monitoring + CTO #4 remediations

> The pilot-readiness stage: turn the production-SHAPED system into a pilot-DEPLOYABLE one. Ships (a) an SRE
> production-readiness-review **deployment runbook** (deploy/rollback/canary, SLOs, on-call) + the EU-AI-Act **Article-26
> deployer-obligations checklist**, (b) an **Article-72 post-market-monitoring plan** folded into the Annex IV pack
> (Stage 19), and (c) the doable CTO #4 Stage-22 technical remediations (audit-chain test-isolation R1, register refresh
> R2, SBOM-CI-dedup R3, non-superuser DB role R8, OpenSSL-3.5 CI R6). The REAL customer pilot + published A/B
> (R11/G-035/G-043) and the wire-on-go-live items (R4 A2A live-mTLS, R5 first-real-PLC sil_bridge) are honestly staged
> in the runbook but NOT build-time-completable (need a buyer/real fleet — Rule 9). Research §32; KB_10/KB_15/KB_18.
> Prior: Stage 21.5 (CTO #4) closed with verdict ON TRACK; gate G-1 (audit-chain green) already paid.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_22/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: (list of prior stages this depends on)
- Decision logs honoured: (list of ADRs)
- KB files at minimum version: (list)
- Gaps ledger rows pulled in (IDs): (from `audits/OPEN_GAPS_LEDGER.md`)

## Acceptance criteria

(Folds CTO #4 Stage-22 remediations R1,R2,R3,R6,R8,R11 + ledger G-035/G-043/G-076/G-066. BUILDABLE-NOW vs
DEFERRED-NEEDS-BUYER are separated honestly — a deferred item is staged in the runbook, not faked as done.)

**Buildable now (free/OSS/local):**
- [ ] **AC1 — Pilot deployment runbook.** `compliance/pilot-deployment-runbook.md`: SRE PRR (deploy → verification → rollback criteria → rollback steps + named decision owner), canary/staged rollout, SLO draft, on-call/escalation, security-scan + capacity gates, links to the DR runbook (Stage 21).
- [ ] **AC2 — EU AI Act deployer + post-market monitoring.** `compliance/post-market-monitoring-plan.md` (Art-72) + an Art-26 deployer-obligations checklist; the PMM plan is INGESTED into the Annex IV pack (`scripts/generate-annex-iv-doc.py`) so the pack carries it (Art-72 ↔ Annex IV). Regenerate + verify the section appears.
- [ ] **AC3 — R3: de-duplicate the shadowed `sbom:` CI job.** `.github/workflows/ci.yml` has two `sbom:` jobs (YAML last-wins drops the Stage-18 blocking one). Keep exactly one blocking SBOM job; fold in the doc-drift fixes (cyclonedx pin 7.3.0; risk-register "BLOCKING pip-audit" wording; KB_13 hybrid-TLS assertion). Verify only one `sbom:` key remains.
- [ ] **AC4 — R8/G-076: non-superuser app DB role.** A migration + compose/env so the app connects as a NON-superuser role by default, so mem0 RLS holds even if a code path forgets `SET ROLE` (keep `_authorize` as the first gate). Verify a direct app-role client is fail-closed WITHOUT the per-op `SET ROLE`.
- [ ] **AC5 — R1/G-1: durable audit-chain test-isolation.** Stop test runs polluting the attestable chain (a test-isolated audit DB / a `pytest` fixture that points `audit_chain` at a throwaway DB, OR a dedicated keystore). Verify: run the suite, then `verify-audit-chain.py` on the real DB still exits 0.
- [ ] **AC6 — R2: risk-register refresh @ checkpoint.** Add/refresh rows (live-chain re-attestation, SBOM-dedup, A2A interim-unauth, G-075, G-078) + update Last-reviewed.
- [ ] **AC7 — R6: OpenSSL-3.5 CI (crypto/full-hybrid gate).** Add an OpenSSL-3.5 CI container (or scheduled host runner) so SLH-DSA + hybrid-TLS + the full-hybrid OWASP eval are gate-enforced, not only nightly. (If infeasible free, document honestly + keep nightly.)
- [ ] **AC8 — Tests + audit.** New tests pass live; `bash scripts/audit.sh` holds/decreases (`--no-baseline-drop` justified if flat).

**Deferred (staged in the runbook; NOT build-time-completable — needs a buyer/real fleet, Rule 9):**
- [ ] **AC9 — Pilot-onboarding kit (the buildable half of R11/G-035/G-043).** A pilot-onboarding checklist + data-intake + A/B-measurement template + the real-fleet re-fit PLAN — so a real engagement can start day-one. The actual customer pilot + published A/B is the post-build engagement (honestly deferred, ledgered).
- [ ] **AC10 — Go-live wiring documented (R4/R5).** The runbook specifies EXACTLY how A2A live-mTLS binding (R4) + first-real-PLC `sil_bridge` contract hardening (R5) are wired as the pilot goes live (with the code touch-points), since both flip to load-bearing the moment a real peer/PLC connects.

## Files to CREATE

| Path | Purpose |
|---|---|
| `compliance/pilot-deployment-runbook.md` | SRE PRR deploy/rollback/canary + SLO + on-call + Art-26 deployer checklist + go-live wiring (R4/R5) |
| `compliance/post-market-monitoring-plan.md` | EU AI Act Art-72 PMM plan (ingested by the Annex IV pack) |
| `compliance/pilot-onboarding-kit.md` | Pilot onboarding + data-intake + A/B-measurement template + real-fleet re-fit plan (R11 buildable half) |
| `backend/alembic/versions/0009_*.py` | Non-superuser app role + grants for mem0 RLS (R8/G-076) |
| `backend/tests/.../test_audit_chain_test_isolation.py` | Prove test runs don't pollute the attestable chain (R1/G-1) |

## Files to MODIFY

| Path | Change |
|---|---|
| `.github/workflows/ci.yml` | R3: remove the shadowed duplicate `sbom:` job; R6: add OpenSSL-3.5 crypto/eval gate |
| `scripts/generate-annex-iv-doc.py` | Ingest the post-market-monitoring plan (Art-72 ↔ Annex IV) |
| `backend/memory/mem0_adapter.py` / `backend/tests/conftest.py` | Non-superuser role default (R8) + audit-chain test-isolation fixture (R1) |
| `compliance/risk-register.md` | R2 refresh: new rows + Last-reviewed |
| `knowledge-base/KB_18_Governance_Evidence.md` / `KB_10_Production_Hardening.md` | Art-26/72 + PMM + pilot runbook |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | additive docs/config/migration stage |

## KB files this stage updates

(The KB-diff CI gate enforces these. Every listed file must have a non-trivial diff in the closing PR.)

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_NN_<topic>.md`

## Verification commands

```bash
# Audit baseline strictly decreases (or hold with explicit --no-baseline-drop justification)
bash scripts/audit.sh

# Tests pass
cd backend && pytest -q
cd frontend-nextjs && npm test && npm run build

# Stage-specific
```

## Audit target

- Pre-stage baseline: (capture from `.audit-baseline` at stage open)
- Target: (strictly less than pre-stage; specify expected drop and which patterns fall)

## Role

- Primary: (per CLAUDE.md §3 decision tree — `backend-engineer` / `ml-engineer` / ... )
- Secondary (hand-offs): (list)

## Risks / unknowns

(Append-only as the stage progresses. Convert resolved items to ADRs in `compliance/decision-logs/`.)

-

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-06-26T13:56:51Z)

### Suggested role (from slug heuristic)

**agentic-governance-engineer** — open `.claude/skills/agentic-governance-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_06_Agent_Coordination_Protocol.md`
- `knowledge-base/KB_18_Governance_Evidence.md`
- `knowledge-base/KB_README.md`
- `knowledge-base/KB_TASK_LOG.md`

### Pre-requisites (from previous stage's hand-off — STAGE_21_dr_ha_backups.md)


- What is now true that wasn't before this stage:
  -
- What the next stage starts with:
  -
- Open items deferred to a future stage (name the stage if known):
  -

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### CTO checkpoint remediations targeting this stage (auto-routed)

- (from CTO_2_remediation_map.json) Add dependency provenance for the expanded OSS surface: hash-pinned lockfile + SBOM (causal-learn, dice-ml, stable-baselines3, sb3-contrib, gymnasium; dice-ml pulls TensorFlow); document the tts<2.0 breakage from the pandas pin
- (from CTO_2_remediation_map.json) Carry forward the un-converted credibility constraints: real-fleet re-fit of all proxy/benchmark models (G-035) + a real pilot (G-043)
- (from CTO_3_remediation_map.json) Carry forward the still-not-yet-due credibility constraints: real-fleet re-fit of all proxy/benchmark models (G-035) + a reference pilot with a published A/B (G-043)
- (from CTO_4_remediation_map.json) Re-attest the live audit_chain to a green verify-audit-chain.py (exit 0) AND fix the recurring test-key pollution durably (a production keystore / a test-isolated audit DB so test runs never pollute the attestable chain) � G-1/G-079/G-073-follow-up.
- (from CTO_4_remediation_map.json) Refresh compliance/risk-register.md at this checkpoint: rows for the live-chain re-attestation gap, the duplicate-SBOM-job CI defect, the A2A interim-unauth gate, G-075 sil_bridge forgeable residual, G-078 silent-Neo4j-restart; update Last-reviewed � G-2.
- (from CTO_4_remediation_map.json) De-duplicate the sbom: CI job so the Stage-18 blocking SBOM gate is the one CI runs; fold in the LOW doc-drift fixes (cyclonedx pin agreement 7.3.0; risk-register row 'BLOCKING pip-audit' correction; KB_13 hybrid-TLS test-assertion wording) � Stage-18 F1-F5 / G-3.
- (from CTO_4_remediation_map.json) Before any exposed pilot, make the A2A peer gate load-bearing: a LIVE containerised hybrid-mTLS run that binds the client cert -> peer_state (not just compose config); keep the exposed capability set read-only until then � G-4/G-064 Network pillar.
- (from CTO_4_remediation_map.json) Harden sil_bridge.execute against forgery/TOCTOU for the FIRST real PLC caller: re-run validate() from contract+world_state inside execute (or sign the Decision and verify in the bridge), and wire the VDA dispatch path to its named SIL contract (battery/path/zone) not just the structural gate � G-075 / Stage-17 F2.
- (from CTO_4_remediation_map.json) Add an OpenSSL-3.5 CI container (or a scheduled host runner) so SLH-DSA + the hybrid-TLS handshake + the full-hybrid OWASP-LLM01 eval (0.99 target) are GATE-enforced on PRs, not only host/nightly-verified � Cross-cutting #3.
- (from CTO_4_remediation_map.json) Build the live message-cascade / latency observability UI (agent->head->embodied->head->agent, per-hop latency + decision) on top of the existing spans � G-021 (CTO #3 R6 unbuilt half).
- (from CTO_4_remediation_map.json) Connect the app as a NON-superuser DB role by default so mem0 RLS holds even if a code path forgets SET ROLE; keep _authorize as the first gate � G-076.
- (from CTO_4_remediation_map.json) Add recurring detector-hardening + CONTINUOUS (runtime) behavioural anomaly detection: a learned/LLM-judge tier to lift indirect/multilingual recall + tune the semantic threshold to drop the benign FP; close the input-tier physical-safety residual � G-077 / G-064 continuous-anomaly tail.
- (from CTO_4_remediation_map.json) Real-fleet re-fit of all proxy/benchmark models (G-035) + a reference pilot with a published A/B (G-043) � the single biggest fundability/credibility gap.
- (from CTO_4_remediation_map.json) Carry the still-open low/medium ledger items forward and close at their stages: G-066 horizontal-scale hardening; G-021 cascade UI (R7); G-060 pgaudit; G-061 DVC procedural memory; G-067 Langfuse UI; G-070 a2a-sdk; G-055/G-056 langchain-core 1.0 dependency-refresh drill.


These items MUST appear as acceptance criteria above.

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-012: **Pre-revenue / no install base** � counter via OSS pilots in multi-vendor warehouses.  (target: Stage 22 (pilot) / post-GA; status: OPEN)
- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)
- G-035: **Re-fit PdM on REAL plant/robot telemetry** � current brain is an AI4I (CNC-machine) proxy, not robots / not this project's SimPy telemetry. Re-train on real d�  (target: Stage 22 (pilot) / when real data exists; status: OPEN)
- G-043: **Reference pilot + published A/B case** � the single biggest fundability/adoption gap (research �14.6 D-v): no buyer or investor fully credits the product unti�  (target: Stage 22; status: OPEN)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
