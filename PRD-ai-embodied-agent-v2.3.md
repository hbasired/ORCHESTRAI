# PRD v2.3 — The Additive Innovation: Causal Self-Healing Engine

**Version**: 2.3 · **Date**: 2026-05-31
**Extends**: [PRD v2.2](PRD-ai-embodied-agent-v2.2.md) → v2.1 → v2.0. v2.0 = architecture; v2.1 = specs/evals/QSC; v2.2 = breadth pillars; **v2.3 = the genuinely-new innovation + N-domain + dynamic features + DL/RL stack**.
**ADR**: [compliance/decision-logs/2026-05-31_causal_self_healing_engine.md](compliance/decision-logs/2026-05-31_causal_self_healing_engine.md)
**Spec**: [knowledge-base/KB_25_Causal_SelfHealing_Engine.md](knowledge-base/KB_25_Causal_SelfHealing_Engine.md) · research log §13 · [explainer HTML §2b](research/system-explainer/index.html)

> Corrects v2.2's positioning: breadth/foresight/trust is the *foundation* (already built); the **differentiator
> is the Causal Self-Healing Engine** layered on top. Where v2.3 conflicts with earlier on the headline
> innovation, v2.3 wins.

## v2.3.1 — The differentiator (additive, research-grounded, NOT yet in code)

Upgrade the `EmbodiedCoordinator` from *reactive coordination* to a **predict → causally-reason → verify →
intervene** self-healing loop:
1. **Predict** failures — learned world model (LSTM-Autoencoder + Transformer; CNN-LSTM/Transformer-GRU).
2. **Causally reason** — Causal Digital Twin: root-cause + counterfactual "what-if".
3. **Verify** — neuro-symbolic: LLM planner grounded in a formal constraint/logic engine; reject unsafe plans.
4. **Intervene** — RL (PPO): no-interruption recovery (self-repair / robot-fixer dispatch / backup online /
   slow + catch-up).

**Why it's new & substantial:** the system today has none of (learned world model, causal/counterfactual
reasoning, neuro-symbolic verification, RL recovery). Causal AI = 2026 breakout; neuro-symbolic = third wave.
It also defeats the competitors' #1 weakness — **black-box opacity** — with explainable, counterfactual,
auditable decisions.

## v2.3.2 — DL/RL stack (was implicit; now explicit)

YOLOv8 (vision, BUILT) · LSTM/Transformer (predict, Stage 4/8) · PPO RL (intervene, Stage 7) · causal +
neuro-symbolic (reason/verify, NEW). Full mapping: KB_25 §2. These are the engine's building blocks.

## v2.3.3 — N-domain embodiment

The coordinator handles N head agents. New domains: **Quality & Inspection**, **Workforce & Safety**,
**Facilities/Building-energy** (+ Energy, KB_20). Gaps G-016..G-018.

## v2.3.4 — Dynamic / interactive operator features (requirements; staged)

- **Live agent-trigger observability** — real-time message-cascade graph + per-hop decision + ledging (G-021; Stages 11–12.5).
- **Chatbot "ask the factory"** — status + causal "why did X happen?" (G-022; Stage 12+).
- **NL problem injection** — describe → parse → mutate state → re-plan (G-023; Stage 11+).
- **Bidirectional DB-edit-triggers-problem** — edit DB → CDC detects → reason → self-optimize (G-024; Stage 13).

## v2.3.5 — Surpass Siemens/Rockwell (honest)

Functionally superior on **explainability** (causal/neuro-symbolic vs black-box), **cross-domain** optimization
(they are siloed), and **openness** (vendor-neutral). Not by distribution — we win where those three matter; we
do not displace their installed base.

## v2.3.6 — Status & honesty

Everything in v2.3 is **PLANNED/PARTIAL** — the engine and dynamic features are not built. The roadmap stages
(4/7/8/11/13/16/17) implement them, folding in gaps ledger G-005, G-016..G-025. A research spike + a single
narrow scenario (the machine-failure case) should precede broad build (execution risk: causal/neuro-symbolic are
research-grade).
