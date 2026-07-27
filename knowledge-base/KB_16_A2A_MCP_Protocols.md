---
name: A2A + MCP Protocols
description: MCP servers (internal agent→tools) + A2A surface (external agent↔agent) — server inventory, agent-card schema, trust boundary, hybrid TLS layout
type: spec
last-updated: 2026-05-18
---

# KB_16 — A2A + MCP Protocols

## Purpose

Specify how the agent runtime reaches tools internally (MCP) and how it federates with external agents across organisations (A2A) — post-Linux-Foundation-Agentic-AI-Foundation merger (late 2025).

## Source of truth

- Model Context Protocol (MCP) — Anthropic origin, donated to Linux Foundation Agentic AI Foundation Dec 2025.
- A2A protocol — Google origin, donated to Linux Foundation; 150+ production organisations as of April 2026.
- ACP (IBM) — folded into the same foundation.
- This file is the contract for `backend/mcp_servers/` and `backend/a2a/`.

## Body

### Why both, not one

- **MCP** = vertical (agent ↔ tools / resources / prompts). Internal to one agent's runtime. Stage 11.5.
- **A2A** = horizontal (agent ↔ agent across organisations or vendors). External boundary. Stage 14.
- **ACP** is now functionally folded; we don't ship a third protocol.

Examples of where A2A (not MCP) is needed:
- Warehouse fulfilment agent delegating to a carrier's logistics agent.
- Plant orchestration agent talking to a vendor-supplied robot-fleet agent without giving it MCP-level ERP access.
- Cross-site agents in multi-plant manufacturers with per-site MES.

### MCP server inventory (Stage 11.5)

Five FastMCP-based servers, each a separate supervised process under `backend/mcp_servers/`. Mounted into the LangGraph runtime via `langchain-mcp-adapters`.

| Server | Tools (as built, Stage 11.5) | Source file |
|---|---|---|
| `sim_world_server` | `inject_event(event_type, target_id, details, severity)`, `query_state(scope)`, `subscribe_events(since_index, event_type)` | `backend/mcp_servers/sim_world_server.py` |
| `kpi_query_server` | `throughput(state)`, `oee(state, stage_id)`, `utilization(state, unit)`, `queue_depth(state, stage_id)` | `backend/mcp_servers/kpi_query_server.py` |
| `decision_log_server` | `append_decision(decision)`, `query_decisions(decision_type, status, limit)` | `backend/mcp_servers/decision_log_server.py` |
| `model_inference_server` | `predict_demand(history)`, `predict_failure(air_temp_k, …, type_)`, `classify_defect(image_path)` | `backend/mcp_servers/model_inference_server.py` |
| `policy_query_server` | `recommend_action(telemetry)`, `explain_action(telemetry, top_k)` | `backend/mcp_servers/policy_query_server.py` |

Each tool wraps a REAL Stage-4-10 model / the simulation / the KPI math / the decision ledger, and returns
`{"available": false, "reason": …}` (the truth) when its backend can't load — never a fabricated result (Hard Rule
1a). KPI tools compute real Availability×Performance×Quality OEE from a plant snapshot (ideal cycle time from the
real stage calibration). `decision_log` writes **directly to the Postgres `decisions` table** now; it will route
through `backend/memory/audit_chain.py` (SHA-256 chained, ML-DSA-65 signed) when that lands at **Stage 13.5**.

Supervisor: `backend/mcp_servers/__main__.py` (multiprocess + watchdog) runs the five as long-lived **streamable-HTTP**
services (ports 9101-9105). **Transport:** stdio in CI tests + the runtime mount (the client spawns the server as a
subprocess); streamable HTTP for the supervised production services.

**Runtime mount (Stage 11.5):** `backend/agents/runtime/mcp_mount.py::MCPToolMount` opens persistent stdio sessions
and wraps each MCP tool as a `langchain_core.tools.StructuredTool`. We use this thin in-house bridge over the
official `mcp` stdio client **instead of `langchain-mcp-adapters`**, which requires `langchain-core>=1.0` — a major
migration off our frozen `langchain-core 0.3.28` runtime (research §18; ledgered for the langchain-core-1.0 work).
`main.py` mounts the suite at startup when `MCP_MOUNT=1` (env-gated; spawns 5 stdio subprocesses).

> **Implementation note (worker-thread import deadlock):** FastMCP runs a sync `@tool` in an anyio worker thread; a
> first-time heavy import (torch/xgboost/numpy/the simulation) inside that thread deadlocks on the CPython import lock
> in an stdio subprocess. Each server therefore warms its heavy imports at module top-level (main thread). The
> sim/kpi servers advance SimPy **synchronously** (`env.run(until=…)`, no background thread) for the same stdio-safety.

### MCP testing

Every tool gets a schema test under `backend/tests/mcp/test_<server>.py`:

- `tools/list` returns the documented manifest.
- Each tool's input schema validates expected and unexpected payloads.
- Each tool's output schema is honoured.
- Conformance: hits the official MCP inspector if available.

CI gate `mcp-conformance` runs this on every PR.

### A2A surface (Stage 14)

Discovery: `GET /.well-known/agent.json` returns the signed agent card.

JSON-RPC dispatch endpoint: `POST /a2a/v1/rpc`.

### Agent card shape

```python
# backend/a2a/agent_card.py
from pydantic import BaseModel, Field
from datetime import datetime

class AgentCard(BaseModel):
    name: str
    version: str
    capabilities: list[str]            # skill names this agent offers
    endpoints: dict[str, str]          # protocol → URL
    public_key_b64: str                # ML-DSA-65 public key
    supported_kems: list[str] = ["ML-KEM-768+X25519", "X25519"]
    supported_signatures: list[str] = ["ML-DSA-65"]
    supported_protocols: list[str] = ["a2a/1.0"]
    provenance: dict[str, str]         # build info, git SHA, model registry refs
    expiry: datetime
    revocation_list_url: str | None = None
    signature_b64: str = Field(..., description="ML-DSA-65 signature over JCS-canonicalized JSON of this card minus the signature field")
```

Signing (as built, Stage 14): `backend/a2a/agent_card.py:sign_card(card) -> AgentCard` sets the card's ML-DSA-65
public key (the `agent-identity` key from `backend/crypto/pqc_signing.py`) and signs `jcs.canonicalize(card minus
signature_b64)` (RFC 8785).

Verifying: `verify_card(card, *, pinned_roots=None, is_revoked=None, now=None) -> bool` — checks revocation → expiry →
ML-DSA-65 signature → (when given) pinned roots; any failure returns False. Pinned roots live in
`docker/secrets/a2a_roots/`.

### Transport security

A2A traffic terminates at an OpenSSL 3.5 + oqs-provider sidecar (`docker/docker-compose.pqc.yml`):

- Hybrid TLS: ML-KEM-768 + X25519 key exchange.
- mTLS: client cert from peer; server cert from us. Both signed with ML-DSA-65 in the trust chain.
- Sidecar fronts the FastAPI app on plain HTTP. The Python process doesn't need PQC TLS bindings.

### Trust boundary

```
                    ┌────────────────────┐
                    │   External peer    │
                    │   (other org)      │
                    └─────────┬──────────┘
                              │ Hybrid TLS (ML-KEM-768 + X25519)
                              │ mTLS (ML-DSA-65 cert chain)
                    ┌─────────┴──────────┐
                    │  oqs-provider      │
                    │  sidecar           │  ←── enforces TLS, mTLS, hostname verification
                    │  (haproxy/stunnel) │
                    └─────────┬──────────┘
                              │ plain HTTP (loopback)
                    ┌─────────┴──────────┐
                    │  FastAPI app       │  ←── verifies agent card ML-DSA-65 signature
                    │  /a2a/v1/rpc       │      against pinned root + revocation list
                    │  /.well-known/...  │
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │  LangGraph runtime │  ←── route delegated request to appropriate node
                    │  + MCP tools       │      (NOT all MCP tools exposed to external peers —
                    │                    │       only the capabilities declared in our agent card)
                    └────────────────────┘
```

Critical asymmetry: external peers reach our agent through A2A; they do NOT get MCP-level access to our tool surface. The set of A2A-callable skills is a deliberate subset (declared in our agent card's `capabilities`).

### Revocation

`backend/a2a/revocation.py`:

- Polls a configurable URL (default: `https://revocation.example/<org>/agents.json`) on a 5-minute schedule.
- Caches the revocation list locally.
- `verify_card(card)` checks the revocation list before signature; refuses cards whose `public_key_b64` appears revoked.

### Federation testing

`docker/docker-compose.a2a.yml` runs two instances of the same image with different agent-identity keys. Test suite under `backend/tests/a2a/test_federation.py`:

- Both instances start; each fetches the other's agent card from `/.well-known/agent.json`.
- Card signature verifies.
- Instance A invokes a capability on instance B via JSON-RPC.
- Reply signed by B; verified by A.
- Revocation list updated on B; A's next fetch sees the change.

CI gate `a2a-conformance` runs this on every PR after Stage 14.

### Use cases for A2A in this product (concrete)

| Scenario | Inbound or outbound? | Capability |
|---|---|---|
| Carrier's logistics agent picks up shipment from our warehouse | inbound | `request_pickup_window` |
| Supplier's order-management agent confirms expedited delivery | inbound | `confirm_expedite` |
| Customer's MES queries our agent for OEE forecast | inbound | `forecast_oee` |
| Our agent delegates predictive-maintenance scoring to vendor's specialist agent | outbound | `score_failure` |
| Plant A's orchestrator coordinates with Plant B's orchestrator | both | `propose_handoff` |

Each capability has a Pydantic input/output schema in `backend/a2a/skills/<name>.py`.

### What we do NOT expose over A2A

- Direct MCP tool surface (sim_world, kpi_query, etc.) — these are internal.
- Raw `audit_chain` writes from external peers.
- Memory writes to namespaces other than the requesting peer's own session namespace.
- Operator override channels (those go through the customer UI / their own A2A surface, not us).

### MCP threat model + Zero-Trust posture (2026-06-15, research §20)

**Documented MCP attack surface (2026):** tool poisoning (TPA — malicious instructions hidden in tool
descriptions/metadata the model reads), full/advanced schema poisoning (FSP/ATPA), direct + indirect prompt
injection via tool inputs/results, resource-content poisoning, and **credential-aggregation single-point-of-failure**
(one compromised server leaking OAuth tokens across services). Canonical controls: OAuth 2.1 + PKCE + capability
scoping, TLS 1.2+/mTLS server-to-server, a centralized MCP gateway, supply-chain validation of tool definitions, and
multi-layer identification (static metadata analysis + decision-path tracking + behavioural anomaly detection).

**Our current posture (honest — the trust boundary is the local process tree).** Stage-11.5 MCP servers run over
**stdio as local subprocesses spawned by our own runtime** — **no network listener, no remote/third-party MCP server,
no OAuth-token aggregation, no LLM reading untrusted tool descriptions** (tools are wired by us, not discovered). So
the highest-impact MCP threats (rogue-server tool poisoning, token theft, network MITM) are **not currently
reachable**. Already-present controls: typed input schemas (conformance-tested), honest-unavailable (no fabricated
results), memory namespace isolation, append-only `audit_chain`. **NOT yet present (gap G-063):** per-tool
capability authorization, prompt-injection/input sanitisation on tool args, rate-limiting, a **signed tool
manifest** (supply-chain integrity of our own definitions), and — the moment streamable-HTTP is exposed or any
third-party MCP server is mounted (Stage 14) — **mTLS + OAuth 2.1 + a gateway**.

**Zero-Trust for the agentic system (target: CSA Agentic Trust Framework + NIST SP 800-207 + OWASP Top-10 Agentic).**
Four principles → our mapping: **verify explicitly** (HITL `interrupt()` on SIL-1+; neuro-symbolic plan verifier
gates execution) · **least privilege** (Mem0 namespace isolation; no-LLM-direct-actuator; A2A capability subset) ·
**assume breach** (tamper-evident append-only `audit_chain`; PQC migration) · **continuously validate** (every
decision audited + traced; `verify_range`). We are **partially zero-trust by design** but **not yet a coherent ZT
architecture** — missing: per-agent **non-human identity** (ML-DSA-65 agent cards are specced above; not yet issued
to internal agents/tools), per-action authz, ZTNA segmentation, and continuous behavioural anomaly detection. **Why
staged, not now:** ZT needs the PQC identity layer (13.5), the A2A identity/mTLS boundary (14), the safety wrapper
(17), and the red-team eval harness (20) — building a half ZT layer before those would be theatre. **Plan (gap
G-064):** adopt the named frameworks; issue each agent/tool an ML-DSA-65 identity; scope MCP tools to capabilities;
add OWASP-Agentic + prompt-injection evals (Stage 20). The ZT posture is also a **market moat** — "the governed,
zero-trust, evidence-producing agent your auditors + insurers allow on the OT network" (KB_26 / survivability HTML).

## Last verified

2026-06-15 (Stage 14): the **A2A external boundary is BUILT** — `backend/a2a/`: `agent_card.py` (the KB_16 agent-card
schema + `sign_card`/`verify_card` using the Stage-13.5 **ML-DSA-65** KeyProvider + **JCS** RFC-8785 canonicalisation),
`server.py` (`GET /.well-known/agent.json` signed card + `POST /a2a/v1/rpc` **JSON-RPC 2.0** dispatch), `revocation.py`
(5-min poller, fail-safe), `peer_state.py` (active/quarantine/revoked), `skills/forecast_oee.py` (the deliberate
exposed capability — real OEE; NOT an MCP tool). **Trust boundary verified:** the JSON-RPC dispatch serves
`forecast_oee` but refuses `predict_failure` (an MCP tool) with `-32601` — external peers get capabilities, never the
MCP tool surface. **Hand-rolled** (a2a-sdk 1.1.0 needs httpx≥0.28.1 vs our pinned 0.27.2 + pulls google-api-core/
protobuf — research §24; a2a-sdk adoption ledgered G-070). Migration `0007_a2a_peers`; `main.py` mounts the routes.
9 A2A tests pass (card sign/verify/tamper/expiry/revoke/pinned-roots + a two-identity in-process federation + the
trust boundary); CI gate `a2a-conformance`; audit holds 364. **Hybrid ML-KEM-768 mTLS remains Stage 18** (KB_13);
`transport_tls.py` + `docker-compose.pqc.yml` are the sidecar scaffold; the two-instance Docker federation is owed
when Docker is up (G-069). ADR `2026-06-15_stage14_a2a_protocol.md`.

Prior: 2026-06-15 (Stage 11.5): the **five MCP servers + the runtime mount are BUILT + verified** — `backend/mcp_servers/`
(5 FastMCP servers + multiprocess supervisor) + `backend/agents/runtime/mcp_mount.py`. 22 conformance tests pass
(`backend/tests/mcp/`, real stdio client: manifest == this inventory, input/output schema validation, real tool
calls incl. a real Postgres decision-log round-trip + the LangGraph runtime mount of all 14 tools). CI gate
`mcp-conformance` added. Full backend suite 208 passed / 2 skipped; audit holds 364 (no theatre added). ADR
`2026-06-15_stage11_5_mcp_servers.md`. The **A2A** surface (`backend/a2a/`) remains future — Stage 14.

Prior: 2026-05-18, agentic-governance-engineer + security-pqc-engineer review (spec only; no code existed yet).


## Stage 25 note (2026-07-03) — external federation status

The two-instance federation over real HTTP (two distinct ML-DSA-65 identities) was proven at Stage 14 / re-verified at
CTO #4. The Stage-25 AC "federation with a second VENDOR" is **honestly deferred** — it needs a non-internal partner
(vendor / customer / LF Agentic AI Foundation reference peer); no partner exists pre-pilot. `STAGE_25_a2a_federation.md`
was deliberately NOT written (nothing external was tested). Channel-fit work (Kagenti/kagent-compatible AgentCard,
watsonx-Orchestrate A2A) lands at Stage 27 per ADR 2026-07-02.

## Stage 26 note (2026-07-03) — supply-chain coordination evidence surface

The Stage-26 Contract-Net layer writes `supply_chain.cfp` / `supply_chain.award` signed audit rows + emits
`supply_chain.cnp.round` spans per coordination round (the same evidence discipline as the A2A boundary). The five
role agents are in-process today; exposing supplier proxies as A2A peers with signed AgentCards (true inter-org
federation) is the natural Stage-27+ step once mesh identity lands.

## Stage 27 — A2A authentication (R4/G-4 closure) + Kagenti/A2A-spec AgentCard export (2026-07-04)

The A2A endpoint (`a2a/server.py`) now AUTHENTICATES peers via SVID mTLS: when an mTLS-terminating front supplies
the verified client cert (`X-Forwarded-Client-Cert`, the mesh convention), the peer's SPIFFE ID is extracted +
trust-domain/allowlist-checked (`security.spiffe_identity.authenticate_peer`); a foreign-trust-domain peer is
REJECTED, an in-domain SVID becomes the authenticated `peer_id` for governance (R4/G-4 closed on that path).
Without a front, the endpoint falls back to the Stage-24 CONFINEMENT posture (anonymous L0, read-only) — honestly
weaker, named as such. Channel-fit: `agent_card_cnstyle.py` exports our signed card as (a) the LF A2A-spec
AgentCard JSON and (b) a Kagenti AgentCard-CRD, both carrying the dual identity — so our agent is discoverable
INSIDE a CNCF platform / IBM watsonx Orchestrate. Deploying into a live mesh is the pilot deployment step.
