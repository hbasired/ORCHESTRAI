# PRODUCT REQUIREMENTS DOCUMENT (PRD) v3.0
## The Vendor-Neutral Trust & Self-Healing Layer for Industrial Robot + OT Fleets

**Document Version**: 3.0
**Date**: 2026-06-11
**Status**: **Authoritative.** Consolidates and supersedes v2.0 (2026-05-18), v2.1, v2.2, v2.3 (all 2026-05-31). Where v3 conflicts with any earlier version, **v3 wins**. All earlier PRD files (v1, v2.0–v2.3) are **archival and frozen** (hook-enforced; CLAUDE.md hard rule 6). The next PRD increment is a new file (`PRD-ai-embodied-agent-v4.md`).
**ADR**: [compliance/decision-logs/2026-06-11_strategic_product_reset.md](compliance/decision-logs/2026-06-11_strategic_product_reset.md)
**Companion artifacts**: [research/market-viability-2026-06/index.html](research/market-viability-2026-06/index.html) (sourced market analysis, June 2026) · [research/initial-research.md §14](research/initial-research.md) · [knowledge-base/KB_26_Product_Market_Strategy.md](knowledge-base/KB_26_Product_Market_Strategy.md)

> **Honesty contract (binding on every section).** Every external figure is cited or labeled a qualitative judgment.
> Every quantitative target is a *commitment-to-verify* (design target) unless a stage marks it **measured**.
> Every capability is tagged **BUILT** / **PARTIAL** / **PLANNED** against the repository at 2026-06-11
> (Stages 0–5 closed, audit baseline 402). This document states where the product will NOT win (§19).

---

## 0. Document control & lineage

| Version | Date | What it was | Status |
|---|---|---|---|
| v1.0 | 2026-01 | Multi-domain manufacturing AI agent (4-quadrant dashboard, LSTM/PPO/SHAP) | Archival (frozen) |
| v2.0 | 2026-05-18 | Repositioning: vendor-neutral, EU-AI-Act-grade, PQC-ready control plane; 25-stage roadmap | Archival (frozen) |
| v2.1 | 2026-05-31 | Specs/SLOs, operator dashboard, KeyProvider/HSM boundary, EU AI Act date fix | Archival (frozen) |
| v2.2 | 2026-05-31 | USP three legs (breadth/foresight/trust); capability pillars; honest viability | Archival (frozen) |
| v2.3 | 2026-05-31 | Causal Self-Healing Engine as headline differentiator; N-domain; dynamic features | Archival (frozen) |
| **v3.0** | **2026-06-11** | **Standalone consolidation + market validation + niche sharpening + de-risked roadmap** | **Authoritative** |

Conflict rule within v3 lineage: v3 > v2.3 > v2.2 > v2.1 > v2.0 > v1 (relevant only for historical interpretation; v3 is self-contained).

---

## 1. One-liner, the niche, and the differentiator

**One-liner.** *The vendor-neutral trust and self-healing layer for mixed robot/OT fleets — every autonomous decision predicted, causally explained, safety-gated, and cryptographically provable — running above whatever fleet manager you already have. Open source, evidence-ready for the EU AI Act's December 2027 date.*

**The niche (deliberately narrow).** We are NOT a fleet manager (that layer is now a free commodity — InOrbit open-sourced OpenRobOps in Feb 2026 [research §14.2]). We are NOT a general agent platform (Cisco bought that category with Galileo, 2026-05-22 [research §14.2]). We are NOT an "Industrial AI OS" (Siemens+NVIDIA own that lane with distribution we will never have). The niche is the **four-way intersection nobody occupies**:

> **autonomous** (closed-loop self-healing, not dashboards) × **certifiable** (SIL-gated actuation, EU AI Act evidence) × **neutral** (multi-vendor, open standards, Apache 2.0) × **provable** (ML-DSA-signed, hash-chained, replayable decision records)

**The headline differentiator — the Causal Self-Healing Engine** (carried from v2.3; spec in [KB_25](knowledge-base/KB_25_Causal_SelfHealing_Engine.md)). The `EmbodiedCoordinator` upgrades from reactive coordination to a closed loop:

1. **Predict** failures before they happen — learned world model (XGBoost PdM **BUILT**, PR-AUC 0.847 measured; LSTM demand **BUILT**, MAPE 21% measured; LSTM-AE/Transformer **PLANNED** Stage 8).
2. **Diagnose / causally reason** — active probing + Causal Digital Twin: root cause + counterfactual "what-if" (**v0 PLANNED Stage 6** — deterministic root-cause; causal twin Stage 8).
3. **Verify** — neuro-symbolic: LLM planner grounded in a formal constraint engine; unsafe plans rejected before execution (**PLANNED** Stages 11/17).
4. **Intervene without interruption** — RL-selected recovery: self-repair / dispatch robot-fixer / backup online / slow-and-catch-up (**v0 PLANNED Stage 6** — sim-only; PPO Stage 7; production Stage 11).

The three legs from v2.2 are the **foundation** under that engine: **Breadth** (robots + machines + supply chain as ONE optimization — `EmbodiedCoordinator` BUILT), **Foresight** (simulate-before-act — SimPy BUILT, USD/Omniverse PLANNED 22.7), **Trust** (safety-gated + signed provenance — PLANNED 13.5/17/19).

**Why this niche survives contact with the June-2026 market** (full analysis: [market-viability HTML](research/market-viability-2026-06/index.html)):
- Orchestration commoditized (OpenRobOps, Open-RMF, GRID) → we **integrate** those rails instead of competing; our value starts where theirs stops.
- The reliability category validated + vacated (Cisco×Galileo) → no remaining independent player covers OT + safety + evidence + PQC.
- Humanoid fleets ship with per-OEM platforms (Agility Arc, BD Orbit) → mixed fleets make a neutral trust layer MORE necessary, not less.
- Fixed compliance dates (Annex III: 2 Dec 2027) → an 18-month, legally-certain "evidence-ready by design" sales runway.

---

## 2. Market context & problems-to-solve matrix

All figures sourced in [research §14](research/initial-research.md) and the [market-viability HTML §12](research/market-viability-2026-06/index.html).

**Market anchors.** Warehouse robotics: $7.35B (2026) → $25.41B (2034), CAGR 16.8% (Fortune Business Insights). AMR fleet-management software: $198M (2026) → $567M (2034), CAGR 19.5% (Intel Market Research). AI-driven PdM software: $1.18B (2026), CAGR 15.6% (TBRC). Combined direct SAM ≈ $1.3–1.4B in 2026 (estimate: sum of segments, overlap unquantified).

| # | Industry problem (sourced) | Who feels it | Today's alternative | Our answer | Status / stage |
|---|---|---|---|---|---|
| P1 | Labor shortage: 76% of supply-chain ops impacted (Descartes); 41% of warehouse managers can't retain staff (MHI 2025) | Warehouse / 3PL operations | More hiring spend; single-vendor automation islands | Cross-domain autonomous coordination raising throughput without headcount | PARTIAL (sim-proven; pilot Stage 22) |
| P2 | Multi-vendor fleets don't interoperate; VDA 5050 / MassRobotics adoption "a long way to go" (SYNAOS) | Ops + OT integrators | One fleet manager per vendor; manual deconfliction | Neutral control plane over VDA 5050 / MassRobotics / Open-RMF; integrates OpenRobOps | PLANNED Stage 16 |
| P3 | Integration overhead = 50–100% of hardware cost on first deployment; WMS/robot state divergence is a top deployment-killer (Robotomated) | CFO + systems integrators | Custom SI projects per site | Standards adapters + canonical incident envelope + CDC; documented 90-day integration playbook (§15) | PARTIAL (envelope BUILT; adapters Stages 13/15/16) |
| P4 | Unplanned downtime; PdM adoption >45% in large manufacturers but black-box mistrust; XAI now expected (ifactoryapp) | Maintenance + ops | Opaque sensor-vendor PdM; reactive repair | Causal self-healing loop: predict → root-cause → verify → no-interruption intervention, explainable + signed | PARTIAL (predict BUILT; loop Stages 6–11) |
| P5 | EU AI Act high-risk evidence burden from 2 Dec 2027 (Council 2026-05-07) | Compliance officers | Consulting projects; manual doc packs | Append-only ML-DSA-signed audit chain; Annex IV pack ≤ 60 s (target) | PLANNED Stages 13.5/19 |
| P6 | 10–20-year equipment lifecycles vs RSA/ECC deprecation by 2030, disallowed 2035 (NIST IR 8547) | Security architects | Ignore until forced | FIPS 203/204-aligned PQC now; KeyProvider boundary for HSM/parameter swap | PLANNED Stages 13.5/18 |
| P7 | Autonomous decisions nobody can explain to an auditor | Everyone above | Trust-me dashboards | Counterfactual causal explanations bound to the signed decision record | PLANNED Stages 8/10 |

**PQC claim discipline (binding):** our ML-DSA-65 / ML-KEM-768 selections are NIST security level 3 — FIPS 203/204 compliant and appropriate for commercial/industrial use. They are **not** the CNSA 2.0 NSS parameter sets (ML-KEM-1024 / ML-DSA-87). Approved language: *"FIPS-aligned, CNSA-2.0-aware crypto-agility (parameter swap via the KeyProvider boundary)."* Never claim "CNSA 2.0 compliant." (research §14.3)

---

## 3. Product specification & objectives

**What it is.** An open-source (Apache 2.0 / MIT) control plane that sits *above* heterogeneous robots, AMRs, PLCs and OT systems and *below* the customer's business systems, turning multi-agent reasoning into **safe, auditable, post-quantum-signed** actions on an industrial fleet.

**Capability objectives.**
- **O1 — Orchestrate** heterogeneous fleets via open standards (VDA 5050, OPC UA, MQTT Sparkplug B, ISA-95, ROS 2), not a single-vendor SDK. *(PLANNED 15/16)*
- **O2 — Reason** with a durable, interruptible agent workflow (LangGraph) that plans but never directly actuates. *(PLANNED 11)*
- **O3 — Gate** every actuator command through a functional-safety wrapper (LLM-planner / SIL-rated-executor split). *(PLANNED 17)*
- **O4 — Prove** every decision with an immutable, hash-chained, ML-DSA-65-signed audit chain and an auto-generated EU AI Act Annex IV pack. *(PLANNED 13.5/19)*
- **O5 — Protect** every trust boundary with post-quantum (hybrid) crypto and *crypto-agility* (algorithm/provider swappable by config). *(PLANNED 13.5/18)*
- **O6 — Observe** the whole system — agentic and non-agentic — through one operator surface with alarming and reporting. *(PARTIAL: WS plumbing BUILT; surface 11–19)*
- **O7 — Heal** — the Causal Self-Healing Engine (§1): predict → diagnose → verify → intervene without interruption. *(PARTIAL: predict BUILT; v0 loop Stage 6)*

**For whom.** Warehouse operations leads, manufacturing engineers, OT/IT integrators, compliance officers (personas in §14).

**Wedge → expansion.** Warehouse/fulfillment first (shortest sales cycle, lowest safety classification, multi-vendor pain is acute) → discrete manufacturing → process industries.

**Explicit non-goals.** Not a certified safety PLC (we integrate the customer's certified PLC). Not a robot OEM. Not a paid SaaS at build time (hard rule 9). Not an automotive-assembly or defense-platform product in this version. Not a replacement for hardwired SIL-3+ emergency-stop circuits (the LLM observes those, never commands them). Not a fleet manager (we integrate OpenRobOps/Open-RMF). Not a generic LLM-agent observability tool.

---

## 4. Architecture

Authoritative design: [KB_24_System_Design_HLD_LLD.md](knowledge-base/KB_24_System_Design_HLD_LLD.md) (HLD/LLD + hand-off map). Six-layer spine, every seam an open interface:

```
┌─ Experience    Operator dashboard (agentic vs non-agentic, alarms, reports)      [11–19]
├─ Trust         Safety wrapper (LLM-planner/SIL-executor) · audit_chain (signed)  [13.5/17/19]
├─ Coordination  EmbodiedCoordinator (head-of-heads, N domain heads)               [BUILT, reactive]
├─ Cognition     LangGraph durable runtime · MCP tools · Causal Self-Healing loop  [11/11.5; v0 Stage 6]
├─ World         SimPy DES (BUILT) → causal digital twin → USD/Omniverse           [2 BUILT; 8/22.7]
├─ Ingress/OT    VDA 5050 · OPC UA · Sparkplug B · ISA-95 · ROS 2 · CDC            [13/15/16]
└─ Data/Memory   Postgres · Redis · Neo4j · pgvector · DVC · KubeEdge (edge)       [BUILT core; 12/22.5]
```

**Built today (verified):** FastAPI backend (~17.6k LOC, 40+ passing tests); SimPy deterministic simulator (10 stages, 20 AMRs, 6-event catalog, ~500 units/hr); Redis pub/sub → WebSocket broker (11.6 ms p95 measured on live Redis); XGBoost failure predictor (PR-AUC 0.847, recall-tuned threshold, model card); LSTM demand forecaster (MAPE 21%, +59% vs persistence, model card); coordinator + 3 domain heads; Next.js 15 frontend (17 routes); Alembic migrations; Docker Compose stack; DVC + model-card CI gates.

**Key flows.** *Incident*: OT/sim event → Postgres + Redis pub/sub → WS broker → dashboard (**BUILT**). *Decision*: observe → plan (LangGraph) → simulate-before-act → safety-gate → execute via SIL bridge → sign → audit_chain (**planner/coordinator BUILT; gate/sign PLANNED**). *Evidence*: audit_chain → Annex IV pack (**PLANNED 19**). *Self-healing*: predict → diagnose → verify → intervene (**v0 = Stage 6**, production = Stage 11).

---

## 5. Standards map

First-class (full mapping: [KB_12_Standards_Map.md](knowledge-base/KB_12_Standards_Map.md)): **VDA 5050 v2.1.0** (AGV/AMR ↔ master control), **MassRobotics AMR Interop** (complementary), **Open-RMF** (multi-fleet interop — integration target), **OPC UA** (+ Safety profile), **MQTT Sparkplug B v3.0**, **ISA-95 / IEC 62264** (equipment hierarchy), **ROS 2 Jazzy/Kilted**, **ISO 10218-1/2:2025** + **ISO/TS 15066** (robot safety), **IEC 61508** / **ISO 13849-1:2023** / **IEC 62061:2021** (functional safety), **ISO/IEC 42001:2023** (AI management system), **NIST AI RMF + Agentic Profile**, **EU AI Act** (Art. 9–72; timeline §11), **FIPS 203/204/205** (PQC). MCP + A2A under the Linux Foundation Agentic AI Foundation (150+ orgs on A2A; ~97M MCP installs — research §14.5).

---

## 6. A2A + MCP surface

**MCP (internal, agent→tools):** five FastMCP servers — `sim_world_server`, `kpi_query_server`, `decision_log_server`, `model_inference_server`, `policy_query_server` — JSON-schema-enforced, per-tool RBAC, schema tests CI-gated (Stage 11.5).
**A2A (external, agent↔agent):** discovery via `/.well-known/agent.json`; **ML-DSA-65-signed agent cards**; pinned root keys + revocation list; ML-KEM-768 + X25519 hybrid TLS; replies signed (Stage 14). Industrial A2A endpoints remain rare in June 2026 → early-mover surface intact (research §14.5).

## 7. PQC strategy & the KeyProvider/HSM boundary

**Algorithm placement** ([KB_13](knowledge-base/KB_13_PQC_Crypto_Strategy.md)): ML-KEM-768 + X25519 hybrid (external TLS) · ML-DSA-65 (action signatures, audit chain, agent cards) · SLH-DSA-SHA2-128s (firmware/policy bundles, long-horizon trust) · HMAC-SHA-384 (OT message integrity). Claim discipline per §2.

**KeyProvider boundary (the "buy an HSM, swap by config" requirement).** No caller in `backend/` imports a concrete crypto backend; all depend on the abstract `KeyProvider` (generate_keypair / sign / verify / public_key / rotate / capabilities). Concrete backends selected by config only: `SoftwareKeyProvider` (liboqs, dev) → `Pkcs11KeyProvider` (SoftHSM dev / real HSM prod — same PKCS#11 driver) → `VaultTransitProvider`. `audit_chain` rows carry `key_version` + `algorithm` so historical verification survives swaps. Acceptance: documented config-only swap drill; `verify-audit-chain.py` passes across the boundary. (Stage 13.5 spec; pilot drill Stage 22.)

## 8. Functional safety wrapper

**LLM = planner (non-deterministic). Classical SIL-rated controller = executor (validated).** Pydantic safety-contract DSL; `backend/safety/validator.py` gates every actuator path; SIL routing: SIL 0 = LLM direct, SIL 1 = LLM → validator → operator HITL, SIL 2+ = LLM → validator → classical executor → PLC. CI enforces a `safety.validate` OTel span before every actuator span (hard rule 3). STO/SS1 paths integrate the customer's certified hardware — never replaced. (Stage 17; spec [KB_17](knowledge-base/KB_17_Functional_Safety_Wrapper.md).)

## 9. Agent memory

Six layers ([KB_14](knowledge-base/KB_14_Agent_Memory_Architecture.md)): Working (LangGraph state + Postgres checkpointer, 11) · Episodic default (Mem0 + pgvector, per-incident/operator namespaced, cross-namespace reads forbidden, 12) · Episodic long-horizon (Letta, opt-in) · Semantic (pgvector + Neo4j ISA-95, 12) · Procedural (DVC-versioned skills) · **Audit (immutable)**: append-only, SHA-256-chained, ML-DSA-65-signed `audit_chain` — the EU AI Act Art. 12 evidence substrate (13.5).

## 10. Observability, evidence & the operator dashboard

**Two-store design:** Langfuse v3 self-hosted (mutable, 90-day, debugging) + `audit_chain` (immutable, indefinite, regulators). OpenTelemetry GenAI semconv on every layer; Arize Phoenix for offline evals (12.5).

**Operator dashboard requirement (carried verbatim in intent from v2.1.4).** One surface, real-time, both **agentic and non-agentic** activity. Seven required panes: activity timeline (every event tagged `actor_class ∈ {agent, human, system, external}` + SIL level — an Art. 14 human-oversight enabler); agent reasoning panel (live LangGraph trace, MCP calls, HITL prompts); plant panel (telemetry, OEE, energy); safety-gate panel (every validate decision, STO/SS1 events); audit-chain viewer (one-click verify); A2A federation status; policy/governance status. **Alarming:** severity model info→safety-critical; routing via config (no hard SaaS dependency); every ack audited; safety-critical alarms never silently auto-cleared. **Reporting:** shift / incident / EU-evidence summaries, exportable, signed, audit-chain head hash embedded. SLOs in §17-D.

## 11. Governance & compliance mapping

ISO/IEC 42001:2023 AIMS controls; EU AI Act Art. 9 (risk mgmt — `compliance/risk-register.md`, 18 risks live), Art. 11/Annex IV (auto doc-pack, 19), Art. 12 (logging — audit_chain), Art. 14 (human oversight — HITL + actor_class), Art. 15 (accuracy/robustness — KB_23 evals); NIST AI RMF Agentic Profile (prompt-injection via tool outputs, memory leakage, tool-chain poisoning — mitigations staged 11.5/12/20); OWASP LLM Top 10 as per-PR checklist; policy DSL + per-tool RBAC + budget caps (11.5/19).

**EU AI Act timeline (verified 2026-06-11, research §14.3):** Digital Omnibus provisional agreement 2026-05-07 — **Annex III high-risk: 2 Dec 2027**; Annex I: 2 Aug 2028; sandboxes: 2 Aug 2027. Formal adoption expected before 2 Aug 2026; re-verify at every CTO checkpoint. Manufacturing safety components remain high-risk — only the clock moved. Pitch: evidence-ready reference architecture for the 2027 window, with PQC + safety + neutrality leading.

## 12. Causal Self-Healing Engine, N-domain, dynamic features

Carried in full from v2.3 (spec: [KB_25](knowledge-base/KB_25_Causal_SelfHealing_Engine.md)); status honest:

- **The loop** (§1): predict (BUILT v0 — XGBoost/LSTM proxies) → diagnose (Stage 6 deterministic v0; causal twin + active `diagnose.request/report` probing Stage 8/11) → verify (neuro-symbolic, 11/17) → intervene (Stage 6 sim-only v0; PPO Stage 7; production 11).
- **DL/RL stack:** YOLOv8 (vision, BUILT pretrained) · LSTM/Transformer (predict, 4 BUILT/8) · PPO (intervene, 7) · causal discovery + counterfactual + neuro-symbolic constraint engine (8/11/17).
- **N-domain embodiment:** coordinator handles N heads; Quality & Inspection, Workforce & Safety, Facilities/Energy domains ledgered (G-016..G-018) — **post-slice**, not before Stage 11 ships.
- **Dynamic operator features** (staged, G-021..G-024): live message-cascade observability (11–12.5); "ask the factory" chatbot (12+); NL problem injection (11+); bidirectional DB-edit-triggers-reasoning via CDC (13).
- **Execution honesty:** everything in this section beyond Stage-4/5 predictors is PLANNED. Stage 6 builds the narrowest end-to-end version (machine-failure scenario only) before any widening — CTO Checkpoint #1's explicit gate.

## 13. Capability pillars & competitive posture (June 2026)

| Pillar (category leader) | Target depth | Stage | Status |
|---|---|---|---|
| Cross-domain coordination (unique to us) | Robots + machines + supply chain as one optimizer | — | BUILT (reactive) |
| Causal self-healing (unique to us) | Predict→diagnose→verify→intervene, explainable | 6→11 | PARTIAL |
| Digital twin (Siemens/NVIDIA) | Simulate-before-act; USD/Omniverse later | 2 BUILT / 22.7 | PARTIAL |
| Predictive maintenance + dashboard (Augury/Tractian/Cognite) | Open, provenance-logged RUL/anomaly | 4 BUILT / dashboard 12.5 | PARTIAL |
| Fleet orchestration to standards (InOrbit/Open-RMF) | **Integrate** OpenRobOps/Open-RMF beneath us; VDA 5050 conformance | 16 | PLANNED |
| Observability/teleop (Formant/InOrbit) | OTel + operator surface + fleet data ops | 12.5+ | PLANNED |
| Evals/guardrails (ex-Galileo, now Cisco) | Tool-selection/action-completion/coherence evals → runtime guardrails | 20 | PLANNED |
| Determinism/safety heritage (Rockwell/Siemens) | LLM-planner/SIL-executor; integrate customer PLC | 17 | PLANNED |
| Trust: signed evidence + PQC (us) | Audit chain + Annex IV + crypto-agility | 13.5/18/19 | PLANNED |

**Posture per competitor band** (full landscape + maps: [market-viability HTML §3–6](research/market-viability-2026-06/index.html)): incumbents → we are the open/neutral/inspectable layer that integrates their equipment; fleet platforms → we are the trust layer above (integrate, don't fight); Cisco/Galileo → we are the industrial-grade version (OT + SIL + signed evidence + PQC); new entrants (Ati, GRID) → we are the one with a regulator-shaped spine.

## 14. ICP & buyer personas (qualitative, grounded in research §14.4)

**Ideal customer profile:** EU-exposed warehouse/fulfillment or light-manufacturing operator, 2+ robot vendors on the floor (or humanoid pilots arriving), existing WMS/MES, a compliance function that has read the AI Act, and an integration budget that already hurts (50–100% of hardware cost).

| Persona | Role in deal | What they buy | Veto risk |
|---|---|---|---|
| **Warehouse/plant ops lead** | Economic buyer | Throughput without headcount; downtime that fixes itself; one pane for mixed fleets | "Another dashboard" fatigue → lead with the A/B slice metric |
| **OT/IT integrator (in-house or SI)** | Technical buyer + channel | Standards adapters that delete custom glue; compose-up deploy; OSS inspectability | NIH / fear of displacement → we reduce their custom code, not their revenue |
| **Compliance / EHS officer** | Veto-holder | Art. 12 logging, Art. 14 oversight, Annex IV pack on demand | Overclaim allergy → BUILT/PARTIAL/PLANNED tags, signed evidence |
| **Security architect** | Gatekeeper (growing) | PQC posture for 10–20-yr assets; key custody (HSM swap); supply-chain transparency | "PQC is premature" → FIPS-aligned + crypto-agility framing, zero rip-out |

Buying committee insight (qualitative): the ops lead starts the conversation, the integrator implements, compliance signs off, security can stall — the product must hand each one their artifact (A/B metric, adapter docs, evidence pack, key-custody drill) without custom work.

## 15. GTM & adoption/integration playbook

**Motion: OSS-land → prove → paid pilot → SI channel** (detail: [KB_26 §8](knowledge-base/KB_26_Product_Market_Strategy.md), [market-viability HTML §9](research/market-viability-2026-06/index.html)).

1. **Land ($0, friction-free):** Docker Compose next to the existing WMS/fleet manager; reads existing Postgres/MQTT; **shadow mode** (observe + predict only, zero actuation risk).
2. **Prove (30–90 days):** counterfactual report — "we would have prevented X" — the Stage 6 A/B artifact, generated against the customer's own incidents.
3. **Pilot (paid, 3–6 months):** advisory → gated actuation on ONE workflow under the safety wrapper; weekly signed evidence pack to compliance. Priced against the $30–150k integration baseline the customer already pays (research §14.4).
4. **Expand (SI channel):** integrators carry it — the OSS control plane standardizes their glue work (they keep services revenue); Stage 23 conformity dry-run unlocks regulated verticals.

**The 90-day integration claim is a target, not a boast:** it is auditable against the sourced 3–6-month hardware ramp and the WMS-divergence failure mode our canonical envelope + CDC attack directly. Measured at first pilot (Stage 22) or revised.

## 16. Monetization & open-core strategy (options — no commitment before a pilot; hard rule 9 holds: zero paid cost at build time)

| Option | Model | Precedent | When viable |
|---|---|---|---|
| A (default) | **Open-core**: Apache 2.0 spine (runtime, adapters, simulator); commercial tier = evidence-pack automation, fleet-scale features, signed-report service, support SLAs | PickNik MoveIt/MoveIt Pro (research §14.5) | After Stage 19 (evidence pipeline is the natural commercial seam) |
| B | **Paid pilots + support/integration contracts** ($150–400k/yr/site, estimate per SOM method) | InOrbit pre-Series-A motion | After Stage 6 slice + first reference (Stage 22) |
| C | **Managed control plane** (hosted, post-GA) | Standard OSS-to-cloud path | Post-Stage-24 only |

Profit logic (qualitative, honest): the commodity layers (orchestration) stay free and grow adoption; the layers buyers MUST pay for under regulation (evidence, safety attestation, key custody) are the commercial seam. That seam is defensible precisely because it is the niche (§1) — nobody else is building it vendor-neutrally.

## 17. Evals & success metrics

Methodology, datasets, baselines, CI wiring: [KB_23_Evals_and_Benchmarks.md](knowledge-base/KB_23_Evals_and_Benchmarks.md). **All targets are commitments-to-verify unless marked measured.**

**A. System/performance:** sim throughput ~500 units/hr ±10% (Stage 2, **measured**); event→WS fan-out p95 ≤ 250 ms (broker path **measured 11.6 ms**); agent decision latency p50 ≤ 2 s / p95 ≤ 5 s (11); **Stage 6 slice A/B: intervention vs no-intervention downtime delta on the machine-failure scenario — a measured number, not a target, before close**; cycle-time −25–30% and carbon −15–20% (pilot targets, 22); uptime ≥ 99.5% (21).
**B. Trust/safety/compliance:** audit-chain verifies end-to-end anytime (13.5+); Annex IV pack ≤ 60 s (19); 100% actuator paths safety-gated (17, CI-enforced); prompt-injection block ≥ 99% on OWASP LLM01 + NIST Agentic corpora (20); zero cross-namespace memory reads (12); VDA 5050 conformance 100% (16); A2A interop between 2 independent instances (14).
**C. Crypto-agility:** hybrid PQC TLS on 100% external boundaries (18); key rotation ≤ 15 min zero downtime (18, re-drilled 25); HSM provider swap config-only with chain still verifying (13.5 spec / 22 drill); algorithm swap via `migrate(old,new)` (25).
**D. Operator dashboard:** live activity p95 ≤ 1 s; alarm delivery p95 ≤ 2 s (12.5); 100% events actor-class-tagged (11+); signed report export ≤ 10 s (19).
**E. Business (new in v3; design targets):** time-to-integrate ≤ 90 days at pilot; 1 reference pilot with published A/B by Stage 22; slice-demo → pilot conversion tracked from first demo; SOM re-estimated at every CTO checkpoint.

**Production-grade workflow requirement (binding, from v2.1.6):** durable LangGraph state checkpointed to Postgres (crash-resume ≤ 30 s); HITL `interrupt()` for SIL-1; idempotent tool calls + bounded retries + compensation; per-tool RBAC + budget caps in-loop; non-determinism confined to planning nodes; zero duplicate actuator commands on replay (verified Stage 11+).

## 18. Roadmap (de-risked, re-sequenced to actuals — NO new stages)

Stages 0–5 reflect what actually shipped (the v2.0 table's Stage 5 "defect detection" moved later; demand forecasting landed as Stage 5). CTO checkpoints every 10 closures.

| # | Stage | Status |
|---|---|---|
| 0–1 | Planning refresh · Foundation & KB (Alembic, secrets sweep, baseline locked) | ✅ Done |
| 2 | SimPy DES — 6-event catalog → `incidents` (deterministic, calibrated) | ✅ Done |
| 3 | WebSocket broker + Redis fan-out (11.6 ms p95 measured) | ✅ Done (3.5 CTO #1 interim — independent pass owed, G-031) |
| 4 | Predictive maintenance — XGBoost failure predictor (PR-AUC 0.847, carded) | ✅ Done |
| 5 | Demand forecasting — LSTM (MAPE 21%, +59% vs persistence, carded) | ✅ Done |
| **6** | **Vertical Slice v0: predict → diagnose → intervene, sim-closed-loop on the machine-failure scenario, measured A/B** (CTO #1's gate; `tasks/STAGE_06_vertical_slice_predict_diagnose.md`) | ⏭️ **Next** |
| 6.5 | Energy intelligence (KB_20) — deferred until after the slice | ⚪ |
| 7 | RL intervention (PPO recovery policies — deepens slice intervene) | ⚪ |
| 8 | World model + causal diagnose (LSTM-AE/Transformer + causal twin — deepens slice diagnose) | ⚪ |
| 9 | Vision + defect detection (YOLOv10, Real-IAD/KSDD2) | ⚪ |
| 10 | Explainability (SHAP + DiCE counterfactuals) · **10.5 CTO #2** | ⚪ |
| 11 | **Production slice**: LangGraph durable runtime + HITL + repair-dispatch + active diagnosis + Ollama fallback proven (G-005/G-014/G-025/G-026/G-036) | ⚪ |
| 11.5 | MCP server suite (×5, schema-tested, RBAC) | ⚪ |
| 12 / 12.5 | Agent memory (Mem0/pgvector/Neo4j) · Observability (OTel/Langfuse/Phoenix) + PdM dashboard (G-006) | ⚪ |
| 13 / 13.5 | CDC ingestion · **PQC Foundations (KeyProvider, ML-DSA-65 signing, audit_chain)** | ⚪ |
| 14 / 14.5 | A2A surface (signed cards, hybrid mTLS) · CTO #3 | ⚪ |
| 15 / 16 | OT/IT bridge (OPC UA, Sparkplug B, ISA-95) · Fleet adapter (VDA 5050 + **OpenRobOps/Open-RMF integration**) | ⚪ |
| 17 / 18 | Functional safety wrapper · PQC Wave 2 (hybrid TLS everywhere, SLH-DSA firmware) | ⚪ |
| 19 / 20 | Evidence pipeline (Annex IV generator) · Red-team eval harness (CI gate) | ⚪ |
| 21 / 21.5 | DR/HA/chaos · CTO #4 | ⚪ |
| 22 / 22.5 / 22.7 | Pilot runbook (re-fit brains on real telemetry, G-035) · KubeEdge edge · USD/Omniverse twin | ⚪ |
| 23 / 24 / 24.5 / 25 | Conformity dry-run · GA · CTO #5 · Post-GA (rotation drill, federation, post-market monitoring) | ⚪ |

**Sequencing principle (CTO #1, binding):** depth before breadth. Stages 6–11 build ONE vertical slice to production grade; N-domain heads, energy, dynamic features, and twin upgrades come after. No stage opens while its predecessor's gaps are unledgered.

## 19. Risks & honest viability verdict

**Risks (refreshed June 2026):**
1. **Incumbent bundling accelerating** — Siemens+NVIDIA "fully AI-driven factory" blueprint starts 2026 (Erlangen). *Mitigation:* stay the open/neutral/provable layer; integrate their equipment; never compete on distribution.
2. **Cisco extends Galileo toward OT** before Stages 11–20 ship. *Mitigation:* OT standards + SIL + PQC depth is multi-year work Cisco must also do; our slice-first sequencing shortens our proof time.
3. **Agentic entrants add compliance stories** (Ati, GRID). *Mitigation:* evidence architecture (signed chain) is structural, not a feature toggle; ship 13.5 on schedule.
4. **EU softening dilutes the compliance leg.** *Mitigation:* compliance is one leg of four; OEE/self-healing value stands alone.
5. **Spec-deep/code-thin (the dominant risk, CTO #1).** *Mitigation:* Stage 6 slice gate; spec freeze; carry-forward ledger; independent audits.
6. **Solo execution bandwidth.** *Mitigation:* de-risked sequencing; honest statement: a founding team/first hires is the real fix (qualitative).
7. **Functional-safety hubris** — one LLM-driven SIL incident ends the project. *Mitigation:* architectural split, CI-enforced gate, conformity dry-run before any actuating pilot.
8. **Free-tier LLM single point of failure** (Groq). *Mitigation:* Ollama-local fallback proven as a Stage 11 acceptance criterion.
9. **Proxy-trained brains oversold.** *Mitigation:* model cards state proxy status; G-035 blocks production claims until pilot re-fit.

**Viability verdict (honest, full analysis in the [market-viability HTML §10](research/market-viability-2026-06/index.html)):** The lane is real, widened in June 2026, and fundable on comparables (Galileo exit; InOrbit Series A; BMW i Ventures $300M / KOMPAS €160M physical-AI funds) — **conditional on a working closed loop (Stage 6) and a reference pilot (Stage 22)**. Where we will NOT win: out-distributing Siemens/Rockwell; sensor-PdM hardware; pure fleet orchestration (free commodity). Winning outcome: the trusted neutral layer regulated multi-vendor operators adopt → SI-channel revenue → strategic partnership or acquisition by an incumbent that needs the trust stack.

## 20. Process & lifecycle requirements

Per-task lifecycle (CLAUDE.md §5): `/begin` → `start-task.sh` → implement under role persona → `audit-task.sh` → `rectify-task.sh` → **independent audit by a different agent (PASS required)** → hand-off → `seed-next-task.sh` → KB updates → `close-task.sh` (baseline strictly decreases or justified hold). CTO checkpoint every 10 closures; carry-forward gaps ledger folds into each stage's acceptance criteria (hard rule 10); every web-research session appends to `research/initial-research.md`; every architectural decision is a new ADR; **product/market decisions are owned by the `product-manager` role** (new in v3 — `.claude/skills/product-manager/SKILL.md`), which maintains this PRD chain, KB_26, and the viability artifacts, and may not expand build scope without an ADR + CTO alignment.

## 21. Related documents

- [CLAUDE.md](CLAUDE.md) — session entrypoint, roles, hard rules · [SKILLS.md](SKILLS.md) — persona index
- [KB_24](knowledge-base/KB_24_System_Design_HLD_LLD.md) HLD/LLD · [KB_25](knowledge-base/KB_25_Causal_SelfHealing_Engine.md) self-healing engine · [KB_26](knowledge-base/KB_26_Product_Market_Strategy.md) product-market strategy (new) · [KB_23](knowledge-base/KB_23_Evals_and_Benchmarks.md) evals · [KB_12](knowledge-base/KB_12_Standards_Map.md) standards · [KB_13](knowledge-base/KB_13_PQC_Crypto_Strategy.md) PQC · [KB_19](knowledge-base/KB_19_Competitor_Comparative_Governance.md) competitor governance matrix · [KB_11](knowledge-base/KB_11_Pitch_Strategy.md) pitch layer
- [research/market-viability-2026-06/index.html](research/market-viability-2026-06/index.html) (June 2026, sourced) · [research/market-analysis/index.html](research/market-analysis/index.html) (May 2026) · [research/system-explainer/index.html](research/system-explainer/index.html) · [research/strategic-reset-explainer/index.html](research/strategic-reset-explainer/index.html) (this reset's change log)
- [audits/OPEN_GAPS_LEDGER.md](audits/OPEN_GAPS_LEDGER.md) · [audits/CTO_1_review.md](audits/CTO_1_review.md) · [compliance/risk-register.md](compliance/risk-register.md)
- ADR trail: [compliance/decision-logs/](compliance/decision-logs/) — this version: `2026-06-11_strategic_product_reset.md`

---

*PRD v3.0 — authored 2026-06-11 under the `product-manager` + `agentic-governance-engineer` personas as part of the out-of-band Strategic Product Reset. This file is frozen on the next PRD version's creation (hook-enforced).*
