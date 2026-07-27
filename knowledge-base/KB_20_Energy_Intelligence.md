---
name: Energy Intelligence
description: Microgrid optimization via PPO RL + Battery RUL via Transformer + Carbon-aware compute scheduling. New domain added 2026-05-24 in response to Project Aether gap analysis.
type: spec
last-updated: 2026-05-24
---

# KB_20 — Energy Intelligence (NEW DOMAIN — 2026-05-24)

## Purpose

Industrial facilities are simultaneously the consumers of energy AND, increasingly, the producers (renewables + BESS). PRD v1/v2 treated energy as a constraint variable. Project Aether (operator-supplied 2026-05-24 report) reframes it as a **first-class control domain** — the factory becomes a *Grid-Interactive Efficient Building* whose physical state optimises the energy grid and whose energy state constrains robotic operations.

This KB adds Energy Intelligence as a new pillar of the control plane. It is not a replacement for the existing manufacturing/robotics/supply-chain pillars; it sits alongside them.

## Source of truth

- Project Aether report (operator-supplied 2026-05-24).
- DeepMind data center cooling RL paper (40% energy reduction).
- BatteryLife dataset (2025) — 90,000+ samples / 16 integrated datasets / 80 chemistries / 12 temperatures / 646 charge-discharge protocols. ArXiv 2502.18807.
- US DOE Grid-interactive Efficient Buildings (GEB) framework.
- ISO 50001 (energy management systems) — complementary to ISO/IEC 42001 (AI management).

## Body

### Three sub-pillars

#### 20.1 Microgrid Optimization (PPO RL)

The factory's microgrid (solar + BESS + grid + variable loads) is controlled by a Deep RL agent.

- **State space:** Battery State of Charge (SoC), 24h solar forecast, factory load forecast, real-time grid price, current carbon intensity (kgCO₂/kWh from API), HVAC setpoint.
- **Action space (continuous):** charge battery rate, discharge to factory rate, discharge to grid (sell) rate, throttle robotic-fleet utilisation %.
- **Reward function:** `R = -(electricity_bill + λ_carbon * carbon_emissions + λ_throttle * production_delay)`. The λ_throttle penalty ensures the agent does not starve production to save electricity (a Project-Aether-style hard constraint).
- **Algorithm:** PPO (Proximal Policy Optimization) via Stable Baselines3. Validated baseline: Google DeepMind data center cooling RL achieved 40% energy reduction.
- **Implementation:** `backend/ml/energy/microgrid_ppo.py` (Stage 6.5 — see roadmap).

#### 20.2 Battery Remaining Useful Life (Transformer)

Stationary BESS health is critical for industrial energy resilience. AMR fleet batteries degrade rapidly under high-utilisation cycles.

- **Dataset:** BatteryLife (PRIMARY for battery work) — 90,000+ samples, Li-ion + Zn-ion + Na-ion, 8 formats, 80 chemical systems. Supersedes NASA PCoE for battery-specific use cases (we keep C-MAPSS for turbofan/RUL generic).
- **Model:** Compact Transformer encoder over voltage-capacity curves. Predicts FULL capacity loss curve (not just single cycle-life number) — enables health-aware charging.
- **Feedback loop:** when the model predicts accelerated degradation, the KubeEdge controller alters the robotic fleet's charging schedule to reduce thermal stress.
- **Implementation:** `backend/ml/energy/battery_rul_transformer.py` (Stage 6.5).
- **Acceptance metric:** MAE < 5% capacity at 80% SoH boundary.

#### 20.3 Carbon-Aware Computing

Heavy ML jobs (model retraining, batch inference) get scheduled when local grid carbon intensity is lowest.

- **Carbon-intensity source:** WattTime API (free tier) or ElectricityMaps API.
- **Scheduler hook:** custom Kubernetes scheduler plugin (when KubeEdge lands — Stage 22.5). Until then: scheduled cron jobs guarded by carbon-intensity check.
- **Policy** (registered in `compliance/policies/2026-NN-NN_carbon_aware_compute.yaml`):
  ```yaml
  name: carbon_aware_training
  scope: training_jobs.*
  rule: defer_until(grid_carbon_intensity < 200 gCO2/kWh)
  enforcement: soft  # warn, do not block, if local grid is consistently high-carbon
  ```
- **Edge inference:** by deploying models to the edge (KubeEdge), we avoid the transmission-energy cost of round-trip cloud calls. Documented as "Green AI" in ESG section of PRD v2.

### Why this is a competitive moat (vs Galileo / Guild.ai / Huawei / Project Aether)

| Capability | Galileo | Guild.ai | Huawei Pangu | Project Aether (blueprint) | **This project** |
|---|---|---|---|---|---|
| Microgrid PPO optimisation | NO | NO | Partial (cloud) | YES (planned) | **YES (Stage 6.5, after this update)** |
| Battery RUL with BatteryLife dataset | NO | NO | NO | YES (planned) | **YES (Stage 6.5)** |
| Carbon-aware compute scheduling | NO | NO | Partial | YES (planned) | **YES (Stage 6.5 + Stage 22.5 K8s scheduler)** |
| Integrated with safety wrapper (cannot starve production) | n/a | n/a | n/a | NO explicit | **YES — reward penalty λ_throttle + Stage 17 safety contract for power-throttle actions** |
| ML-DSA-signed energy decisions in audit_chain | n/a | n/a | n/a | NO | **YES — every microgrid decision goes through audit_chain** |
| Vendor-neutral (Apache 2.0; not locked to a cloud) | YES | YES | NO | YES | **YES** |
| Aligned with ISO 50001 (energy mgmt) + ISO/IEC 42001 (AI mgmt) | NO | NO | Partial | NO mentioned | **YES** |

Project Aether describes microgrid + battery + carbon — but as a **portfolio project blueprint**, not a production-grade architecture. We adopt the same domain coverage with our existing rigour (ML-DSA audit chain, safety contract integration, vendor neutrality, full standards mapping). **The result is a strictly stronger energy domain than the Aether blueprint.**

### Integration with existing domains

- **Manufacturing (Stage 4 PdM, Stage 5 defect, Stage 6 demand):** energy domain takes their forecasts as inputs (load forecast = sum of manufacturing stage forecasts).
- **Robotics (Stage 7 RL policy, Stage 16 VDA 5050):** PPO action `throttle_robotic_fleet` is mediated by VDA 5050 instantActions; safety wrapper (Stage 17) gates the throttle against minimum-throughput contracts.
- **OT/IT bridge (Stage 15):** OPC UA reads from real or simulated grid meters; Sparkplug B publishes microgrid state.
- **Observability (Stage 12.5):** energy decisions emit `energy.microgrid.decide` OTel spans; cost + carbon as labelled metrics in Langfuse.

### Standards we adopt

- **ISO 50001** — Energy management system. Add to KB_12 Standards Map.
- **DOE GEB framework** — Grid-interactive Efficient Buildings (informative).
- **IEC 61850** — Substation communication (for grid-side integration; deferred to Stage 25+ pilot).

## Last verified

2026-05-24, agentic-governance-engineer + ml-engineer review. Project Aether report referenced. Stage 6.5 task doc will be added in the next session (currently not in the 25-stage v2 roadmap — to be inserted between Stage 6 and Stage 7).
