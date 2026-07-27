---
name: Pitch Strategy
description: Target customers, value props, demo storyboard, KPIs, ROI math, comparable startups, pilot integration playbook
type: spec
last-updated: 2026-06-11
---

# KB_11 — Pitch Strategy

## Purpose
The translation layer between what we are building and what an investor / pilot customer is buying. If a roadmap decision doesn't move one of these levers, it can wait.

> **2026-06-11:** the strategy layer above this file is now [`KB_26_Product_Market_Strategy.md`](KB_26_Product_Market_Strategy.md)
> (owned by the `product-manager` role), with the sourced June-2026 analysis in
> [`research/market-viability-2026-06/index.html`](../research/market-viability-2026-06/index.html). Where this
> file and KB_26 conflict on positioning, claims language, or monetization, **KB_26 wins**.

## Target customers (2026)

| Customer | Pain | Our hook | Integration vehicle |
|---|---|---|---|
| **Amazon Robotics & Operations** | Warehouse fleet idle time + collision events under disruption | Embodied coordinator reduces robot idle time and collision events 25–30% in simulated disruption tests | MQTT + Postgres table writes (Stage 13 wedge) |
| **DHL Supply Chain** | Sortation throughput under late-delivery + demand-spike disruption | Cross-domain replan absorbs the disruption with single-digit throughput dip | REST API + DB integration |
| **Siemens (MES / PLC)** | Customers want an optimization brain *above* the MES they already paid for | Coordination layer (not a replacement); cohabits with Siemens MES, sells as add-on | Postgres + OPC-UA; namedrop Isaac Sim (Siemens uses it for Digital Twin Composer) |
| **Bosch (Tier-1 manufacturer)** | QA + predictive maintenance; mixed real + simulated sensor data | We trained on their own publicly released CNC dataset; credibility shortcut | MQTT + Postgres |
| **Huawei (Factory networks)** | Factory operations layer that combines with their 5G-for-industry play | Edge-friendly compose deploy; works with their network primitives | Containerized deploy + Postgres |

## Value propositions (locked)

1. **Cross-domain coordination** — most competitors optimize one domain at a time. Our embodied agent decides across all three (robotics, manufacturing, supply chain) in one cycle.
2. **Predictive, not reactive** — the world model gives the agent 5–60 minute foresight; agents act on predictions, not symptoms.
3. **Explainable by design** — SHAP + Integrated Gradients + DiCE counterfactuals per decision. ~~EU AI Act Art. 14 compliant out of the box.~~ *(2026-06-11 correction: overclaim — explainability is an Art. 14 human-oversight **enabler**; compliance is assessable only after the Stage 23 conformity dry-run. Approved claim language lives in KB_26 §6.)*
4. **Land-and-expand integration** — customers integrate by writing to a Postgres table (Stage 13). No new API to learn. Sales motion is *much* shorter than the typical industrial AI deploy.
5. **Trained on real industrial data** — Bosch CNC vibration, NEU-DET steel defects, M5 retail demand, Real-IAD industrial anomalies. Not synthetic toy data.
6. **Compliance-ready** — EU AI Act high-risk scaffolding from day 1; NIST AI RMF Agentic Profile controls baked in.

## Demo storyboard

See `KB_09_UX_Scenarios.md` for the 60-second auto-loop. Quantitative result the demo delivers:

> Same disruption, run twice: rule-based baseline loses 25% throughput for 5 minutes; our system loses 8% throughput for 90 seconds.

## ROI math (Stage 15 calculator)

Inputs: plant size (small / mid / large) + cycle time + energy cost + downtime cost. Output: projected € (or $) annual savings range based on our measured 25–30% throughput improvement on simulated disruptions.

Formula skeleton:
```
annual_savings = (baseline_throughput_loss - our_throughput_loss) × disruption_frequency × revenue_per_unit
               + (baseline_energy_use - our_energy_use) × annual_hours × energy_cost
               + (baseline_downtime_minutes - our_downtime_minutes) × downtime_cost_per_min
```

Bounded by published manufacturer figures (PdM delivers 10–25% reduction in maintenance costs, 25–30% breakdown elimination, 70–75% downtime reduction per industry reports — we under-claim to that range).

## Comparable startups (anchors for valuation conversation)

| Company | Funding | Domain | Why comparable |
|---|---|---|---|
| **Augment** | $85M Series A | Logistics AI teammate ("Augie") | Agentic logistics; similar TAM framing |
| **Pallet (CoPallet)** | $27M | Logistics workflow agents | 10× faster at half cost; conversation-driven |
| **Siemens Digital Twin Composer** | (incumbent, not startup) | Industrial Metaverse | Pepsico case study: 90% of issues identified pre-physical-modification — we cite as proof the *concept* works |

Series A AI average: $51.9M (30% higher than non-AI). Gartner: 40% of enterprise applications will feature task-specific AI agents by end of 2026 (vs <5% in 2025). 80% of warehouses operate without any automation today.

**2026-06-11 refresh (research §14; older rows above kept for the record):**

| Company | Event | Why it matters to the pitch |
|---|---|---|
| **Galileo → Cisco** | $68M raised; acquisition completed 2026-05-22 | The agent-reliability category is acquisition-grade — and the independent leader is gone; our OT-grade version of that category is unoccupied |
| **InOrbit** | $10M Series A (Sep 2025); open-sourced OpenRobOps (Feb 2026) | Fleet orchestration is now a free commodity — our pitch must sit ABOVE it (trust + self-healing), and integrate it |
| **Ati Robotics / General Robotics (GRID)** | Agentic-first entrants, 2026 | The lane is validated; none have evidence/safety/PQC — speed on Stages 6–13.5 is the moat-keeper |
| **BMW i Ventures $300M / KOMPAS VC €160M** | Physical-AI/industrial funds, 2026 | Capital exists for exactly this category — after a working slice + reference pilot |

## Moat candidate

The defensible IP claim is the **world-model + agentic-PdM coupling**: a single coordinated agent that predicts disruption and acts across robotics + manufacturing + supply chain simultaneously, trained per-customer. Competitors deploy single-domain optimizers; we deploy the layer above.

Future moat candidates (post v2):
- Federated learning across pilots (each plant's data improves the global model; the global model improves every plant). Premature today.
- Customer-specific reward weight tuning that the operator UI can adjust (already in scope — Stage 7).
- The Isaac Sim synthetic data factory pre-bakes customer-specific scenarios (Stage 9 unlocks).

## Pilot integration playbook (Stage 15 ships)

- **2-week pilot**: Postgres table integration only; operator dashboard + alerts. Customer continues to act manually; we surface the AI's recommendations.
- **4-week pilot**: Same + WebSocket realtime + voice interface (Stage 11) for one shift supervisor.
- **8-week pilot**: Full coordination loop (agent acts directly within bounded safety constraints); operator override surface; EU AI Act Art. 14 documented hand-off.

## Funding-stage strategy

- **Seed-equivalent (now → Q3 2026)**: ship Stages 1–8 + Stage 11; demo recorded; 1 paying LOI from a mid-market plant.
- **Series A target ($10M–$50M, late 2026)**: 3 paying pilots running; production drift monitoring active; EU AI Act scaffolding mature enough to satisfy a Siemens / Bosch procurement diligence call.

## What we are *not* claiming (honesty discipline)

- We are **not** replacing PLCs or MES. We sit above them as a coordination layer.
- We are **not** a robot OEM. We integrate with existing AMR fleets via MQTT / OPC-UA / DB writes.
- We are **not** an LLM company. We use Groq / Gemini / Ollama as substrates; the value is in the world model + RL + cross-domain coordination + compliance scaffolding.
- We are **not** EU AI Act *certified* on day 1. We are EU AI Act *scaffolded* so a pilot diligence call doesn't kill the deal in the first hour.

## Last verified
- 2026-05-11 — Plan-mode session. Comparable startup numbers, Gartner stat, and warehouse-automation figure cross-checked against Section 6.9 of `research/initial-research.md`.
