# PRODUCT REQUIREMENTS DOCUMENT (PRD) v2.1 — Specification Hardening Increment
## Vendor-Neutral, EU-AI-Act-Grade, PQC-Ready Agent Control Plane for Industrial Robot + OT Fleets

**Document Version**: 2.1
**Date**: 2026-05-31
**Extends (does NOT supersede)**: [PRD-ai-embodied-agent-v2.md](PRD-ai-embodied-agent-v2.md) (v2.0, 2026-05-18)
**Archival baseline**: [PRD-ai-embodied-agent.md](PRD-ai-embodied-agent.md) (v1.0, January 2026)
**ADR**: [compliance/decision-logs/2026-05-31_prd_v2_1_and_lifecycle.md](compliance/decision-logs/2026-05-31_prd_v2_1_and_lifecycle.md)
**Status**: Active specification increment. v2.0 remains the authoritative base; v2.1 adds the sections below and corrects time-sensitive facts. Where v2.1 and v2.0 conflict on a *date or metric*, v2.1 wins; on architecture, v2.0 stands unless v2.1 explicitly extends it.

---

## v2.1.0 — Why this increment exists

A 2026-05-31 verification pass against the live codebase + a fresh, fully-sourced market scan produced five
needs that v2.0 either left implicit or that changed under our feet:

1. **Clear, consolidated product specifications & objectives** (v2.0 spreads these across §1 and the appendix).
2. **Target evaluations + quantitative benchmarks/SLOs** as one auditable table with datasets, baselines, and CI gates.
3. **An explicit ecosystem & integration strategy** — the product must be an *ecosystem with clear interfaces*, not a monolith.
4. **An operator dashboard requirement** that tracks **agentic vs non-agentic** activity with first-class reporting and alarming.
5. **A pluggable QSC→HSM crypto-provider boundary** so a purchased HSM replaces built-in software key generation as a *configuration change*, plus a **production-grade workflow** requirement.

It also corrects the **EU AI Act timeline** (changed 2026-05-07, after v2.0 was written) and folds in the
verified competitive picture (see [research/market-analysis/index.html](research/market-analysis/index.html)
and research log §11).

> Honesty note (per `docs/honesty-accuracy-prompt.md`): external figures here are cited or labelled as
> design targets. Quantitative benchmarks are *targets we commit to verify*, not yet-measured results, unless
> a stage marks them measured.

---

## v2.1.1 — Product specification & objectives (consolidated)

**What it is.** An open-source (Apache 2.0 / MIT) control plane that sits *above* heterogeneous robots, AMRs,
PLCs and OT systems and *below* the customer's business systems, turning multi-agent reasoning into
**safe, auditable, post-quantum-signed** actions on an industrial fleet.

**What it does (capability objectives).**
- **O1 — Orchestrate** heterogeneous fleets via open standards (VDA 5050, OPC UA, MQTT Sparkplug B, ISA-95, ROS 2), not a single-vendor SDK.
- **O2 — Reason** with a durable, interruptible agent workflow (LangGraph) that plans but never directly actuates.
- **O3 — Gate** every actuator command through a functional-safety wrapper (LLM-planner / SIL-rated-executor split).
- **O4 — Prove** every decision with an immutable, hash-chained, ML-DSA-65-signed audit chain and an auto-generated EU AI Act Annex IV pack.
- **O5 — Protect** every trust boundary with post-quantum (hybrid) crypto and *crypto-agility* (algorithm/provider swappable).
- **O6 — Observe** the whole system — agentic and non-agentic — through one operator surface with alarming and reporting.

**For whom.** Manufacturing engineers, warehouse operations leads, OT/IT integrators, compliance officers
(unchanged from v2.0 §0).

**Wedge → expansion.** Warehouse/fulfillment first → discrete manufacturing → process industries (v2.0 §1.3).

**Explicit non-goals (boundaries).** Not a certified safety PLC (we integrate the customer's certified PLC);
not a robot OEM; not a paid SaaS; not an automotive-assembly or defense-platform product in this version;
not a replacement for hardwired SIL-3+ emergency-stop circuits (LLM observes those, never commands them).

---

## v2.1.2 — Target evaluations & quantitative benchmarks (SLOs)

Full eval methodology, datasets, baselines and CI wiring live in the new
[knowledge-base/KB_23_Evals_and_Benchmarks.md](knowledge-base/KB_23_Evals_and_Benchmarks.md). This is the
headline contract. **All values are commitments-to-verify (design targets) unless a stage marks them measured.**

### A. System / performance SLOs (carried + quantified from v1 §1.3 and KB_10 latency budget)
| Metric | Target (SLO) | How measured | Stage |
|---|---|---|---|
| Simulator baseline throughput | ~500 units/hr (±10%) | `tests/test_sim_calibration.py`, 30-sim-min run | 2 (built), re-asserted each stage |
| Event inject → WebSocket fan-out | **p95 ≤ 250 ms** | live e2e against compose stack | 3 |
| Agent decision latency (advisory) | **p50 ≤ 2 s, p95 ≤ 5 s** | OTel `langgraph.node.*` spans | 11 |
| Cycle-time reduction (pilot) | 25–30% vs baseline | pilot A/B (design target) | 22 |
| Carbon reduction (pilot) | 15–20% vs baseline | carbon-aware scheduling eval | 6.5 / 22 |
| Platform uptime | ≥ 99.5% | DR/HA + chaos drills | 21 |

### B. Trust / safety / compliance evals (the differentiating column)
| Metric | Target | How measured | Stage |
|---|---|---|---|
| Audit-chain integrity | `verify-audit-chain.py` passes end-to-end at any time | CI + on-demand | 13.5+ |
| Annex IV auto-pack generation | ≤ 60 s full pack | `generate-annex-iv-doc.py` timed | 19 |
| Functional-safety gate coverage | **100%** of actuator paths have preceding `safety.validate` span | CI trace inspection | 17 |
| Prompt-injection resistance | **≥ 99%** block on OWASP LLM01 corpus + NIST RMF Agentic vectors | Phoenix eval gate | 20 |
| Cross-namespace memory leakage | **0** unauthorized cross-namespace reads | `mem0_adapter` enforcement tests | 12 |
| VDA 5050 conformance | **100%** schema validation vs VDA reference fixtures | conformance suite | 16 |
| A2A federation interop | 2 independent instances exchange + verify signed messages | `a2a-conformance` CI | 14 |

### C. Crypto-agility evals (PQC + HSM swap)
| Metric | Target | How measured | Stage |
|---|---|---|---|
| Hybrid-PQC TLS on external boundaries | ML-KEM-768 + X25519 on 100% of external surfaces | handshake inspection | 18 |
| Key-rotation drill | ≤ 15 min, **zero data-plane downtime** | `rotate-pqc-keys.sh` drill | 18, re-drilled 25 |
| **HSM provider swap** | software→PKCS#11 HSM with **no caller/code change** (config only); audit chain still verifies | `KeyProvider` swap drill (see v2.1.5) | 13.5 spec, 22 pilot drill |
| Algorithm swap | swap ML-DSA-65 for a future NIST PQC finalist via `migrate(old,new)` | Stage-25 acceptance drill | 25 |

### D. Operator-dashboard SLOs (new — see v2.1.4)
| Metric | Target | Stage |
|---|---|---|
| Live activity latency (event → dashboard) | p95 ≤ 1 s | 12.5 |
| Alarm delivery latency (trigger → operator notification) | p95 ≤ 2 s | 12.5 |
| Agentic vs non-agentic activity separability | 100% of timeline events tagged `actor_class ∈ {agent, human, system, external}` | 11+ |
| Report export (shift / incident / Annex IV summary) | ≤ 10 s, signed | 19 |

---

## v2.1.3 — Ecosystem & integration strategy

The product is an **ecosystem with clear, versioned interfaces** at every seam — this is a deliberate moat
against single-vendor "AI OS" bundling (Siemens+NVIDIA, Rockwell+AWS — see market analysis).

| Seam | Open interface | We compose / integrate (not rebuild) | Swap mechanism |
|---|---|---|---|
| Fleet / AMR | VDA 5050, MassRobotics AMR interop, **Open-RMF** | InOrbit/OpenRobOps, Open-RMF as a *layer beneath* us | adapter per protocol |
| OT / PLC | OPC UA (+ Safety), MQTT Sparkplug B, ISA-95 / IEC 62264 | customer's existing certified PLC | `sil_bridge` adapter |
| Robot middleware | ROS 2 (Jazzy/Kilted) | existing ROS 2 graphs | ROS 2 bridge |
| Agent ↔ agent | **A2A** (Linux Foundation AAIF) | third-party A2A peers via signed agent cards | agent-card capabilities |
| Tools | **MCP** (FastMCP) | external MCP servers (read-only, schema-checked) | per-tool RBAC |
| Crypto / keys | **PKCS#11** + Vault Transit | Entrust / Thales / Utimaco HSMs | `KeyProvider` config (v2.1.5) |
| Observability | OpenTelemetry GenAI semconv | Langfuse (OSS), Arize Phoenix | OTel exporter config |
| Model registry / data | MLflow, DVC, `.safetensors` | HF models, customer datasets | DVC pin + model card |

**Ecosystem principle:** every external dependency sits behind an interface (per v2.0 §12 risk 4). We **compose**
the commoditising layers (fleet orchestration, agent observability) and **own** the differentiating layers
(safety wrapper, signed audit chain, PQC crypto-agility, governance evidence). Partners (HSM vendors, standards
bodies) are explicitly *ecosystem*, not competition.

---

## v2.1.4 — Operator dashboard requirement (agentic + non-agentic)

A single operator surface (frontend) MUST present, in real time, both **agentic** and **non-agentic** activity,
with reporting and alarming as first-class features. Page-level spec lands in KB_08; data/telemetry contract in
KB_15; phased implementation across Stages 11–19 (Stage 3 WS broker is the live-data plumbing it rides on).

**Required panes.**
1. **Activity timeline** — unified, with every event tagged `actor_class ∈ {agent, human, system, external}` and
   `sil` level. Operators can filter agentic-only vs non-agentic-only. (Distinguishing who/what acted is an
   EU AI Act Art. 14 human-oversight enabler.)
2. **Agent reasoning panel** — live LangGraph node trace, tool calls (MCP), confidence, HITL `interrupt()` prompts.
3. **Non-agentic / plant panel** — robot/stage/supplier telemetry, queues, throughput, OEE, energy/carbon, PLC state.
4. **Safety-gate panel** — every `safety.validate` decision (pass/fail, contract, SIL, fail-safe path); STO/SS1 events.
5. **Audit-chain viewer** — append-only rows, chain-verify status, key version/algorithm, signer; one-click `verify`.
6. **A2A federation status** — connected peers, card fingerprints, revocation status.
7. **Policy / governance status** — active policies, budget caps, PII-filter actions, approvals pending.

**Alarming.** Severity model (info / warning / critical / safety-critical); routing (UI toast, optional
webhook/email/Slack via config — no hard SaaS dependency); acknowledge + audit every ack to the audit chain;
de-duplication and storm-suppression; **safety-critical alarms are never silently auto-cleared**.

**Reporting.** Shift report, incident report, and an EU AI Act evidence summary; exportable (HTML/PDF/CSV/JSON),
signed with the current key, with the audit-chain head hash embedded. SLOs in v2.1.2 §D.

---

## v2.1.5 — Pluggable QSC → HSM provider boundary (the "buy an HSM, swap with zero disruption" requirement)

**Requirement.** Built-in software key generation/signing MUST sit behind a single provider boundary so that
adopting a purchased HSM (Entrust nShield, Thales, Utimaco — all expose PQC via **PKCS#11**; see market analysis
§3) is a **configuration change**, not a code change. No caller in `backend/` ever imports a concrete crypto
backend; they depend only on the abstract `KeyProvider`.

**Spec (contract; implemented Stage 13.5 — full design in KB_13):**
```python
# backend/crypto/key_provider.py  (Stage 13.5)
class KeyProvider(ABC):
    """Vendor-neutral signing/keygen boundary. Concrete backends are selected by config only."""
    @abstractmethod
    def generate_keypair(self, alias: str, algorithm: str) -> KeyHandle: ...
    @abstractmethod
    def sign(self, key_alias: str, data: bytes) -> Signature:        ...   # ML-DSA-65 default
    @abstractmethod
    def verify(self, public_key: bytes, data: bytes, sig: bytes) -> bool: ...
    @abstractmethod
    def public_key(self, key_alias: str) -> bytes: ...
    @abstractmethod
    def rotate(self, key_alias: str) -> KeyHandle: ...               # overlap rotation
    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...              # supported algs, FIPS level, attestation

# Concrete backends (selected by CRYPTO_PROVIDER env / config — NOT by importing them):
#   SoftwareKeyProvider   -> liboqs-python (dev/no-budget; Docker/Linux)
#   Pkcs11KeyProvider     -> python-pkcs11 -> SoftHSM (dev) OR a real HSM (pilot/prod), same code path
#   VaultTransitProvider  -> HashiCorp Vault Transit (pilot)
def get_key_provider() -> KeyProvider:   # factory; the only thing callers touch besides the ABC
    ...
```

**Design constraints that make the swap "fast and undisturbed":**
- `Pkcs11KeyProvider` targets the **PKCS#11** standard, so SoftHSM (dev) and a real HSM (prod) are the *same*
  driver with a different slot/token config — the buy-an-HSM path is already exercised in dev.
- `audit_chain` rows carry `key_version` + `algorithm` columns so historical verification survives a provider/key swap.
- Acceptance test (v2.1.2 §C): a documented drill swaps `SoftwareKeyProvider`→`Pkcs11KeyProvider` via config only;
  the running system continues signing and `verify-audit-chain.py` still passes across the boundary.

---

## v2.1.6 — Production-grade workflow requirement

The agent runtime MUST be a **durable, recoverable, human-in-the-loop workflow**, not a fire-and-forget script:
- **Durable state.** LangGraph `AgentState` checkpointed to Postgres; a crash/restart resumes mid-workflow.
- **HITL.** SIL-1 actions pause via LangGraph `interrupt()` for operator confirmation (Art. 14 oversight); SIL-2+ route to the SIL bridge (never LLM-direct).
- **Reliability.** Idempotent tool calls (input-hash dedupe), bounded retries with backoff, and **compensation/rollback** for partially-applied multi-step plans.
- **Governance in-loop.** Per-tool RBAC, token/call **budget caps**, and `approval-required` tags enforced inside the workflow (KB_18).
- **Determinism boundary.** All non-deterministic reasoning is confined to planning nodes; execution is via deterministic, audited adapters.
- **SLO.** Workflow recovery after restart ≤ 30 s; zero duplicate actuator commands on replay (verified Stage 11+).

---

## v2.1.7 — Market positioning (summary; full analysis is the HTML)

Full sourced analysis with SWOT, capability matrix, and four perceptual maps:
[research/market-analysis/index.html](research/market-analysis/index.html); competitor matrix in
[knowledge-base/KB_19_Competitor_Comparative_Governance.md](knowledge-base/KB_19_Competitor_Comparative_Governance.md).

**Position.** No competitor on public evidence combines all four pillars — vendor-neutral/open + EU-AI-Act
evidence + functional-safety split + PQC crypto-agility. Incumbents are building **closed** "Industrial AI
Operating Systems" (Siemens+NVIDIA, Rockwell+AWS); fleet players (InOrbit/OpenRobOps, Formant, Open-RMF, Boston
Dynamics Orbit) are open but have no safety/compliance/crypto plane; agent-governance tools (Galileo, Arize,
LangSmith) are software-only with no OT/safety/crypto. The intersection is genuine white-space.

**Verdict.** Opportunity, not graveyard — **conditional** on execution speed and on keeping the
PQC/safety/neutrality depth ahead of incumbents who have distribution.

---

## v2.1.8 — EU AI Act timeline correction (changed 2026-05-07; verify before external use)

v2.0 §9.2 / §11 / risk-2 reflect the pre-amendment timeline. The **Digital Omnibus on AI** (provisional
agreement, Council + Parliament, **2026-05-07**) defers high-risk obligations:

| Obligation | Old date (v2.0) | New date (v2.1) |
|---|---|---|
| High-risk **Annex III** (use-based) | 2 Aug 2026 | **2 Dec 2027** |
| High-risk **Annex I** (product-regulated) | 2 Aug 2027 | **2 Aug 2028** |
| National regulatory sandboxes | 2 Aug 2026 | 2 Aug 2027 |

Sources: Council of the EU press release 2026-05-07; Gibson Dunn; Covington/Inside Privacy (see research log §11
and HTML Sources). **Pitch implication:** lead near-term with PQC + functional safety + vendor-neutrality;
position EU-AI-Act readiness as the reference architecture for the 2027 window rather than an August-2026
deadline scramble. Manufacturing safety components remain high-risk (Annex III), so the evidence pipeline stays
core — only the clock moved.

---

## v2.1.9 — Updated success-criteria delta vs v2.0 §11

v2.0 §11 stands; v2.1 adds: operator-dashboard SLOs (v2.1.2 §D), HSM-provider-swap drill (§C), workflow recovery
SLO (v2.1.6), and the date corrections (§v2.1.8). No v2.0 architectural criterion is removed.

## v2.1.10 — Related documents
- [PRD-ai-embodied-agent-v2.md](PRD-ai-embodied-agent-v2.md) — base spec (authoritative architecture).
- [knowledge-base/KB_13_PQC_Crypto_Strategy.md](knowledge-base/KB_13_PQC_Crypto_Strategy.md) — `KeyProvider` boundary.
- [knowledge-base/KB_15_Observability_Evidence_Pipeline.md](knowledge-base/KB_15_Observability_Evidence_Pipeline.md) + [KB_08_Frontend_Pages_Spec.md](knowledge-base/KB_08_Frontend_Pages_Spec.md) — operator dashboard.
- [knowledge-base/KB_23_Evals_and_Benchmarks.md](knowledge-base/KB_23_Evals_and_Benchmarks.md) — eval/benchmark methodology.
- [knowledge-base/KB_19_Competitor_Comparative_Governance.md](knowledge-base/KB_19_Competitor_Comparative_Governance.md) — competitor matrix.
- [research/market-analysis/index.html](research/market-analysis/index.html) — sourced market analysis + perceptual maps.
- [compliance/decision-logs/2026-05-31_prd_v2_1_and_lifecycle.md](compliance/decision-logs/2026-05-31_prd_v2_1_and_lifecycle.md) — ADR.
