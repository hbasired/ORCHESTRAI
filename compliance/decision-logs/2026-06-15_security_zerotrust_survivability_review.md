# ADR — Out-of-band review: MCP security, zero-trust posture, scaling/dependency strategy, frontier-model survivability

**Date**: 2026-06-15
**Status**: Accepted (out-of-band strategic/security review — NOT a numbered build stage; precedent: the 2026-05-18 /
2026-06-11 strategic resets. No backend/frontend code edited; audit baseline untouched.)
**Author personas**: `agentic-governance-engineer` + `security-pqc-engineer` + `product-manager`
**Relates**: research §20 (+ §15). KB_16 (MCP/A2A), KB_23 (evals), KB_26 (market), risk-register. Follows Hard Rule
1a (no claimed-but-unbuilt security), Rule 9 (free/OSS), Rule 11 (research-first). Two HTMLs + ledger gaps
G-063…G-066 (+ G-008 reaffirmed).

---

## Context

Operator-mandated honest review of five questions: (1) do our pinned (non-latest) dependency versions become a
production/scale problem + how do we scale agents? (2) is the shipped MCP architecture secure (it shares sensitive
data; rogue-human/agent bugs/malware)? (3) are we zero-trust — if not, why, and can we? (4) are evals/specs/benchmarks
set correctly + are we on-track? (5) market/frontier (Fable 5/Mythos 5) survivability + resilience. Web-researched
(IBM/CSA/NIST/OWASP for security+ZT; vertical-AI defensibility for survivability).

## Decisions

**D1 — MCP security: honest posture + staged hardening (G-063).** The shipped Stage-11.5 MCP servers run over LOCAL
stdio as our-code subprocesses — **no network listener, no remote/third-party server, no OAuth-token aggregation, no
LLM reading untrusted tool metadata** — so the high-impact 2026 MCP threats (tool poisoning, token theft, MITM) are
**unreachable by construction** (the trust boundary is the local process tree). We will NOT claim more security than
that. What's present: typed schemas, honest-unavailable, memory namespace isolation, append-only audit_chain. What's
owed (G-063): per-tool capability authz, prompt-injection/arg sanitisation, a signed tool manifest, rate-limiting,
and — at HTTP/third-party exposure (Stage 14) — mTLS + OAuth 2.1 + a gateway (the KB_16 A2A boundary already specs
the network case). KB_16 gains an MCP threat-model section.

**D2 — Zero-trust: partial-by-design, adopt a named framework (G-064, HIGH).** We are partially ZT today — verify
explicitly (HITL + neuro-symbolic verifier), least privilege (namespace isolation + no-LLM-direct-actuator + A2A
capability subset), assume breach (tamper-evident audit_chain + PQC), continuously validate (per-decision audit +
trace) — but NOT a coherent ZT architecture (no per-agent non-human identity, per-action authz, ZTNA, or continuous
anomaly detection). **Why staged:** ZT needs the PQC identity layer (13.5), A2A identity/mTLS (14), the safety
wrapper (17), and the red-team evals (20) — a half ZT layer before those is theatre. **Decision: adopt the CSA
Agentic Trust Framework + NIST SP 800-207 + OWASP Top-10 for Agentic Apps as the named target**, issue every
agent/tool an ML-DSA-65 non-human identity (agent cards already specced in KB_16), scope MCP tools to capabilities,
and add OWASP-Agentic + prompt-injection evals — routed across 13.5/14/17/20. The ZT posture is also a market moat.

**D3 — Dependency pinning + scaling (G-065, G-066).** Pins are deliberate + correct for a reproducible, audit-grade
build (Annex IV needs a frozen attestable set) + several are load-bearing; the real risk is **missing patches on the
frozen set**, not "old". Decision (G-065): SBOM (CycloneDX) + promote `pip-audit`/`bandit` CI to BLOCKING + a
quarterly bump-and-full-live-re-test drill (langgraph-1.0 / langchain-core-1.0 = the first drill). Scaling: the
architecture is scale-friendly (deterministic LangGraph + durable per-`thread_id` checkpointer → incidents are
independent shardable units; minimal per-super-step-immutable state → no shared-mutable-state chaos; LLM-free loop →
no orchestrator-reasoning bottleneck; per-decision audit/trace → centralized observability), but runs single-process
today with Postgres as the shared bottleneck → G-066 (multi-worker sharding router + PG scale-out, Stage 21).

**D4 — Evals on-track check.** KB_23 is a real measurable contract (12 MEASURED evals with baselines + anti-gaming).
The **agentic + security eval suites remain SPEC** (prompt-injection ≥99%, safety-gate 100%, Galileo-depth
tool-selection — G-008) owed at Stage 20, and KB_23 lacked Stage 11/11.5/12 rows. **Decision:** add the
Stage-11/11.5/12 conformance/integrity rows (3 PRD trust targets move spec→measured: 0 cross-namespace reads,
audit-chain verify, MCP per-tool schemas) + an explicit "agentic/security evals owed (Stage 20)" note; reaffirm
G-008. Verdict: **on-track for the depth/honesty bar; the revenue-converting evidence (pilot SLOs + security/agentic
evals) is still ahead, as the roadmap intends.**

**D5 — Survivability verdict (honest, no assurance).** The code is NOT a moat (a Fable-class team rebuilds it in
days; §15). What survives Fable/Mythos: (1) time-anchored signed evidence history (un-backdatable), (2) the per-site
data flywheel (G-035 → moat), (3) certification + notified-body relationships, (4) OT system-of-record, (5)
accountability/liability. **The most anti-fragile move: be the zero-trust/safety/audit layer FOR frontier models** —
"the agent your auditors + insurers allow on the OT network" makes better models demand, not threat. Survival is
**conditional** on reaching evidence-producing deployments before better-capitalized users of the same models —
the roadmap (slice→pilot→certification→flywheel) is built to win that race. No dishonest assurance is given.

## Why
- Answering "is it secure / are we zero-trust" honestly requires stating what is secured *by construction*, what is
  *not yet built*, and *why the rest is staged* — claiming a ZT/MCP-security layer we haven't built would be exactly
  the theatre Rule 1a forbids. The security posture is also the market moat (D5), so the security and survivability
  answers are the same answer.

## Consequences
- New: this ADR, `research/security-zero-trust-2026-06/index.html`, `research/survivability-analysis-2026-06/index.html`,
  research §20, ledger G-063…G-066, risk-register rows. Modified: KB_16 (MCP threat-model + ZT section), KB_23
  (Stage-11/11.5/12 rows + agentic/security-evals-owed), KB_TASK_LOG (out-of-band entry).
- **No backend/frontend code changed** — audit baseline untouched (out-of-band review). The hardening itself is
  routed to the named security stages (13.5/14/17/20/21), honestly ledgered, not faked now.

## References
- research/initial-research.md §20 (+ §15) · KB_16 · KB_23 · KB_26 · risk-register · the two new HTMLs.
- Sources: CSA Agentic Trust Framework, NIST SP 800-207, OWASP Top-10 for Agentic Apps, IBM Agentic Trust blueprint;
  MCP threat-model (arxiv 2603.22489 / 2601.17549, sentinelone, practical-devsecops); vertical-AI defensibility 2026
  (crunchbase/NEA, menlovc, symphonyai, buildmvpfast).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-21T13:37:30+00:00 -->
<!-- signature: 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 -->
