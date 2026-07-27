# Capability-Readiness Matrix (Stage 32)

> The honest inventory of what the platform can do, WHAT it was measured on, and WHAT real data each capability needs
> before a pilot can validate it. Every number is from THIS build's SimWorld / benchmark studies (cited to the stage +
> results file) — none is a real-deployment number. The pattern throughout: **sim-proven → real-data dependency
> (G-035) → pilot A/B hypothesis**. This is the "sold honestly" artefact — a buyer sees exactly what is proven vs.
> what the pilot will test.

## Legend
- **Readiness:** `SIM-PROVEN` (measured on sim/benchmark, real-data re-fit needed) · `BENCHMARK-PROVEN` (measured on a
  real public benchmark, domain re-fit needed) · `BUILT-UNMEASURED` (shipped, pilot will measure) · `REAL-DATA-BLOCKED`
  (needs the site's data to even run meaningfully).

## Predictive & self-healing loop (KB_25)

| Capability | Readiness | Measured (this build) | Real-data dependency (G-035) | Pilot A/B hypothesis |
|---|---|---|---|---|
| RUL / failure prediction | BENCHMARK-PROVEN | Transformer RUL on C-MAPSS FD001, test RMSE 13.80 (beats CNN/LSTM), Stage 8 | re-fit on the site's equipment telemetry (map tags → feature schema) | earlier-warning → downtime ↓ |
| Learned causal diagnosis | SIM-PROVEN | causal-learn PC recovers the SCM hub, skeleton F1 0.75, Stage 8 | re-discover on the site's incident + telemetry history | correct root-cause ≥ threshold |
| Neuro-symbolic verify | BUILT | rejects unsafe plans under a binding PlantState, Stage 8/11 | site's crew/throughput/SIL constraints | 0 unsafe plans executed |
| Active diagnosis (probe→reason) | SIM-PROVEN | info-gain policy localizes the true fault @ ~0.87–0.97 conf in ~3–4 probes, Stage 29 | site's real agent/sensor probe reliabilities (tpr/fpr) | fewer unnecessary interventions |
| RL intervention (shadow) | SIM-PROVEN | MaskablePPO beats the rule −125.1 vs −137.4 (CI [6.0,18.71]) on the group-MDP; runs SHADOW in the runtime, Stage 7/30 | live agreement measurement before promotion | shadow→active only after agreement validated |
| **Repair-robot dispatch** | SIM-PROVEN | **downtime −47.9%, 95% CI [7696,12733]s** (paired A/B, Stage 30) | real fleet + physical-proximity routing | downtime reduction ≥ threshold |

## Supply chain (KB_25, second domain)

| Capability | Readiness | Measured | Real-data dependency | Pilot A/B hypothesis |
|---|---|---|---|---|
| Multi-agent Contract-Net coordination | SIM-PROVEN | **stockouts −51%, bullwhip −98%, material −73%** (10 paired seeds, Stage 26) | real orders/lead-times/supplier reliability | stockout reduction ≥ threshold |
| Disruption monitoring | SIM-PROVEN | detects a 10×-median freeze during the freeze, controlled drill PASS, Stage 26 | real supplier telemetry | detected-before-impact rate |
| Demand forecaster (served) | BENCHMARK-PROVEN | LSTM MAE 32.9 (Bike-Sharing proxy, +59% vs persistence); SERVED into the live 7-day forecast, Stage 5/30 | **real hourly demand history** (bike proxy → real orders) | forecast MAE vs the site's naive baseline |

## Conversational & adoption (Stages 28–29)

| Capability | Readiness | Measured | Real-data dependency | Pilot A/B hypothesis |
|---|---|---|---|---|
| GraphRAG grounding | SIM-PROVEN | grounded/honest-empty/citation-precision 1.0 on the 4-SOP corpus, Stage 28 | the site's real SOPs + ISA-95 topology | grounded-answer usefulness ≥ threshold |
| "Ask the factory" QA | BUILT | grounded from Art-12 traces + GraphRAG + live sim; Verifier honest-empty; live Groq cited real handles, Stage 29 | real operator questions + the site KB | operator-rated usefulness + citation correctness |
| NL problem injection | BUILT | NL → validated incident → the gated loop; Hard Rule 3 preserved, Stage 29 | real operator phrasings | parse accuracy + honest-abstain rate |
| Adoption UX (trust calibration / progressive autonomy / WIIFM) | BUILT-UNMEASURED | shipped on real data / honest-empty, Stage 28 | real operators (adoption is a human outcome) | adoption / trust telemetry ≥ threshold |

## Safety, security & evidence

| Capability | Readiness | Measured | Real-data dependency | Pilot gate |
|---|---|---|---|---|
| Functional-safety wrapper (validator/sil_bridge/STO-SS1) | BUILT | every actuator path validator-gated + trace-paired (CI-enforced), Stage 17 | certified PLC + accredited assessment (G-011) | **0 unsafe actuations (hard gate)** |
| Prompt-injection detector | SIM-PROVEN | learned tier: detection 0.9935→1.0, FPR 0.0156→0.0 (held-out CV, Stage 31) | real-traffic + multilingual corpus | detection/FPR on the site's real inputs |
| Continuous behavioural monitor | BUILT | robust-Z + trajectory checks; labelled eval 1.0/0.0, Stage 31 | real runtime behaviour baseline | anomalies caught / false-alarm rate |
| PQC-signed audit chain | BUILT | ML-DSA-65, chain verifies 10k+ rows exit 0, Stage 13.5+ | — (production-ready) | **chain verifies throughout (hard gate)** |
| A2A authentication (SPIFFE mTLS) | BUILT | SVID-mTLS peer auth, foreign-domain rejected, Stage 27 | production node attestation / mesh | authenticated peers only |

## Platform / performance

| Capability | Readiness | Measured | Notes |
|---|---|---|---|
| Sim throughput | SIM-PROVEN | ~500 units/hr ±10% (Stage 2) | the digital twin, not the site |
| Event→WS fan-out latency | MEASURED | p95 11.6 ms (broker path) | real code path |
| DR restore | BUILT | RTO ~4 s, restore-verify asserts parity, Stage 21 | free/OSS DR; production HA = pilot/cloud |

## The honest bottom line
- **Nothing here is a real-deployment number.** The platform is pilot-DEPLOYABLE and its value is measured on
  simulator + public benchmarks; the pilot converts these to real evidence (G-035/G-043, buyer-blocked).
- The two **hard safety/evidence gates** (0 unsafe actuations; chain verifies) are production-ready properties, not
  pilot hypotheses — they must hold from day one.
- Certification (accredited functional-safety + CE/EU-registration, G-011) needs an accredited body + certified PLC —
  a real-engagement item, not buildable free/local.
