# ADR — Governance Hardening + ML Training Scaffold (2026-05-24)

**Status**: accepted
**Stage**: between Stage 1 close and Stage 2 — second addendum to the 2026-05-18 PRD v2 repositioning ADR; first companion to the 2026-05-24 EU AI Act amendment ADR.
**Author**: agentic-governance-engineer + compliance-engineer + ml-engineer personas (Claude session, 2026-05-24)
**Related**: [`compliance/decision-logs/2026-05-18_prd_v2_repositioning.md`](2026-05-18_prd_v2_repositioning.md), [`compliance/decision-logs/2026-05-24_eu_ai_act_amendment_response.md`](2026-05-24_eu_ai_act_amendment_response.md), [`knowledge-base/KB_19_Competitor_Comparative_Governance.md`](../../knowledge-base/KB_19_Competitor_Comparative_Governance.md), [`research/initial-research.md` §9](../../research/initial-research.md)
**KB updates**: KB_19 (new); KB_18 (extended); risk register (extended).

---

## Context

User asked, in three parts:

1. **"Are we ready for the above competition [Galileo, Guild.ai, Huawei] after the build? I want the system to be robust and governed. Check the web for governance of the relative systems and will our system become good in governance and will be enforced?"**
2. **"Are we using deep learning, if yes do you provide me with the code and datasets available or synthetic so that I can use colab for training as free GPU's are available and get the pickle files and paste it in the folder for system to access."**
3. **"And how do you know when building that you need to be a backend engineer or front-end engineer and how context for respective tasks will be extracted."**

Question (3) is mostly already-built (CLAUDE.md §3 decision tree + suggest_role function in context_loader.py + start-task.sh slug heuristic) and is answered inline in the final reply.

Questions (1) and (2) drove this ADR.

### Research

A 9-query web research pass (captured in `research/initial-research.md` §9) on 2026-05-24 surfaced the actual enforcement architectures of Galileo Agent Control, Guild.ai, and Huawei Pangu. KB_19 is the structured side-by-side. Highlights:

- **Galileo (Apache 2.0):** policy DSL with runtime enforcement; bounded autonomy pattern; PII blocking, cost routing, approval workflows, brand voice.
- **Guild.ai ($44M):** Governed Runtime sandbox monitoring every execution; agent registry; IAM; cost management; budget caps + rate limits + approval workflows; OAuth integrations.
- **Huawei Pangu:** 170+ certifications; multi-layer protection / encryption / IAM / AI-powered threat detection; 30+ industries / 500+ use cases. "AI amplifies governance failures, not new risks."

Additionally surfaced two **new ISO standards** we did not previously reference:

- **ISO/IEC 42005:2025** — AI system impact assessment guidance (lifecycle).
- **ISO/IEC 42006** — audit requirements for ISO 42001 certification bodies.

### Gap analysis

KB_19 §"Side-by-side comparison" shows that our project ALREADY EXCEEDS competitors on 6 dimensions (PQC audit chain, functional safety wrapper, industrial standards, Annex IV generator, red-team CI gate, federation A2A) but currently LACKS 3 of their key capabilities (policy DSL, governed-runtime extensions, budget caps).

---

## Decision

**G1. Adopt policy DSL pattern (NEW Stage 19 acceptance criterion).**

- Pydantic-validated policy contracts.
- Policies live in `compliance/policies/*.yaml`, signed with ML-DSA-65 like ADRs (append-only).
- Enforcement layered at: OTel span emit + MCP server boundary + safety validator + close-task.sh CI gate.
- At least 8 starter policies: PII redaction at MCP output, budget cap per incident, approval-required for SIL≥1 actions, safety.validate pairing for actuators, audit_chain append on every decision, KB diff coverage, model-card presence, ADR signing.

**G2. Extend MCP server design (NEW Stage 11.5 acceptance criteria).**

- Per-tool RBAC: each MCP tool declares `required_capabilities`; agent identity (A2A card or internal session) must hold them.
- Agent registry under `audit_chain` namespace `actor:agent:*` with capability list + identity key version.
- Sandbox boundary tightened: MCP server processes drop filesystem + network privileges they don't need.
- Token / call budget tracker integrated with the LangGraph runtime.

**G3. PII output filter (NEW Stage 19 acceptance criterion).**

Output filter at MCP server boundary. Email, phone, SSN, IBAN, credit card patterns. Soft mode (mask) for non-EU; hard mode (drop) for EU pilots. Documented in KB_18.

**G4. ISO/IEC 42005:2025 impact assessment (NEW Stage 19 acceptance criterion).**

- `compliance/impact-assessments/<system>.md` template auto-generator (`scripts/generate-impact-assessment.py`).
- Reads from: PRD v2 §1.2 + risk register + Annex III classification + model cards + safety contracts.
- Output is part of the Annex IV pack (Stage 19).

**G5. ISO/IEC 42006 audit readiness (NEW Stage 23 acceptance criterion).**

- `compliance/iso-42006-audit-readiness.md` checklist.
- Auditor-facing structure: AIMS scope, controls evidence, internal audit results, external audit corrections, management review records.
- Updated quarterly post-GA.

**G6. ML training scaffold landed this session.**

- `backend/training/README.md` — master Colab workflow.
- `data/datasets/CATALOG.md` — per-stage dataset catalog.
- `backend/training/stage_04_predictive_maintenance/{train.py,README.md,requirements.txt}` — starter notebook for the first ML stage.
- Stages 5–10 are scaffolded by their respective task docs and will follow the same pattern when their turn comes.

**G7. Block `.pkl` for runtime weights.**

- `pre_tool_use.sh` hook extension: block creation of `.pkl` files under `backend/ml/` or `models/`. `.safetensors` required.
- Allowed in `backend/training/` for transient intermediates (training scripts may pickle dataclasses or loader caches).
- Rationale: pickle allows arbitrary code execution on load — incompatible with EU AI Act Article 15 cybersecurity + CNSA 2.0 trust requirements. `.safetensors` is PQC-signable (SLH-DSA-SHA2-128s at Stage 18).

**G8. Positioning narrative reinforced.**

Per KB_19 §"Positioning statement": "Galileo and Guild.ai are the Kubernetes of agents for enterprise SaaS — governance for chatbots, code-assistants, and back-office automations. This project is the Kubernetes of agents for industrial fleets — governance for systems where an LLM action can cause a $50M production line stop or, worse, an injury."

This pitch line is the canonical one-sentence positioning. PRD v2 §1.4 already has a comparable line; KB_11 (Pitch Strategy) — when next revised — should align.

---

## Why

1. **Galileo and Guild.ai are real competitors.** Pretending otherwise weakens our credibility when a customer asks "what about Galileo?". Their policy DSL + governed runtime + budget caps ARE good ideas. Adopting their best ideas costs us nothing strategic — our moat is the industrial standards + PQC + functional safety, which they cannot match without a multi-year build.

2. **ISO/IEC 42005 + 42006 strengthen the Stage 23 conformity dry-run.** When a notified body shows up, having a structured impact assessment + audit-readiness checklist beats hand-wavy "yes we have governance" answers. These standards are published (May 2025); pretending they don't exist would be theatre.

3. **Pickle-to-safetensors is non-negotiable** for a system claiming PQC posture. ML-DSA-65 signing a pickle is incoherent (pickle decodes arbitrary Python on load — the signature is moot if the load itself can execute hostile code). Safetensors is a structured binary; signing it actually means something.

4. **Training scaffold removes the "where do I even start" friction.** User has free Colab access; they shouldn't have to figure out from scratch how to stand up training for each model. The starter notebook + dataset catalog reduces Stage 4 implementation from "design + code + dataset + train" to "open Colab, paste, run, drop output in models/".

5. **Honest answer to "will the build be governed and enforced?":** YES, more rigorously than any of the three competitors, IF we close the policy-DSL + governed-runtime + budget-caps gaps (G1, G2). This ADR locks those in as Stage 19 + Stage 11.5 acceptance criteria so they CANNOT be silently dropped.

---

## Consequences

**Immediate:**
- New file: `knowledge-base/KB_19_Competitor_Comparative_Governance.md`.
- New file: `backend/training/README.md`.
- New file: `data/datasets/CATALOG.md`.
- New files: `backend/training/stage_04_predictive_maintenance/{train.py,README.md,requirements.txt}`.
- This ADR.
- `research/initial-research.md` §9 appended.

**Next stages affected:**
- Stage 11.5 (MCP servers) — gains G2 acceptance criteria.
- Stage 19 (Evidence pipeline) — gains G1, G3, G4 acceptance criteria.
- Stage 23 (Conformity dry-run) — gains G5 acceptance criterion.
- Stage 4 (Predictive maintenance) — has a ready starter notebook + dataset catalog.

**Risks tracked (added to risk-register.md):**
- Galileo / Guild.ai industrial vertical pivot (low → medium probability over 12 months).
- Huawei Pangu Western market expansion (geopolitically gated).
- Training data license drift (Real-IAD changes terms; DVC pinning + CARD.md attestation mitigate).
- Colab terms-of-service constraints (Google can change free-tier limits; document fallback to local RTX).

**Audit baseline:** unchanged. This is a docs + scaffold change.

**Stage 2 (SimPy) unchanged.** Still the next executable task.

---

## Closure

Two questions answered honestly:

(1) "Are we ready for the competition after the build?" → YES on the moat dimensions (industrial standards, PQC, functional safety, Annex IV, A2A); not-yet on policy DSL + governed runtime + budget caps; this ADR locks those in.

(2) "Are we using deep learning? Code + datasets + Colab?" → YES; stages 4-10 are all neural-network training; the scaffold landed this session for Stage 4; Stages 5-10 follow the same pattern when their task docs execute.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:02+00:00 -->
<!-- signature: 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 -->
