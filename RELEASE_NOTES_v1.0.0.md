# Release Notes — v1.0.0 (GA)

**Industrial Agent Control Plane** — a vendor-neutral, EU-AI-Act-grade, post-quantum-ready agent control plane for
industrial robot and OT fleets. Open source (Apache-2.0 / MIT), free/OSS/local through the entire build (Rule 9).

GA released at **Stage 24** after 24 build stages + 4 CTO checkpoints, every stage independently reviewed by a different
agent, with a theatrical-fallback audit baseline held at **364** throughout (no fakery). Spec: `PRD-ai-embodied-agent-v3.md`.

## What v1.0.0 is
A stable, fully-tested, independently-reviewed, **conformity-assessment-READY** open-source platform. **Full suite: 344
passed / 10 skipped / 0 failed** (live). Public contract stable across Stages 0–23 → semver **1.0.0**.

## Capabilities (by build stage)
- **Self-healing decision loop (KB_25):** predict → diagnose → reason → verify → intervene, as a durable, deterministic
  LangGraph `StateGraph` (Stage 11) with HITL human oversight on SIL-1+ decisions.
- **Real ML (depth-first, on benchmarks):** Transformer RUL on C-MAPSS (Stage 8), learned causal discovery + neuro-symbolic
  plan verifier, ResNet transfer-learning defect detection 99.3% on NEU-CLS (Stage 9), MaskablePPO intervention RL (Stage 7),
  SHAP/DiCE explainability (Stage 10). Every weight has a model card + metrics.
- **MCP tool servers + agent memory** (Mem0/pgvector + Neo4j ISA-95, namespace-isolated + Postgres RLS) + **CDC ingestion**
  (Stages 11.5–13).
- **Post-quantum crypto:** ML-DSA-65 signing (audit chain + ADRs + agent identity), hybrid ML-KEM-768+X25519 TLS,
  SLH-DSA long-trust, on the host's OpenSSL 3.5 (Stages 13.5/18).
- **A2A federation** (signed agent cards, JSON-RPC capability boundary) + **OT/IT bridge** (OPC UA, MQTT Sparkplug B) +
  **VDA 5050 robot-fleet** master (Stages 14–16).
- **Functional safety wrapper** (SIL-rated validator + STO/SS1 + the `actuator`-must-follow-`safety.validate` CI invariant)
  + **zero-trust** (NIST SP 800-207, per-agent ML-DSA identity, signed MCP tool manifest) (Stage 17).
- **Governance evidence:** EU AI Act Annex IV technical-documentation pack generator (14 sections, ML-DSA-65 signed),
  load-bearing audit-chain verifier, post-market-monitoring plan (Stages 19/22).
- **Red-team eval harness:** OWASP-LLM01 prompt-injection (0.9935 hybrid detection) + NIST-RMF-Agentic (14/14) + agentic
  metrics, CI-gated (Stage 20).
- **DR/HA:** tested backup→restore→verify + chaos drill + runbook (RPO ≤60s / RTO ~4s) (Stage 21).
- **Governance access control:** Bell-LaPadula MAC + agent-hierarchy function-scoped RBAC + total-traceability, LIVE-enforced
  at the A2A boundary + runtime decision node (Stages 23/24).
- **Conformity:** ISO 10218-2:2025 risk assessment, ISO/IEC 42001 internal audit + management review, ISO/IEC 42005 impact
  assessment, EU Declaration-of-Conformity template (internal-control / Annex VI route) (Stages 23/24).

## What v1.0.0 is NOT (honest)
NOT certified, NOT CE-marked, NOT EU-registered, NOT running a real customer pilot, NOT sold. Those need a legal-entity
provider + an accredited body + a buyer/real fleet, and are honestly deferred. All proxy/benchmark models must be re-fit
on real site data before autonomous operation (`compliance/pilot-onboarding-kit.md`).

## Known open items (post-GA, ledgered in `audits/OPEN_GAPS_LEDGER.md`)
Real pilot + published A/B (G-035/G-043); accredited functional-safety certification (G-011); horizontal scale (G-066);
pgaudit (G-060); Langfuse-UI render (G-067); a2a-sdk (G-070); customer/supplier records (NC-3). CE marking + EU-database
registration await the real provider entity + completed conformity.

## Next
Stage 24.5 — CTO Checkpoint #5 (final); then post-GA operations (Stage 25).
