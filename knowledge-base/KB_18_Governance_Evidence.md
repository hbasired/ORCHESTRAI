---
name: Governance Evidence
description: ISO/IEC 42001 + EU AI Act + NIST AI RMF Agentic control mapping; Annex IV technical-doc pack generator; evidence retention
type: spec
last-updated: 2026-05-18
---

# KB_18 — Governance Evidence

## Purpose

Map every governance control this product claims to honour against where in the repo the evidence lives. Specify the auto-generated Annex IV technical-documentation pack for EU AI Act Art. 11 conformity.

## Source of truth

- ISO/IEC 42001:2023 — AI management system.
- EU AI Act (Regulation (EU) 2024/1689); ~~enforcement 2026-08-02 for high-risk~~ → **corrected 2026-05-31**: the "Digital Omnibus on AI" (provisional Council+Parliament agreement, 2026-05-07) defers high-risk **Annex III** to **2 Dec 2027** and **Annex I** to **2 Aug 2028**; sandboxes to 2 Aug 2027. Manufacturing safety components remain Annex III high-risk. See research log §11 + [PRD v2.1 §v2.1.8](../PRD-ai-embodied-agent-v2.1.md).
- NIST AI RMF 1.0 + Agentic Profile (Feb 2026).
- OWASP LLM Top 10 (current).
- This file is the contract for `compliance/` and `scripts/generate-annex-iv-doc.py` (Stage 19).

## Body

### ISO/IEC 42001:2023 control mapping

(Selected highlights; full mapping populated as stages fire. The Annex IV pack generator reads this file's mapping table to assemble evidence references.)

| Control | Annex | Description | Repo evidence | Status |
|---|---|---|---|---|
| 4.1–4.4 | Context | Org, stakeholders, scope, AIMS | `compliance/ai-policy.md` §1 (Stage 19) | **shipped** |
| 5.1–5.3 | Leadership | Top-mgmt commitment, AI policy | `compliance/ai-policy.md` §4 | **shipped** |
| 6.1 | Planning | Risk + opportunity actions | `compliance/risk-register.md` | shipped |
| A.6.1 | AI policy | Written AI policy | `compliance/ai-policy.md` | **shipped (Stage 19)** |
| A.6.2 | AI roles | Role accountability | `.claude/skills/<role>/SKILL.md` × 9 | shipped (this session) |
| A.7 | Resources | Data, tools, compute | DVC + model cards + `KB_03` | partial |
| A.8.2 | AI system impact assessment | Per-system impact assessment | `compliance/risk-register.md` + per-stage ADRs | partial |
| A.8.3 | AI system development | Requirements, design, dev | PRD v2 + KB_* + stage task docs | shipped |
| A.9.2 | Use of AI systems | Operator instructions | `compliance/human-oversight.md` | shipped (extended this session) |
| A.10 | Data for AI systems | Data management | DVC + `data/datasets/*/CARD.md` + `KB_03` | partial |
| A.10.4 | Data quality | Bias + accuracy + completeness | Per-stage eval results | per-stage |

### EU AI Act article mapping

| Article | Obligation | Repo evidence | Stage |
|---|---|---|---|
| Art. 9 | Risk management | `compliance/risk-register.md` | continuous |
| Art. 10 | Data governance | DVC + `data/datasets/*/CARD.md` + Stage 5/6/9 model cards | Stages 5/6/9 |
| Art. 11 | Technical documentation (Annex IV) | `scripts/generate-annex-iv-doc.py` → `compliance/annex-iv-packs/` (14 sections, ML-DSA-65-signed footer) — **shipped Stage 19** | Stage 19 |
| Art. 12 | Record-keeping (6-month minimum) | `audit_chain` table (indefinite); `scripts/verify-audit-chain.py` **load-bearing** (Stage 19, G-073) | Stage 13.5 + Stage 19 |
| Art. 13 | Transparency | Frontend decision panel + SHAP/DiCE | Stage 10 + Stage 11 frontend |
| Art. 14 | Human oversight | LangGraph `interrupt()` HITL + `compliance/human-oversight.md` | Stage 11 + ongoing |
| Art. 15 | Accuracy + cybersecurity | PQC + hybrid TLS + Stage 20 evals | Stages 13.5 / 18 / 20 |
| Art. 26 | Deployer obligations | `compliance/incident-playbook.md` + **deployer checklist in `compliance/pilot-deployment-runbook.md` §3 (Stage 22)** | continuous |
| Art. 49 | Conformity assessment | Stage 23 dry-run | Stage 23 |
| Art. 72 | Post-market monitoring | **`compliance/post-market-monitoring-plan.md` (Stage 22) — ingested into the Annex IV pack (§11); maps each Chapter-III §2 dimension → a built signal → a threshold**; **Stage 25: loop OPERATIONAL** — nightly `jobs/post_market_anomaly_sweep.py` (robust-Z + IsolationForest over per-day audit_chain features; honest-empty <14 days; signed `post_market.sweep` rows) + `/ops/post-market` + `/ops/cascade` live views + quarterly report `compliance/post-market-monitoring/2026-Q3.md` (labelled REHEARSAL — no deployed customer; field monitoring starts at the first pilot) | Stage 22 (plan) / **Stage 25 (shipped — rehearsed on the live env)** |
| Annex III | High-risk classification | `compliance/risk-register.md` row 1 | shipped |

### NIST AI RMF Agentic Profile mapping

> **Red-team verified (Stage 20, 2026-06-22).** Each vector below is now exercised by an automated adversarial corpus
> (`backend/training/evals/`, research §30) scored against the REAL defence — NIST suite **14/14 blocked**.

| Attack vector | Mitigation | Where |
|---|---|---|
| Prompt injection via tool outputs | `security/prompt_guard.py` hybrid detector (heuristic + bge-small kNN) inspecting 100% LLM traffic (hard-block on the 0%-FP heuristic tier; semantic tier logged, `=hybrid` to block) + JSON schema enforcement; **red-team 0.9935 detection** | `agents/llm_client.py` (Stage 20) |
| Cross-session memory leakage | Per-`incident_id` namespacing; cross-namespace reads rejected (+ Postgres RLS); **red-team memory probes 100% blocked** | `backend/memory/mem0_adapter.py` (Stage 12/19/20) |
| Tool-chain provenance gaps / poisoning | Every tool call records `(caller, tool, input_hash, output_hash)`; ML-DSA-65 signed tool manifest detects rogue tools; **red-team tool probes 100% detected** | `audit_chain` + `security/tool_manifest.py` (Stage 13.5/17/20) |
| Excessive agency | Safety wrapper + operator confirmation for SIL 1+; **red-team agency probes 100% blocked** | `backend/safety/validator.py` (Stage 17/20) |
| Model supply-chain | DVC pinning + model cards + SLH-DSA-signed bundles | Stage 18 |

### OWASP LLM Top 10 controls

| ID | Risk | Control | Where |
|---|---|---|---|
| LLM01 | Prompt injection | `security/prompt_guard.py` hybrid detector + OWASP-LLM01 corpus (217 cases) Phoenix CI gate — **red-team 0.9935 detection / 0.0156 FPR (shipped Stage 20)** | Stage 20 |
| LLM02 | Insecure output handling | Pydantic schema validation on every tool I/O | Stage 11+ |
| LLM03 | Training data poisoning | DVC pinning, dataset CARDs, license attribution | Stage 5/6/9 |
| LLM04 | Model denial of service | Rate limiting at FastAPI; circuit breakers around LLM providers | Stage 11 / 21 |
| LLM05 | Supply-chain | SBOM (CycloneDX), SLH-DSA-signed firmware bundles | Stage 18 + Stage 22 |
| LLM06 | Sensitive info disclosure | Output filter; PII redaction in `audit_chain` payload | Stage 19 |
| LLM07 | Insecure plugin design | MCP servers schema-checked; no plugin loads external code | Stage 11.5 |
| LLM08 | Excessive agency | Safety wrapper (KB_17) | Stage 17 |
| LLM09 | Overreliance | Operator-in-the-loop + decision explanations + confidence scores | Stage 10 + 11 |
| LLM10 | Model theft | mTLS at boundaries; weights served via Triton with auth (Stage 22 pilot) | Stage 22 |

### Annex IV technical-documentation pack generator (Stage 19)

`scripts/generate-annex-iv-doc.py` produces a single PDF (or HTML bundle) containing:

1. **System description** — from PRD v2.
2. **Intended purpose** — from PRD v2 §1.
3. **System architecture** — from KB_01 + KB_06.
4. **Risk management** — from `compliance/risk-register.md` (all rows).
5. **Data governance** — DVC graph + `data/datasets/*/CARD.md` table.
6. **Model documentation** — `compliance/model-cards/*.md` aggregated.
7. **Performance** — eval results from `backend/training/evals/*/results.json`.
8. **Record-keeping** — `audit_chain` summary (row count, time range, key versions, chain-verify status).
9. **Decision logs** — all `compliance/decision-logs/*.md` since project start.
10. **Human oversight** — `compliance/human-oversight.md`.
11. **Incident playbook** — `compliance/incident-playbook.md`.
12. **Standards compliance** — KB_12 table + KB_17 ISO mappings.
13. **Cybersecurity** — KB_13 (PQC) + Stage 20 eval results.
14. **Conformity declaration** — auto-stamped with the latest signed key version and current `audit_chain` head hash.

CI gate `annex-iv-pack-builds` runs the generator on every PR (Stage 19+) and fails if the output is incomplete.

### Evidence retention

| Artefact | Retention | Why |
|---|---|---|
| `audit_chain` | indefinite | Art. 12 — only purge on legally-mandated SAR, which writes a `redaction` row preserving chain |
| Decision logs (`compliance/decision-logs/`) | indefinite | Architectural history; ADRs are append-only |
| Risk register snapshots | quarterly | Track risk evolution |
| Model cards | indefinite | Annex IV evidence |
| Dataset CARDs | indefinite | Licence audit trail |
| Annex IV doc-pack | rebuilt on demand; latest pinned per release | Conformity evidence |
| Langfuse traces | 90 days | Debug only |
| Phoenix eval results | 90 days | Debug only |
| `pgaudit` DB log | 1 year | Independent DB activity record |

### What this control plane refuses to ship without

- A new high-risk surface without a `risk-register.md` row.
- A new model without a model card.
- A new dataset without a CARD.md.
- A new external boundary without a hybrid-TLS posture documented in KB_13.
- A new actuator path without a safety contract (Stage 17+).
- A new architectural decision without an ADR.

`scripts/audit-task.sh` enforces these checks; `scripts/close-task.sh` refuses if any fail.

---

## Governance hardening (2026-05-24 update — competitive parity with Galileo / Guild.ai)

Per `compliance/decision-logs/2026-05-24_governance_hardening_and_training_scaffold.md` and [`KB_19_Competitor_Comparative_Governance.md`](KB_19_Competitor_Comparative_Governance.md), three capabilities are added to match best-in-class governance platforms while keeping our existing moat (PQC audit chain + functional safety wrapper + industrial standards).

### Policy DSL (NEW — Stage 19)

Declarative policies enforced at runtime across all agent paths without code changes.

- **Storage:** `compliance/policies/*.yaml`, signed with ML-DSA-65 like ADRs (append-only).
- **Validator:** `backend/governance/policy_dsl.py` — Pydantic models for `Policy`, `Rule`, `Scope`, `Enforcement`.
- **Enforcement layers:**
  - OTel span emit (every span checked against active policies).
  - MCP server boundary (every tool input + output evaluated).
  - Safety validator (every actuator path).
  - CI gate (`scripts/audit-task.sh` runs the policy linter).

### Per-tool RBAC + Governed Runtime (NEW — Stage 11.5)

- Each MCP tool declares `required_capabilities`.
- Agent identity (from A2A agent card or internal session) must hold those capabilities.
- Agent registry stored as `audit_chain` rows in namespace `actor:agent:*` with capability list + identity key version.
- MCP server processes run sandboxed: filesystem read-only outside designated dirs, network only to declared peers.

### Budget caps + approval workflows (NEW — Stage 11.5)

- Token + call budget tracker integrated with LangGraph runtime.
- Hard cap → halt the run via `interrupt()`; soft cap → emit warning span.
- Tools tagged `approval-required: true` trigger HITL `interrupt()` and surface to the operator UI.

### PII output filter (NEW — Stage 19)

- MCP server boundary regex + entropy-based detector.
- Default classes: email, phone, SSN, IBAN, credit card.
- EU pilots: hard mode (drop output). Non-EU: soft mode (mask).

### ISO/IEC 42005:2025 — AI system impact assessment (NEW — Stage 19)

- `compliance/impact-assessments/<system>.md` per system.
- Auto-generated by `scripts/generate-impact-assessment.py` from PRD v2 §1.2 + risk register + Annex III classification + model cards + safety contracts.
- Part of the Annex IV pack.

### ISO/IEC 42006 — audit readiness (NEW — Stage 23)

- `compliance/iso-42006-audit-readiness.md` — auditor-facing checklist.
- Sections: AIMS scope, controls evidence, internal audit results, external audit corrections, management review records.
- Refreshed quarterly post-GA.

### What we still EXCEED competitors on (the moat)

Per KB_19 side-by-side: PQC-signed audit chain (ML-DSA-65 cryptographic non-repudiation), functional safety wrapper (LLM-planner / SIL-rated-executor split), industrial standards depth (VDA 5050 / OPC UA / Sparkplug B / ISA-95 / ROS 2), EU AI Act Annex IV auto-generator, red-team CI gate, federation A2A.

**None of Galileo / Guild.ai / Huawei Pangu has these six together. That is the differentiation. After Stage 25 closes, no other open-source platform offers this combination.**

### Traceability, agent hierarchy, function-scoped RBAC & Bell-LaPadula MAC (added 2026-05-31) — **SHIPPED Stage 23**

Governance is strengthened along three axes the operator called out. **SHIPPED 2026-06-22 (Stage 23)** as
`backend/governance/`: **`mac.py`** = Bell-LaPadula confidentiality MAC (G-030 — `SecurityLabel` level+categories,
`dominates`=level-dominance+category-containment, `can_read` no-read-up / `can_write` no-write-down ⋆-property; the
Stage-17 safety wrapper is the Biba integrity dual; audited allow/deny); **`rbac.py`** = agent-hierarchy function-scoped
RBAC (G-029 — `AgentTier` L3_EMBODIED→L2_HEAD→L1_WORKER→L0_PEER, `check_function_access` tier≥min + least-privilege grant,
L0 external peer confined to `a2a_capability` [assume-breach], composes with the Stage-17 ZeroTrustGateway);
**`traceability.py`** = total-traceability `record_decision_trace` (G-028 — `state_snapshot(pre/post)` + decision → one
signed `audit_chain` row, atop the per-decision rows [Stage 12] + spans [Stage 12.5/19]). Pure/deterministic decisions
(DB-independent; best-effort audit, honest degradation); **9/9 governance tests pass**; audit-chain wiring verified live
when Docker is up. The original spec/contract below is retained for the rationale.

**A. Total traceability (every message, every state, every decision).**
- **Every agent communication** — including the coordination messages (`observe`, `plan`, `conflict`,
  `diagnose.request`, `diagnose.report`) and every head↔embodied↔head hop — is recorded with
  `{from, to, type, payload_hash, ts, correlation_id}`.
- **State before AND after** every problem/decision: the engine captures a `state_snapshot(pre)` when an
  incident/prediction fires and a `state_snapshot(post)` after the intervention, both linked by
  `correlation_id`, so any decision can be replayed against the exact world it acted on.
- **Every decision** (plan, safety verdict, intervention choice, operator override) is appended to the
  immutable `audit_chain` (append-only, SHA-256 hash-chained, ML-DSA-65 signed — KB_14). Mutable detail goes to
  Langfuse traces (KB_15, 90-day); the *evidence* is the signed chain (indefinite). This satisfies EU AI Act
  Art. 12 (record-keeping) + ISO/IEC 42001 A.9 (lifecycle) + NIST RMF tool-chain provenance. (G-028)
- **Slice (predict→diagnose→verify→intervene) decisions** additionally persist to the Stage-1 `decision_logs` table in
  the LIVE path (Stage 39, G-045): `slice_runner._persist_decision_log()` writes `caller`/`tool` + SHA-256
  `input_hash`/`output_hash` over the input (telemetry+prediction) → output (decision+verification) provenance chain +
  `inputs`/`outputs` JSONB. AUTOMATIC (no operator step) — the Art-12 shape (research §50). Honest: no DB → no-op (never
  a fabricated id); OFF for the offline A/B.

**B. Agent hierarchy (explicit levels).**
```
L3  EmbodiedCoordinator          (global plan, cross-domain optimization)
L2  Head agents                  (Robotics / Manufacturing / SupplyChain / + Quality / Workforce-Safety / Energy / Facilities)
L1  Domain & worker agents        (per-machine, per-robot, per-supplier; diagnostic self-checks)
L0  External A2A peers            (other orgs' agents; least trust)
```
Messages flow up (problem/report) and down (command/diagnose); the hierarchy is the routing + authority model
(KB_06). (G-029)

**C. Function-scoped accessibility (RBAC) — what an agent may DO.**
Each agent and each MCP tool declares `required_capabilities` + a `function_category`
∈ {robotics, manufacturing, supply_chain, quality, safety, energy, crypto, governance}. The MCP boundary +
coordinator verify the caller's identity/capabilities before a tool/command runs; every check is logged
(builds on the existing per-tool RBAC). A robotics worker cannot invoke a supply-chain command, etc. (G-029)

**D. Bell-LaPadula mandatory access control (MAC) — what an agent may READ/WRITE (confidentiality).**
Each subject (agent) and object (data/message/command) carries a **level** (mapped to the hierarchy:
L3>L2>L1>L0) plus **categories** (the `function_category` compartments). Two enforced properties:
- **Simple Security ("no read up")** — an agent may not read an object classified above its level (an L1 worker
  cannot read the L3 global plan; an L0 external peer reads only what the agent card exposes).
- **\*-property ("no write down")** — an agent may not write/leak high-level information into a lower-level
  channel (L3 cannot push the full plan into an L0 A2A reply).
- Access requires **level dominance AND category containment** (need-to-know by function).
- **Honest complement:** BLP is a *confidentiality* model. Command/actuation *integrity* (a low-trust agent must
  not drive a high-SIL actuator) is enforced by the functional-safety wrapper (KB_17, Biba-like "no write up"
  for commands). We implement BLP for read/write confidentiality of agent data as requested, with the safety
  wrapper providing the integrity dual — together they bound both leakage and unsafe actuation. Enforcement:
  `backend/governance/mac.py` (PLANNED, Stage 19); every allow/deny is audit-logged. (G-030)

## Last verified

2026-06-21 (Stage 19), by compliance-engineer + agentic-governance-engineer: the **Annex IV pack generator is BUILT** —
`scripts/generate-annex-iv-doc.py` assembles all 14 KB_18 sections from live repo evidence into an HTML bundle + a PDF
(`compliance/annex-iv-packs/<date>_annex_iv.{html,pdf}` + `latest.*`) with an **ML-DSA-65-signed conformity-declaration
footer** (over the pack SHA-256 + the audit_chain head). `compliance/ai-policy.md` authored (ISO 42001 A.6.1). CI gate
`annex-iv-pack-builds` (BLOCKING). **4 CTO #3 remediations done:** **G-073** (`verify-audit-chain.py` is now
load-bearing — fails on any non-verifying post-cutover row + reports the placeholder→ML-DSA cutover seq; 94 dev rows
re-attested via `scripts/back-sign-legacy-rows.py`, chain verifies OK); **G-074** (`a2a.rpc.<method>` spans + an
`audit_chain` row per A2A capability call); per-model `ml.inference.*` spans (world_model/diagnose/explain/decide) + a
`cdc.ingest` span; **mem0 RLS** (migration `0008` FORCE row-level security + non-superuser `mem0_app` role; the adapter
`SET ROLE`s + `set_config`s the namespace — a direct SQL client is now fail-closed). Honesty (research §29.1): the pack
is conformity-assessment-READY Annex IV documentation, NOT a conformity certificate (ISO 42001 unharmonised; no
harmonised AI-Act standard published; actual conformity = Stage 23 + notified body). The KB_18 governance-hardening
wishlist (Policy DSL, Bell-LaPadula MAC, PII filter, ISO 42005 generator — G-028/G-029/G-030) was NOT in the Stage-19
task-doc ACs → stays ledgered for a later governance stage. ADR `2026-06-21_stage19_evidence_pipeline.md`.

Prior: 2026-05-18 (base) + 2026-05-31 (traceability + hierarchy + RBAC + Bell-LaPadula MAC spec added), by
compliance-engineer + agentic-governance-engineer + system-designer (those were the *contract* for Stages 19+).
