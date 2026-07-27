# Stage 24 — Independent Review (GA release v1.0.0)

**Auditor**: fresh `task-auditor` agent (did NOT implement Stage 24)
**Date**: 2026-06-29
**Method**: DYNAMIC (live run + DB query) + static code read
**Infra**: Docker UP — Postgres `ai-agent-postgres` :5544 (aiagent / manufacturing)
**ADR**: `compliance/decision-logs/2026-06-22_stage24_ga_release.md`

## VERDICT: PASS

Stage 24 (GA v1.0.0 + governance LIVE-enforcement G-080 + ISO-42001 NC-1/NC-2 + EU provider-
readiness) is honest and complete against the four decisive checks. Governance enforcement is
genuinely LIVE — real RBAC + MAC + decision-trace rows are written by real code in the
request/decision paths, not dead code. The gate does NOT break dispatch. The GA framing carries no
certified / CE-marked / EU-registered / real-pilot / sold overclaim (the DoC is a labelled
REHEARSAL). Mechanical audit holds at the 364 baseline.

---

## Acceptance-criteria evidence table

| # | Check | Mode | Result |
|---|-------|------|--------|
| 1 | G-080 fires live (decision.trace / rbac.check / mac.read rows present + calls are real) | DYNAMIC + static | PASS |
| 2 | Governance gate does not break A2A dispatch | DYNAMIC | PASS — 18 passed, 1 skipped |
| 3 | GA framing honest (no certified/CE/registered/pilot/sold overclaim; DoC = rehearsal; ISO docs substantive) | static | PASS |
| 4 | Mechanical audit count | DYNAMIC | PASS — 364 (= baseline) |

## Findings (severity-ranked)

No new gaps. Deferrals are honest, ledgered, and correctly scoped to needing a real buyer/fleet
(Rule 9): real customer pilot + published A/B (G-035/G-043); accredited functional-safety cert
(G-011); horizontal scale (G-066); pgaudit (G-060); Langfuse-UI (G-067); a2a-sdk (G-070);
customer/supplier records (NC-3). CE marking + EU-database registration correctly deferred (need a
legal entity placing the system on the market). Conformity is NOT certified — stated honestly
everywhere it matters.

## Re-run commands & output

### Check 1 — G-080 fires LIVE (DYNAMIC + static) — PASS

Live DB:
```
$ docker exec ... psql -U aiagent -d manufacturing -tAc "SELECT action, count(*) FROM audit_chain
  WHERE action IN ('decision.trace','rbac.check','mac.read') GROUP BY action;"
decision.trace | 2
mac.read       | 1
rbac.check     | 1
```
All three governance row-types present in the live `audit_chain` — concrete evidence the
enforcement paths executed and audited, not just compiled.

Static confirmation the calls are REAL (not dead code):
- `backend/a2a/server.py::a2a_rpc` (lines ~83–99): every A2A RPC invokes
  `governance.rbac.check_function_access(peer_id, AgentTier.L0_PEER, {"a2a_capability"}, "a2a_capability")`
  and `governance.mac.can_read(SecurityLabel.of("internal"), ..., actor=peer_id)` IN the request
  path BEFORE the handler runs. A deny returns JSON-RPC `-32600` (`governance/RBAC` or
  `governance/MAC`) and audits via `_audit_a2a(...)`. Load-bearing on the live external boundary —
  not behind a flag, not stubbed. `ImportError` → honest fallback to peer-key + method-allowlist
  gates (no fabrication).
- `backend/agents/runtime/nodes.py::log` (lines ~342–354): after each decision is written to the
  audit chain, calls `governance.traceability.record_decision_trace(...)` with the Art-12 pre-state
  (prediction/ttf/diagnosis/sil) + post-state (verification/hitl/executed) snapshot. Best-effort
  with honest degradation when no DB (audited=False, no seq) — not fabricated.

### Check 2 — Gate does NOT break dispatch (DYNAMIC) — PASS

```
$ cd backend && DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing \
   HF_HUB_DISABLE_TELEMETRY=1 MEM0_EMBED_DIM=384 MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5 \
   python -m pytest tests/a2a/ tests/governance/ -q --timeout=200
... 18 passed, 1 skipped, 1 warning in 14.98s
```
A2A capability dispatch + governance RBAC/MAC suites both pass with the live gate wired in.

### Check 3 — GA framing honest, no overclaim (static) — PASS

- `RELEASE_NOTES_v1.0.0.md:38` — explicit: *"NOT certified, NOT CE-marked, NOT EU-registered, NOT
  running a real customer pilot, NOT sold."* Deferred items listed honestly (G-035/G-043 pilot+A/B,
  G-011 cert, G-066 scale, G-060 pgaudit, G-067, G-070, NC-3).
- `compliance/eu-declaration-of-conformity.md` — titled **"EU Declaration of Conformity — REHEARSAL
  (Stage 24)"**; header: *"THIS IS A REHEARSAL / TEMPLATE … NOT a legally-effective DoC"*; CE
  marking + EU-database registration explicitly DEFERRED (Art-48/49); notified body N/A (internal-
  control route). Closing: *"does not assert that the system is certified or legally placed on the
  market."*
- `compliance/iso-42001-internal-audit/2026-Q4_management-review.md` — substantive (38-line §9.3
  management-review table). Closes **NC-1**; **NC-2** closed via ISO-42005 doc; **NC-3** honestly
  **OPEN** (customer/supplier records — blocked on a real pilot, accepted as a known limitation, not
  a defect).
- `compliance/iso-42005-impact-assessment.md` — substantive (57 lines), not a stub; authored to
  close NC-2.

### Check 4 — Mechanical audit (DYNAMIC) — PASS

```
$ bash scripts/audit.sh
... TOTAL 364 ; mock_detections 0
Baseline (from .audit-baseline): 364
```
Governance-wiring + compliance-doc + GA stage — additive, no new fabrication surface; holding 364 is
correct.

---

**Independent verdict: PASS.** A different agent reproduced the G-080 live rows, ran the
gate-doesn't-break-dispatch suite green, confirmed the governance calls are load-bearing (not dead
code), confirmed the GA framing carries no certification/market overclaim, and confirmed the audit
holds 364.
