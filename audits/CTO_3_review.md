# CTO Checkpoint #3 — Review (Stages 11–14: runtime + MCP + memory + observability + CDC + PQC + A2A)

**Date**: 2026-06-20
**Scope**: Stages 11 (LangGraph durable runtime), 11.5 (MCP server suite), 12 (agent memory: audit_chain / Mem0 /
Neo4j ISA-95), 12.5 (observability/OTel), 13 (CDC ingestion), 13.5 (PQC foundations: ML-DSA-65 KeyProvider), 14 (A2A
protocol). Fires at Stage 14.5 per the roadmap, covering everything since CTO #2 (which covered Stages 4–10 + the
depth-hardening pass).
**Reviewer persona**: `cto-reviewer` (read-only). This file + `audits/CTO_3_remediation_map.json` are the only writes.
**Independence**: I am a FRESH agent — I did **not** implement any of Stages 11–14. The Docker stack was **UP** this
session, so this is a **DYNAMIC, independent** checkpoint (the strongest posture to date — contrast CTO #2, which was
a caveated self-review). No spawn/tooling limitation this round.

## 0. Live verification I actually ran (read-only, this session)

```
bash scripts/audit.sh
  → TOTAL 364 — Baseline (.audit-baseline) 364  (held flat; Rule-1a audit-invisible: Stages 11–14 add real crypto/
    runtime/memory, not grep-counted theatre)
python scripts/verify-audit-chain.py
  → "Audit chain OK (110 rows verified)"   (hash-chain linkage intact end-to-end; see G-073 re: what this does NOT check)
audit_chain signature census (direct SQL):
  → ML-DSA-65 rows: 31  (sig len 3309, key_version 1 — real FIPS-204)   placeholder-sha256: 79  (sig len 32, kv 0, legacy pre-13.5)
  → spot-verified the newest ML-DSA-65 row (seq 110): pqc_signing.verify(hash, sig, pub)=True, pub len 1952 (real)
ADR signature footers: 34/34 carry an ML-DSA-65 footer; spot-verified 2026-06-15_stage14_a2a_protocol.md footer
  → verify=True, key agent-identity:v1, sig len 3309 (signed_at 2026-06-20 = re-signed when Docker returned)
Cross-tenant memory probe (Mem0Adapter bound to incident TENANT_A):
  → incident:TENANT_B BLOCKED, operator:op2 BLOCKED (CrossNamespaceAccessError); own + semantic:/agent: ALLOWED
Targeted suites (live infra: PG@5544 + Neo4j@7687 + Redis):
  → tests/a2a/ + tests/crypto/ ............ 18 passed, 1 skipped (Docker two-instance, correctly skipif)
  → tests/mcp/ + tests/memory/ + tests/observability/ ... 42 passed, 1 skipped
All seven Stage 11–14 independent reviews read: PASS (Stage 12 carries the documented G-062 different-agent caveat).
```

## 1. Executive verdict

**ON TRACK, and the strongest checkpoint yet — the architecture pillars are real, deep, honestly-deferred where
deferred, and (this time) independently verified on live infra.** Since CTO #2 the project gave the deep models a
real body: a deterministic, durable LangGraph runtime (`agents/runtime/`); five FastMCP tool servers with schema
conformance tests; a five-layer memory stack with a genuinely-enforced namespace boundary; an OTel span layer; a
transactional-outbox CDC wedge; **real FIPS-204 ML-DSA-65** signing (audit_chain rows + all 34 ADRs verify
cryptographically); and an A2A federation boundary whose load-bearing security property (the KB_16 trust asymmetry —
external peers reach capabilities, never MCP tools) is enforced and adversarially confirmed. The honesty discipline
held: audit flat at 364, every deferral (live PQC TLS → 18, a2a-sdk → G-070, langchain-mcp-adapters → G-056) is
ledgered and accurately scoped, and honest-unavailable (`raise`/`return False`/`{available:False}`) is used
consistently instead of fabrication.

**Three things temper the verdict (none is theatre; all are scope/maturity):**
(a) **The runtime is wired to memory but NOT to MCP** — the self-healing nodes still import the Stage-4–10 models
directly; `app.state.mcp_tools` is exposed but un-consumed by the graph (**G-059**, OPEN through three stages now).
The MCP servers are real and tested, but they are a parallel surface, not the runtime's execution path.
(b) **Two security/identity HIGHs that this wave was supposed to *begin* paying are still mostly open** — named
zero-trust + per-internal-agent ML-DSA-65 identity (**G-064**) and MCP-server hardening (**G-063**). PQC foundations
(13.5) + A2A (14) built the *primitives* (KeyProvider, signed cards, trust boundary) but did not issue identities to
the *internal* agents/tools or scope tools to capabilities — exactly the work G-064 named.
(c) **The system is still proxy/benchmark-validated, not fleet-validated, and has no real actuator** (G-035/G-043,
Stage 22). "Production-grade" remains *method- and infrastructure-grade*, not *deployment-proven*. The runtime
`execute` node explicitly records intent only (no actuator until the Stage-17 safety wrapper) — correctly honest, but
it means the end-to-end "self-healing" claim stops at the simulator.

## 2. Prior CTO #2 remediation verification (cross-check `CTO_2_remediation_map.json`)

| CTO #2 remediation (target) | Status now | Evidence |
|---|---|---|
| R1 — run 5 owed per-increment indep reviews + indep CTO #2 (G-049/G-050) → 11 | **HONORED** | `audits/STAGE_0{6,7,8,9,10}_depth_independent_review.md` (all PASS) + `audits/CTO_2_independent_review.md` (CONCUR). G-049/G-050 RESOLVED in ledger. |
| R2 — sweep process gaps G-015/G-038/G-039/G-048 → 11 | **HONORED** | All four RESOLVED in `OPEN_GAPS_LEDGER.md` (G-038 word-boundary role map; G-039 append-only shrink hook; G-048 base-10 arithmetic; G-015 demonstrated instance fixed). |
| R3 — refresh risk-register (stale stages + C-MAPSS/NEU/OSS/pandas rows) → 11 | **HONORED (now going stale again)** | Register carries C-MAPSS/NEU-CLS/causal-learn/dice-ml/SB3/pandas + A2A/PQC/memory rows; dates through 2026-06-15. BUT last-reviewed is 2026-06-15 and the "refresh every CTO checkpoint" cadence is again unmet at THIS checkpoint → R-CTO3 below. |
| R4 — fix test harness G-044 (lifespan + Neo4j) → 11 | **HONORED** | `conftest.py` now runs app lifespan; G-044 RESOLVED (`test_api` 21-failed→24-passed; `test_websocket_smoke` hang→2-passed). Verified live suites boot. |
| R5 — wire deepened models into live runtime + prove Ollama fallback → 11 | **HONORED (runtime); PARTIAL (Ollama)** | LangGraph runtime consumes the real models end-to-end (`agents/runtime/nodes.py`, tests `test_canned_decision.py`). Ollama fallback EXISTS structurally (`agents/llm_client.py:316-369`, Groq→Ollama) but the self-healing loop is **LLM-free**, so the fallback is not exercised by the runtime and there is no live-Ollama proof. CTO #1 #5 / CTO #2 R5's "prove it is real" is code-real, not run-proven. → re-route low. |
| R6 — dependency provenance (lockfile + SBOM) → 22 | **NOT YET DUE** | Stage 22. `pip-audit` CI job exists but `continue-on-error: true` (warn-only). G-065 OPEN. |
| R7 — real-fleet re-fit (G-035) + pilot (G-043) → 22 | **NOT YET DUE** | Stage 22. G-035/G-043 OPEN. |
| R8 — replace placeholder-SHA256 ADR signing with real ML-DSA-65 → 13.5 | **HONORED + VERIFIED** | 34/34 ADRs carry real ML-DSA-65 footers; I cryptographically verified one (True). audit_chain `_sign()` produces real ML-DSA-65 for new rows (verified seq 110). |

**Net: 6 honored (R1–R5, R8), 2 not-yet-due (R6/R7 → Stage 22). One honored-but-re-staling (R3 register).** This is
the cleanest prior-remediation scorecard across the three checkpoints. CTO #2's own owed items G-049/G-050 are paid;
the only carried independence debt is **G-062** (formal different-agent pass on Stage 12 — its dynamic verification is
done; the different-agent judgement was blocked by a session limit). This CTO #3 being a real fresh-agent pass partly
discharges the spirit of that debt for the wave, but not Stage 12 specifically.

## 3. The 7 required assessments

**1. LangGraph runtime determinism + checkpoint coverage — REAL.** `graph.py` compiles a `StateGraph` with a
checkpointer keyed by `thread_id` (`get_checkpointer()` → Postgres when reachable, honest in-memory otherwise;
`test_checkpointer_factory_defaults_to_memory` asserts no fake durability). The loop nodes (`nodes.py`) are
deterministic and side-effect-free except `execute`/`log`; there is no `random.*` in the loop (audit confirms).
`test_canned_decision.py` proves the full ordered loop, a *genuine* verifier rejection under a binding PlantState
(`test_runtime_verifier_genuinely_rejects_unsafe_plan`), HITL consumption on SIL-1+, and Postgres durability when
DATABASE_URL is set. **Caveat (LOW):** there is no explicit *two-run-identical* determinism assertion — determinism
is structural and indirectly tested, not pinned by a regression. → R-CTO3 (add a determinism replay test → Stage 21).

**2. MCP tool schema discipline — REAL.** `tests/mcp/` (per the invariant) includes a manifest-conformance test
(`test_manifest_matches_documented`) and an input-schema test (`test_input_schemas_have_expected_fields` asserts
`inputSchema["properties"]` for `predict_failure`/`predict_demand`/`classify_defect`). 42 mcp+memory+observability
tests pass live. CI gate `mcp-conformance` runs over a real stdio path against a pgvector Postgres. Honest gaps
already ledgered: per-process sim world (G-057), HTTP mount path untested (G-058), `langchain-mcp-adapters` deferred
(G-056). **No schema theatre.**

**3. Memory namespace isolation under stress — REAL and ENFORCED (probed live).** `mem0_adapter.py:100-109`
`_authorize()` does **exact-string** matching (`namespace == f"incident:{self.incident_id}"`) — no substring/prefix
leak — and raises `CrossNamespaceAccessError` for anything outside the bound incident/operator + the shared
`semantic:`/`procedural:`/`agent:` prefixes. My live probe (adapter bound to TENANT_A) confirmed `incident:TENANT_B`
and `operator:op2` are **BLOCKED**, own + shared **ALLOWED**. Queries are parameterized (`WHERE namespace = %s`), so
no SQL-injection bypass of the filter. The enforcement is at the Python authorization layer, not the DB (there is no
Postgres RLS policy on `mem0_memories`) — adequate because every read goes through the adapter, but a direct SQL
client bypasses it. → R-CTO3 (add RLS / DB-level tenant policy → Stage 19, the governance/RBAC stage).

**4. audit_chain integrity end-to-end — VERIFIED, with one honesty correction to the claim.** `verify-audit-chain.py`
returns "Audit chain OK (110 rows verified)" — but read what it verifies: it walks the **SHA-256 hash chain**
(`prev_hash`/`hash` linkage + recompute) and the ML-DSA-65 signature check is wrapped in `try/except: pass` using
`key_manager.get_public_key_by_version` (which the script comment itself calls "best-effort"). So the script's "OK"
attests **hash-chain integrity, not that every signature is cryptographic.** The reality (which I checked by direct
SQL + an independent `pqc_signing.verify`): **31 rows are real ML-DSA-65 (verified True), 79 are legacy
`placeholder-sha256` (32-byte, key_version 0).** That is honest — `audit_chain.py:55-65` labels placeholders
explicitly and `verify_range` counts them as "chain-valid, signature-not-yet-cryptographic" — but two things follow:
(a) the **task doc's "sample 1000 rows" is aspirational** (chain has 110); (b) the 79 placeholder rows are **NOT
post-quantum-non-repudiable** and were never back-signed. For Art-12 evidence to be regulator-clean, either back-sign
the legacy rows or document a cutover seq below which signatures are placeholder. → R-CTO3 (→ Stage 19 evidence
pipeline). **G-073** (verify script does not actually fail on a bad/placeholder signature) is a new MEDIUM.

**5. OTel coverage of every layer — PARTIAL.** Confirmed spans: `langgraph.node.*` (every node, via
`graph._traced_node`), `mcp.tool.<server>.<tool>` (`mcp_mount.py:115,124`), `memory.mem0.search`/`.add`,
`ml.inference.failure_predictor`, `audit_chain.append` (`evidence_sink`), `eval.<suite>` (`phoenix_evals`). FastAPI
auto-instrumentation is installed. **Uninstrumented layers:** (a) **A2A has ZERO spans** — `backend/a2a/` has no
`traced_span`/`start_as_current_span` (the external federation surface — card serving, JSON-RPC dispatch, capability
calls — emits no traces; the one regulator-relevant external boundary is invisible to the evidence pipeline);
(b) **`ml.inference.*` wraps only `failure_predictor`** — the world-model TTF, learned-causal diagnose, SHAP explain,
and RL decide steps get only the coarse `langgraph.node.*` span, not a per-model `ml.inference.*` span; (c) CDC
ingestion (`cdc_listener`) has no span. KB_15 says "spans every layer must emit." → R-CTO3 (instrument A2A + the
remaining model calls + CDC → Stage 19/20). **G-074** (A2A surface uninstrumented) is a new MEDIUM.

**6. PQC signing posture — STRONG and VERIFIED.** Real FIPS-204 ML-DSA-65 via `dilithium-py` behind the KB_13
`KeyProvider` ABC (pk1952/sk4032/sig3309 confirmed). audit_chain new rows + agent cards + all 34 ADRs sign and
**verify cryptographically** (I checked an audit_chain row, an ADR footer, and the A2A adversarial cross-key-forge
probe in the Stage-14 review — all correct). No RSA/ECDSA in `backend/crypto/` (hook + `pqc-crypto-tests` CI gate
enforce). **Honest caveats correctly stated:** software provider is NOT side-channel-hardened (dev/no-budget tier;
HSM/Vault swap is config-only via `CRYPTO_PROVIDER`); the 79 legacy placeholder audit rows (item 4). **One scope
gap, not a defect:** ML-DSA-65 identity is issued to the *agent-identity* alias (one key) for ADRs/audit/cards, but
**not per-internal-agent** — G-064's "issue each agent/tool an ML-DSA-65 identity" is unstarted.

**7. A2A federation security posture — REAL, the trust boundary is the right property and it holds.**
`server.py:75-79` dispatches JSON-RPC ONLY to `a2a.skills.SKILLS` (= `{forecast_oee}`) and returns `-32601` for
anything else; the Stage-14 independent review adversarially confirmed three *real* MCP tool names
(`predict_failure`/`run_inference`/`query_kpi`) are refused — **no code path from `/a2a/v1/rpc` to the MCP surface.**
`verify_card` enforces revocation → pinned-roots → expiry → signature with any failure → False (no partial trust;
cross-key-forge rejected). Revocation poller is fail-safe (never clears a known-revoked key on fetch error) with
bounded clean shutdown. **Honest deferrals:** live hybrid ML-KEM-768 mTLS → Stage 18 (`transport_tls.status()
['live_pqc_tls']=False`, not overclaimed); a2a-sdk → G-070; two-instance Docker federation now RESOLVED over real
HTTP (G-071, 2026-06-20). **The interim peer gate is advisory** (`server.py:67-73`: `X-A2A-Peer-Key` header is checked
only *if present* — an unauthenticated caller is not blocked at this layer). That is correctly scoped (real mTLS
client-cert→peer_state binds at Stage 18, and the surface only ever exposes capabilities), but until Stage 18 the
A2A endpoint is **effectively unauthenticated for capability calls** — fine for a closed pilot, NOT for an exposed
deployment. → folds into G-063/G-064 + Stage 18.

## 4. Gaps (immediate — for the follow-up `agentic-governance-engineer` session)

1. **G-062 (Stage 12 formal different-agent review) is still OPEN.** Stage 12's dynamic verification is done, but the
   *different-agent* judgement was blocked twice. This CTO #3 (a real fresh agent) reduces the risk but does not
   formally discharge Stage 12. Run `scripts/independent-audit.sh 12` now that fresh-agent tooling works.
2. **Risk register refresh is owed AT THIS CHECKPOINT.** Cadence ("every CTO checkpoint refreshes the full
   register") is unmet — last-reviewed 2026-06-15. Add rows for: A2A interim-unauth gate, the 79 legacy placeholder
   audit rows, the verify-script signature-check gap (G-073), A2A trace blindness (G-074), and update Last-reviewed.
3. **`pip-audit` is still `continue-on-error: true` (warn-only).** Its own comment says "flip to required when Stage
   11 deps clean." Stage 11+ shipped four stages ago. Either promote it to blocking or document why the frozen set
   (langgraph0.2.60↔checkpoint<3, starlette<0.42, httpx0.27.2) keeps it warn-only (G-065).
4. **Document the audit_chain signature cutover.** State the seq below which rows are `placeholder-sha256` (legacy,
   pre-13.5) so no reader mistakes "Audit chain OK" for "all rows post-quantum-signed."

## 5. Vulnerabilities (file:line, verified read-only this session)

1. **V1 (MEDIUM) — `verify-audit-chain.py` cannot fail on a bad signature (G-073).** `scripts/verify-audit-chain.py:142-152`
   wraps the ML-DSA-65 verify in `try: ... except Exception: pass`, and resolves the key via
   `key_manager.get_public_key_by_version` which may not match the `pqc_signing` path. Result: the script's exit-0/"OK"
   attests hash linkage only; a row with a forged/garbage `sig_mldsa` (but a correct hash) would still print "OK". The
   chain hash IS tamper-evident, so this is not a silent data-integrity hole — but the *non-repudiation* guarantee the
   script implies is not actually checked. Make the signature verify load-bearing (and fail on a non-placeholder row
   whose sig doesn't verify).
2. **V2 (MEDIUM) — A2A external surface emits no telemetry (G-074).** `backend/a2a/` (`server.py`, `agent_card.py`,
   `skills/`) has no `traced_span` — the one external trust boundary is invisible to the OTel evidence pipeline and to
   audit_chain (capability calls are not audit-logged either). For an EU-AI-Act Art-12 posture, every external
   interaction across a trust boundary should be evidenced. Add `a2a.rpc.<method>` spans + an audit_chain row per
   capability call.
3. **V3 (MEDIUM, interim — folds into G-063/G-064 + Stage 18) — A2A capability endpoint is effectively unauthenticated
   until the Stage-18 mTLS sidecar.** `server.py:68` `if peer_key:` gates only when the header is present; a caller
   omitting `X-A2A-Peer-Key` reaches `forecast_oee` unauthenticated. Acceptable for a closed pilot + the surface
   exposes no tools, but must not ship exposed without the Stage-18 client-cert binding. Already scoped in the ADR;
   re-flagged so it is not forgotten.
4. **V4 (LOW) — `mem0_memories` has no DB-level tenant policy (RLS).** `mem0_adapter.py` enforces namespace isolation
   in Python only; a direct SQL client (or any non-adapter reader) bypasses `_authorize`. Adequate today (single
   in-process reader), but defense-in-depth wants Postgres RLS keyed on namespace once multi-tenant. → Stage 19.
5. **V5 (informational) — runtime self-healing loop is LLM-free, so the Groq→Ollama free-cost fallback
   (`agents/llm_client.py:316-369`) is never exercised by the runtime.** The fallback is code-real but
   live-unproven; CTO #1 #5 / CTO #2 R5's "prove it is real" remains a structural claim. NL-injection / "ask the
   factory" (G-022/G-023) are where the LLM path actually runs — prove it there.

## 6. Missing implementations (all specified, on-roadmap — none mis-claimed as done)

- **G-059 — runtime↔MCP wiring (the headline architectural gap of this wave).** The runtime consumes models via direct
  Python import; `app.state.mcp_tools` is exposed but un-read. "Runtime decisions are MCP-mediated" is NOT true yet.
  OPEN through Stages 11.5→12→14. → Stage 15/16 (or a dedicated runtime-MCP-routing increment).
- **G-064 — named zero-trust + per-internal-agent ML-DSA-65 identity (HIGH).** Primitives built (KeyProvider, cards,
  trust boundary); internal agents/tools have no issued identity, no per-action authz, no behavioral anomaly
  detection. The CSA-Agentic/NIST-800-207/OWASP-Agentic adoption is unstarted. → Stage 17/20.
- **G-063 — MCP server hardening (per-tool authz, arg sanitisation, signed tool manifest, rate-limiting).** Local
  stdio makes the high-impact MCP threats unreachable today, but these are required before HTTP exposure / any
  third-party server. → Stage 17.
- **G-021/G-009 — live cascade observability + the message-cascade graph UI.** Spans exist; the operator-facing
  real-time cascade/latency graph does not. → Stage 19+ (with A2A/CDC instrumentation).
- Per roadmap: OT/IT + VDA 5050 / Open-RMF (G-010/G-041, 15/16); functional-safety actuator wrapper (Stage 17 — the
  runtime `execute` is intent-only until then); Annex IV + RBAC/BLP (G-029/G-030, 19); red-team/agentic evals
  (G-008, 20); real-fleet re-fit + pilot (G-035/G-043, 22). The pgaudit (G-060) and DVC procedural-memory (G-061)
  layers from KB_14 remain unbuilt.

## 7. Cross-cutting risks

1. **Security/identity HIGHs are accumulating faster than they are paid.** G-064 (HIGH, ZT + agent identity) and
   G-063 (MEDIUM, MCP hardening) were named in the 2026-06-15 security review and routed through 14→17→20, but
   13.5+14 built only the *primitives*. The risk is that "we have ML-DSA-65 and a trust boundary" gets read as "we
   are zero-trust." We are not — internal agents are unsigned, tools are uncapped, the A2A endpoint is interim-unauth.
   Hold Stage 17 to actually issuing identities + scoping tools, not deferring again.
2. **The runtime is a credible body that does not yet use its own organs.** MCP tools (G-059) and the LLM fallback
   (V5) are built and tested in isolation but not on the runtime's critical path. This is the same "brains without a
   body / body without nerves" pattern CTO #2 flagged, one layer up. Wire G-059 before adding more surfaces.
3. **Evidence-pipeline completeness for Art-12.** The audit_chain is real and tamper-evident, but: 79 rows are
   placeholder-signed, the verify script doesn't enforce signatures (G-073), the A2A boundary isn't audited (G-074),
   and capability calls aren't logged. For a *regulator-grade* claim (the task doc's bar) these must close at the
   Stage-19 evidence pipeline. Today it is *engineer-grade* evidence, not yet *auditor-grade*.
4. **Independence is restored — keep it.** This wave ran with working fresh-agent tooling (Stage 11.5/13/13.5/14
   reviews are genuinely DYNAMIC + different-agent; this CTO #3 is a real fresh pass). That is the single biggest
   process improvement over CTO #2. Do not let it lapse; G-062 (Stage 12) is the one outstanding formal pass.
5. **Scope discipline held** (this wave deepened the platform spine; it did not widen domains). Keep it: do not open
   OT/IT breadth (Stage 15/16) before G-059 + G-062 are closed and the register is refreshed.

## 8. Future-task remediations (routed → `CTO_3_remediation_map.json`)

| # | Remediation | Target |
|---|---|---|
| R1 | Run the owed FORMAL different-agent independent review of Stage 12 (`scripts/independent-audit.sh 12`) — G-062. | 15 |
| R2 | Refresh `compliance/risk-register.md` at this checkpoint: add rows for the A2A interim-unauth gate, the 79 legacy placeholder audit rows, the verify-script signature gap (G-073), A2A trace blindness (G-074); correct any stale stage numbers; update Last-reviewed. | 15 |
| R3 | Wire the runtime graph to consume the mounted MCP `StructuredTool`s for at least one node (route the model/tool calls through MCP, not direct import) so runtime decisions are genuinely MCP-mediated — G-059. | 16 |
| R4 | Make `scripts/verify-audit-chain.py` signature-check load-bearing: fail (exit 1) on any non-placeholder row whose ML-DSA-65 sig does not verify; report the placeholder cutover seq explicitly — G-073. | 19 |
| R5 | Instrument the uninstrumented layers: add `a2a.rpc.<method>` spans + an audit_chain row per A2A capability call (G-074); add per-model `ml.inference.*` spans for world-model/diagnose/explain/decide; add a CDC ingestion span. | 19 |
| R6 | Close the regulator-grade evidence gaps: back-sign (or formally document the cutover for) the 79 legacy placeholder audit_chain rows, and add the message-cascade/latency observability surface (G-021). | 19 |
| R7 | Promote `pip-audit` (and confirm `bandit`) to BLOCKING CI gates, or document the load-bearing-pin exception; generate a CycloneDX SBOM — G-065. | 18 |
| R8 | Adopt a NAMED zero-trust framework + issue a per-internal-agent ML-DSA-65 identity; scope MCP tools to per-tool capabilities + arg sanitisation + a signed tool manifest + rate-limiting (the A2A interim-unauth gate must bind to real mTLS client-cert→peer_state) — G-063/G-064. | 17 |
| R9 | Add DB-level tenant isolation (Postgres RLS) on `mem0_memories` as defense-in-depth behind the adapter's Python `_authorize` — V4. | 19 |
| R10 | Add a runtime determinism regression: assert two runs of the same incident/thread produce identical traces+decisions (pin the structural determinism the runtime relies on). | 21 |
| R11 | Prove the Groq→Ollama free-cost LLM fallback live on the path that actually uses an LLM (NL-injection / "ask the factory", G-022/G-023) — close the long-standing CTO #1 #5 / CTO #2 R5 "prove it is real". | 16 |
| R12 | Carry forward the still-not-due credibility constraints: real-fleet re-fit (G-035) + reference pilot (G-043). | 22 |

## 9. Bottom line

The platform spine is built, real, and — for the first time — independently verified on live infrastructure: a
deterministic durable runtime, schema-disciplined MCP servers, an enforced memory tenant boundary, real FIPS-204
ML-DSA-65 across ADRs/audit-chain/agent-cards, and an A2A trust boundary that adversarially holds. CTO #2's
remediations were honored (6/6 due; R6/R7 not yet due). **Two things to fix before this wave earns "regulator-grade":
(1) finish wiring — the runtime must use its MCP tools (G-059) and the evidence pipeline must cover the A2A boundary
+ enforce signatures (G-073/G-074); (2) actually start the zero-trust/identity work the primitives were built for
(G-063/G-064) instead of deferring it again.** The independence regression from CTO #2 is repaired — protect it. The
trajectory is the strongest it has been; the gaps are honest, ledgered, and scoped — keep them that way.
