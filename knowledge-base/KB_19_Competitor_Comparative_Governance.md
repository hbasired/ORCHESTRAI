---
name: Competitor Comparative Governance
description: Side-by-side governance comparison vs Galileo Agent Control, Guild.ai, Huawei Pangu; gap analysis; what we adopt, what we exceed
type: spec
last-updated: 2026-05-24
---

# KB_19 — Competitor Comparative Governance

## Purpose

Honest side-by-side comparison of governance / enforcement mechanisms across the three closest competitors (Galileo Agent Control, Guild.ai, Huawei Pangu) and our project. Identifies (a) what we adopt from them, (b) where we already exceed them, and (c) the moat we extend further. Companion to KB_18 (Governance Evidence) which lists the actual controls; this file is the competitive positioning rationale.

## Source of truth

- Research/initial-research.md §9 (2026-05-24 governance research).
- Galileo Agent Control public docs + GitHub (Apache 2.0).
- Guild.ai public docs + GlobeNewswire announcement (April 29, 2026).
- Huawei Cloud Pangu public docs + Cybersec Asia 2026 statements.
- ISO/IEC 42001:2023 + 42005:2025 + 42006 (audit).

## Body

### Side-by-side comparison

| Capability | Galileo Agent Control | Guild.ai | Huawei Pangu | **This project (PRD v2)** |
|---|---|---|---|---|
| Open source license | Apache 2.0 | Proprietary ($44M Series A) | Proprietary (Huawei Cloud) | Apache 2.0 / MIT |
| **Policy DSL** | YES (write once, enforce everywhere) | YES (approval workflows, budget caps) | Partial (Huawei Cloud policies) | **NEW: KB_18 §"Policy DSL" — add Pydantic-validated policy contracts (Stage 19)** |
| **Identity & Access Control (IAM)** | Limited | YES (agent registry, OAuth) | YES (170+ certifications) | **NEW: A2A agent cards already use ML-DSA-65 identity; ADD per-tool RBAC at MCP server boundary (Stage 11.5)** |
| **Governed Runtime / Sandbox** | Limited | YES (secure sandbox monitoring every execution) | Multi-layer protection | **EXISTS: LangGraph runtime with `interrupt()` HITL + Stage 17 functional safety wrapper** — Galileo/Guild don't have a SIL-rated executor split |
| **Cost / Budget Caps** | NO | YES (budget caps, rate limits) | Cloud-level | **NEW: Add MCP-level token+call budget enforcement (Stage 11.5)** |
| **Approval Workflows** | YES (human approval for fin txns) | YES | Manual | **EXISTS: HITL interrupts via LangGraph (Stage 11); ADD declarative approval-required tags on MCP tools** |
| **Audit Trail Integrity** | Standard logs | "fully traceable" — DB-backed | Multi-layer encryption | **WE EXCEED: ML-DSA-65 signed, SHA-256 hash-chained, append-only `audit_chain` with Postgres immutability trigger. Cryptographic non-repudiation under post-quantum threat model. NONE of the competitors offer this.** |
| **PII / Data Privacy** | YES (PII blocking) | YES | YES | **NEW: Adopt PII output filter at MCP server boundary (Stage 19); same pattern as Galileo** |
| **Brand Voice / Output Conformance** | YES | Not core | N/A | Not a priority for industrial (we're not user-facing chat); skip |
| **EU AI Act Article 11/12 evidence** | NO native | NO native | China-specific compliance | **WE EXCEED: `scripts/generate-annex-iv-doc.py` (Stage 19) generates Annex IV pack on demand; `audit_chain` IS Article 12 record. NONE of competitors solve this.** |
| **ISO/IEC 42001 AIMS mapping** | NO native | NO native | Generic ISO compliance | **WE EXCEED: KB_18 has per-control evidence mapping. ADD ISO/IEC 42005 AI-system impact assessment (Stage 19); ADD ISO/IEC 42006 audit readiness (Stage 23).** |
| **Functional safety (ISO 10218 / IEC 61508 family)** | NO | NO | Partial (industrial SDK) | **WE EXCEED — UNIQUE: KB_17 functional-safety wrapper; LLM-planner / SIL-rated-executor split; STO/SS1 paths. Galileo + Guild are software-only governance; they can NEVER claim SIL-2 actuator safety. Huawei does it in cloud, not architecturally enforced.** |
| **Robot fleet protocol support (VDA 5050)** | NO | NO | Partial via Huawei industrial cloud | **WE EXCEED — UNIQUE: VDA 5050 v2.1.0 master controller (Stage 16)** |
| **OT/IT bridge (OPC UA + Sparkplug B + ISA-95)** | NO | NO | Partial (Huawei industrial cloud lock-in) | **WE EXCEED — UNIQUE: Stage 15 OT/IT bridge with full standards** |
| **Post-Quantum Crypto (PQC)** | NO | NO | Not advertised | **WE EXCEED — UNIQUE: ML-DSA-65 (signatures), ML-KEM-768 + X25519 hybrid (TLS), SLH-DSA-128s (firmware), HMAC-SHA-384 (OT integrity). CNSA 2.0 aligned. NONE of competitors mention PQC publicly.** |
| **Crypto-Agility** | NO | NO | Cloud-only key mgmt | **WE EXCEED — UNIQUE: KB_13 rotation drill; algorithm negotiation per session; `audit_chain` carries `key_version` + `algorithm` columns for future PQC swap.** |
| **Multi-vendor neutrality** | YES (Apache 2.0) | YES (multi-model) | NO (locked to Huawei Cloud) | **TIES with Galileo/Guild on neutrality + EXCEEDS Huawei** |
| **Federation / Cross-org A2A** | NO native | OAuth integrations | NO | **WE EXCEED — UNIQUE: A2A protocol surface (Stage 14) with ML-DSA-signed agent cards** |
| **Red-team / adversarial eval as CI gate** | NO native | NO native | Internal threat monitoring | **WE EXCEED — UNIQUE: Phoenix evals CI gate Stage 20; OWASP LLM01 corpus + NIST AI RMF Agentic vectors enforced on every PR** |
| **Industrial certification readiness (Notified Body / TÜV)** | NO native | NO native | China-specific | **WE EXCEED — UNIQUE: Stage 23 conformity dry-run; Annex IV pack auto-regenerates** |
| **Reproducibility / DVC** | Generic | Generic | Cloud-platform | **WE EXCEED: DVC pipeline for datasets + skills + weights; cryptographic SHA-256 + SLH-DSA-128s signing of model bundles** |

### Three "we adopt" items (close known gaps)

These are real capabilities we currently lack. Stage 19 (Governance Evidence Pipeline) is expanded to include them.

#### 1. Policy DSL (inspired by Galileo)

**Goal:** Declarative policies written once, enforced at runtime across all agent paths without code changes.

**Design (new in Stage 19):**
- `backend/governance/policy_dsl.py` — Pydantic-validated policy contracts.
- Policy lives in `compliance/policies/*.yaml`, signed with ML-DSA-65 like ADRs.
- Examples:
  ```yaml
  - name: pii_redaction_at_mcp_output
    scope: mcp_servers.*
    rule: redact_pii(output, classes=[email, phone, ssn, iban])
    enforcement: hard  # hard = drop output; soft = warn
  - name: budget_cap_per_incident
    scope: agent.runtime
    rule: max_tokens_per_incident <= 100_000
    enforcement: hard  # halt if exceeded
  - name: sil_2_actuator_requires_safety_validate
    scope: backend.integrations.*
    rule: every actuator span has preceding safety.validate span
    enforcement: ci_gate
  ```
- Policies enforced at OTel span emit time + at MCP server boundary + at safety validator.

#### 2. Governed Runtime / Sandbox (inspired by Guild.ai)

**Goal:** Every agent execution monitored; identity verified; access scoped.

**Design (Stage 11 + 11.5 already partial; extended):**
- LangGraph runtime already wraps every node execution.
- ADD: per-MCP-tool RBAC — each MCP tool declares `required_capabilities`; agent identity (from A2A agent card OR internal session) must hold those capabilities.
- ADD: agent registry under `audit_chain` namespace `actor:agent:*` with capability list + identity key version.
- Sandbox boundary: MCP servers run in separate processes (already in Stage 11.5 design); sandbox extended to limit filesystem + network access (Stage 17 functional safety wrapper extends this for SIL paths).

#### 3. Cost / Budget Caps (inspired by Guild.ai)

**Goal:** Hard limits on tokens, calls, and inferences per incident / per operator / per hour.

**Design (new in Stage 11.5 + Stage 19):**
- Token counter wrapping every LLM call via the OTel `gen_ai.completion` span.
- Per-incident budget defined in policy DSL.
- Hard cap → halt the LangGraph run via `interrupt()`; soft cap → emit warning span.
- Aggregated metrics surface in Langfuse dashboard.

### Six "we exceed" items (the moat)

These are differentiators NO competitor has end-to-end. Keep + strengthen.

1. **PQC-signed audit chain** — KB_13 + KB_14. Cryptographic non-repudiation under post-quantum threat model.
2. **Functional safety wrapper with LLM-planner / SIL-executor split** — KB_17. NO software-only governance platform can claim SIL-2 actuator safety.
3. **VDA 5050 robot fleet master controller** — Stage 16. Industrial-specific.
4. **OT/IT bridge** (OPC UA + Sparkplug B + ISA-95) — Stage 15. Industrial-specific.
5. **EU AI Act Annex IV pack auto-generator** + ISO/IEC 42005 impact assessment (NEW) + ISO/IEC 42006 audit readiness — Stage 19 + 23.
6. **Red-team eval as CI gate** with OWASP LLM Top 10 + NIST AI RMF Agentic corpus — Stage 20.

### Positioning statement

> Galileo and Guild.ai are the *Kubernetes of agents* for enterprise SaaS — governance for chatbots, code-assistants, and back-office automations.
>
> This project is the *Kubernetes of agents for industrial fleets* — governance for systems where an LLM action can cause a $50M production line stop or, worse, an injury.
>
> The boundary between us is: **can your governance platform stop an LLM from commanding a SIL-2-classified actuator? If no, you are not in our market.**

### What changes in the build

Three Stage 19 acceptance criteria gain new items:

1. `backend/governance/policy_dsl.py` + `compliance/policies/*.yaml` with at minimum 8 policies covering: PII redaction, budget caps, approval workflows, safety-validate pairing, audit-chain append, KB diff coverage, model-card presence, ADR signing.
2. ISO/IEC 42005 impact assessment template at `compliance/impact-assessments/<system>.md` regenerated by `scripts/generate-impact-assessment.py`.
3. ISO/IEC 42006 audit-readiness checklist at `compliance/iso-42006-audit-readiness.md` (Stage 23 also references).

Two Stage 11.5 acceptance criteria gain new items:

1. MCP server identity-and-capability checks at every tool call boundary.
2. Token/call budget tracker integrated with LangGraph runtime.

## Multi-dimensional comparison (extension 2026-05-24 — beat them on EVERY axis)

User instruction (2026-05-24): "Not only on the governance we need to beat Galileo, Guild.ai, Huawei on each and every level. In performance, metrics, efficiency, latency, effectiveness, easy to use, transparency, explainability, auditability, and robustness."

This section adds **Project Aether** (the operator-supplied 2026-05-24 industrial-AI blueprint) as a fourth comparator and evaluates all four against this project across 10 dimensions.

| Dimension | Galileo | Guild.ai | Huawei Pangu | Project Aether (blueprint) | **This project (after roadmap closes)** |
|---|---|---|---|---|---|
| **Performance (throughput)** | not published | not published | 500+ industrial scenarios at Huawei Cloud scale | not measured (portfolio project) | Stage 2 calibration target: ~500 units/hr; Stage 11 LangGraph: ≥5 decisions/sec/agent under load |
| **Performance (accuracy)** | not core (governance only) | not core (governance only) | YOLO QC 70→95% in nitrile rubber example | unverified | Stage 4 RUL < 15 RMSE; Stage 5 I-AUROC ≥ 0.85; Stage 6 WRMSSE < 0.65; Stage 9 mAP@50 ≥ 0.90 (per CATALOG acceptance metrics) |
| **Latency (decision p95)** | "real-time enforcement without downtime" — not quantified | not quantified | not quantified | <10 ms control loop target (claim) | PRD v2 §1.3 + KB_10: **<500 ms decision p95 SLA; 205 ms p95 budget; Stage 2 ≤250 ms p95 inject latency** |
| **Latency (TTFT)** | not in scope | not in scope | not in scope | not in scope | We compose against LLM providers; matched to Groq 120 ms TTFT for time-critical paths; Ollama fallback for offline |
| **Efficiency (resource footprint)** | Apache 2.0 server (size n/a) | proprietary runtime | Huawei Cloud (heavyweight) | Standard K8s | **KubeEdge ~70 MB EdgeCore footprint** (Stage 22.5); ONNX-quantised edge models; carbon-aware compute scheduler (KB_20.3) |
| **Efficiency (energy / Green AI)** | not addressed | not addressed | mentioned not architected | central pillar (carbon-aware + microgrid PPO + Edge AI) | **YES — full Energy Intelligence domain (KB_20): microgrid PPO + Transformer battery RUL + carbon-aware Kubernetes scheduling + Edge AI via KubeEdge** |
| **Effectiveness (task completion)** | governance layer (not the agent itself) | governance layer | Huawei industrial deploys (Baowu Steel +5% hot rolling accuracy) | unverified portfolio project | Cycle-time reduction 25-30% (PRD §1.3); carbon reduction 15-20%; >=99% uptime; Phoenix red-team CI gate ≥99% pass rate on OWASP LLM01 |
| **Ease of use (developer)** | Apache 2.0 + SDK + docs | Code-first SDK | Huawei Cloud console | Six-month portfolio roadmap | **`/begin` slash command + 9 role personas + auto-context-loader + per-stage task templates + Colab training scaffold — onboarding is one slash command** |
| **Ease of use (operator)** | not user-facing | enterprise admin UI | Huawei Cloud Web UI | Conceptual "chat with factory" | Frontend dashboard (Next.js 15 LTS + R3F) + Stage 22.7 USD Omniverse twin + Stage 25.5 Digital Triplet chat-with-factory |
| **Transparency (decision visibility)** | logs + Galileo dashboards | observability + audit logging | Cloud-level monitoring | LLM+RAG over time-series DB | **OTel GenAI semconv spans on EVERY node/tool/model call + Langfuse self-hosted + Phoenix evals + audit_chain table** |
| **Explainability** | not core | not core | "fully traceable" generic | mentioned not architected | **Stage 10: SHAP attributions + DiCE counterfactuals + attention heatmaps + confidence scores. Every decision card surfaces 3+ explanations** |
| **Auditability** | logs | DB-backed audit logging | Multi-layer encryption + 170 certs | logs + whitepapers | **PQC-signed (ML-DSA-65) append-only SHA-256 hash-chained `audit_chain` table with Postgres immutability trigger; verifiable end-to-end via `scripts/verify-audit-chain.py`. No competitor has cryptographic non-repudiation under PQ threat model.** |
| **Robustness (chaos engineering)** | not published | not published | Multi-layer protection | Six-month plan | Stage 21 DR/HA/chaos engineering as explicit acceptance criterion |
| **Robustness (functional safety)** | NO | NO | Partial | NOT in scope | **Stage 17 functional-safety wrapper with LLM-planner / SIL-rated executor split. ISO 10218 / IEC 61508 / ISO 13849 / IEC 62061 mapped. CI gate: every actuator span paired with safety.validate span.** |
| **Robustness (offline autonomy)** | n/a (cloud SaaS) | n/a (cloud SaaS) | Huawei Cloud-dependent | KubeEdge offline (planned) | **YES — KubeEdge EdgeCore continues operating during WAN outages (KB_21)** |
| **Robustness (self-healing)** | NO | NO | Partial (Huawei Cloud HA) | Conceptual joint-torque anomaly + diagnostic calibration | **YES — KB_17 self-healing extension: joint-torque anomaly → behaviour-tree self-repair → STO escalation, ALL audit_chain-logged with safety.validate pairing intact** |
| **Crypto posture (PQ-ready)** | NO | NO | NO advertised | NO advertised | **YES — UNIQUE: ML-DSA-65 + ML-KEM-768+X25519 hybrid + SLH-DSA-128s + HMAC-SHA-384, full crypto-agility, CNSA 2.0 aligned (KB_13)** |
| **Industrial standards depth** | NO | NO | Huawei industrial cloud-bound | OPC UA + ROS2 + MQTT | **VDA 5050 v2.1.0 + OPC UA + Sparkplug B v3.0 + ISA-95 Part 2 + ROS 2 Jazzy + ISO 10218 family + IEC 61508 family + ISO/IEC 42001/42005/42006 — full Western regulatory stack (KB_12)** |
| **Regulatory alignment (EU AI Act + ISO/IEC 42001)** | NO native | NO native | China-specific | NO mentioned | **YES — Stage 19 Annex IV doc-pack auto-generator; ISO/IEC 42005 impact assessment; ISO/IEC 42006 audit readiness; EU AI Act Articles 9-15, 26, 72 control-mapped (KB_18)** |
| **Federation (cross-org A2A)** | NO native | OAuth integrations | NO | NO | **YES — Stage 14 A2A surface with ML-DSA-signed agent cards (KB_16)** |

**Score (out of 19 dimensions):**
- Galileo: ~5 (governance core + Apache 2.0)
- Guild.ai: ~7 (governance + identity + costs + observability)
- Huawei Pangu: ~6 (industrial deploys + certifications, but cloud-locked)
- Project Aether (blueprint): ~9 (full-stack vision but unverified)
- **This project (after Stage 25): 19/19** — every dimension addressed, multiple with no competitor match (PQC, functional safety, federation, regulatory).

## Landscape refresh (2026-05-31) — verified, four bands

Full sourced analysis + SWOT + capability matrix + four perceptual maps:
[research/market-analysis/index.html](../research/market-analysis/index.html); sources in research log §11.

- **Band A — closed "Industrial AI OS" incumbents.** Siemens+NVIDIA publicly building an "Industrial AI Operating
  System" (Isaac/GR00T/Omniverse + Xcelerator; Erlangen humanoid pilot, Apr 2026); Rockwell+AWS "autonomous
  industrial operations" + AI-orchestrated design (Hannover Messe 2026); Huawei Pangu 5.5 (718B, 500+ scenarios;
  proposes open "R2C" protocol; geopolitically gated for EU/NSS). Distribution-rich, vendor-locked; **no public
  PQC/audit-chain/Annex-IV story**.
- **Band B — robot fleet orchestration/observability (open-ish).** InOrbit + **OpenRobOps** (permissive OSS fleet
  manager, 2026), Formant (observability/teleop), Open-RMF (OSS multi-fleet interop), Boston Dynamics Orbit (Spot
  fleet mgmt, CES 2026), Standard Bots. Closest to us on *openness*; **no safety-SIL / compliance / PQC plane** — we
  integrate Open-RMF/OpenRobOps *beneath* us rather than compete.
- **Band C — horizontal agent governance/observability.** Galileo (Luna-2 eval→guardrail), Arize, LangSmith,
  Langfuse (OSS, we adopt). Software-only; **no OT/safety/crypto**.
- **Band D — ecosystem partners (not rivals).** HSM/PQC vendors (Entrust, Thales, Utimaco — PKCS#11) plug into our
  `KeyProvider` boundary (KB_13); standards bodies define interfaces we conform to.

**Finding:** no competitor on public evidence combines all four pillars — open/vendor-neutral + EU-AI-Act evidence +
functional-safety split + PQC crypto-agility. That intersection is the defensible white-space (verdict: opportunity,
*conditional* on execution speed and on the moat staying ahead of incumbents who have distribution). ABB 2026
agentic-orchestration detail was **not verified** this pass — watch-item.

## Last verified

2026-05-24, agentic-governance-engineer + compliance-engineer review. Research: research/initial-research.md §9 + §10.
+ **2026-05-31 landscape refresh** (research log §11; HTML market analysis). ADRs:
`compliance/decision-logs/2026-05-24_governance_hardening_and_training_scaffold.md`,
`compliance/decision-logs/2026-05-24_multi_dimensional_competitive_plan.md`,
`compliance/decision-logs/2026-05-31_prd_v2_1_and_lifecycle.md`.
