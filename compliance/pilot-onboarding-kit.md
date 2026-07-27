# Pilot Onboarding Kit (Stage 22)

> The **buildable half** of CTO #4 R11 / G-035 / G-043 — "the single biggest fundability/credibility gap." Everything
> in the platform is validated on proxies/benchmarks/simulator; there is **no real actuator and no buyer yet**. That
> real engagement cannot be built free/local (it needs a customer + a real fleet — Rule 9). What CAN be built now, and
> is here, is the **kit that lets a real pilot start day-one**: an onboarding checklist, a data-intake spec, an
> A/B-measurement protocol, and the real-fleet re-fit plan. The actual pilot + published A/B remains honestly
> deferred + ledgered (G-035/G-043). Research §32; ADR `2026-06-22_stage22_pilot_deployment_runbook.md`.

## 1. Pilot onboarding checklist (per site)

- [ ] **Scope & intended purpose** agreed + documented (feeds Annex IV §intended-purpose); ICP fit per KB_26.
- [ ] **Site OT inventory** — PLCs/AGVs/AMRs, protocols in use (OPC UA / Sparkplug B / VDA 5050), firmware versions.
- [ ] **Read-only integration first** — connect via the Stage-15 OPC UA client + Sparkplug subscriber in
      OBSERVE-ONLY mode; verify ISA-95 graph populates (`graph_isa95.populate_from_ot_event`). No writes yet.
- [ ] **Deployer obligations** walked through with the customer (pilot-deployment-runbook §3, Art-26); overseers named + trained.
- [ ] **Pre-flight gate** green on the customer stack (runbook §0).
- [ ] **Go-live wiring** scheduled (runbook §4 — R5 sil_bridge + R4 A2A mTLS) BEFORE any actuation.
- [ ] **Baseline window** recorded (see §3) before the agent influences anything.

## 2. Data-intake specification

What the pilot needs from the site to re-fit the proxy models onto real data (§4):

| Data | Used for | Format | Notes |
|---|---|---|---|
| Equipment telemetry (vibration/temp/torque/speed/tool-wear or site analogues) | RUL/failure model re-fit (Stage 4/8) | time-series CSV/historian export or live OPC UA | map site tags → the model feature schema (`ml/failure_predictor.feature_names`) |
| Defect images (if visual QC) | defect classifier re-fit (Stage 9) | labelled image folders | per-class; for transfer-learning fine-tune |
| Maintenance / work-order logs | diagnosis grounding + A/B downtime baseline | CSV | timestamps + action + outcome |
| Incident history | episodic memory seed (Mem0) + risk calibration | CSV/JSON | namespaced per site (`incident:<site>`) |
| Production / OEE records | A/B throughput baseline | CSV | shift-level |

All site data is namespaced (`incident:<site>` / `semantic:<site>`); cross-namespace isolation is RLS- + `_authorize`-
enforced (Stage 19/22). Retention + Art-26 input-data governance per the runbook.

## 3. A/B measurement protocol (the published-A/B template — G-043)

The credibility deliverable is a **measured** before/after, not a claim:

1. **Baseline (control) window** — N weeks, agent in OBSERVE-ONLY (records recommendations, does not act). Capture:
   unplanned-downtime minutes, OEE, defect rate, MTBF, mean-time-to-diagnose.
2. **Treatment window** — same length, agent in assisted/supervised-autonomous. Same metrics.
3. **Analysis** — paired comparison with confidence intervals (reuse the Stage-6/CRN A/B harness pattern,
   `backend/scripts/run_slice_ab.py`); report effect size + CI, not a point estimate; pre-register the primary metric
   (unplanned downtime) to avoid cherry-picking (KB_23 anti-gaming).
4. **Publish** — the signed result + method into the evidence set (audit_chain + a research/ A/B artifact), feeding the
   Annex IV performance section and the GTM case study (KB_26).

## 4. Real-fleet re-fit plan (G-035)

Every model currently on a proxy/benchmark, and its re-fit path onto real site data:

| Model | Current (proxy/benchmark) | Re-fit on real data |
|---|---|---|
| RUL / world model (Stage 8) | C-MAPSS FD001 Transformer | fine-tune/transfer on site telemetry (feature-map + the data-intake export) |
| Failure predictor (Stage 4) | AI4I/UCI predictive-maintenance | re-fit on site equipment + work-order labels |
| Defect classifier (Stage 9) | NEU-CLS transfer-learning | fine-tune on site defect images |
| RL intervention (Stage 7) | SimWorld MaskablePPO | re-train on the site's calibrated SimWorld + real maintenance constraints |
| Causal diagnosis (Stage 8) | learned PC on SimWorld rollouts | re-discover on real telemetry; validate edges with site engineers |

Each re-fit keeps the model-card + `*.metrics.json` discipline (Hard Rule: no weights without a card) and re-runs the
red-team + safety gates before the model goes live in the pilot.

## 5. Honest status

- **BUILT (this kit):** the checklist, data-intake spec, A/B protocol, and re-fit plan — a real engagement can start
  day-one against them.
- **DEFERRED (needs a buyer/real fleet — not free/local-buildable, G-035/G-043, ledgered):** the actual customer pilot,
  the real-data re-fits, and the published A/B. This is the platform's biggest remaining credibility gap, and it is
  named as such, not hidden.

## 6. Stage-32 addendum — the capabilities added since Stage 22

The pilot package is now completed for everything Stages 26–31 shipped. Use the new companion docs alongside this kit:
`pilot-charter-template.md` (predefined success criteria + Scale/Iterate/Pivot/Stop gates — the discipline ~60% of
pilots skip), `capability-readiness-matrix.md` (the honest sim-vs-real inventory with every measured number), and
`pilot-ab-protocol.md` (the per-capability A/B design). Additional data-intake beyond §2:

| Data | Used for | Format | Notes |
|---|---|---|---|
| Real hourly demand / order history | demand-forecaster re-fit (Stage 5/30 — bike-proxy → real orders, G-036) | time-series CSV | maps to the forecaster's feature schema; the service already SERVES it once it flows |
| Purchase orders, lead times, supplier reliability | supply-chain Contract-Net re-fit (Stage 26) | CSV / ERP export | drives the (s,S) ROP + supplier bids (currently observed-proxy) |
| Site SOPs + equipment/ISA-95 topology | GraphRAG grounding corpus (Stage 28/29 — replaces the 4-SOP demo corpus) | docs + graph export | the "ask the factory" answers cite these instead of demo SOPs |
| Real operator questions + phrasings | conversational QA + NL-injection tuning (Stage 29) | logged transcripts | measures parse accuracy + honest-abstain + answer usefulness |
| Real inbound-request traffic (labelled) | injection-detector re-fit + threshold tuning (Stage 31 — corpus 217 → real traffic) | labelled prompts | the learned tier's "1.0" is a single-corpus number until this exists |
| Runtime behavioural baseline | continuous behavioural monitor warmup (Stage 31) | (auto-collected) | the online robust-Z baseline forms during the shadow window |

The re-fit discipline (§4) applies to all: no weights without a model-card + `*.metrics.json`; re-run the red-team +
safety gates before any re-fitted model goes live; the injection classifier + behavioural monitor re-baseline on real
data during the shadow window.
