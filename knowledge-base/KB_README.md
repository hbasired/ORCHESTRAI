---
name: Knowledge Base Index & Update Contract
description: Master index for the project's knowledge base; defines the file shape, update rules, and the closure ritual every stage runs before merging
type: index
last-updated: 2026-06-11
---

# Knowledge Base — Index

> The knowledge base is the project's **source of truth**. The 25-stage roadmap ([PRD v3 §18](../PRD-ai-embodied-agent-v3.md)) and the per-stage task docs (`tasks/STAGE_NN_*.md`) drive what gets built; the KB records what *is*. Code, READMEs, and marketing claims drift; the KB is the place where reality is kept honest. ~~The 15-stage plan (`yor-are-an-agentic-optimized-cookie.md`)~~ *(superseded by the 25-stage roadmap, 2026-05-18; pointer updated to PRD v3, 2026-06-11.)*

## File shape (every body file)

```
---
name: <Title>
description: <one-line hook for grep-ability>
type: <user | feedback | project | reference | spec | catalog>
last-updated: YYYY-MM-DD
---

# Title

## Purpose
<one paragraph: what this file owns>

## Source of truth
<which code/dataset/system this file mirrors; how to verify it's still accurate>

## Body
<the actual content, freely structured>

## Last verified
<YYYY-MM-DD, by whom, against which commit SHA>
```

## The body files — KB_01–KB_26 (extended 2026-06-11 for PRD v3.0)

| File | Owns |
|---|---|
| `KB_01_System_Architecture.md` | Actual code architecture (services, data flow, deployment topology) — verified against the repo, not marketing claims |
| `KB_02_Models_Inventory.md` | Every ML model: class file, weights file, training script, dataset, status, last metrics, hyperparameters |
| `KB_03_Datasets_Catalog.md` | Every approved dataset: source URL, license, size, download command, target model, sanity-check notebook |
| `KB_04_Data_Schema.md` | Postgres schema, Redis keys, SimPy entity model, WebSocket message envelopes, Pydantic schemas |
| `KB_05_Simulation_Spec.md` | SimPy entity definitions, scenario catalog, problem catalog (machine_crack, robot_down, late_delivery, demand_spike, defect_surge, power_dip) |
| `KB_06_Agent_Coordination_Protocol.md` | Embodied agent ↔ sub-agents message format, decision protocol, conflict resolution, override semantics; LangGraph + MCP + A2A reframe |
| `KB_07_API_Contracts.md` | REST + WS endpoints with request/response schemas; the canonical backend↔frontend contract |
| `KB_08_Frontend_Pages_Spec.md` | Per-page: which API + WS topics it consumes, which interactions it produces, animation rules |
| `KB_09_UX_Scenarios.md` | 60-second demo storyboard with timing; problem-injection flow; chat + DB-driven scenarios |
| `KB_10_Production_Hardening.md` | Secrets policy, MLOps, monitoring, CI/CD, drift detection, reliability targets, **latency budget**, EU AI Act + NIST RMF controls, **PQC posture** |
| `KB_11_Pitch_Strategy.md` | Target customers, value props, demo storyboard, KPIs, ROI math, comparable startups, pilot playbook |
| `KB_12_Standards_Map.md` | **(NEW)** Industrial standards adopted — VDA 5050, OPC UA, MQTT Sparkplug B, ISA-95, ROS 2, ISO 10218 / IEC 61508 / ISO 13849-1 / IEC 62061, ISO/IEC 42001 |
| `KB_13_PQC_Crypto_Strategy.md` | **(NEW)** Post-quantum crypto placement (ML-DSA-65, ML-KEM-768, SLH-DSA-128s, HMAC-SHA-384), library matrix, key lifecycle, CNSA 2.0 timeline |
| `KB_14_Agent_Memory_Architecture.md` | **(NEW)** Five memory layers — working/episodic/semantic/procedural/audit. Mem0 + pgvector + Neo4j ISA-95 + audit_chain. SQL not NoSQL |
| `KB_15_Observability_Evidence_Pipeline.md` | **(NEW)** OpenTelemetry GenAI semconv + Langfuse (self-hosted) + Arize Phoenix; separate immutable evidence sink |
| `KB_16_A2A_MCP_Protocols.md` | **(NEW)** MCP servers (internal agent→tools) + A2A surface (external agent↔agent); agent-card schema; trust boundary |
| `KB_17_Functional_Safety_Wrapper.md` | **(NEW)** LLM-as-planner / SIL-as-executor; safety contract DSL; STO/SS1 paths; ISO 10218 / IEC 61508 / ISO 13849-1 / IEC 62061 mapping |
| `KB_18_Governance_Evidence.md` | **(NEW)** ISO/IEC 42001 + 42005 + 42006 + EU AI Act + NIST AI RMF Agentic + OWASP LLM Top 10 control mapping; Annex IV doc-pack generator; policy DSL; per-tool RBAC; budget caps |
| `KB_19_Competitor_Comparative_Governance.md` | **(NEW 2026-05-24)** Side-by-side vs Galileo Agent Control / Guild.ai / Huawei Pangu / Project Aether; 19-dimension matrix (perf/latency/efficiency/transparency/explainability/auditability/robustness/safety/crypto/standards); positioning statement |
| `KB_20_Energy_Intelligence.md` | **(NEW 2026-05-24)** Microgrid PPO + BatteryLife Transformer RUL + carbon-aware computing. New domain added in response to Project Aether report. Stage 6.5. |
| `KB_21_Edge_Compute_KubeEdge.md` | **(NEW 2026-05-24)** CNCF KubeEdge cloud-edge continuum with offline autonomy + ArgoCD GitOps + MLflow registry. Stage 22.5. |
| `KB_22_Digital_Twin_USD_Triplet.md` | **(NEW 2026-05-24)** NVIDIA Omniverse USD digital twin + Digital Triplet (Physical + Twin + GenAI semantic layer). Siemens Xcelerator Mega Blueprint alignment. Stages 22.7 + 25.5. |
| `KB_23_Evals_and_Benchmarks.md` | **(NEW 2026-05-31)** Evaluation suites, datasets, baselines, quantitative thresholds + CI gates per stage. Measurable contract behind PRD v2.1 §v2.1.2 / v2.0 §11. |
| `KB_24_System_Design_HLD_LLD.md` | **(NEW 2026-05-31)** High-Level + Low-Level system design (layers, flows, deployment, failure modes; component contracts, schemas, sequences). Owned by the `system-designer` role. |
| `KB_25_Causal_SelfHealing_Engine.md` | **(NEW 2026-05-31)** The additive innovation — predict→causally-reason→verify→intervene self-healing loop (learned world model + causal digital twin + neuro-symbolic verification + RL recovery); maps the LSTM/YOLO/RL/DL stack + the dynamic operator features. |
| `KB_26_Product_Market_Strategy.md` | **(NEW 2026-06-11)** Product-market strategy layer — market sizing, ICP/personas, problems matrix, competitive snapshot (June 2026), positioning + claim discipline, monetization options, GTM/adoption playbook, honest viability verdict. Owned by the `product-manager` role; reviewed at every CTO checkpoint. Supersedes KB_11 on positioning/claims conflicts. |
| `KB_TASK_LOG.md` | Append-only log of every stage: what shipped, what didn't, what we learned, next-stage adjustments |

## Update rules (enforced by `scripts/audit.sh` + CI gate)

1. **At the end of every stage**, every KB file listed in the stage's "KB Updates Expected" block **must be touched** in the same PR as the code changes. CI rejects merges where code changes but the listed KB diff is absent.
2. The `Last-updated` field gets bumped to the merge date.
3. The `Last verified` block at the bottom of each body file records who verified the content against which git SHA. If the body claims something the code doesn't say, the body wins until the code catches up — but the discrepancy lands in `KB_TASK_LOG.md` as a follow-up.
4. **Outdated guidance gets strikethrough, not deletion**. We need to see how our thinking evolved (mirrors the protocol in `research/initial-research.md`).
5. **`KB_TASK_LOG.md` gets a new entry every stage** — Shipped / Skipped / Learned / Next-stage adjustments. No exceptions.
6. **Decision logs** for architectural choices land in `compliance/decision-logs/YYYY-MM-DD_<topic>.md` (also serves as EU AI Act Article 12 evidence). The KB cross-references the decision log file rather than duplicating the rationale.

## How this directory was bootstrapped

Stage 1 (per `tasks/STAGE_01_foundation_and_kb.md`) created the 13 files with initial content drawn from:
- The original audit (`yor-are-an-agentic-optimized-cookie.md` Appendix B + B.4).
- The original research (`research/initial-research.md` Sections 1–5).
- The Stage 0 refresh (`research/initial-research.md` Section 6 — May 2026 updates: EU AI Act, NIST RMF Agentic Profile, LangGraph, MsFormer, LeWorldModel, Isaac Sim, Real-IAD, latency budget).

Subsequent stages overwrite stale content with fresh observations from the codebase, training runs, and pilot interactions.

## Reading order for a new session

If a future Claude session needs to come up to speed, read in this order:

1. `CLAUDE.md` (repo root) — Claude Code session entrypoint, role decision tree, hard rules.
2. `KB_README.md` (this file) — what the KB is and how it's maintained.
3. `KB_TASK_LOG.md` — what we just shipped, what we're about to do next.
4. `KB_01_System_Architecture.md` — what's actually running.
5. `KB_02_Models_Inventory.md` — what's trained, what's still untrained.
6. The current stage's task doc in `tasks/` (`scripts/load-context.py --mode=session-start` surfaces this automatically).
7. `KB_10_Production_Hardening.md` for the latency budget and compliance constraints that bound every change.
8. Stage-specific KB files (KB_12–18 for protocols / PQC / memory / observability / safety / governance work).

The SessionStart hook (`.claude/hooks/session_start.sh`) automates steps 2–6 by emitting the context bundle into Claude's context at session start. If the hook isn't registered, run the loader manually:

```bash
python scripts/load-context.py --mode=session-start
```

## Per-task lifecycle (PRD v2.0)

Every stage runs (order updated 2026-05-31 — next task doc is seeded BEFORE KB/.md updates):
```
scripts/start-task.sh <stage> <slug>  →  scripts/audit-task.sh  →  scripts/rectify-task.sh
  →  scripts/seed-next-task.sh <stage>   (generates the NEXT task doc here, before KB/.md updates)
  →  [append KB_TASK_LOG + update KB/.md]  →  scripts/close-task.sh   (next-task call is now an idempotent safety net)
```
Every 10 task closures: `scripts/cto-review.sh` (fresh Claude Code subprocess with `cto-reviewer` skill). See `CLAUDE.md` §5.
