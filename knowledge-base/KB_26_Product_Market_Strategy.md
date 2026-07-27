---
name: Product Market Strategy
description: The product-market strategy layer — market sizing, ICP/personas, problems matrix, competitive snapshot, positioning, GTM motion, monetization options, adoption playbook, honest viability verdict. Owned by the product-manager role.
type: spec
last-updated: 2026-07-02
owner-role: product-manager
---

# KB_26 — Product Market Strategy

> **Purpose.** The single strategy source of truth above the pitch layer. KB_11 (Pitch Strategy) = demo/pitch
> material; KB_19 (Competitor Comparative Governance) = the governance-dimension competitor matrix. Neither is
> superseded — this file is the layer that decides *what we sell, to whom, against whom, and how we make money*.
> **Sources of truth feeding this file:** `research/initial-research.md §14` ·
> `research/market-viability-2026-06/index.html` · PRD v3 §§1–2, 13–16, 19.
> **Honesty rule:** every number here carries a source or an explicit "estimate (method shown)" label.

## 1. Market sizing (verified 2026-06-11; analyst scopes differ — treat as ranges)

| Layer | Figure | Source |
|---|---|---|
| TAM — warehouse robotics | $7.35B (2026) → $25.41B (2034), CAGR 16.8% | Fortune Business Insights (research §14.1) |
| SAM — AMR fleet-mgmt software | $198M (2026) → $567M (2034), CAGR 19.5% | Intel Market Research (research §14.1) |
| SAM — AI-driven PdM software | $1.18B (2026), CAGR 15.6% | The Business Research Company (research §14.1) |
| Combined direct SAM | ≈ $1.3–1.4B (2026) | **Estimate**: sum of the two segments; overlap unquantified |
| SOM | ~$10–25M ARR potential by 2029 | **Estimate**: 30–60 mid-size EU pilots × $150–400k/yr support+pilot contracts; anchored to InOrbit comparable. Revisit at every CTO checkpoint |

Demand tailwinds: 76% of supply-chain ops hit by labor shortage (Descartes); 41% of warehouse managers can't retain staff (MHI 2025); 60% of warehouses raising automation budgets ~20% in 2026; >45% PdM adoption in large manufacturers (all sourced, research §14.1/§14.4).

## 2. The niche (PRD v3 §1 — binding)

**autonomous × certifiable × neutral × provable** — the four-way intersection no competitor occupies.
We are NOT: a fleet manager (commodity — OpenRobOps is free), a general agent platform (Cisco/Galileo), an
Industrial AI OS (Siemens+NVIDIA distribution lane), a sensor-PdM vendor, a safety PLC. The headline
differentiator is the **Causal Self-Healing Engine** (KB_25) on top of the breadth/foresight/trust foundation.

## 3. ICP & buying committee

ICP: EU-exposed warehouse/fulfillment or light-manufacturing operator; ≥2 robot vendors (or humanoid pilots
arriving); existing WMS/MES; a compliance function aware of the AI Act; integration budgets already at 50–100%
of hardware cost (research §14.4). Personas + artifacts each one needs (PRD v3 §14): ops lead → A/B slice
metric; OT/IT integrator → adapter docs + compose deploy; compliance officer → signed evidence pack;
security architect → key-custody/HSM drill. [Committee dynamics: qualitative judgment.]

## 4. Problems-to-solve matrix

Canonical version: PRD v3 §2 (P1 labor shortage, P2 multi-vendor interop, P3 integration tax + WMS state
divergence, P4 downtime + black-box PdM mistrust, P5 EU AI Act evidence burden, P6 PQC/crypto lifecycle,
P7 unexplainable autonomy). Each row maps problem → buyer → current alternative → our answer → stage → status.

## 5. Competitive snapshot (June 2026) + deltas since 2026-05-31

| Delta | Implication |
|---|---|
| InOrbit open-sourced OpenRobOps (Feb 2026); $10M Series A (Sep 2025) | Fleet orchestration = free commodity → integrate it beneath us; orchestration is no one's moat anymore |
| Cisco completed Galileo acquisition (2026-05-22; $68M raised pre-exit) | Agent-reliability category validated (exit) and vacated of independents; OT white space widened |
| Siemens+NVIDIA "Industrial AI OS"; Erlangen fully-AI factory blueprint 2026 | Incumbent bundling intensified; remains vendor-locked → neutrality + open evidence still our axis |
| Humanoid orchestration OEM-bundled (Agility Arc @ GXO >100k totes; BD Orbit + Atlas @ Hyundai; Figure 03 at ~1/hr) | Mixed fleets strengthen the neutral-trust-layer case; humanoid adapters = new ledger row (post-Stage-16) |
| New agentic entrants: Ati Robotics (above ERP/MES), General Robotics GRID (cross-OEM) | Lane validated; none have evidence/safety/PQC → speed on Stages 6–13.5 matters |
| A2A 150+ orgs, MCP ~97M installs (Linux Foundation AAIF) | Protocol bet confirmed mainstream; industrial A2A endpoints still rare = early-mover surface |

Full landscape, capability matrix, four perceptual maps, SWOT: `research/market-viability-2026-06/index.html` §3–6.

## 6. Positioning & messaging house

**Positioning statement:** *"The vendor-neutral trust and self-healing layer for mixed robot/OT fleets — every
autonomous decision predicted, causally explained, safety-gated, and cryptographically provable — running above
whatever fleet manager you already have. Open source, evidence-ready for December 2027."*

Per-audience lines (PRD v3 §13): vs incumbents → open/neutral/inspectable, integrates their equipment;
vs fleet platforms → the trust layer above (integrate, don't fight); vs Cisco/Galileo → the industrial-grade
version (OT + SIL + signed evidence + PQC); vs new entrants → the one with a regulator-shaped spine.
**Claim discipline:** BUILT/PARTIAL/PLANNED tags mandatory; PQC language = "FIPS-aligned, CNSA-2.0-aware
crypto-agility," never "CNSA 2.0 compliant" (research §14.3).

## 7. Monetization options (no commitment before a pilot; hard rule 9 holds at build time)

A (default): **open-core** — Apache 2.0 spine; commercial seam = evidence-pack automation, fleet-scale features,
signed-report service, support SLAs (precedent: PickNik MoveIt Pro). Viable after Stage 19.
B: **paid pilots + support/integration** ($150–400k/yr/site — estimate per §1 SOM method). Viable after Stage 6 slice + Stage 22 reference.
C: **managed control plane** (post-GA only).
Profit logic (qualitative): commodity layers stay free and drive adoption; regulated must-pay layers (evidence,
safety attestation, key custody) are the commercial seam — defensible because they ARE the niche.

## 8. GTM & adoption playbook (PRD v3 §15)

OSS-land (compose-up, shadow mode, $0) → prove (30–90 days, counterfactual "we would have prevented X" report =
the Stage 6 A/B artifact) → paid pilot (3–6 months, ONE gated workflow, weekly signed evidence pack) → SI channel
(integrators keep services revenue; our adapters delete their custom glue). The 90-day integration target is
auditable against sourced ramp/integration-cost baselines and is measured-or-revised at first pilot (Stage 22).

## 9. Viability verdict (honest — full version: market-viability HTML §10)

**Startup-worthy: yes, conditionally.** Comparables exist (Galileo exit; InOrbit Series A; BMW i Ventures $300M
+ KOMPAS €160M physical-AI funds). Conditions not yet met: working closed loop (→ Stage 6), reference pilot
(→ Stage 22), real-telemetry models (G-035), team beyond one builder (qualitative). Where we will NOT win:
distribution vs Siemens/Rockwell; sensor-PdM hardware; pure fleet orchestration. Target outcome: the trusted
neutral layer for regulated multi-vendor operators → SI-channel revenue → partnership or acquisition.

## 10. Review cadence

Re-verify at **every CTO checkpoint** (every 10 closures): market figures (§1), competitor deltas (§5), EU AI
Act formal-adoption status (provisional as of 2026-06-11; OJ publication expected before 2026-08-02), SOM
estimate, monetization-option readiness, and — added 2026-06-12 — the **frontier-model threat analysis**
(`research/frontier-model-threat-2026-06/index.html` + research §15: model-capability deltas, OpenClaw-class
agent ecosystem, moat-layer status, patent posture). Material changes land as a new ADR + a PRD v4 increment —
never as edits to frozen PRDs.

## 11. Frontier-model resilience posture (2026-06-12; full analysis in the threat HTML)

The code is replicable by any Fable-class team (proven in-house); the defensible assets are exclusively
non-code: time-anchored signed evidence history (13.5/19), per-site data flywheel (G-035-as-moat, pilot
contracts include consented retention), certification artifacts (23), system-of-record position + SI channel,
and accountability. **Speed-to-evidence is the race**; shadow-mode deployments pull forward at Stage 11.
Patents: narrow filings (2–4) on the evidence-chain construction / sim-gated intervention / crypto-swap drill,
AFTER the open-core split is formalized (Apache 2.0 patent-grant interaction); attorney-led; signaling +
defense, not a blocker. No unmatchability assurance exists or is claimed.

---

*Last verified: 2026-06-11 (Strategic Product Reset; ADR `2026-06-11_strategic_product_reset.md`). Owner: `product-manager` role.*

---

## 12. July-2026 refresh — post-GA strategic audit (ADR `2026-07-02_strategic_audit_and_post_ga_roadmap.md`)

> Added 2026-07-02. Grounded in `research/initial-research.md §35` + `research/strategic-audit-2026-07/index.html`.
> Supplements (does not replace) §§1–11. Honesty rule still binding: every figure carries a source or an estimate label.

### 12.1 Competitive intelligence refresh (sourced, research §35.4)
Market: AI-driven PdM **$2.61B (2026) → $19.27B (2032), 39.5% CAGR** (marketsandmarkets 56600288); "Industrial Copilot"
TAM ~**$42B**; Deloitte — **80% of manufacturing execs plan to invest in agentic AI** by year-end. Player shape:

| Player | Category | Their moat | Gap we fill |
|---|---|---|---|
| Palantir Foundry/AIP | ontology data+decision platform | Forward-Deployed-Engineer delivery, data integration | closed, non-neutral, no SIL/PQC/OSS |
| Cognite Data Fusion | OT/IT contextualization | mixed-vendor data w/o hardware change | data layer, not safety/evidence control plane |
| Siemens Industrial Copilot (+NVIDIA) | vendor-bundled industrial AI OS | distribution + install base | vendor-locked = the opposite of our axis |
| **IBM watsonx Orchestrate** | **enterprise agent control plane** | govern/audit 1000s of agents, hybrid, runs LangGraph/A2A, Supply-Chain domain agents | generic IT/business agents — no OT/robotics/SIL/PQC depth → **treat as a CHANNEL** |
| C3.ai | platform-agnostic brain on IIoT | enterprise scale | lost ground to Palantir; no safety/evidence spine |
| Augury / Uptake / Samsara | sensor-PdM / fleet telematics | proprietary sensor models; fleet view | point solutions, no cross-vendor decision/evidence layer |
| **Kagenti / kagent** (CNCF) | cloud-native agent platforms | SPIFFE/SPIRE identity, mesh mTLS, MCP-Gateway, K8s scale | horizontal infra, no OT/safety domain → **adopt their identity pattern + be a compatible agent** |
| **NVIDIA** Cosmos/Isaac/Metropolis | physical-AI world models + robot brains | the perception/robot substrate | **complement, not competitor** — makes robots smart, not provable to a regulator; we sit above |

### 12.2 Positioning (unchanged thesis, reinforced)
The **autonomous × certifiable × neutral × provable + Causal Self-Healing** intersection (§2) is *reinforced* by the
2026 landscape: every serious player lacks the **combined** OSS + SIL-functional-safety + PQC + signed-EU-AI-Act-evidence
spine. Realistic role = the **neutral trust / safety / evidence layer that rides above** whatever platform the customer
already bought (integrate, don't fight) + a channel-fit agent for watsonx Orchestrate / Kagenti. Perceptual maps (two)
in `research/strategic-audit-2026-07/index.html §4`: top-right of (neutrality × governance/safety/PQC depth) is unoccupied;
we are high-differentiation / low-reach → classic wedge + channel, not head-on.

### 12.3 Differentiators & new innovations (the edge — research §35.7)
1. The only **5-in-1 spine** (OSS × neutral × SIL-safe × PQC × signed-AI-Act-evidence). 2. **Causal Self-Healing Engine**
(learned causal discovery + neuro-symbolic verify). 3. **Cryptographic accountability as a feature** (PQC-signed tamper-
evident decision history — hard to retrofit). 4. **GraphRAG grounding** (Stage 28 — cited, graph-grounded explanations,
~30–40% fewer factual errors). 5. **Anti-fragile identity + durable execution** (Stage 27 — SPIFFE/SPIRE pattern + mesh-
mTLS + idempotent compensable effects + circuit breakers). 6. **Adoption-as-a-feature** (Stage 28 — design-thinking UX +
behavioural onboarding; rivals optimize accuracy, not operator adoption). 7. **Channel-fit** (Kagenti/kagent-compatible
AgentCard + A2A so we run inside IBM Orchestrate / CNCF platforms).

### 12.4 End-user / ICP adopter list + outreach (research §35.8; full table in the strategic-audit HTML §7)
- **EU 3PL / warehouse operators** (labor shortage + mixed AMR + AI-Act exposure) — reach: MHI/LogiMAT/SI integrators/OSS
  inbound; pitch: neutral trust layer above your fleet manager, evidence-ready for Dec 2027, $0 shadow trial.
- **Discrete / light manufacturing** (automotive Tier-1/2, electronics) — reach: ISO/SIL auditors, Siemens/Rockwell SI
  partners; pitch: causal self-healing + SIL-gated autonomy + a signed audit trail your safety auditor accepts.
- **Regulated process** (pharma / food / chemicals) — reach: GxP/validation consultancies, notified bodies; pitch: every
  autonomous decision cryptographically provable + post-quantum = your validation dossier.
- **SI / integrators (channel)** — pitch: our open adapters cut your integration weeks, you keep the services margin.
- **Platform channel** (IBM watsonx Orchestrate, CNCF Kagenti) — pitch: a certifiable OT-grade safety+PQC agent your
  catalog doesn't have.
Motion (§8 unchanged): OSS-land $0 shadow → 30–90-day counterfactual A/B → paid pilot (one gated workflow, weekly signed
pack) → SI/platform channel. **First real pilot (G-035/043) is the single biggest fundability/credibility gap.**

### 12.5 Design-thinking + behavioural-science adoption layer (Stage 28 build target; research §35.8)
Behavioural facts: only **13%** of workers get any AI training; **$2–3 reskilling per $1 tooling**; trust/training/**WIIFM**
is the primary work. Levers to build in: **persona-shaped dashboards** (ops-lead = A/B minutes; compliance = signed pack;
integrator = adapters), **calibrated trust** (always show confidence + uncertainty + counterfactual + graph citation),
**progressive autonomy** (shadow→assisted→supervised→autonomous — already our canary), **loss-aversion framing** ("prevented
downtime we would have suffered" > "efficiency +X%"), **friction removal** (compose-up, $0, no data leaves site, HITL
default). This is a genuine differentiator because competitors optimize model accuracy, not operator adoption.

### 12.6 Production-readiness verdict (honest; full version in the strategic-audit HTML §2, §8)
**Production-grade engineering discipline + pilot-deployable, but NOT production-scaled.** Ready for a single controlled
pilot line/site; not for enterprise/multi-site magnitude. Software is real/tested/honest (344 tests green, real PQC, signed
evidence chain, no committed secrets); real-world efficacy is **unproven** until a pilot re-fits models on real telemetry.
Convert to a gamechanger by closing four gaps **in order**: real pilot (G-035/043) → scale (G-066) → certification (G-011)
→ adoption UX (Stage 28). "Gamechanger?" — credible *candidate*, not proven. "Adopted easily?" — no; earned pilot-by-pilot,
but the OSS/$0/HITL wedge lowers the barrier more than most. "Works efficiently?" — as software yes; as a real-world outcome
engine, unproven pending a real pilot.

### 12.7 EU AI Act timeline — MATERIAL update (research §35.6)
Political agreement **2026-05-07 extended high-risk deadlines**: high-risk areas incl. **critical infrastructure** now
apply from **2 December 2027** (was ~Aug 2026); product-integrated systems from **2 August 2028**. Harmonised standards
**delayed to H2 2026 / H1 2027**; until published, no presumption of conformity (voluntary code of practice bridges). Net:
more runway + the burden is confirmed and dated → our "evidence-ready before the deadline" wedge is real and time-boxed.
Our route unchanged: Annex-III points 2–8 → **internal-control (Annex VI)**, no notified body mandated, self-declaration.
**Supersedes §10's "OJ publication expected before 2026-08-02" note for the high-risk-application deadlines.**

---

*§12 added 2026-07-02 (Post-GA Strategic Audit; ADR `2026-07-02_strategic_audit_and_post_ga_roadmap.md`). Owner:
`product-manager` role. Full sourced basis: research §35.*

## 13. Pilot-readiness posture (Stage 32, 2026-07-13; research §43)

The buildable half of the pilot engagement is now COMPLETE — the single biggest fundability/credibility gap (G-043)
is de-risked to the point where only a buyer is missing. Three artefacts make a real pilot start day-one, with the
discipline ~60% of AI pilots skip (predefined success criteria):

- **`compliance/pilot-charter-template.md`** — predefined per-capability success criteria + thresholds, two hard gates
  (0 unsafe actuations; audit chain verifies), a 4–6-week window, and Scale/Iterate/Pivot/Stop decision gates.
- **`compliance/capability-readiness-matrix.md`** — the HONEST sell: every capability tagged sim-proven /
  benchmark-proven / built, with its REAL measured number (cited) + its real-data dependency (G-035) + its pilot A/B
  hypothesis. Headline sim results the pilot will test on real data: **repair-dispatch downtime −47.9%**, **supply-chain
  stockouts −51% / bullwhip −98%**, **injection detection 0.9935→1.0 / FPR→0**, GraphRAG grounding 1.0.
- **`compliance/pilot-ab-protocol.md`** — the proof-of-value A/B (baseline window, paired test + CI) reusing the
  Stage-6/26/30 harnesses, covering all five value drivers + the two hard gates.

**Honest posture:** the product is pilot-DEPLOYABLE and its value is measured on simulator + public benchmarks; NO
real-world number exists yet. Conversion path (unchanged, KB_26 §12): real pilot (G-035/G-043) → scale (G-066) →
accredited certification (G-011). The GA'd platform + this package = everything free/local-buildable toward that first
reference pilot is done; what remains needs a buyer / accredited body / legal-entity provider.

*§13 added 2026-07-13 (Stage 32 pilot-readiness package; ADR `2026-07-13_stage32_pilot_readiness_package.md`). Owner:
`product-manager` / `compliance-engineer`.*
