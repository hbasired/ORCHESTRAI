---
status: done
stage: 33
slug: safety_oversight_hardening
created: 2026-07-13
---

# Stage 33 — Safety & runtime-oversight hardening (CTO #6 in-house remediations)

> Pays down the in-house hardening items CTO #6 routed: (C6-R1/**G-075**) closes the longest-lived open safety item —
> the `sil_bridge` trusted a caller-settable `Decision.allow`/`route`, so a FORGED `Decision(allow=True)` could
> actuate — by minting an unforgeable, action-bound, time-limited **capability token** on validate() that execute()
> must redeem (or re-validate); (C6-R3) wires the Stage-31 behavioural monitor as an always-on runtime hook on 100%
> of live incidents; (C6-R4) refreshes the risk register for Stages 29–33 + records the G-075 closure. Research §44.
> Free/local; the binding gate remains `safety/validator`.

## Cross-cutting requirements (MANDATORY every stage — CLAUDE.md §4 rules 9–11 + §5)

- [ ] Read `KB_24_System_Design_HLD_LLD.md` (design) + `KB_25_Causal_SelfHealing_Engine.md` (self-healing engine: predict→diagnose→reason→verify→intervene; dynamic features; N-domain) and align this stage with them.
- [ ] Read `audits/OPEN_GAPS_LEDGER.md` and **fold every OPEN gap whose `target_stage` ≤ this stage into the acceptance criteria below** (list the gap IDs).
- [ ] **SOTA research + depth justification (MANDATORY, research-first — CLAUDE.md Hard Rule 11):** BEFORE implementing, run a web-research pass on this stage's domain SOTA and append a dated numbered section to `research/initial-research.md` (date, scope, sources+URLs, findings, decision impact). Then choose the **deepest honest free/local/CPU-feasible** method (real benchmark datasets, attention/Transformer, learned/library methods over toy/hand-coded ones) and **justify here why this is the most thorough achievable** under the constraints. A toy/shallow choice where a deeper free path exists is a close-blocking gap; the missing research section is itself a gap.
- [ ] **Free-cost only:** Groq free tier (`GROQ_API_KEY` in `backend/.env`) / Ollama local for LLM; OSS/local infra. No paid SaaS at build time. No committed keys.
- [ ] **Stage explainer HTML (operator mandate, 2026-06-11):** before close, write `research/stage-explainers/STAGE_33/index.html` — self-contained (inline CSS, no CDN), explaining: what this stage built and why now, how it works (with the real file paths), what was measured (real numbers, honesty-tagged BUILT/PARTIAL/PLANNED), what changed in the system, and what the next stage starts with. Same honesty discipline as `research/*/index.html` artifacts.

## Pre-requisites

- Stage(s) closed: 17 (functional-safety wrapper / sil_bridge), 31 (behavioural monitor), 32 (CTO #6 predecessor); CTO #6 done
- Decision logs honoured: `2026-07-13_stage31_detector_eval_hardening.md`, the Stage-17 safety ADR; CTO_6_review.md
- KB files at minimum version: KB_17 (functional safety wrapper)
- Gaps ledger rows pulled in (IDs): **G-075** (sil_bridge forgery/TOCTOU — CTO-#6 C6-R1), C6-R3 (behavioural-monitor runtime hook), C6-R4 (risk-register refresh); G-027 (free-cost, ongoing)

## Acceptance criteria

- [x] **AC1 (C6-R1/G-075) — a forged Decision can no longer actuate.** `safety/capability_token.py` mints an HMAC
  capability token (bound to the canonical decision + action-hash + nonce + issued_at) in `validate()` on ALLOW;
  `sil_bridge.execute()` actuates ONLY via (a) authoritative re-validation from contract+world_state OR (b) a valid,
  fresh token bound to THIS action. Verified: `tests/safety/test_capability_token.py` — a forged `Decision(allow=True)`
  (no token/contract), a token minted for a different action, a stale token, and a tampered token are ALL rejected;
  the genuine round-trip + re-validate path actuate.
- [x] **AC2 (G-075) — no regression to the existing safety gate.** The full `tests/safety/` suite (26) still passes;
  blocked/mis-routed decisions still rejected before the token check; SIL routing unchanged.
- [x] **AC3 (C6-R3) — continuous behavioural oversight on live incidents.** `run_incident` feeds every live incident's
  real behavioural features to the Stage-31 monitor when `RUNTIME_BEHAVIOR_MONITOR=1` (off by default; off the hot
  path; honest-degrading — a monitor error never fails the run). Verified: runtime determinism holds with it off;
  with it on, the result carries `behavior_anomaly`.
- [x] **AC4 (C6-R4) — risk register refreshed for Stages 29–33.** `compliance/risk-register.md` gains the Stage 29–33
  rows (conversational Rule-3 posture, repair-dispatch + RL-shadow gates, detector single-corpus caveat, oversight
  hook) and records **G-075 CLOSED**; the `sil_bridge`/`safety/__init__` defence-in-depth wording is narrowed to the
  now-accurate guarantee.
- [x] **AC5 — free-cost + no regression.** New deps: none (stdlib hmac). Audit holds 3. Also FIXED a latent Stage-29
  honest-empty bug found in regression (off-topic questions grounded on arbitrary decision traces once the DB filled).
- [x] **AC6 — research-first (§44) + explainer + independent review.** Research §44 appended BEFORE implementing;
  `research/stage-explainers/STAGE_33/index.html`; independent review by a DIFFERENT agent = PASS.

## Files to CREATE

| Path | Purpose |
|---|---|
| `backend/safety/capability_token.py` | G-075: mint/verify unforgeable, action-bound, time-limited actuation capability tokens (stdlib HMAC) |
| `backend/tests/safety/test_capability_token.py` | 7 tests — forged/stale/wrong-action/tampered rejected; genuine + re-validate paths actuate |
| `research/stage-explainers/STAGE_33/index.html` | stage explainer |

## Files to MODIFY

| Path | Change |
|---|---|
| `backend/safety/validator.py` | `validate()` mints a capability token on ALLOW |
| `backend/safety/contract.py` | `Decision` gains `token`/`nonce`/`issued_at` |
| `backend/safety/sil_bridge.py` | `execute()` requires re-validation OR a valid+fresh token; rejects forged (G-075) |
| `backend/safety/__init__.py` | narrow the defence-in-depth wording to the now-accurate guarantee |
| `backend/agents/runtime/graph.py` | C6-R3: always-on behavioural-monitor hook in `run_incident` (gated) |
| `backend/conversation/evidence.py` | fix a latent Stage-29 honest-empty bug (off-topic no longer grounds on arbitrary traces) |
| `compliance/risk-register.md` | C6-R4: Stage 29–33 rows + G-075 CLOSED |
| `audits/OPEN_GAPS_LEDGER.md` | G-075 RESOLVED |

## Files to DELETE

| Path | Reason |
|---|---|
| (none) | additive stage |

## KB files this stage updates

- `knowledge-base/KB_TASK_LOG.md` (always)
- `knowledge-base/KB_17_Functional_Safety_Wrapper.md` (capability-token authorization at the sil_bridge)

## Verification commands

```bash
bash scripts/audit.sh                    # holds at 3 (additive; --no-baseline-drop)

cd backend && DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5544/manufacturing \
  python -m pytest tests/safety/ -q      # 33 pass incl. the 7 capability-token tests

# behavioural-monitor hook (off by default -> determinism holds; on -> behavior_anomaly present)
cd backend && python -m pytest tests/agents/runtime/ -q
```

## Audit target

- Pre-stage baseline: 3
- Target: hold at 3 (`--no-baseline-drop`) — additive safety/oversight hardening; zero new `random.*`/mock (the
  capability token uses stdlib `hmac`/`os.urandom`, not the theatrical-fallback `random`).

## Role

- Primary: `robotics-integration-engineer` (functional-safety wrapper / sil_bridge)
- Secondary: `agentic-governance-engineer` (behavioural oversight + risk register), `security-pqc-engineer` (token design)

## Risks / unknowns

- The capability-token secret is per-process (`os.urandom` at import) — tokens don't survive a restart (fine: they're
  single-actuation, sub-second-lived). A same-process caller could in principle read the key, but that is a far higher
  bar than forging a dict, and the authoritative re-validation path does not depend on the token at all.
- `sil_bridge` still has no real production caller (the live emitter is `master.dispatch_order`→`validate_order`); the
  hardening is defence-in-depth readied for the first real SIL≥2 PLC caller — done NOW as code per CTO #6, not deferred.

## Hand-off (read by `scripts/next-task.sh` when seeding the next stage)

- What is now true that wasn't before this stage:
  - The longest-lived open safety item (G-075) is CLOSED: a forged/stale/wrong-action Decision can no longer actuate
    via `sil_bridge` (capability tokens + mandatory re-validation).
  - The behavioural monitor runs on 100% of live incidents (gated on); the risk register covers Stages 29–33.
- What the next task starts with:
  - The remaining CTO #6 in-house items: C6-R2 (dependency-refresh — its own dedicated increment) + C6-R3 tail
    (multi-turn dialogue memory) + C6-R5 (frontend real-data wiring). The big real-world items (pilot G-035/G-043,
    cert G-011, scale G-066) stay buyer/accredited-body-blocked.
- Open items deferred to a future stage:
  - C6-R2 dependency-refresh (langchain-core 1.x + a2a-sdk, pin-blocked — dedicated increment).
  - The real pilot + certification (buyer/accredited-body-blocked).

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

## Pre-populated by start-task.sh (2026-07-13T12:15:55Z)

### Suggested role (from slug heuristic)

**robotics-integration-engineer** — open `.claude/skills/robotics-integration-engineer/SKILL.md` before touching code.

### KB files to update (seeded from role's Mandatory reads)

- `knowledge-base/KB_TASK_LOG.md`
- `knowledge-base/KB_12_Standards_Map.md`
- `knowledge-base/KB_17_Functional_Safety_Wrapper.md`

### Pre-requisites (from previous stage's hand-off — STAGE_32_pilot_readiness_package.md)


- What is now true that wasn't before this stage:
  - The pilot-prep is COMPLETE: a charter with predefined success criteria + gates, an honest capability-readiness
    matrix (every capability's real measured number + real-data dependency), an A/B protocol for the full capability
    set, and the data-intake for everything Stages 26–31 added — a real engagement can start day-one.
  - The four post-Stage-28 build stages (29–32) are done.
- What the next task (CTO #6) starts with:
  - A read-only every-10 CTO checkpoint across Stages 29–32 (run `scripts/cto-review.sh`) — the operator sequenced it
    AFTER the four stages.
- Open items deferred to a future stage:
  - The real pilot + real-data re-fits + published A/B (G-035/G-043) and accredited certification (G-011) — all
    buyer/accredited-body-blocked, not free/local-buildable.

---

*Template version: 2026-06-11 (adds the mandatory per-stage explainer HTML; previous: 2026-05-18 PRD v2.0 expansion). Created by `scripts/start-task.sh`.*

### CTO checkpoint remediations targeting this stage (auto-routed)

- (from CTO_6_remediation_map.json) Harden sil_bridge.execute against Decision forgery/TOCTOU (G-075) � re-run validate() from contract+world_state inside execute (or sign+verify the Decision); narrow the defence-in-depth wording. Code-hardening, do NOT keep deferring to 'first PLC caller'. Longest-lived open safety item.
- (from CTO_6_remediation_map.json) Dedicated dependency-refresh increment (G-055/G-056/G-070) � coordinated langchain+langgraph major bump to langchain-core 1.x, adopt a2a-sdk + langchain-mcp-adapters once httpx unpins; full live re-test; refresh SBOM.
- (from CTO_6_remediation_map.json) Always-on runtime hook for the behavioural monitor (wire it on 100% of live incidents, not just eval) + multi-turn dialogue memory / chat-history persistence for the conversation endpoints.
- (from CTO_6_remediation_map.json) Risk-register refresh for Stages 29-32 (conversational-injection Rule-3 posture, repair-dispatch gate, detector single-corpus caveat) + carry the single-corpus detector caveat into any external-facing material.


These items MUST appear as acceptance criteria above.

### Open gaps-ledger rows targeting this stage (auto-surfaced; CLAUDE.md hard rule 10)

- G-027: **Free-cost constraint** (CLAUDE.md rule 9): every stage uses Groq free / Ollama / OSS / local; no paid SaaS at build time. Engine reasoning must fit free-tier �  (target: every stage; status: ONGOING)

Fold each into the acceptance criteria above (or explicitly defer with a justification + new target stage).
