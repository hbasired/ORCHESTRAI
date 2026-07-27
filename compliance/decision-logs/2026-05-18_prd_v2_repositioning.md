# ADR — PRD v2.0 Repositioning + 25-Stage Roadmap Expansion (2026-05-18)

**Status**: accepted
**Stage**: between Stage 1 (closed) and Stage 2 (queued) — this ADR captures the scope expansion that happens *before* Stage 2 executes
**Author**: agentic-governance-engineer persona (Claude session, 2026-05-18)
**Related task doc**: [`tasks/STAGE_02_simpy_simulator.md`](../../tasks/STAGE_02_simpy_simulator.md) — UNCHANGED; this ADR adds new stages around it.
**KB updates**: KB_README (new file count), KB_01 (topology), KB_06 (LangGraph/MCP/A2A reframe), KB_10 (PQC + evidence), new KB_12–18, KB_TASK_LOG (2026-05-18 entry to be appended at Stage 2 open)

---

## Context

PRD v1 (January 2026) framed this product as another "AI embodied agent for multi-domain manufacturing optimization." Between January and May 2026 the agentic-industrial market shipped at speed: Microsoft Copilot Studio + Bosch Manufacturing Co-Intelligence, Siemens Industrial Copilot + Nvidia Erlangen factory, Nvidia Isaac GR00T N1.7 commercial, IBM watsonx Orchestrate GA, AWS Bedrock AgentCore GA, Anthropic MCP donated to Linux Foundation Agentic AI Foundation alongside Google A2A and IBM ACP.

A market-intelligence pass (full sources in research/initial-research.md Section 7, appended in this same session) confirmed: the **generic "industrial AI copilot" lane is closed.** Competing head-on against the vendor stacks above with another copilot is a losing position regardless of execution quality.

Three concentrated gaps remain that no incumbent has a credible end-to-end answer for:

1. **Vendor-neutral, EU AI Act Article 11/12 evidence pipeline** spanning robot fleets (VDA 5050 / ROS 2), OT (OPC UA / Sparkplug B), and LLM agent traces (OpenTelemetry GenAI) into one append-only, hash-chained, signed provenance graph. EU AI Act high-risk obligations begin **2026-08-02** — ~75 days from this ADR.
2. **Crypto-agile, PQC-ready transport** for industrial equipment with 10–20 year lifecycles. NIST FIPS 203/204/205 finalized August 2024. **CNSA 2.0** mandates PQC for new NSS acquisitions by **2027-01-01**. Hyperscalers are migrating cloud edges; the agent-to-PLC last mile is open.
3. **Open multi-vendor agent-fleet orchestration** on the post-merger MCP + A2A + ACP stack glued to industrial standards (VDA 5050, OPC UA, Sparkplug B, ISA-95, ROS 2).

The user briefed: "I want to build the system all the big techs would like to integrate in their system." That requirement aligns with a *vendor-neutral plumbing* play, not another copilot.

---

## Decision

**D1. Repositioning.** v2 is positioned as: *"A vendor-neutral, EU-AI-Act-grade, post-quantum-ready agent control plane for industrial robot and OT fleets — warehouse-first, then discrete manufacturing, then process industries."*

**D2. PRD v2 alongside v1.** The new document lives at `PRD-ai-embodied-agent-v2.md`. `PRD-ai-embodied-agent.md` (v1.0) is preserved as archival reference (mirrors the KB convention of strikethrough-not-deletion).

**D3. Roadmap expansion (15 → 25 stages).** Stage 2 (SimPy) is unchanged. New stages inserted: 3.5 (CTO #1), 10.5 (CTO #2), 11 (LangGraph runtime — pulled forward from old Stage 11+), 11.5 (MCP servers), 12 (Agent memory), 12.5 (Observability), 13.5 (PQC foundations), 14 (A2A protocol — replaces old "Stage 14 production hardening" which moves to 21), 14.5 (CTO #3), 15 (OT/IT bridge — OPC UA + Sparkplug B), 16 (VDA 5050 robot fleet), 17 (Functional safety wrapper), 18 (PQC Migration Wave 2), 19 (Governance evidence pipeline), 20 (Red-team eval harness), 21 (DR/HA/chaos — reframed from old 14), 21.5 (CTO #4), 22 (Pilot deployment runbook — reframed from old graduation), 23 (Conformity dry-run), 24 (GA — reframed), 24.5 (CTO #5), 25 (Post-GA).

**D4. CTO checkpoints every 10 tasks.** A `cto-reviewer` skill persona, invoked via `scripts/cto-review.sh` which spawns a **fresh Claude Code subprocess** (clean context, no working-memory contamination). Output: `audits/CTO_<N>_review.md` following template. Findings are split into immediate gaps (handled by the next agentic-governance-engineer session) and future-task remediations (appended as acceptance criteria to upcoming task docs by `scripts/generate-remediation-tasks.sh`).

**D5. Role-based orchestration via Claude Code skills.** Nine personas under `.claude/skills/<role>/SKILL.md`: agentic-governance-engineer (default), backend-engineer, frontend-engineer, ml-engineer, devops-sre, security-pqc-engineer, compliance-engineer, robotics-integration-engineer, cto-reviewer. Selection driven by file paths touched and task type — codified in CLAUDE.md decision tree.

**D6. Hook-driven context loading.** Five Claude Code hooks under `.claude/hooks/`: SessionStart (loads KB index + current task + last audit + last decision log + suggested role); UserPromptSubmit (re-injects current task doc); PreToolUse Write/Edit/MultiEdit (blocks edits to finalized ADRs, .audit-baseline without closure marker, model cards without metrics, new `random.*` imports outside tests/training); PostToolUse Write/Edit/MultiEdit (KB-update reminders, audit-needed marker); Stop (warns if audit not run, verifies audit chain quick-check).

**D7. Per-task lifecycle scripts.** Eight bash scripts and three Python helpers under `scripts/` that drive start → audit → rectify → close → next cycle. Closure refuses if gaps open or if `KB_TASK_LOG.md` lacks a new entry.

**D8. A2A + MCP both, not one or the other.** MCP for internal agent→tools; A2A for external agent↔agent. Library choices: FastMCP for MCP servers, `a2a-sdk` (Python) for A2A. KB_16 documents the trust boundary.

**D9. PQC algorithm placement.** ML-KEM-768 + X25519 hybrid for TLS at external boundaries; ML-DSA-65 for agent action signatures and the `audit_chain` table; SLH-DSA-SHA2-128s for firmware/long-trust signed bundles; HMAC-SHA-384 for OT message integrity. Library matrix: `liboqs`, `liboqs-python`, OpenSSL 3.5 + oqs-provider (sidecar), Python `cryptography`. **Docker/Linux only on dev** — no Windows-native `liboqs` build required. Vault Transit for pilot key storage; SoftHSM (PKCS#11) for no-budget dev default.

**D10. Memory architecture.** Mem0 (default, PG + pgvector) for episodic; Letta (opt-in per pilot) for shift-persistent identity memory; Neo4j for ISA-95 Part 2 graph; DVC for procedural skills; PostgreSQL `audit_chain` (append-only, ML-DSA-65 signed, SHA-256 hash chained) for evidence. **SQL, not NoSQL.**

**D11. Observability stack.** OpenTelemetry GenAI semantic conventions; Langfuse v3 self-hosted (90-day mutable trace store); Arize Phoenix for offline + CI evals; separate immutable evidence sink (`audit_chain`) for regulator-grade record-keeping. All Apache 2.0.

**D12. Standards first-class.** VDA 5050 v2.1.0, OPC UA, MQTT Sparkplug B v3.0, ISA-95 Part 2, ROS 2 Jazzy/Kilted, ISO 10218-1/2:2025 + ISO/TS 15066, IEC 61508 + ISO 13849-1:2023 + IEC 62061:2021, ISO/IEC 42001:2023 — mapped in `knowledge-base/KB_12_Standards_Map.md`, integrated in `backend/integrations/*` and `backend/safety/*`.

**D13. Functional safety wrapper architecture.** LLM is planner; classical SIL-rated controller is executor; formal Pydantic safety-contract DSL gates every actuator command. CI enforces: every actuator path test must show `safety.validate` OpenTelemetry span immediately before the `actuator` span.

**D14. Audit cycle invariants.** `scripts/audit.sh` count must strictly decrease per stage (current baseline 439) OR explicitly flag `--no-baseline-drop` for protocol/governance-only stages with justification in `KB_TASK_LOG.md`. CTO checkpoints, A2A protocol stages, governance evidence stages qualify.

**D15. No paid SaaS.** Apache 2.0 / MIT / equivalent libraries throughout: LangGraph, Pydantic AI, FastMCP, `a2a-sdk`, `liboqs`, `mem0`, Langfuse (self-hosted), Arize Phoenix, `asyncua`, `paho-mqtt`, `mqtt-spb-wrapper`, OpenSSL 3.5 + oqs-provider.

---

## Why

1. **Vendor-neutral plumbing is the only seat left at the table.** Every other lane is taken by an incumbent with deeper pockets. The "boring plumbing nobody wants to build but everybody needs" position is acquisition-bait or integration-target for the named big techs (Anthropic, IBM, AWS, Google, Siemens, Bosch, Microsoft, Nvidia) — exactly the user's stated goal.

2. **EU AI Act enforcement window is real and acute.** 2026-08-02 high-risk obligations are 75 days away. Buyers in Q3/Q4 2026 will pay for working evidence pipelines. Auto-generating an Annex IV pack from a single command is a sellable feature.

3. **CNSA 2.0 + 10-year industrial equipment lifecycles converge in 2027.** Any defense-adjacent customer (Bosch defense lines, Siemens defense lines, Lockheed suppliers) will inherit CNSA 2.0 requirements. PQC is not a 2030 problem.

4. **MCP + A2A merger removes the "pick a protocol" risk.** Pre-2026, building agents meant picking sides. Post-merger, both are foundation stacks. Adopting both is no longer hedging; it's the correct architecture.

5. **The warehouse-first wedge is short-cycle.** 3–6 month sales cycles fund the longer manufacturing push (9–18 month cycles). Skipping the wedge and going straight at discrete manufacturing puts cash runway under unnecessary strain.

6. **CTO checkpoints catch breadth-over-depth before it metastasizes.** Every 10 stages a fresh-context reviewer audits the whole system for gaps, vulnerabilities, missing implementations. Without this, the 25-stage roadmap risks shipping 25 half-done stages instead of 25 done stages.

7. **Role-based personas reduce context contamination.** A single generalist agent persona that does ML one task and PQC the next loses focus and ends up writing average code in every domain. Per-task role selection (driven by file paths + task type) keeps each task's standard high.

8. **No mocking / no faking is non-negotiable for big-tech adoption.** The audit baseline mechanism (`.audit-baseline`) was already in place from Stage 1; v2 extends it (no classical-only crypto in new code, no LLM-direct actuator commands) and makes the audit-after-every-task cycle mandatory.

---

## Consequences

**Immediate (this session):**
- 4 new files in Workstream A (this ADR, PRD v2, README banner update, PROJECT_STATUS update).
- ~16 new files in Workstream B (CLAUDE.md, SKILLS.md, 9 role personas, 5 hook scripts, 3 hook helpers, 8 lifecycle scripts, 3 task/audit templates, audits/ scaffold, hooks settings patch doc).
- ~10 new/updated files in Workstream C (7 new KB files + 4 KB updates + 3 compliance updates + TASKS_README update).
- ~19 new stage task docs in Workstream D (template-seeded; bodies filled when their turn comes).

**Stage 2 unchanged.** This expansion does not modify `tasks/STAGE_02_simpy_simulator.md`. Stage 2 remains the next executable stage. The expansion landing only adds new files and updates existing KB/compliance docs.

**Audit count stays at 439.** Pure docs/templates expansion — no backend code touched. The new `.audit-baseline` value is 439 (unchanged); KB_TASK_LOG entry must explicitly note "no code changes" to justify the flat baseline (qualifies for the `--no-baseline-drop` allowance).

**Old "Stage 14 production hardening" relocated to Stage 21.** Anyone referencing the old Stage 14 in conversation must understand it's now Stage 21. `yor-are-an-agentic-optimized-cookie.md` master plan should be updated in a later session to reflect the new numbering (out of scope for this ADR; tracked as a follow-up in the 2026-05-18 KB_TASK_LOG entry).

**LangGraph pulled forward to Stage 11.** Original plan deferred LangGraph migration to "Stage 11+" with model training (Stages 4–10) running in a bespoke coordinator. v2 moves the runtime live before model training completes. Trade-off: Stage 11 task doc must clarify the bridging contract for Stages 4–10 (models register as MCP tools as they ship).

**Functional safety claims gated to Stage 23.** PRD v2 carefully says the wrapper makes the architecture *amenable* to certification — actual TÜV / notified-body certification is a Stage 23 + external assessor activity. Marketing/sales copy must not overclaim a SIL rating before then.

**Per-task cycle becomes mandatory.** Future stages cannot close without running `audit-task.sh` → fixing gaps → `close-task.sh` → which appends to KB_TASK_LOG and seeds the next task doc. Manual closures (skipping the script) leave the chain unsigned and the hook will warn loudly.

---

## Risk Register Reference

`compliance/risk-register.md` gains 6 new rows in this expansion session:
- A2A peer compromise (mitigation: ML-DSA signed agent cards + pinned root + revocation list).
- PQC migration rollback (mitigation: crypto-agility flag, overlap rotation drill).
- MCP tool prompt injection (mitigation: JSON schema enforcement + heuristic sanitizer; Stage 20 eval gate).
- Memory cross-tenant leakage (mitigation: per-`incident_id` namespacing enforced in `mem0_adapter.py`).
- VDA 5050 spoofing (mitigation: MQTT broker mTLS + payload-level signatures).
- OPC UA certificate chain (mitigation: rotation drill; PQC overlay tracked in KB_13).

---

## Alternatives Considered (and Why Rejected)

- **Keep v1 framing, expand depth.** Rejected: head-on competition with Siemens Industrial Copilot, MS Copilot Studio, Palantir AIP, Nvidia GR00T. Saturated lane.
- **Hybrid framing (keep manufacturing name, control-plane architecture inside).** Rejected: slower differentiation; sales pitch flexing per audience adds confusion.
- **Compress new work into the existing 15 stages.** Rejected: each stage becomes a multi-week monster with diluted audits and unclear acceptance criteria.
- **Two-track roadmap (product + governance parallel).** Rejected: audit cadence becomes complex; tracks drift.
- **Keep LangGraph at original Stage 11+ slot.** Rejected: Stages 4–10 would run in soon-to-be-replaced bespoke coordinator with weaker observability — every model would need a refactor afterward.
- **Install LangGraph in Stage 3 (earliest possible).** Rejected: Stage 3 becomes complex and risks slipping the runway; Stage 2 (SimPy) is already ambitious enough.
- **CTO review by in-session role switch.** Rejected: working-memory context biases the audit; fresh subprocess gives an independent read.
- **PQC libraries native on Windows dev host.** Rejected: 1–2 days of build/setup pain; Docker exec workflow is fine for the few dev moments where running PQC code outside compose is needed.
- **Single generalist agent persona.** Rejected: average-quality output across domains; role-based personas keep depth per task.

---

## Closure

This ADR is the contract for the 2026-05-18 PRD expansion session. The session ships Workstreams A–D (documentation + templates + scripts). Workstream E (backend code under `backend/agents/runtime/`, `backend/mcp_servers/`, `backend/a2a/`, `backend/memory/`, `backend/crypto/`, `backend/observability/`, `backend/integrations/`, `backend/safety/`) happens stage-by-stage starting from Stage 11.

Stage 2 (SimPy) remains the next executable stage. After Stage 2 closes, Stage 3 (WebSocket broker + Redis fanout) fires. CTO Checkpoint #1 fires after Stage 3 closes (the 10-task boundary counting from Stage 1).


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:02+00:00 -->
<!-- signature: 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 -->
