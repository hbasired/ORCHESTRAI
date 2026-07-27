# Dependency-Refresh Feasibility Assessment (Stage 36 / CTO #6 C6-R2)

- **Date:** 2026-07-18
- **Item:** CTO-#6 **C6-R2** — the coordinated dependency-refresh CTO #6 flagged as "its own dedicated increment":
  langchain-core 1.x (to unblock `langchain-mcp-adapters`, gaps **G-055/G-056**) + httpx ≥ 0.28.1 (to unblock
  `a2a-sdk`, gap **G-070**).
- **Verdict:** **NOT SAFELY EXECUTABLE FREE/LOCAL IN THE WORKING ENV — documented + planned, not executed.** The
  refresh is a cascading multi-major-version migration that would very likely break the verified GA'd stack; it needs a
  dedicated branch/staging + CI gate (which we don't have free/local), and its value is low (the pins are
  SBOM-attested + security-gated, not stale-and-vulnerable). Research §47.

## 1. What was attempted (safely — non-mutating dry-run only)

`pip install --dry-run` resolution probes were run against the installed stack — they RESOLVE the packages but do NOT
install, so the working env is untouched:

| Probe | Result (would-install) |
|---|---|
| `httpx>=0.28.1` + `a2a-sdk` | a2a-sdk-1.1.1 · **httpx-0.28.1** · **protobuf-6.33.6** · json-rpc · culsans · aiologic |
| `langchain-core>=1.0` + `langchain>=0.4` + `langgraph>=0.3` + `langchain-mcp-adapters` | langchain-1.3.14 · langchain-core-1.4.9 · langgraph-1.2.9 · **langgraph-checkpoint-4.1.1** · langchain-mcp-adapters-0.3.0 · **starlette-1.3.1** |

## 2. The hard blockers (confirmed via declared metadata)

1. **`fastapi 0.115.6` requires `starlette<0.42.0,>=0.40.0`** — but the langchain-core-1.x chain pulls
   **starlette 1.3.1**. → the langchain-core 1.x migration FORCES a **fastapi major bump** as well.
2. **`langgraph-checkpoint <3` is pinned deliberately** (4.x needs a newer langchain-core and broke langgraph 0.2.60);
   the refresh pulls langgraph-checkpoint-4.1.1 + langgraph-1.2.9 → re-introduces the **Stage-11 `Reviver(allowed_objects=…)`
   break** that the 0.2.60 pin resolved (the durable-checkpointer path).
3. **httpx 0.27.2 → 0.28.1** is shared by fastapi / starlette / mcp / langfuse — a bump ripples through the whole HTTP
   stack.
4. **a2a-sdk pulls protobuf 6.x** — the ML/VDA-5050 stack was pinned around protobuf<5 for TensorFlow (the installed
   env has drifted to protobuf 7.35.1 with TF 2.15 working, so this specific edge is softer than the pin note, but the
   coordinated bump still perturbs the protobuf/TF/grpcio-tools set that VDA-5050 schema-gen depends on).

**Net:** C6-R2 requires a COORDINATED major bump of **langchain(1.x) + langgraph(1.x) + langgraph-checkpoint(4.x) +
starlette(1.x) + fastapi(major) + httpx(0.28.1) + a2a-sdk + langchain-mcp-adapters** — spanning the runtime core, the
API layer, and the HTTP layer. Every one is a load-bearing, SBOM-attested pin.

## 3. Why NOT execute it now

- **No isolated staging + no CI gate free/local.** This is the working dev env; a failed cascading migration would
  break the verified GA'd stack (the LangGraph runtime + durable checkpointer, the FastAPI app + MCP stdio + A2A, the
  ML/VDA-5050 protobuf set) with no clean rollback path here.
- **Low value.** The pins are NOT stale-and-vulnerable: they are frozen for reproducible, Annex-IV-attestable builds,
  tracked in the CycloneDX SBOM, and gated by bandit (blocking) + pip-audit (informative under the documented
  load-bearing-pin exception, `compliance/dependency-exceptions.md`, G-065). The risk is "missing security patches on a
  frozen set," already ledgered — not a live break.
- **The CTO agreed:** CTO #6 routed C6-R2 as "its own dedicated increment ... full live re-test required," i.e. NOT a
  drop-in.

## 4. The de-risked migration plan (for when it IS done, in a dedicated branch + CI)

1. **Branch + staging only.** Never in the working env; gate behind a CI job that runs the FULL live suite (PG/Neo4j/
   Redis) + the crypto/OpenSSL-3.5 gate.
2. **Coordinated API-layer bump:** fastapi (to a starlette-1.x-compatible major) + starlette 1.x together; re-verify
   every route + the OTel FastAPI instrumentation.
3. **Coordinated runtime bump:** langchain 1.x + langchain-core 1.x + langgraph 1.x + langgraph-checkpoint 4.x
   together; re-verify the durable checkpointer (the Reviver path) + the MCP mount; swap the in-house stdio bridge for
   `langchain-mcp-adapters` (closes G-056) and re-run `tests/mcp/`.
4. **HTTP + A2A:** httpx 0.28.1 + adopt `a2a-sdk` (closes G-070); re-run `tests/a2a/` + the two-instance federation.
5. **ML/VDA-5050:** re-verify the protobuf/TF/grpcio-tools set (VDA-5050 schema-gen + all model loads).
6. **Attest:** regenerate the CycloneDX SBOM + refresh `dependency-exceptions.md`; only merge on a green full-suite +
   green audit-chain.

## 5. Status of the affected gaps

- **G-055 / G-056** (langchain-core 1.0 / `langchain-mcp-adapters`) and **G-070** (`a2a-sdk`) remain **OPEN — now with
  a hard-evidenced feasibility assessment + plan attached** (this doc). They stay pin-blocked until the dedicated
  branch/CI migration above; the in-house stdio bridge (Stage 11.5) + the hand-rolled A2A surface (Stage 14) remain
  the honest, functionally-equivalent stand-ins in the meantime.
- **G-065** (dependency supply-chain hygiene) mitigation remains in force (SBOM + bandit + `dependency-exceptions.md`).

---
*Stage 36 · research §47 · the dry-run evidence is reproducible: `pip install --dry-run "langchain-core>=1.0" ...`. No
package was installed; the working env is unchanged.*
