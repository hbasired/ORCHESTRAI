# ADR — EU AI Act Timeline Amendment Response + 9-Vendor Landscape Update (2026-05-24)

**Status**: accepted
**Stage**: between Stage 1 close (done) and Stage 2 (next executable) — addendum to the 2026-05-18 PRD v2 repositioning ADR.
**Author**: agentic-governance-engineer persona (Claude session, 2026-05-24)
**Related**: [`compliance/decision-logs/2026-05-18_prd_v2_repositioning.md`](2026-05-18_prd_v2_repositioning.md), [`research/initial-research.md` Section 8](../../research/initial-research.md), [`PRD-ai-embodied-agent-v2.md`](../../PRD-ai-embodied-agent-v2.md)
**KB updates**: This ADR does not by itself bump KB files. The next stage that touches PRD or compliance text should reflect the changes here.

---

## Context

The 2026-05-18 PRD v2.0 repositioning ADR was written with these assumptions:
1. EU AI Act high-risk Annex III obligations begin **2026-08-02** (~75 days from that ADR). This was the primary acute urgency driver for the warehouse-first wedge.
2. The competitive landscape included Siemens, Bosch, Microsoft, Nvidia, AWS, IBM, Google, Anthropic — but NOT Huawei (geopolitically separate, but a real industrial AI player).
3. The vendor-neutral control plane lane was "empty" — we identified no direct open-source competitor.

A research pass on 2026-05-24 (captured in `research/initial-research.md` §8) validated PRD v2 against a 9-vendor landscape (added Amazon, Huawei specifically) and surfaced THREE material changes that warrant an addendum ADR rather than a silent PRD edit:

1. **EU AI Act timeline relief.** On 2026-05-07, EU Council + Parliament + Commission reached provisional agreement amending the EU AI Act. High-risk Annex III obligations postponed from **2026-08-02 → 2027-12-02** (16-month relief). Annex I product-regulated obligations postponed from 2027-08-02 → 2028-08-02. Embedded AI in machinery removed from direct AI Act application — moves under Machinery Regulation delegated acts. SME threshold expanded to 750 employees / €150M revenue.

2. **Confirmed direct competitor density.** Two vendor-neutral open-source control plane plays the 2026-05-18 research missed: Galileo Agent Control (2026-03-11, Apache 2.0) and Guild.ai (2026-04-29, $44M Series A). Both target generic-agent governance; neither has industrial-vertical depth (no VDA 5050, no OPC UA, no functional safety wrapper, no PQC).

3. **Protocol convergence consolidated.** MCP + A2A + ACP all now under Linux Foundation Agentic AI Foundation (AAIF). AAIF membership: Anthropic, OpenAI, Google, Microsoft, AWS, Block, Cloudflare, Bloomberg. **MCP has won the agent-to-tool layer** (97M monthly SDK downloads; 10,000+ public servers). **A2A has won the agent-to-agent layer** (150+ orgs in production). **ACP officially merged into A2A** — the 3-protocol race is now 2.

## Decision

**E1. Urgency narrative pivot.** The "ship by Aug 2 2026 to ride compliance urgency" pitch is dead. Replace with two complementary urgency narratives:
- **Short-term (Q3 2026–Q1 2027):** Pilot customers in regulated EU industries still need 18+ months to build, audit, and certify. Buying decisions made in Q3 2026 hit certification cycles that complete by Dec 2027 deadline. Our v2 roadmap (Stage 23 conformity dry-run by ~Q2 2027) fits.
- **Long-term (multi-year):** Position as "10-year-horizon governance moat" — open standards + PQC crypto-agility + functional safety architecture + auditable evidence chain. This is the differentiator that survives regulatory churn AND vendor consolidation.

**E2. Machinery Regulation alignment.** With embedded AI in machinery moved from AI Act direct application to Machinery Regulation delegated acts, the LLM-planner / SIL-rated-classical-executor split (KB_17) becomes MORE strategically aligned: actuator-touching paths now fall under the same regulatory framework that ISO 10218 / IEC 61508 / ISO 13849-1 / IEC 62061 already serve. PRD v2 §6 ("Functional Safety Wrapper") needs no change — its architecture is correct; the regulatory framing strengthens.

**E3. Differentiation vs Galileo / Guild.ai.** They focus on GENERIC agent governance. We focus on INDUSTRIAL vertical:
- VDA 5050 v2.1.0 robot fleet (KB_12, Stage 16)
- OPC UA + MQTT Sparkplug B v3.0 + ISA-95 Part 2 (KB_12, Stage 15)
- ISO 10218 / IEC 61508 / ISO 13849-1 / IEC 62061 functional safety wrapper (KB_17, Stage 17)
- PQC-ready for 10-20 year industrial equipment lifecycles (KB_13, Stages 13.5 + 18)
- EU AI Act + ISO/IEC 42001 + Machinery Regulation evidence pipeline (KB_18, Stage 19)
- Sales positioning: "Galileo / Guild are the Kubernetes of agents for enterprise SaaS. We are the Kubernetes of agents for industrial fleets."

**E4. Siemens Xcelerator Marketplace as an integration target.** Siemens announced (CES 2026) plans for a third-party AI agent marketplace on Xcelerator. Stage 22 (pilot deployment runbook) should include a section on listing the control plane as a Siemens Xcelerator Marketplace agent. This is a co-existence path, not a competitive one.

**E5. ADK as a bridge option.** Google's ADK (Agent Development Kit) is functionally an alternative to LangGraph for the "orchestration brain" layer. Both adopt MCP for tools. Our primary orchestrator stays LangGraph (PRD v2 §10 Stage 11; KB_06). Document an ADK bridge as a Stage 22 customer-driven option for Gemini-stack customers. No change to Stage 11.

**E6. 2-protocol stack confirmed.** MCP (vertical: agent → tools) + A2A (horizontal: agent ↔ agent) is now the industry default. PRD v2 §4 + KB_16 are correct; no change needed.

**E7. Add Huawei Pangu to competitor landscape.** Huawei Pangu Models 5.5 (718B params; 500+ scenarios; 30+ industries) is a real industrial AI play, geopolitically constrained in Western markets. Our addressable market specifically excludes Huawei's stronghold regions in the warehouse-first wedge (we pitch to Western EU + US + Japan first). KB_11 (Pitch Strategy) should note this when revised.

**E8. Production-grade verdict re-affirmed.** The user asked: "Will the project be production-grade with no mocking, no fooling, and no faking?" Answer: NOT today (`.audit-baseline = 439` theatrical occurrences). YES by Stage 25, gated by:
- Audit count strict-decrease per stage (or `--no-baseline-drop` only for protocol/governance/CTO stages).
- Every new weight has metrics.json + model card.
- Every new MCP tool has a schema test.
- Every new actuator path has a `safety.validate` OTel span before the `actuator` span (CI gate Stage 17+).
- ML-DSA-65 signed audit chain (Stage 13.5+) provides cryptographic non-repudiation.

**E9. 100-year sustainability — architectural verdict.** The architecture is sustainable iff:
- Implementations stay swappable behind stable interfaces (MCP tool schemas, A2A agent cards, safety contract DSL, OTel spans, `audit_chain` row format).
- Open standards (VDA 5050, OPC UA, Sparkplug B, ISA-95, ROS 2, ISO 10218 family, ISO/IEC 42001, NIST PQC) carry forward — they evolve in place over multi-decade cycles.
- Crypto-agility plumbing (KB_13) handles algorithm rotation across the full horizon.
- LangGraph / Mem0 / Letta / specific libraries WILL be replaced within 5-10 years; that's expected and supported by the interface-first design.

The PRD v2 picks the right SEAMS. That is what makes 100-year sustainability possible — not specific framework choices.

## Why

1. **Honesty.** The 2026-05-18 ADR cited Aug 2026 as an urgency driver. That driver moved 16 months. Not capturing this in writing creates a stale-record problem the next CTO review would (correctly) flag.
2. **Competitor truth.** Galileo and Guild.ai are real; pretending otherwise weakens the pitch when a customer asks "what about Galileo?".
3. **Protocol position.** Confirming MCP + A2A as industry consensus (not just our bet) strengthens the architecture's case AT NO COST.
4. **Machinery Regulation alignment.** This is a positive: it gives our functional-safety wrapper a clean regulatory home.
5. **Production-grade verdict honesty.** User directly asked. Answering candidly that we are NOT production-grade today but have a defensible path is more credible than a "yes we are" deflection.

## Consequences

**Immediate (this ADR):**
- This file lands. No KB bumps needed (ADRs are evidence themselves).
- `research/initial-research.md` §8 captures the supporting evidence (~270 lines appended).

**Soon (next stages that touch these files):**
- PRD v2 §1.1 and §1.2 to get a footnote pointing here when Stage 22 pilot deployment runbook is written (or sooner if a customer asks).
- KB_11 (Pitch Strategy) — when next revised — should add Huawei context + Galileo/Guild.ai differentiation + Siemens Xcelerator Marketplace integration path.
- KB_18 (Governance Evidence) — when next revised — should note Machinery Regulation delegated-acts pathway for embedded AI.

**Audit baseline:** unchanged. This is a docs+ADR change. Audit count stays at 439.

**Stage 2 (SimPy) unchanged.** This ADR adds no new acceptance criteria to Stage 2.

## Risks tracked

- **EU AI Act amendment is "provisional".** The 2026-05-07 agreement is provisional pending final adoption. Track via `compliance/risk-register.md` if it's not yet rowed.
- **Huawei Pangu market expansion.** If Huawei extends into Western industrial markets via APAC supply chain customers, our wedge competition gets harder. Track quarterly.
- **Galileo / Guild.ai industrial pivot.** If either pivots into industrial verticals, the differentiation narrows. Track quarterly.

## Closure

The Stage 1.5 expansion phase (PRD v2 repositioning, 25-stage roadmap, role personas, lifecycle scripts, KB extensions, research documentation, sweep) is complete and audit-clean (count 439 = baseline). Stage 2 (SimPy DES) is the next executable task. Run `/begin` to enter it.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:02+00:00 -->
<!-- signature: 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 -->
