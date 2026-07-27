# ADR — Causal Self-Healing Cognitive Engine (the additive innovation) (2026-05-31, run 3)

**Status**: accepted (spec; implementation staged)
**Stage**: cross-cutting (innovation + roadmap)
**Author**: system-designer + agentic-governance-engineer (Claude session, 2026-05-31); operator-directed
**Related**: research/initial-research.md §13; knowledge-base/KB_25_Causal_SelfHealing_Engine.md; PRD v2.3
**KB updates**: KB_25 (new), KB_README; gaps ledger G-016..G-025

---

## C1 — A genuinely-new innovation, not a rebrand

**Context.** The operator correctly rejected "embodiment (breadth/foresight/trust)" as the USP — it described
the *existing* reactive coordinator, not a new innovation. Demanded a substantial, additive, research-grounded
differentiator.

**Decision.** Add a **Causal Self-Healing Cognitive Engine** on top of the existing `EmbodiedCoordinator`:
**predict → causally-reason → verify → intervene** (KB_25). New capabilities the system does NOT have today:
(1) a learned world model for failure prediction (LSTM-AE + Transformer); (2) a causal digital twin doing
root-cause + counterfactual "what-if"; (3) neuro-symbolic verification (LLM planner grounded in a formal
constraint/logic engine); (4) RL-selected no-interruption recovery. Research-grounded (arXiv 2510.12033,
2510.09616, 2602.08373; PMC11125296).

**Why.** Causal AI is the 2026 "breakout"; neuro-symbolic is the "third wave"; both are research frontier and
neither exists in the system. Together they convert reactive coordination into proactive, explainable,
verifiable self-healing — and directly attack competitors' #1 named weakness (**black-box opacity**).

**Consequences.** This is the headline differentiator going forward (PRD v2.3). It is **PLANNED** — no engine
code exists yet; it is the contract for Stages 4/7/8/11/13/16/17.

## C2 — DL/RL stack mapped (operator: "why aren't LSTM/YOLO/RL here?")

They were staged, not dropped. KB_25 §2 pins each to the engine: YOLO=vision/quality, LSTM/Transformer=predict +
world-model, PPO=intervene, causal+neuro-symbolic=reason/verify. Surfaced in the explainer HTML.

## C3 — N-domain embodiment

New head-agent domains: Quality & Inspection (G-016), Workforce & Safety (G-017), Facilities/Building energy
(G-018), in addition to Energy (KB_20). The coordinator is designed for N domains, not 3.

## C4 — Dynamic/interactive features (spec; staged)

Live agent-trigger observability (G-021), chatbot "ask the factory" (G-022), NL problem injection (G-023),
bidirectional DB-edit-triggers-problem via CDC (G-024). All spec'd in KB_25 §4; staged Stages 11–13; not built.

## C5 — "Surpass Siemens/Rockwell" framing (honest)

We cannot out-distribute incumbents. We surpass them **functionally** on measurable axes: explainability
(causal/neuro-symbolic vs their black-box), cross-domain coordination (they are siloed), and openness
(vendor-neutral vs lock-in). The win condition is buyers who need those three; not displacement of their install base.

## Risk register references
- Adds execution risk (causal/neuro-symbolic are research-grade) → mitigate with a research spike + a narrow
  first scenario (the operator's machine-failure case) before broad build. New risk row proposed.
- No new high-risk actuator surface beyond what KB_17 already gates.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:02+00:00 -->
<!-- signature: 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 -->
