# PRD v2.2 — USP Repositioning & Capability-Breadth Increment

**Version**: 2.2 · **Date**: 2026-05-31
**Extends**: [PRD-ai-embodied-agent-v2.1.md](PRD-ai-embodied-agent-v2.1.md) (which extends v2.0). v2.0 = authoritative architecture; v2.1 = specs/evals/dashboard/QSC-boundary; **v2.2 = strategic repositioning + capability breadth + process**.
**ADR**: [compliance/decision-logs/2026-05-31_usp_repositioning_and_process.md](compliance/decision-logs/2026-05-31_usp_repositioning_and_process.md)
**Companion artifacts**: [research/system-explainer/index.html](research/system-explainer/index.html) · [research/market-analysis/index.html](research/market-analysis/index.html) · [knowledge-base/KB_24_System_Design_HLD_LLD.md](knowledge-base/KB_24_System_Design_HLD_LLD.md) · research log §12.

> Where v2.2 and earlier conflict on *positioning or pillar priority*, v2.2 wins. Architecture and hard rules stand.

## v2.2.0 — Why this increment

The v2.0/v2.1 pitch leaned on EU AI Act evidence + post-quantum crypto. Those are necessary trust features but
they are **not a product idea**, and a product strong on only one or two axes is fragile. v2.2 repositions the
USP around a substantial, fundamental innovation and makes the product strong across **every** axis competitors
lead on — so its strengths look like the full-coverage profile in the market analysis, not a two-trick pony.

## v2.2.1 — The repositioned USP (three legs)

**The open, vendor-neutral control plane that runs robots, machines, and supply chain as ONE self-optimizing
system — every decision simulated in a digital twin, safety-gated, and cryptographically provable.**

1. **Breadth — cross-domain embodied coordination.** A head-of-heads agent (`EmbodiedCoordinator`, BUILT)
   coordinates robotics + manufacturing + supply chain as a single optimization, resolving cross-domain
   conflicts. Competitors are single-lane (fleet OR MES OR maintenance OR governance). This is the structural moat.
2. **Foresight — simulate-before-act.** Consequential decisions are validated in a digital-twin/world-model
   (SimPy → USD/Omniverse) before execution.
3. **Trust — verifiable decision provenance.** Safety-gated (LLM plans, SIL executor acts) + signed, replayable
   audit chain. EU AI Act + PQC are *features* of this leg, not the headline.

## v2.2.2 — Capability pillars (competitor strengths, made ours — staged)

| Pillar (leader) | Target depth | Stage | Ledger |
|---|---|---|---|
| Cross-domain coordination (unique) | global optimizer across 3 fleets | BUILT | — |
| Digital twin (Siemens/NVIDIA) | USD/Omniverse simulate-before-act + closed-loop | 22.7 | G-007 |
| Predictive maintenance **+ dedicated dashboard** (Augury/Tractian/Cognite) | open RUL/anomaly models, provenance-logged | 4 + dashboard | G-006 |
| Observability · teleoperation · fleet-data-ops (Formant/InOrbit) | OTel + operator teleop + fleet data pipeline | 12.5+ | G-009 |
| Orchestration to industry standards (InOrbit/Open-RMF) | VDA 5050 / OPC UA / ISA-95 / Open-RMF conformance + RL scheduling | 16 | G-010 |
| Evals / guardrails to **Galileo depth** | tool-selection / action-completion / reasoning-coherence → 100%-traffic runtime guardrails | 20 + KB_23 | G-008 |
| Determinism · safety heritage · PLC install base (Rockwell/Siemens) | LLM-planner/SIL-executor; integrate customer PLC | 17 | — |
| Durable, HITL, production-grade workflow | LangGraph checkpoint + interrupt + compensation/idempotency | 11 | G-014 |
| Trust: PQC + EU AI Act evidence (us) | signed audit chain + Annex IV + crypto-agility | 13.5/18/19 | — |

## v2.2.3 — New capability requirements

- **Cross-fleet repair-dispatch coordination (NEW).** The head agent dispatches a repair resource (a free
  robot / maintenance agent) to a downed machine/robot and re-plans around the outage — the original "repair
  mode" vision, beyond today's automatic timed recovery. Stage 11 (runtime) + Stage 16/17 (dispatch/safety). G-005.
- **Predictive-maintenance dashboard (NEW).** A dedicated operator surface for machine health, RUL, anomaly
  alerts, and recommended/auto-created work orders — open and provenance-logged (vs. rivals' opaque models). G-006.
- **Large-scale-deployment readiness.** Multi-fleet scaling, edge autonomy (KubeEdge), and HA/DR are first-class
  (Stages 21/22.5), so "scale of product is large" is a tested claim, not a slogan.

## v2.2.4 — Honest viability (the real-world scenario)

- **Path:** open-source, vendor-neutral integration/orchestration LAYER above/between Siemens/Rockwell/NVIDIA
  stacks → multi-vendor warehouse wedge (single-OEM lock-in unacceptable; auditable evidence required) → 3–6
  month pilots → integration partner / acquisition target.
- **What it is NOT:** a rip-and-replace of incumbent products. Incumbents have distribution + lock-in. We win
  where breadth (multi-fleet) + verifiable/safe autonomy + no-lock-in matter, and prove it with the eval suite
  + a signed decision trail.
- **Funding angle:** fundable as an "industrial agent control plane / reliability layer" (cf. Galileo's $68M for
  agent reliability alone) — *after* a reference pilot. The 2027 EU AI Act high-risk deferral softens the
  compliance-led pitch, so lead with breadth + reliability + safety.
- **Truth:** today the product is spec-deep and code-thin (Stage 2 done, Stage 3 in-progress). The moat is real
  only once Stages 11–22 ship and a pilot validates it. Both the opportunity and the multi-year build are true.

## v2.2.5 — Process changes (so breadth doesn't collapse into theatre)

- **Independent audit** by a different agent at every stage (`task-auditor` + `scripts/independent-audit.sh`);
  the report is handed to a fixer, then re-audited; PASS required to close.
- **Carry-forward gaps ledger** (`audits/OPEN_GAPS_LEDGER.md`): deferred gaps carry their `target_stage` and are
  folded into that stage's implementation.
- **CTO remediations** embed into the next task doc (`generate-remediation-tasks.sh`).
- **`system-designer` role + KB_24 (HLD/LLD)** for design altitude before implementation.

## v2.2.6 — Related documents
- [research/system-explainer/index.html](research/system-explainer/index.html) — what/how/why + viability + USP (honest, sourced).
- [knowledge-base/KB_24_System_Design_HLD_LLD.md](knowledge-base/KB_24_System_Design_HLD_LLD.md) — HLD + LLD.
- [audits/OPEN_GAPS_LEDGER.md](audits/OPEN_GAPS_LEDGER.md) — carry-forward gaps → stages.
- [knowledge-base/KB_23_Evals_and_Benchmarks.md](knowledge-base/KB_23_Evals_and_Benchmarks.md) — how we measure/evaluate.
