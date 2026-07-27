# Stage 23 — Independent Review (task-auditor)

**Date**: 2026-06-29
**Reviewer**: Fresh, independent `task-auditor` agent. **Did NOT implement Stage 23.**
**Stage**: 23 — Conformity Assessment Dry-Run (+ governance MAC/RBAC/traceability; pays G-028/029/030, G-011 path).
**Mode**: Mostly **DYNAMIC** (governance tests run live, theatre-grep run live, audit run live). The DB-dependent
audit-wiring + final Annex-IV regeneration are **Docker-gated → static doc-review only** (Docker is DOWN; this is
expected and disclosed by the implementer).

---

## VERDICT: PASS-WITH-GAPS

The stage honestly implements its acceptance criteria. The governance code is **real, not theatre** (correct
Bell-LaPadula logic, sound RBAC, honest audit-degradation), tests pass live (9/9), the conformity docs are evidence-
backed and honestly scoped, and nothing overclaims certification or a real notified body. The gaps are the
**deferred-by-design** items the implementer already disclosed (Docker-gated live wiring + 3 minor NCs → Stage 24) plus
one I add: the governance library has **no live enforcement call site** yet (EA-5). None is a theatre/fabrication
finding; hence PASS-WITH-GAPS, not FAIL.

---

## Per-criterion evidence

| AC (task doc) | Claimed | Independently confirmed? | Note |
|---|---|---|---|
| CTO R10: mock notified-body assessment; close G-028/029/030; define G-011 path | done | **YES** | External review written (`audits/STAGE_23_external_review.md`); ledger rows G-028/029/030 = RESOLVED, G-011 = PATH DEFINED — all read live |
| Annex IV `<date>_dry_run.pdf` via generator | done | **YES (file present)** | `compliance/annex-iv-packs/2026-06-22_dry_run.{pdf,html}` exist (32 KB / 40 KB); 14 sections; Art-12 section discloses DB-down degradation |
| `iso-10218-risk-assessment.md` per ISO 10218-2:2025 §6 | done | **YES** | H1–H9 hazards tied to real codebase measures; honest scope boundary + G-011 cert path §5 |
| `iso-42001-internal-audit/2026-Q4_audit.md` covering controls | done | **YES** | Clauses 4–10 + 9 Annex-A objectives, cited evidence; 7/9 C, 3 minor NC, 0 major |
| External reviewer feedback in `STAGE_23_external_review.md` | done | **YES** | Authored this session (mock-assessor hat) |
| Gaps routed as Stage 24 remediations | done | **YES** | NC-1/2/3 → Stage 24 in the audit doc; EA-4/EA-5 added to ledger this session |
| ADR `<date>_stage_23_dry_run_outcome.md` | done | **YES** | Present, accepted, honest-framing section explicit |

---

## Check A — Governance code is REAL, not theatre (DYNAMIC)

**Bell-LaPadula (`backend/governance/mac.py`) — CORRECT.**
- `dominates(a,b)` = `a.level >= b.level and b.categories <= a.categories` (line 51) — exactly level-dominance +
  category-containment. ✔
- `can_read` (no-read-up): `allow = dominates(subject, obj)` (line 67) — subject must dominate object. ✔
- `can_write` (no-write-down / ⋆-property): `allow = dominates(obj, subject)` (line 76) — object must dominate
  subject. ✔
- `require_read/require_write` raise `MacViolation` (never swallowed). ✔
- Verified by tests: read-down OK / read-up blocked / read-equal OK / write-up OK / write-down blocked / incomparable
  (higher level but missing category) denied — `test_governance.py` lines 13–46. All pass.

**RBAC (`backend/governance/rbac.py`) — SOUND.**
- Tier ordering L0<L1<L2<L3 (IntEnum); `FUNCTION_MIN_TIER` enforces least-privilege per function.
- `check_function_access` (lines 54–70) denies in correct priority order: unknown function → **L0-peer confinement
  to `a2a_capability` (assume-breach, checked before tier/grant)** → tier below minimum → function not in grant set →
  else allow. The L0 confinement-before-grant ordering is the right defence-in-depth posture. ✔
- Verified: worker-can't-actuate, embodied-can-when-granted, right-tier-but-not-granted denied, L0 peer confined,
  unknown function denied — tests lines 51–76. All pass.

**Traceability (`backend/governance/traceability.py`) — HONEST DEGRADATION.**
- `record_decision_trace` builds a bounded pre/post snapshot + decision and appends ONE `audit_chain` row; on any
  exception it returns `seq=None, audited=False` and **does NOT fabricate a seq** (lines 59–66). The monkeypatched
  DB-failure test asserts exactly this (lines 81–96). ✔
- The `audited=False` path is the genuinely-honest degradation, not faking a record — matches Rule 1a.

**Audit-wiring honesty:** all three modules' `_audit`/append helpers wrap the DB call in `try/except` returning a
boolean `audited` flag — the decision never depends on the DB, and a missing DB is reported, not faked. ✔

**Test run (live, no Docker):**
```
cd backend && python -m pytest tests/governance/ -q
......... 9 passed in 0.75s
```

**Theatre grep (live):**
```
grep -rn "random.uniform|random.choice|Math.random|RESPONSES = {|MODELS = [|_get_demo_" backend/governance/
(no matches — exit 1)
```

---

## Check B — Conformity assessment (see `STAGE_23_external_review.md`)
Conducted as the mock-notified-body hat in the companion file. Summary: route classification correct (Annex-VI
internal control, no notified body for Annex-III pts 2-8, no presumption of conformity); RA + 42001 audit + Annex-IV
pack evidence-backed; 3 NCs honestly flagged; readiness = substantially-conformant pre-cert file, NOT certifiable
today.

---

## Check C — Honesty / no overclaim (DYNAMIC doc-read)
- No claim of certification, accredited body, real notified body, or completed pilot anywhere. The ADR §"Honest
  framing" and every doc header state "self-audit dry-run." ✔
- The Annex-IV pack's Art-12 record-keeping section **discloses** "DB not reachable at generation time" and the
  red-team section reports the honest **heuristic-only 0.7582** (NOT the inflated hybrid 0.9935). ✔  **No overclaim: YES.**

---

## Check D — Audit (live)
- `.audit-baseline` = **364**.
- `bash scripts/audit.sh` → **TOTAL 364** (== baseline 364; "NO PROGRESS" message is expected — governance code is additive + real, no fakery to replace; held with `--no-baseline-drop "conformity dry-run; doc-only"` per task doc).
- `grep` for theatre patterns in `backend/governance/` → no matches.

---

## Findings (severity-ranked)

| # | Severity | Finding | file:line | Disposition |
|---|---|---|---|---|
| F-1 | MEDIUM | Governance MAC/RBAC/traceability is a **pure library with tests but NO live enforcement call site** — no import of `governance.*` exists outside `backend/governance/` and `backend/tests/` (grep returned empty). The audited allow/deny rows will only appear once it is wired into a runtime/request path. Honestly consistent with the ADR (runtime-node wiring "verified when Docker is up" is NOT claimed done), but a real assessor (EA-5) will ask where it is enforced. | `backend/governance/*` (no callers) | **NEW gap EA-5 → ledger, Stage 24** |
| F-2 | MEDIUM | Final Annex-IV pack's Art-12 record-keeping section is degraded (Docker down); must be regenerated with the DB up + `verify-audit-chain.py` exit-0 attached before a real assessment. | `compliance/annex-iv-packs/2026-06-22_dry_run.html` §8 | **NEW gap EA-4 → ledger, Stage 24 (Docker-gated)**; already disclosed by implementer |
| F-3 | MINOR | 3 ISO-42001 minor NCs (mgmt-review record, ISO-42005 standalone doc, customer/supplier records). | `iso-42001-internal-audit/2026-Q4_audit.md` §NCs | Already ledgered (NC-1/2/3) → Stage 24 |
| F-4 | INFO (cert) | Functional-safety certification (G-011) requires an accredited body + certified PLC — correctly deferred post-build. | `iso-10218-risk-assessment.md` §5 | Already ledgered (G-011) |

No theatre, no bypass, no faked tests, no hard-rule violation found. Baseline correctly held (governance code is
additive/real; the task doc authorises `--no-baseline-drop "conformity dry-run; doc-only"`).

---

## Gaps to fold into Stage 24
- EA-4 (regenerate Annex-IV with DB up), EA-5 (wire governance into a live enforcement point), NC-1/2/3, G-011 cert.
All appended/confirmed in `audits/OPEN_GAPS_LEDGER.md`.
