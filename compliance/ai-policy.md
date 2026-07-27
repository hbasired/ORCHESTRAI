# AI Policy

> ISO/IEC 42001:2023 **A.6.1** (AI policy) + clauses 4–5 (context, leadership). The written, top-management-endorsed
> policy for the AI management system (AIMS) of this vendor-neutral, EU-AI-Act-grade agent control plane.
> Authored Stage 19 (2026-06-21). Reviewed at every CTO checkpoint. Part of the Annex IV pack (KB_18 §1–2).

## 1. Purpose & scope (ISO 42001 cl. 4)

This policy governs the design, development, and operation of the AI components of the **embodied-agent control plane**
for industrial robot/OT fleets: the LLM planner(s), the ML models (predictive-maintenance, RUL, vision-defect,
RL-intervention, world-model, explainability), the agent runtime (LangGraph), the MCP tool surface, the A2A federation
boundary, and the functional-safety wrapper. Scope = all of `backend/`, the model artefacts under `models/`, and the
governance evidence under `compliance/`.

## 2. AI principles (commitments)

1. **Human oversight first.** No SIL-1+ actuator action executes without passing `backend/safety/validator.py`; SIL-1
   advisory actions require operator confirmation (HITL). The LLM is a *planner*, never the executor (KB_17).
2. **Honesty / no fabrication.** No mocked, faked, or theatrical outputs in production code (Hard Rule 1/1a). A model
   that is unavailable returns honest-unavailable, never a plausible fake. Claims are verified against running code.
3. **Record-keeping & non-repudiation.** Every decision is appended to the immutable, SHA-256-hash-chained,
   **ML-DSA-65-signed** `audit_chain` (EU AI Act Art-12; indefinite retention). Verification is load-bearing.
4. **Security & post-quantum readiness.** Hybrid ML-KEM-768+X25519 TLS on every external boundary; ML-DSA-65 signing;
   SLH-DSA-SHA2-128s long-trust bundles; zero-trust per NIST SP 800-207 + per-agent identities (KB_13, Stage 17/18).
5. **Privacy & least privilege.** Memory namespace isolation (Python `_authorize` + Postgres RLS); MCP tool capability
   authz + argument sanitisation; PII handling per the deployment region.
6. **Free-cost / open by default.** OSS + local/free-tier only through the build (Apache-2.0 / MIT); no paid SaaS lock-in.
7. **Standards alignment.** ISO/IEC 42001/42005/42006, EU AI Act Annex IV, NIST AI RMF (+ Agentic Profile), OWASP LLM
   Top-10, IEC 61508 / ISO 13849-1 / ISO 10218 / ISO 15066 (functional safety), VDA 5050 / OPC UA / Sparkplug B / ISA-95.

## 3. Honesty boundary (no overclaim)

This system is **amenable to** conformity assessment; it does **not** claim certification. ISO/IEC 42001 is an
operational governance framework (not harmonised under the EU AI Act); as of 2026 no harmonised AI-Act standard is
published, so **no presumption of conformity** exists from any standard. Actual conformity = the Stage-23 dry-run + a
notified-body assessment. The Annex IV pack (`scripts/generate-annex-iv-doc.py`) is conformity-assessment-READY
technical documentation, not a certificate.

## 4. Roles & accountability (ISO 42001 A.6.2, cl. 5)

Top management commits the resources for the AIMS and endorses this policy. Role accountability is defined in
`.claude/skills/<role>/SKILL.md` (9 roles). The risk owner per surface is named in `compliance/risk-register.md`.

## 5. Risk management (cl. 6 / A.8.2, Art. 9)

Risks are managed in `compliance/risk-register.md` (reviewed every stage + CTO checkpoint). New high-risk surfaces,
models, datasets, external boundaries, actuator paths, and architectural decisions are **refused at close** without
their required evidence artefact (`scripts/audit-task.sh` / `close-task.sh` enforce — KB_18 §"refuses to ship without").

## 6. Continual improvement (cl. 9–10)

Every-10-closures CTO checkpoints, per-stage independent (different-agent) reviews, the open-gaps ledger
(`audits/OPEN_GAPS_LEDGER.md`), and the quarterly dependency bump-and-re-test drill drive continual improvement of the
AIMS. Incidents are handled per `compliance/incident-playbook.md` (Art-26) and recorded in the audit chain.

## 7. Review

Owner: agentic-governance-engineer + compliance-engineer. Endorsed by top management (project owner). Reviewed at each
CTO checkpoint; next review: CTO #4 (Stage 21.5). Last reviewed: 2026-06-21 (Stage 19, authored).
