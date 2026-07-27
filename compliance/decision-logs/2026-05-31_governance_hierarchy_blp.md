# ADR — Total traceability, agent hierarchy + RBAC, Bell-LaPadula MAC (2026-05-31, run 5)

**Status**: accepted (spec; enforcement staged)
**Stage**: cross-cutting (governance / security)
**Author**: compliance-engineer + system-designer + agentic-governance-engineer (operator-directed)
**Related**: KB_18 (governance), KB_06 (coordination), KB_14 (audit_chain); gaps G-028..G-030
**KB updates**: KB_18 + KB_06

---

## G1 — Total traceability (every message, every state, every decision)

**Decision.** Record (a) **every agent message** `{from,to,type,payload_hash,ts,correlation_id}` including the
new `diagnose.*` types; (b) a **`state_snapshot(pre)` + `state_snapshot(post)`** bracketing every
incident/decision (replay any decision against the exact world it acted on); (c) **every decision** signed into
the immutable `audit_chain` (hash-chained, ML-DSA-65). Mutable detail → Langfuse; evidence → signed chain.

**Why.** Operator: traceability is paramount. Satisfies EU AI Act Art. 12 + ISO/IEC 42001 A.9 + NIST RMF
provenance — and it is what makes the causal "why did X happen?" answerable. (G-028; Stages 12/12.5.)

## G2 — Agent hierarchy + function-scoped RBAC

**Decision.** Explicit levels L3 EmbodiedCoordinator → L2 Heads → L1 workers → L0 external peers. Each agent/MCP
tool declares `required_capabilities` + `function_category`; the MCP boundary + coordinator verify caller
identity/capabilities before any tool/command; every check logged. An agent acts only within its function.
(G-029; Stage 11.5.)

**Why.** Operator: hierarchy + accessibility-by-function. Least privilege; bounds blast radius.

## G3 — Bell-LaPadula mandatory access control

**Decision.** Subjects (agents) + objects (data/message/command) carry a **level** (mapped to hierarchy) +
**categories** (function compartments). Enforce **Simple Security ("no read up")** + **\*-property ("no write
down")**; access needs level-dominance AND category-containment. `backend/governance/mac.py` (Stage 19); every
allow/deny audited.

**Why.** Operator explicitly requested Bell-LaPadula. It bounds confidentiality leakage across the hierarchy
(an L1 worker can't read the L3 plan; L3 can't leak into an L0 channel).

**Honest note (integrity dual).** BLP is confidentiality-only. Command/actuation **integrity** (a low-trust
agent must not drive a high-SIL actuator) is the Biba-like dual, already enforced by the functional-safety
wrapper (KB_17). We implement BLP as requested for read/write confidentiality; the safety wrapper provides the
integrity side. Together they bound both leakage and unsafe actuation. (G-030.)

## Risk register references
- Strengthens record-keeping (Art. 12) + access-control (Annex III cybersecurity) posture.
- Free-cost (rule 9) preserved: MAC + RBAC are pure logic, no paid dependency.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:03+00:00 -->
<!-- signature: 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 -->
