# Stage 11.5 — Independent Review (MCP Server Suite + LangGraph Runtime Mount)

**Reviewer:** independent `task-auditor` persona (a DIFFERENT agent than the implementer).
**Date:** 2026-06-15
**Verification mode:** **DYNAMIC** — `scripts/audit.sh` and `cd backend && python -m pytest tests/mcp/ -q`
were executed in this session (results below). No execution was denied this round. (Static line-by-line
trace was also performed for every deliverable file.)

---

## VERDICT: **PASS**

The Stage 11.5 deliverables are honest, real, and verified. Five MCP servers each wrap a genuine backend and
return the canonical honest-unavailable contract on failure; the mount uses the official `mcp` stdio client
(not a stub); the tests spawn real stdio subprocesses and assert real behaviour; the CI gate is real; the ADR,
KB_16, and research §18 match the code. The audit holds at 364 (verified), legitimately `--no-baseline-drop`
for an additive Rule-1a stage that wraps real backends and adds no grep-counted theatre.

One real residual is identified that the implementer's docs slightly overstate: the mounted tools are
**exposed but not yet consumed** by the LangGraph graph nodes. This does not block PASS (the acceptance
criteria as written are met and the ADR does not overclaim it), but it is ledgered as **G-059** for Stage 12.

---

## Dynamic re-run results (independently executed)

| Command | Claimed | Independently observed |
|---|---|---|
| `scripts/audit.sh` | audit holds **364** | **TOTAL = 364**, equal to baseline 364 (confirmed) |
| `cd backend && python -m pytest tests/mcp/ -q` | 22 passed / 1 skipped | **22 passed, 1 skipped, 2 warnings in 111.31s** (confirmed) |

The 111s runtime is itself evidence the tests are real: it reflects 5 stdio subprocess spawns + first-time
heavy-ML imports (torch/xgboost/torchvision/simpy), not in-process mocks. The single skip is the Postgres
round-trip (`test_append_then_query_roundtrip_real_db`), honestly gated on `DATABASE_URL` which is unset in my
local run; CI sets it (the `mcp-conformance` job's Postgres service), so the round-trip IS exercised there.

---

## Per-criterion evidence (task doc `tasks/STAGE_11_5_mcp_servers.md`)

| Criterion | Claimed | Confirmed? | Note |
|---|---|---|---|
| 5 servers start under `python -m backend.mcp_servers` with the documented tools | yes | **YES** | All 5 files present; tools match `SERVER_TOOLS` and KB_16 exactly (14 tools). `__main__.py:55-68` `--once` liveness path is real. Tests spawn each via stdio and assert `tools/list` == manifest. |
| `__main__.py` is a multiprocess supervisor with watchdog | yes | **YES** | `backend/mcp_servers/__main__.py:82-95` — real `subprocess.Popen` per server, `p.poll()` death detection, bounded backoff restart (`max_restarts`), SIGINT/SIGTERM clean teardown. Not faked. |
| Runtime mounts all five | yes (via in-house bridge, not `langchain-mcp-adapters`) | **YES (mount), PARTIAL (wiring)** | `MCPToolMount` (mcp_mount.py:79-128) opens persistent stdio sessions to all 5 and binds 14 `StructuredTool`s; `test_runtime_mount.py:7-13` asserts all 14 namespaced tools load. **BUT** the tools land on `app.state.mcp_tools` and are never read by the graph nodes — see Finding F1. The `langchain-mcp-adapters` deferral is honest (see F3). |
| Each tool has a schema test under `backend/tests/mcp/` (manifest + I/O schema validates) | yes | **YES** | 5 server test files each assert `{t.name} == manifest`; `test_model_inference_server.py:16-23` asserts `inputSchema.properties` fields; real tool calls assert honest-unavailable-or-real. |
| CI gate `mcp-conformance` runs on every PR | yes | **YES** | `.github/workflows/ci.yml:108-145` — `runs-on: ubuntu-latest`, Postgres 16 service, `alembic upgrade head`, `pytest tests/mcp/` with `DATABASE_URL` set. Real job, exercises the DB round-trip in CI. |
| `KB_16` server inventory matches reality | yes | **YES** | KB_16:40-44 lists all 14 tools with correct signatures, matching `SERVER_TOOLS` and the actual `@mcp.tool()` defs. |

---

## Honesty audit (Hard Rule 1 / 1a) — every tool traced to a real backend

| Server / tool | Real backend confirmed | Honest-unavailable confirmed |
|---|---|---|
| `kpi_query.oee` | **Genuine A×P×Q.** Availability = `(elapsed − time_broken − time_maintenance)/elapsed` from real `Stage.snapshot()` fields (`entities/stage.py:295-296`). Performance = `min(1, ideal_cycle×produced/uptime)` where `ideal_cycle = exp(cycle_mu_log_seconds)` from the real `calibration.STAGES` (`calibration.py:93-104`). Quality = `(produced−defective)/produced` from real snapshot fields. **No fabricated term.** Hand-recomputed the test fixture: quality 0.96, availability 0.95 — match. | `unavailable("elapsed sim time is zero…")`, `"no snapshot available"`, `"no stage matched…"` (kpi_query_server.py:71,68,94) |
| `model_inference.*` | Calls the **real singletons** `get_demand_forecaster`/`get_failure_predictor`/`get_defect_classifier` (verified present in `ml/`). No literals returned. | `_guard` (model_inference_server.py:25-34) converts `ModelUnavailableError` → `unavailable(str(e))`; never a fake number. |
| `policy_query.recommend_action` / `explain_action` | Runs the **real** `predict_failure → services.diagnosis.diagnose → services.intervention_policy.decide_intervention` chain; explain calls real `ml.failure_explainer` (exact TreeSHAP). All three functions verified present. | `ModelUnavailableError`/`ValueError`/`KeyError` → honest unavailable (policy_query_server.py:59-64, 84-89); `ex.is_available()` gate before explain. |
| `decision_log.*` | **Real Postgres.** Genuine `INSERT INTO decisions(...)` / `SELECT ... ORDER BY timestamp DESC`; columns map exactly to alembic `0001_init.py:84-103`; `_VALID_STATUS` matches the table CHECK. `persisted = cur.rowcount > 0` (no faked ack). | `unavailable("no Postgres reachable (set DATABASE_URL)")` when DSN absent / connect fails (decision_log_server.py:73,109); `"write failed"/"query failed"` on exception. |
| `sim_world.*` | Drives a **real seeded SimPy** `SimWorld` advanced synchronously (`_common.py:39-75`); `query_state` returns the engine's actual `snapshot()`. | `ImportError` → `unavailable("simulation unavailable…")`; unknown event/scope → `input_error=True`. |

`grep` for `random.uniform|random.choice|generateMockState|_get_demo_*|RESPONSES = {|MODELS = [` across
`backend/mcp_servers/` → **no matches**. No synthetic-constant fabrications (no `confidence = 0.9 − …`, no
hardcoded `feature_importance` literals, no fake `model_version` labels). The honest-unavailable contract is
genuine, not a plausible-looking fake. **Clean on Rule 1/1a.**

---

## The mount — real `mcp` stdio client, not a stub (criterion 3)

`MCPToolMount.__aenter__` (mcp_mount.py:93-106) imports the **official** `mcp.ClientSession` and
`mcp.client.stdio.stdio_client`, spawns each server via `StdioServerParameters(command=sys.executable,
args=["-m", module])`, calls `session.initialize()` + `session.list_tools()`, and wraps each tool as a real
`langchain_core.tools.StructuredTool` whose `coroutine` calls `session.call_tool`. `_model_from_schema`
builds a real pydantic args model from the tool's JSON `inputSchema`. `_extract_result` prefers MCP
`structuredContent`. This is the genuine protocol path, confirmed by the 111s real-subprocess test run and the
`test_mount_invokes_a_real_model_tool` `ainvoke` assertion. **Not a stub.**

---

## Findings (severity-ranked)

**F1 (MEDIUM) — Mounted tools are exposed but not consumed by the runtime graph.**
`main.py:179` sets `app.state.mcp_tools = mcp_tool_mount.tools`, but a repo-wide grep shows **no reader** of
`app.state.mcp_tools` anywhere — the LangGraph nodes (`agents/runtime/graph.py`, `nodes.py`) still call the
models via direct Python imports, not via the MCP tools. So the self-healing loop's decisions do **not** flow
through MCP yet. The task doc's "Files to MODIFY → `backend/agents/runtime/graph.py` — Mount MCP tools" was
**not done** (the mount moved to `main.py` lifespan instead — an architecturally reasonable place for
long-lived subprocess sessions, but it leaves the graph un-wired). The task doc Hand-off line "internal agent →
tool interactions are MCP-mediated" is therefore **slightly overstated**: tools are mounted and callable, but
the graph's actual decision path is not MCP-mediated. The ADR itself does NOT make this overclaim (it says
"mounts the suite at startup" and "runtime mount loads 14 tools + invokes real ones" — both literally true).
*Not a fabrication; the tools genuinely work.* Recommend ledger **G-059**, target Stage 12 (when the memory
layer wires into the runtime, route the runtime's tool calls through the mounted `StructuredTool`s).
*Does not block PASS* — the acceptance criteria as written ("runtime mounts all five") are met.

**F2 (LOW, accuracy nuance) — "Every current langchain-mcp-adapters release requires langchain-core>=1.0".**
The ADR (D2) and `requirements.txt:53` state this. The *conclusion* (incompatible with the frozen 0.3.28) is
correct and the deferral is honest, but the universal phrasing is imprecise: some older adapter releases
required `langchain-core>=0.3.36` (still incompatible with 0.3.28), and only the current 1.x line requires
`>=1.0`. The incompatibility holds either way, so this is a wording nuance, not a substantive error. No action
required beyond awareness.

**F3 (INFO) — Deferral of `langchain-mcp-adapters` is honest and correctly ledgered.** The acceptance
criterion literally names `langchain-mcp-adapters`; the implementer substituted a functionally-equivalent
in-house stdio bridge and ledgered the swap as **G-056** with the langchain-core-1.0 migration. This is a
legitimate, documented engineering decision (keeps the Stage-11 pins frozen), not a quiet drop.

**F4 (INFO) — `--no-baseline-drop` is justified.** The audit holds at 364 (verified). The stage adds new files
that wrap real backends and contain no grep-counted theatre; the bespoke direct-call paths the task doc hoped
would "drop" are still in use (F1 — the graph isn't rewired), so no count decrease was achievable this stage
without rewiring. The hold is honest and consistent with Rule 1a (audit-invisible additive de-mocking).

**F5 (INFO) — stdio-safety fixes are real and verified, not asserted.** The module-top-level warm imports
(every server), the synchronous `env.run(until=…)` SimWorld drive (`_common.py`), and the full-parent-env
subprocess spawn (`mcp_mount.py:34-38`) are all present in code and corroborated by the tests passing over real
stdio (a worker-thread import-lock deadlock would hang the suite; it did not). ADR D4's "verified, not
asserted" claim holds.

---

## New gaps to append to `audits/OPEN_GAPS_LEDGER.md`

| Proposed ID | Gap | Severity | Target stage |
|---|---|---|---|
| **G-059** | MCP tools are mounted onto `app.state.mcp_tools` but **no graph node consumes them** — the LangGraph self-healing loop still calls models via direct Python imports, so runtime decisions are not yet MCP-mediated. Task-doc Hand-off ("interactions are MCP-mediated") is aspirational, not yet true. | medium | Stage 12 (route runtime tool calls through the mounted `StructuredTool`s when memory wiring lands) |

(G-056 / G-057 / G-058 already correctly ledgered by the implementer for this stage; no change needed.)

---

## Summary

Stage 11.5 is a real, honest, deep implementation: five MCP servers over genuine backends with a true
honest-unavailable contract, a real official-`mcp`-SDK stdio mount, real stdio-spawning conformance tests, and a
real CI gate — all independently re-run and confirmed (audit 364, MCP suite 22 passed / 1 skipped). The single
substantive residual (mounted-but-not-consumed tools, F1) is ledgered as G-059 and does not block close; the
ADR is careful not to overclaim it. **VERDICT: PASS.**
