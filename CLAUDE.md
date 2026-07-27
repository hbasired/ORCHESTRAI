# CLAUDE.md — Claude Code Session Entrypoint

> Claude Code auto-loads this file at every session start. It is the source of truth for: who you are on this project, what to read before doing anything, which role persona to take, and what the hard rules are. Keep it scannable.

---

## 1. Project Identity

This repo builds a **vendor-neutral, EU-AI-Act-grade, post-quantum-ready agent control plane for industrial robot and OT fleets**. Warehouse-first wedge, then discrete manufacturing, then process industries. Open source (Apache 2.0 / MIT), no paid SaaS.

Authoritative spec: [`PRD-ai-embodied-agent-v3.md`](PRD-ai-embodied-agent-v3.md) (2026-06-11, standalone consolidation). The earlier chain — v1, v2.0, v2.1, v2.2, v2.3 — is **archival and frozen** (hook-enforced); v3 supersedes all of them.

Key ADRs: [`2026-05-18_prd_v2_repositioning.md`](compliance/decision-logs/2026-05-18_prd_v2_repositioning.md) (v2 repositioning) · [`2026-06-11_strategic_product_reset.md`](compliance/decision-logs/2026-06-11_strategic_product_reset.md) (v3 consolidation, product-manager role, Stage 6 = vertical slice v0).

---

## 2. Start every session with `/begin`

The fastest path: run the project's custom slash command **`/begin`** (defined in `.claude/commands/begin.md`). It runs `scripts/init.sh` which:

1. Pre-flight checks (python, git, CLAUDE.md, `.audit-baseline`, loader).
2. Emits the full context bundle via `scripts/load-context.py` — about 600 lines covering: `.audit-baseline`, latest `KB_TASK_LOG.md` entry, **STATE & DO THIS NEXT** (the most important section), full current task doc, full SKILL.md for the suggested role, KB-file head excerpts, latest audit, latest ADR, CTO remediations targeting this stage.
3. Prints explicit recommended next action.
4. With `/begin --auto-route`, auto-runs `next-task.sh` / `rectify-task.sh` for unambiguous states.

> **Naming note:** Claude Code has a built-in `/init` slash command that *initializes a CLAUDE.md file* by analyzing the codebase. This project already has a hand-authored, production-grade CLAUDE.md (this file), so the built-in `/init` is not what we want here. **Use `/begin` for project session init**, not `/init`.

If the hook hasn't been registered or the slash command doesn't work, fall back to manual context loading:

```bash
bash scripts/init.sh             # full bundle + state + recommendation
# or
python scripts/load-context.py --mode=session-start
```

The bundle reads these sources (in this order) so you don't need to read them all manually:

1. `knowledge-base/KB_TASK_LOG.md` — most recent entry (append-only, newest at bottom).
2. The next-in-line task doc in `tasks/STAGE_NN_*.md` (the one with `status: not-started` or `in-progress` and the lowest number).
3. The KB files that task doc lists in its "KB files this stage updates" block (head excerpts).
4. The most recent `audits/STAGE_NN_audit.md` if present.
5. The most recent file in `compliance/decision-logs/`.
6. `.audit-baseline` (single integer — current theatrical-fallback count to beat).
7. The full SKILL.md for the suggested role.
8. CTO remediation items targeting this stage (from `audits/CTO_<N>_remediation_map.json`).

If the task is a **CTO checkpoint** (filename matches `STAGE_*_cto_checkpoint_*.md`), additionally read:
- The previous `audits/CTO_<N>_review.md` (if any).
- All `audits/STAGE_NN_audit.md` files since the previous CTO checkpoint.
- The full `compliance/risk-register.md`.

---

## 3. Pick Your Role (Decision Tree)

| If the task touches… | Take role |
|---|---|
| `backend/ml/`, `backend/training/`, weights, evals, model cards | `ml-engineer` |
| `frontend-nextjs/` | `frontend-engineer` |
| `backend/crypto/`, `backend/a2a/`, TLS, key rotation, signed bundles | `security-pqc-engineer` |
| `backend/integrations/` (VDA 5050, OPC UA, Sparkplug B, ROS 2), `backend/safety/` | `robotics-integration-engineer` |
| `compliance/`, evidence pipeline, Annex IV pack, risk register | `compliance-engineer` |
| `docker/`, `.github/`, observability, DR, infra | `devops-sre` |
| `backend/` (everything else: FastAPI, Alembic, services, agents) | `backend-engineer` |
| System **design** (HLD/LLD, component boundaries, interfaces, data/control flow, trade-offs) before implementing | `system-designer` (owns `KB_24`) |
| Market/product strategy, PRD stewardship (new-version files only), GTM/pricing/ICP, positioning, `research/*/index.html` viability artifacts | `product-manager` (owns `KB_26`; never code) |
| Filename matches `STAGE_*_cto_checkpoint_*.md` | `cto-reviewer` (read-only persona) |
| Auditing a stage you did **not** implement (independent per-stage review) | `task-auditor` (read-only; MUST be a different agent than the implementer) |
| Cross-cutting, planning, governance, default | `agentic-governance-engineer` |

Role personas live in `.claude/skills/<role>/SKILL.md`. Each persona names its mandatory reads, success criteria, forbidden behaviors, output contract, and hand-off. **Open the role file before touching code.**

---

## 4. Hard Rules (Forbidden)

1. **No mocking, faking, or theatrical fallbacks** in `backend/` (outside `backend/tests/` and `backend/training/`) or `frontend-nextjs/src/`. `scripts/audit.sh` greps for `random.uniform`, `random.choice`, `Math.random`, `generateMockState`, `_get_demo_*`, hardcoded `RESPONSES = {...}` / `MODELS = [...]` literals. The count in `.audit-baseline` (**402** post Stage 5 close — the file itself is the source of truth; this prose is a snapshot) must **strictly decrease** at each stage close — or the stage must be explicitly flagged `--no-baseline-drop` with justification in `KB_TASK_LOG.md` (CTO checkpoints, protocol-only stages, governance-only stages qualify).

    **1a. The audit grep is necessary, NOT sufficient — beware AUDIT-INVISIBLE theatre (2026-06-14 lesson).** A passing/flat audit does **not** prove a path is honest. The grep cannot see **dict-literal / hardcoded-constant fabrications** (e.g. a route returning `feature_importance = [{"feature_name": "...", "importance_score": 0.35}, ...]`), **synthetic constants** (e.g. `confidence = 0.9 - h*0.01`, `±10%` fake uncertainty bounds, a `"model_version": "lstm-v1"` label with no model), or **fabricated fallback returns** in `except`/no-model branches. These are still **forbidden theatre** even though grep-invisible (same class as G-047, G-052). Therefore: (a) when you **de-mock a subsystem, sweep its WHOLE fabrication surface** — every `except`-fallback, every "fallback"/`# Generate mock` block, every hardcoded return on a live route — not just the grep-visible hits; (b) **never write "this path returns honest-empty / is honest / gates execution" in an ADR, KB, model card, or explainer without READING the actual code path and confirming it** — an unverified honesty/capability claim is itself a gap (this session: an ADR claimed `decision_engine` was "honest-empty" when it fabricated; an explainer claimed the verifier "gates execution" when its Stage-6 config made it a no-op). Honest-unavailable means `raise ModelUnavailableError` / honest-empty `[]` — not a plausible-looking fake.
2. **No classical-only signatures in new code** after Stage 13.5 (PQC Foundations). New signing/verification uses ML-DSA-65 via `backend/crypto/pqc_signing.py`. Existing classical paths are migrated on the Stage 18 (PQC Wave 2) schedule. No `RSA-` / `ECDSA-` in new files after Stage 18.
3. **No LLM-direct actuator commands.** All actuator paths must route through `backend/safety/validator.py` (Stage 17+). CI verifies every actuator OpenTelemetry span has a preceding `safety.validate` span.
4. **No edits to finalized decision logs.** `compliance/decision-logs/YYYY-MM-DD_*.md` files are append-only ADRs. A correction is a new ADR, not an edit to the old one. The PreToolUse hook will block this.
5. **No edits to `.audit-baseline`** outside `scripts/close-task.sh`. The closure ritual rewrites it; manual edits break the audit cycle.
6. **No edits to ANY existing PRD version file** (`PRD-ai-embodied-agent*.md`) — all are frozen on creation, **hook-enforced** (generalized 2026-06-11). The authoritative spec is the highest-numbered version (currently v3); new PRD work is always a new file (`PRD-ai-embodied-agent-v4.md` next).
7. **No new ML weights without `*.metrics.json` + `compliance/model-cards/<model>.md`.** CI gate `scripts/check-model-cards.sh` enforces.
8. **No bypassing hooks via `--no-verify` or skipping `close-task.sh`.** If the closure ritual is broken, fix it — don't route around it.
9. **Zero paid cost through the final stage.** Every implementation must use free tier / OSS / local only. Default reasoning LLM = **Groq free tier** (`default_llm_provider="groq"`, `GROQ_API_KEY` in `backend/.env`) with **Ollama (local)** fallback. Real HSM, managed cloud, and paid APIs are post-final-stage/pilot-budget items, not build-time dependencies. Never commit an API key. (See memory `feedback_free_cost_groq`.)
10. **Carry the new concepts forward.** Every stage from Stage 4 on MUST read [`knowledge-base/KB_24_System_Design_HLD_LLD.md`](knowledge-base/KB_24_System_Design_HLD_LLD.md) (HLD/LLD), [`knowledge-base/KB_25_Causal_SelfHealing_Engine.md`](knowledge-base/KB_25_Causal_SelfHealing_Engine.md) (self-healing engine: predict→diagnose→reason→verify→intervene + dynamic features + N-domain), and [`audits/OPEN_GAPS_LEDGER.md`](audits/OPEN_GAPS_LEDGER.md), and **fold the gaps targeted at that stage into its acceptance criteria**. New concepts are built into each stage as it comes, not bolted on at the end.
11. **Depth over expedience + research-first (the toughest honest path).** Every build stage MUST (a) run a web-research pass on the stage's domain SOTA and append a dated `research/initial-research.md` section **BEFORE implementing** (see §5 — this is now mandatory per build stage, not conditional), and (b) choose the **deepest architecture/method that is honest AND free/local/CPU-feasible** — real benchmark datasets over toy signals (e.g. C-MAPSS, NEU-CLS), attention/Transformer over toy nets where it helps, learned methods over hand-coded ones (e.g. learned causal discovery), battle-tested libraries over fragile from-scratch code where credibility matters (e.g. SB3) — and **justify in the task doc why the chosen depth is the most thorough achievable** under the free-cost + honesty constraints. Honest ≠ shallow: a small/toy implementation where a deeper free/local one is feasible is a **hard-rule violation**, not an acceptable shortcut.

    **11a. Full depth in the FIRST pass — no "shallow now, deepen later" (operator mandate, 2026-06-14).** The original Stages 6–10 were honest but shallow and had to be re-opened in a costly depth-hardening pass. That two-pass pattern is now FORBIDDEN: **the depth a hypothetical "second implementation" would add IS the bar for the first implementation.** Do not ship the easy version intending to deepen it later — think deeper up front and build the complete, thorough version in the first go. The canonical illustration of the gap (the size of what "shallow" costs) is **Stage 8, first vs. second implementation**:

    | KB_25 step | First pass (shallow — NOT acceptable) | Second pass (the depth that should have been first) |
    |---|---|---|
    | PREDICT | toy 1-layer LSTM on a near-trivial SimWorld signal (97.8% but trivial) | **Transformer encoder on the real C-MAPSS FD001 benchmark — test RMSE 13.80, beats CNN/LSTM baselines** |
    | REASON | **hand-coded** known-SCM counterfactual (asserted, not measured) | **learned causal discovery** (causal-learn PC) that recovers the SCM hub from data (skeleton F1 0.75) |
    | VERIFY | absent (deferred) | **neuro-symbolic plan verifier** — symbolic constraint engine that rejects unsafe plans (KB_25 step 3) |

    Before implementing any stage, explicitly ask: *"what would a second, deeper pass add — real benchmark datasets, learned over hand-coded, attention/Transformer over toy nets, a battle-tested library, the missing loop step? — and can I do that now, free/local/CPU?"* If yes, that IS the first implementation. A reviewer (and the operator) will treat a shippable-but-shallow first pass, where a deeper free/local path was feasible, as a hard-rule violation. (Precedent: the 2026-06-14 Stages 6–10 depth-hardening pass — ADR `2026-06-14_depth_08_world_model_causal_verify.md`; research §16; memories [[feedback_production_grade_no_shortcuts]], [[feedback_no_mocking]], [[feedback_full_depth_first_pass]].)

    **11b. Shallow/incomplete work HIDES gaps — completeness + independent review are how they surface (2026-06-14 lesson).** Whenever work is not done deeply or a subsystem is only partially cleaned, the un-done part becomes a *latent, often audit-invisible gap* that a shallow self-check will miss (this session: the depth-hardening self-review missed a no-op verifier gate **and** a live fabricating endpoint; the independent reviewers caught both). So: **(a) finish the whole thing** — when you touch a subsystem, complete the sweep (Rule 1a); a partial de-mock/wiring is a gap, not a milestone. **(b) Spend the independence.** A different agent reviewing your work catches your blind spots that you structurally cannot — run `scripts/independent-audit.sh <stage>` (or, if the `task-auditor`/`cto-reviewer` Agent spawn is unavailable, a fresh `general-purpose` agent adopting that persona via its `.claude/skills/<role>/SKILL.md`) BEFORE close; a PASS from a different agent is required (CLAUDE.md §6). **(c) Verify, don't assert** — confirm every honesty/capability claim against the actual code path (Rule 1a). **(d) Gaps will still sometimes appear — that is expected; the rule is to LEDGER and FIX them honestly, never hide or downplay them.** When an audit/review surfaces a gap you can't fix now, append it to `audits/OPEN_GAPS_LEDGER.md` with a `target_stage`, correct any overclaim in the docs, and fix the immediate ones. Depth up front makes gaps rare; honesty about the gaps that remain makes them harmless.

---

## 5. Per-Task Lifecycle

The cycle every stage runs:

```
/begin  (or bash scripts/init.sh)         # determines state; routes to right next action
   ↓
scripts/start-task.sh <stage> <slug>       # bootstraps task doc with: validated stage+slug,
                                           # pre-req sequencing check, suggested role from slug,
                                           # KB files pre-populated from role's SKILL.md mandatory reads,
                                           # Pre-requisites from previous stage's hand-off,
                                           # CTO remediation map entries targeting this stage
   ↓
[ implement under role persona ]
   ↓
scripts/audit-task.sh <stage>              # writes audits/STAGE_<NN>_audit.md (gaps, vulns, missing)
   ↓
scripts/rectify-task.sh <stage>            # loops back to implement until audit reports zero gaps
   ↓
scripts/independent-audit.sh <stage>       # INDEPENDENT review by a DIFFERENT agent than the implementer
                                           # (spawns a fresh task-auditor) → audits/STAGE_<NN>_independent_review.md.
                                           # Re-runs the stage's tests adversarially; fix gaps until verdict = PASS.
   ↓
[author this stage's "## Hand-off" section in the task doc]
   ↓
scripts/seed-next-task.sh <stage>          # GENERATES the NEXT stage's task doc HERE — at the end of the
                                           # previous task, BEFORE KB/.md updates (2026-05-31 lifecycle fix).
                                           # Idempotent: no-op if the next doc already exists (never clobbers).
   ↓
[append KB_TASK_LOG.md entry + update KB files + other .md]
   ↓
scripts/close-task.sh <stage>              # refuses if gaps or KB_TASK_LOG entry missing
                                           # signs new ADRs with ML-DSA-65 (Stage 13.5+)
                                           # rewrites .audit-baseline
                                           # ensures next task doc exists (idempotent safety-net call to next-task.sh)
```

> **Lifecycle ordering note (2026-05-31):** the next task document is now created by `seed-next-task.sh` at the
> *end of the previous task, before the KB/.md updates*, so there is never ambiguity about whether the next task
> doc exists while you write the KB entries. `close-task.sh` still calls `next-task.sh` as an idempotent safety
> net (it no-ops if the doc already exists). `next-task.sh` can still be run directly if needed.

> **Out-of-band strategic reset pattern (precedents: 2026-05-18, 2026-06-11):** strategy/governance work that is
> NOT a numbered stage (PRD versions, market research, role/process changes, loophole fixes) runs between stages
> as: fresh research → `research/initial-research.md` append → new-file PRD/KB/skill changes → ADR (single
> complete write) → out-of-band `KB_TASK_LOG.md` entry. The audit baseline is untouched (no `--baseline`, no
> `close-task.sh`); no backend/frontend code is edited; append-only rules apply throughout.

Every 10 task closures: `scripts/cto-review.sh` (refuses unless task # % 10 == 0). Spawns a **fresh Claude Code subprocess** with the `cto-reviewer` skill. Writes `audits/CTO_<N>_review.md`. `scripts/generate-remediation-tasks.sh` then appends each "future-task remediation" as an acceptance criterion to the named upcoming task doc.

### Research protocol (non-negotiable)

**Two binding triggers — both append a new dated, numbered, append-only section to `research/initial-research.md`:**

1. **Per build stage (MANDATORY, research-first — Hard Rule 11).** Every code-touching stage MUST run a
   web-research pass on that stage's domain SOTA **before implementing**, and record it as a research section,
   so the chosen depth is grounded in current best practice (not guessed). "I didn't do web search this stage"
   is not allowed for a build stage — the absence of the section is a close-blocking gap.
2. **Any session that performs web search, deep fetching, or market analysis** MUST likewise append its section
   before the session ends.

Sections are numbered sequentially; content is append-only (strikethrough, never delete). Minimum entry: date,
scope, sources with URLs, key findings, decision impact. Losing the research file loses the rationale behind every
architectural decision. This is captured as a permanent feedback memory (`feedback_production_grade_no_shortcuts.md`).

---

## 6. Audit Invariants (CI-Enforced)

- `.audit-baseline` count strictly decreases or holds with explicit `--no-baseline-drop`.
- Every new weight has `<model>.pt` + `<model>.metrics.json` + `compliance/model-cards/<model>.md`.
- Every new MCP tool has a schema test under `backend/tests/mcp/`.
- Every new A2A surface has an agent-card signing/verification test under `backend/tests/a2a/`.
- Every new actuator path has a `safety.validate` OpenTelemetry span before the actuator span (CI enforces — Stage 17+).
- Every code-touching stage appends a new entry to `knowledge-base/KB_TASK_LOG.md` before close.
- Every architectural decision lands as a new ADR in `compliance/decision-logs/YYYY-MM-DD_<slug>.md`.
- Every stage (Stage 4+) reads KB_24 (design) + KB_25 (self-healing engine) + `audits/OPEN_GAPS_LEDGER.md` and folds the gaps targeted at it into its acceptance criteria (carry-forward; hard rule 10).
- Every stage uses a free-cost stack (hard rule 9): Groq free / Ollama (LLM), OSS/local infra; no paid SaaS at build time.
- **Every code-touching stage runs a SOTA web-research pass and appends a dated `research/initial-research.md` section BEFORE implementing, and takes the deepest honest free/local path** (hard rule 11): toy/shallow implementations where a deeper free/local one is feasible are close-blocking gaps; the missing research section is itself a gap.
- **Every code-touching stage gets an INDEPENDENT audit by a DIFFERENT agent than the implementer before close** (operator mandate, 2026-05-31): `bash scripts/independent-audit.sh <stage>` spawns a fresh `task-auditor` agent → `audits/STAGE_<NN>_independent_review.md`. The builder must not audit their own work. A PASS verdict is required before `close-task.sh`. (The mechanical `audit-task.sh` count gate is necessary but not sufficient.)
- **Every stage ships an explainer HTML before close** (operator mandate, 2026-06-11): `research/stage-explainers/STAGE_<NN>/index.html` — self-contained, explaining what the stage built and why, how it works (real file paths), what was measured (real numbers), and what changed. Same honesty discipline as the other `research/*/index.html` artifacts; seeded into every task doc by `tasks/TASK_TEMPLATE.md`.

---

## 7. Memory Protocol

Five layers; pick the right one:

| Layer | When to use | Backend |
|---|---|---|
| **Working** | Within a single task; ephemeral | LangGraph `AgentState` (Pydantic) + Postgres checkpointer (Stage 11+) |
| **Episodic (Mem0, default)** | "We tried X last shift, failed" — per-incident, per-shift | `backend/memory/mem0_adapter.py` against PG + pgvector (Stage 12+) |
| **Episodic (Letta, opt-in)** | Multi-day agent personality (per-pilot config) | `backend/memory/letta_adapter.py` (Stage 12+) |
| **Semantic** | Equipment hierarchy, SOPs, KB content | pgvector (semantic namespace) + Neo4j ISA-95 (Stage 12+) |
| **Procedural** | Reusable skills, recipes, playbooks | DVC-versioned `data/skills/<name>/skill.yaml` |
| **Audit (immutable)** | Every decision, every action — EU AI Act Art. 12 evidence | `audit_chain` table — append-only, SHA-256 chained, ML-DSA-65 signed (Stage 13.5+) |

Cross-namespace reads from Mem0 are forbidden (enforced in `mem0_adapter.py`). Every decision in the agent runtime writes an `audit_chain` row signed with ML-DSA-65.

---

## 8. Where Context Lives

| Question | Where to look |
|---|---|
| What is the project? | `PRD-ai-embodied-agent-v3.md` |
| What stage are we on? | `knowledge-base/KB_TASK_LOG.md` (newest entry at bottom) + lowest-numbered `not-started` task doc in `tasks/` |
| Who is it for / how does it make money? | `knowledge-base/KB_26_Product_Market_Strategy.md` + `research/market-viability-2026-06/index.html` |
| What's actually running? | `knowledge-base/KB_01_System_Architecture.md` |
| What standards apply here? | `knowledge-base/KB_12_Standards_Map.md` |
| What crypto goes where? | `knowledge-base/KB_13_PQC_Crypto_Strategy.md` |
| How does memory work? | `knowledge-base/KB_14_Agent_Memory_Architecture.md` |
| How are agents observed? | `knowledge-base/KB_15_Observability_Evidence_Pipeline.md` |
| MCP servers / A2A peers? | `knowledge-base/KB_16_A2A_MCP_Protocols.md` |
| Functional safety wrapper? | `knowledge-base/KB_17_Functional_Safety_Wrapper.md` |
| ISO/IEC 42001 controls / EU AI Act evidence? | `knowledge-base/KB_18_Governance_Evidence.md` |
| What was decided and why? | `compliance/decision-logs/*.md` |
| What are the open risks? | `compliance/risk-register.md` |
| What does the audit say? | `audits/STAGE_<NN>_audit.md` (latest) and `audits/CTO_<N>_review.md` (every 10) |

KB = what is. Tasks = what to do. Compliance = how we prove it. Audits = what's missing. Research = what informed us.

---

## 9. Auto-Load Directive

At session start, the SessionStart hook should inject the context bundle automatically. If you don't see the bundle in this session's context (top of `KB_TASK_LOG.md`, current task doc, suggested role), the hook is not registered. Run:

```bash
python scripts/load-context.py --mode=session-start
```

…and apply the `.claude/hooks/settings.json.patch.md` instructions to wire the hooks permanently.

---

## 10. Tool Allow/Deny Summary

The Claude Code allowlist for this project lives in `.claude/settings.local.json`. Read-only tools (Read, Grep, Glob) are always allowed. Bash, Write, Edit, MultiEdit may prompt; the PreToolUse hook adds project-specific guardrails on top of the allowlist (it blocks edits to finalized ADRs, `.audit-baseline` outside closure, etc.).

If a hook blocks a write, do not retry with `--force`. Read the block message; it tells you which scope marker is missing or which protocol you violated. Adjust your approach.

---

## 11. Current Stage Pointer

> **Anti-staleness rule (added 2026-06-11 after this section went stale twice):** this section is a convenience
> snapshot only — the `/begin` output (live state from `KB_TASK_LOG.md` + task docs) **wins on any conflict**.
> Update this section at every stage close; if you find it stale, fix it in the same session you notice it.

**Snapshot (2026-07-18, after CTO Checkpoint #7 — Stages 33–39):** **CTO #7 is DONE** (`audits/CTO_7_review.md` +
`CTO_7_remediation_map.json`) — the read-only every-10-stages review by a FRESH independent `cto-reviewer` agent,
DYNAMIC (live-verified on the Docker stack). **VERDICT: ON TRACK** — Stages 33–39 are a disciplined, honest close of
the CTO-#6 remediation set; the build is honestly declared complete-and-unproven. Reproduced live: audit = 3
(fabrication 0 both languages), chain green (10,479 rows; a live energy cycle signed 10480); **G-075 GENUINELY CLOSED**
(the reviewer wrote its own 6-attack bypass harness against `sil_bridge`/`capability_token` — forged/wrong-action/stale/
attacker-HMAC/unsafe-world all REJECTED, 0 bypasses); Stage-38 MILP real (peak 130.8→71.8 kW; A/B −22.1% mean, floors
held, min-0% honest); Stage-37 severity magnitude-derived; Stage-39 slice A/B preserved (−190.5 min) under the
now-binding verifier; **Hard Rule 3 intact** (sole emitters `master.dispatch_order` + `sil_bridge.execute`); **Rule 9**
zero new deps across all 7 stages. **CTO-#6 scorecard: 4 honored / 1 honored-by-honest-assessment (C6-R2 dep-refresh) /
4 deferred real-world / 0 skipped / 0 faked**; all 7 stages independently reviewed by a different agent. **7
remediations routed (C7-R1…R7)** — the ONLY immediate in-house item **C7-R1 (risk-register hygiene) is DONE this
session** (added Stage 34–39 posture rows + reconciled two stale "G-075 OPEN" rows to CLOSED + a CTO #7 refresh note);
C7-R2…R7 are real-world/buyer-blocked or optional (real pilot+A/B G-035/G-043; accredited cert G-011; scale + SPIRE
auto-renew G-066/G-084; dep-refresh in isolated CI; detector sensitivity floor; optional Workforce/Safety G-017 domain)
— `generate-remediation-tasks.sh` routed 0 (no numbered-stage targets; the map is the durable record). **Audit
UNTOUCHED (3).** **CTO bottom line: for the first time since CTO #4 there is NO open in-house safety-hardening debt —
G-075 is paid; the single highest-leverage next action is a REAL pilot, not more building.** The next executable
free/local task, if the operator chooses to keep building, is the optional Workforce/Safety head-agent (G-017, C7-R7);
otherwise the path is a real engagement (pilot G-035/G-043, cert G-011, scale G-066 — buyer/accredited-body-blocked).

**Prior snapshot (2026-07-18, after Stage 39 — Slice persistence + non-relaxed verifier, G-045/G-051):** **Stage 39 is
CLOSED** — the THIRD and FINAL build stage of the operator-chosen post-CTO-#6 free/local arc (37 bidirectional CDC →
38 facilities/energy → 39 gap-closers → **consolidated handoff next**). ADR
`2026-07-18_stage39_slice_persistence_verifier.md` (ML-DSA-65 signed); research §50; explainer
`research/stage-explainers/STAGE_39/`. **Closes two Stage-6 honesty gaps carried since 2026-06-12/06-14.** **G-045
RESOLVED:** live slice decisions now AUTOMATICALLY persist to Postgres `decision_logs` (EU-AI-Act Art-12) —
`slice_runner._persist_decision_log()` writes `caller`/`tool` + SHA-256 `input_hash`/`output_hash` over the
telemetry+prediction → decision+verification provenance + JSONB, incident FK when a real UUID (non-UUID sim tag →
`inputs.incident_ref`); wired ON in the live path (`LiveSliceRunner`), OFF for the offline A/B; honest no-op (`None`)
without a DB — the Stage-6 "persisted to decision_logs" claim (was in-memory `SliceTrail` only) is now TRUE. **G-051
fully RESOLVED:** `_build_plant_state` no longer relaxes — it BINDS `throughput_floor_frac=0.6`,
`max_concurrent_critical_offline=1` (SIL), `available_crew = crew_total(2) − stages_in_maintenance`, so the Stage-6
slice VERIFY gate can now GENUINELY REJECT an unsafe plan (proven for a throughput-floor breach AND a
critical-redundancy breach) while the normal safe maintenance still passes (no false-reject) and the measured Stage-6
A/B is preserved (unplanned downtime −190.5 min, 3.67 planned maintenances still fire). **8 new tests + 31 regression
pass; audit holds 3** (`--no-baseline-drop`: additive real code — a DB writer + binding safety constraints; a
genuinely-rejecting gate is the OPPOSITE of theatre); **new deps: none.** Independent review **PASS (different agent,
adversarial — re-ran the make-or-break A/B regression [−190.5 min preserved, maintenances still fire, so the binding
gate does NOT false-reject], HAND-RECOMPUTED the SHA-256 input_hash and it matched the stored row exactly, confirmed the
two rejections return the right violation constraint + no-false-reject, 8/8 + 31/31 tests, audit 3 — cleared to
close)**. KB_18 (Art-12 slice persistence) + KB_25 (non-relaxed VERIFY) + ledger (G-045 + G-051 RESOLVED) updated.
**The post-CTO-#6 free/local build arc (37→38→39) is COMPLETE, AND the consolidated handoff summary (option 1) is
DELIVERED** — `research/handoff-2026-07/index.html` (self-contained state-of-system: what was built [39 stages + 6 CTO
checkpoints; KB_25 loop across 3 domains; safety/PQC/governance/memory/protocol/ops], the honesty record [audit 402→3,
fabrication 0 both languages, 100% of stages independently reviewed, 61 gaps resolved / 12 deferred], what was measured
[every headline number reproduced AND labelled SIM/BENCHMARK; G-035 real-data re-fit is the single dependency], pilot
readiness [charter/matrix/A-B/runbook — buildable half done], the real-world path [pilot/cert/scale — buyer/body/traffic
blocked], and the defining limitation stated plainly). Out-of-band KB_TASK_LOG entry added; audit baseline UNTOUCHED (3);
no backend code edited. **This completes the operator-chosen sequence in full.** The build remains theatre-free (project
fabrication = 0, both languages); the single highest-leverage remaining move is a REAL pilot (buyer-blocked), not more
free/local building. **A CTO Checkpoint #7 (read-only, Stages 33–39) is DUE at the 10-stage cadence** (surfaced by
`close-task.sh` at Stage 39) whenever a fresh independent whole-system pass is wanted.

**Prior snapshot (2026-07-18, after Stage 38 — Facilities/Energy head-agent, G-018):** **Stage 38 is CLOSED** — the SECOND of
the operator-chosen post-CTO-#6 free/local arc (37 bidirectional CDC → 38 new head-agent domain → 39 small gap-closers →
consolidated handoff). ADR `2026-07-18_stage38_facilities_energy_agent.md` (ML-DSA-65 signed); research §49; explainer
`research/stage-explainers/STAGE_38/`. **Resolves G-018: the KB_25 predict→diagnose→verify→intervene loop now runs a
THIRD embodiment domain** (after the production line and supply-chain in Stage 26) — industrial energy management, over
the sim's REAL per-stage `nominal_kw` (`simulation/calibration.py` — intake 2.0 → machining 22.0 kW; the live
`manufacturing_agent` already reports `energy_consumption = nominal_kw when running`). New package
`backend/agents/facilities/` (mirrors `agents/supply_chain/`): `signals.py` (observe real per-stage kW + a documented
HVAC/lighting baseline), `tariff.py` (documented ToU + demand-charge tariff), `optimizer.py` (**a REAL MILP —
`scipy.optimize.milp`/HiGHS, no new deps — minimising `Σ(kW·h·ToU_price)+demand_charge·peak` s.t. the production floor
`Σ_t x[j,t]=required_slots[j]`, per-load windows, and peak≥ every slot's aggregate**; honest labelled greedy fallback),
`orchestrator.py` (the loop: observe→PREDICT the naive demand curve→DIAGNOSE a `demand_charge_breach`→optimise→**VERIFY
via `safety/validator.validate()` under the code-defined `energy_load_shift` contract [Hard Rule 3 — the agent proposes;
`master.dispatch_order` stays the sole actuator emitter]**→INTERVENE with a signed `audit_chain` row `energy.load_shift`,
Art-12). Surface: **`POST /facilities/optimize-energy`**. **Measured:** A/B (`training/evals/results/energy_ab.json`,
parametric sweep) — MILP vs naive baseline: **peak −22.1% mean (max 58.9%), cost −7.6% mean (max 18.8%), all production
floors held** (min 0% where fully constrained — honest, no fabricated saving); a live cycle diagnosed
`demand_charge_breach`, peak 130.8→71.8 kW (−45.1%), signed a real audit row. **15 tests pass** (+ safety 33 / health
regression); **audit holds 3** (`--no-baseline-drop`: additive real code, no random.*/mock/hardcoded fabrication);
**new deps: none**. Independent review **PASS (different agent, adversarial — reproduced the MILP [peak 130.8→71.8,
every stage held to its 6 required slots], the A/B to the digit [−22.095% mean, all floors held, 0% genuinely honest not
a bug], the gate REJECTING a peak-increasing plan AND a production-dropping plan, grep-confirmed ZERO
`actuator.`/`dispatch_order(` in facilities code, 15/15 tests real, chain exit 0 [seq 10479] — cleared to close)**.
KB_25 (third N-domain) + KB_07 + ledger (G-018 RESOLVED) updated. **The next executable task is Stage 39 — small honest
gap-closers** (`tasks/STAGE_39_TBD.md`; **G-045** persist slice decisions to Postgres `decision_logs` [Stage-6 said
"persisted" but shipped in-memory `SliceTrail`] + **G-051** supply a non-relaxed `PlantState` so the Stage-6 verifier
can actually REJECT, not a no-op), then the consolidated handoff summary (option 1) declaring the disciplined build
complete. The build remains theatre-free (project fabrication = 0, both languages); the highest-leverage real-world move
remains a pilot (buyer-blocked). Deferred honestly (G-035): real-utility tariff + metered-load validation + live
tick-loop energy control.

**Prior snapshot (2026-07-18, after Stage 37 — Bidirectional CDC → diagnose → self-optimize):** **Stage 37 is CLOSED** — the
FIRST of the operator-chosen post-CTO-#6 free/local arc (37 bidirectional CDC → 38 new head-agent domain → 39 small
gap-closers → consolidated handoff; the operator chose "options 2+3+4, then option 1"). ADR
`2026-07-18_stage37_bidirectional_cdc_self_optimize.md` (ML-DSA-65 signed); research §48; explainer
`research/stage-explainers/STAGE_37/`. **Resolves G-024 (open since 2026-05-31 — the operator's original product
vision): the CDC loop is now BIDIRECTIONAL.** Stage 13 was one-directional (an `incidents` INSERT / `stages.status`
flip → a PRE-FORMED inject); Stage 37 closes it the other way — an operator EDITS an operational VALUE in Postgres →
a new value-change trigger (`0010_cdc_value_changes`: `cdc_emit_value()` on `stages`/`inventory`/`suppliers` value
columns → `cdc_outbox`+NOTIFY, reusing the durable outbox) → **`ingestion/cdc_reasoner.py::diagnose_change` REASONS
about the induced root-cause problem** (defect_surge / machine_crack / power_dip / late_delivery, severity DERIVED from
the edit MAGNITUDE — not a synthetic constant; a benign/unmonitored edit → `None`, honest, no fabrication) → the
diagnosed incident drives the SAME validator-gated self-healing loop. `change_to_inject` routes value edits FIRST (a
subtle ordering bug — the status branch was swallowing them — caught in live testing + pinned by a regression test).
`process_value_edit` signs the reasoning to `audit_chain` ("cdc.diagnose", Art-12) + optionally runs `run_incident`.
Surface: **`POST /factory/db-edit`**. **Hard Rule 3 preserved** (the reasoner adds NO new `actuator.*` emitter; sole
emitter stays `master.dispatch_order`). **Measured LIVE:** a real `UPDATE stages SET defect_rate=0.15` drains into the
SimWorld as diagnosed `defect_surge/critical`; **64 tests pass** (22 reasoner/routing/loop/live + Stage-13 CDC
regression + `/factory/db-edit` routes); migration reversible; `verify-audit-chain.py` exit 0 (10,477 rows). **Audit
holds 3** (`--no-baseline-drop`: additive real code, no random.*/mock/hardcoded fabrication); **new deps: none**.
Independent review **PASS (different agent, adversarial — reproduced the live path with its OWN `UPDATE`, PROVED
severity is magnitude-derived [0.09/0.14→warning, 0.15/0.30→critical; throughput 100→90→None/→65→warning/→45→critical],
grep-confirmed NO actuator emitter in Stage-37 code, 64/64 tests real not no-ops, chain exit 0 — cleared to close)**.
KB_07 + ledger (G-024 RESOLVED) updated. **The next executable task is Stage 38 — extend the KB_25 predict→diagnose→
verify→intervene loop to a new head-agent embodiment domain** (`tasks/STAGE_38_TBD.md`; **Facilities/Energy G-018
preferred** — the sim HAS a real per-stage energy model: `calibration.py::nominal_kw` [intake 2.0 → machining 22.0 kW]
+ `manufacturing_agent.py` computes live `energy_consumption = nominal_kw when running else 0`, and the `power_dip`
incident type already exists — same extension pattern as supply-chain in Stage 26; or Workforce-Safety G-017), then
Stage 39 (small gap-closers G-045/G-051), then the consolidated handoff. The build remains theatre-free (project
fabrication = 0, both languages); the highest-leverage real-world move remains a pilot (buyer-blocked).

**Prior snapshot (2026-07-18, after Stage 36 — Dependency-refresh feasibility assessment):** **Stage 36 is CLOSED** — the
last routed CTO-#6 in-house item (C6-R2; research §47; ADR `2026-07-18_stage36_dependency_refresh_assessment.md`,
ML-DSA-65 signed; explainer `research/stage-explainers/STAGE_36/`). **C6-R2 handled appropriately: attempted safely,
proven a stack-breaking cascade, documented + planned — NOT executed.** The coordinated refresh (langchain-core 1.x to
unblock `langchain-mcp-adapters`, G-055/G-056; httpx≥0.28.1 to unblock `a2a-sdk`, G-070) was attempted via NON-MUTATING
`pip install --dry-run` probes — they RESOLVE on metadata but CASCADE into stack-breaking bumps: langchain-core-1.4.9 →
langgraph-1.2.9 + langgraph-checkpoint-4.1.1 + **starlette-1.3.1** (which CONFLICTS with `fastapi 0.115.6`'s
`starlette<0.42` → forces a fastapi major bump; langgraph-checkpoint 4.x re-introduces the Stage-11 Reviver break), and
a2a-sdk pulls protobuf 6.x. **Honest verdict:** a cascading multi-major migration (runtime + API + HTTP layers) that
CANNOT be done safely free/local in the working env (no isolated staging/CI; would risk the verified GA'd stack) for a
LOW-VALUE hygiene item (pins are SBOM/bandit/pip-audit gated, not stale-and-vulnerable, G-065). Shipped
`compliance/dependency-refresh-assessment.md` — the dry-run evidence + hard blockers + mitigation + a de-risked
branch/staging + CI migration plan. **Working env verified UNCHANGED** (langchain-core 0.3.28 / httpx 0.27.2 / fastapi
0.115.6 / langgraph 0.2.60 / starlette 0.41.3, all pins intact; a safety smoke test passes). **No requirements/lockfile/
code changed; new deps: none. Audit holds 3** (`--no-baseline-drop`: docs-only). G-055/G-056/G-070 stay OPEN, now
evidence-backed + planned; nothing faked. Independent review **PASS (different agent, adversarial — RE-RAN every
non-mutating dry-run probe: reproduced the would-install sets TO THE DIGIT [starlette-1.3.1; a2a-sdk→protobuf-6.33.6];
confirmed the fastapi `starlette<0.42` conflict is REAL not asserted; confirmed the env is UNCHANGED [versions identical
before/after, a2a-sdk not installed, 7 capability-token tests pass]; confirmed docs-only + audit 3; confirmed
G-055/56/70 stay OPEN not faked-RESOLVED — no gaps, cleared to close)**. **ALL routed CTO-#6 in-house items are now
addressed** (C6-R1 G-075 + C6-R3 hook + C6-R4 → Stage 33; C6-R5 → Stage 34; C6-R3-tail → Stage 35; C6-R2 assessed →
Stage 36). **The build is complete and theatre-free (project fabrication = 0, both languages). What remains is a
REAL-WORLD ENGAGEMENT — a real pilot (G-035/G-043), accredited certification (G-011), horizontal scale (G-066) — all
buyer/accredited-body-blocked, NOT more free/local building.** The single highest-leverage next action is a real pilot.

**Prior snapshot (2026-07-18, after Stage 35 — Multi-turn dialogue memory):** **Stage 35 is CLOSED** — the last routed
CTO-#6 **C6-R3** in-house item (research §46; ADR `2026-07-13_stage35_multi_turn_dialogue_memory.md`, ML-DSA-65 signed;
explainer `research/stage-explainers/STAGE_35/`). **The factory conversation is now multi-turn — without weakening the
honest-empty grounding guarantee one bit.** Shipped + verified: a **durable Postgres sliding-window session store**
(`conversation/session_store.py` — `conversation_turns`, lazy-create, keyed by `session_id`; `recent_turns(window=N)`;
honest no-op → single-turn when no DB, never fabricates history) wired into `/factory/ask` (phrasing) + `/factory/inject`
(coreference) behind an OPTIONAL `session_id`. **The Stage-29 grounding/Verifier invariant is STRICTLY preserved** —
history aids phrasing/coreference but is NEVER evidence: an ungrounded question inside a session STILL returns "I have no
evidence for that.", evidence is gathered per-current-question, prior turns are never cited. **Hard Rule 3 unchanged**
(inject still produces a validated `InjectedIncident` into the validator-gated loop). **Measured live (Groq):** turn 1
"welding cell 3 is overheating" → machine_crack/3; turn 2 "it is getting worse, now vibrating too" (pure coreference) →
machine_crack/3. **6 new tests + Stage-29 suite = 31 passed; audit holds 3** (`--no-baseline-drop`: additive, no new
random.*/mock); **new deps: none** (psycopg present). Independent review **PASS (different agent, adversarial — proved
the grounding invariant by STRUCTURE [honest-empty early-return fires before history is loaded] AND by a live POISON
experiment: seeded a session with fabricated citations `[audit:seq=999]`/`[sop:SOP-FAKE]`/"24 mph", re-asked off-topic
→ honest-empty, citations=[], ZERO leakage; Hard Rule 3 intact; no new dep — cleared to close)**. KB_14 (new
conversational memory layer) + KB_07 updated. **This completes the routed CTO-#6 in-house items except C6-R2
(dependency-refresh — its own pin-blocked, risky increment).** The next executable task is **C6-R2** (attempt a safe
dry-run resolution; the httpx/langchain/langgraph pin set is deeply interlocked with `ResolutionImpossible` recorded —
document honestly if infeasible free/local rather than destabilize the verified stack) — or a real-world engagement
(pilot G-035/G-043, cert G-011, scale G-066, buyer/accredited-body-blocked). The build remains theatre-free (project
fabrication = 0, both languages); the highest-leverage move remains a real pilot.

**Prior snapshot (2026-07-18, after Stage 34 — Frontend real-data wiring + honesty cleanup):** **Stage 34 is CLOSED** — the
CTO-#6 **C6-R5** frontend cleanup (research §45; ADR `2026-07-13_stage34_frontend_realdata_honesty.md`, ML-DSA-65
signed; explainer `research/stage-explainers/STAGE_34/`). **The frontend is now fabrication-clean and strictly
type-checked.** Shipped + verified: **G-047** — deleted both `getMock*` generators in `lib/api.ts` (now
`getModelMetrics`→`{}` / `getEmbodiedComparison`→`null` on error/503, honest-unavailable, never fabricated); rewrote
the `model-metrics` page (which had its OWN hardcoded fake model array) to FETCH real `/api/metrics/models` + an honest
"no live metrics recorded" empty-state pointing to the model cards + `models/*.metrics.json` (the endpoints honestly
503 until real metrics exist). **G-032** — `simulation/page.tsx` now maps to the REAL `SimulationState` (System Health
reads `metrics.current.*` + `scenario`; 3D scenes map real `Robot[]`/`ProductionStage[]` [robot_id→id] with a labelled
demo fallback; fabricated init removed); **`ignoreBuildErrors` flipped to `false`** → **`tsc --noEmit` = 0 errors** and
**`npm run build` exit 0** with strict type-checking (all 18 routes generated). **0 `getMock`/`Math.random` in
`frontend-nextjs/src`** (the honestly-labelled `detRand` deterministic demo layout excepted). **Audit holds 3**
(`--no-baseline-drop`: the removed frontend fabrications were audit-INVISIBLE TS object literals — real honesty gain
grep can't see); **no backend code touched; new deps: none**. Independent review **PASS (different agent, adversarial —
RE-RAN tsc [0 errors] + `npm run build` [exit 0, strict types, a type error would now FAIL the build]; confirmed 0
getMock + honest empty-states + detRand is a genuine deterministic PRNG labelled demo-only + package.json/lock ZERO
diff — cleared to close)**. KB_07 updated; G-047 + G-032 RESOLVED. **The next executable task is a further CTO-#6
in-house item** — C6-R2 dependency-refresh (langchain-core 1.x + a2a-sdk, its own pin-blocked increment) or C6-R3-tail
multi-turn dialogue memory — **or a real-world engagement** (pilot G-035/G-043, cert G-011, scale G-066 —
buyer/accredited-body-blocked). The build remains theatre-free (project fabrication = 0, both languages); the
highest-leverage move remains a real pilot.

**Prior snapshot (2026-07-13, after Stage 33 — Safety & runtime-oversight hardening):** **Stage 33 is CLOSED** — the first
post-CTO-#6 increment, paying the routed in-house remediations (C6-R1/C6-R3/C6-R4; research §44; ADR
`2026-07-13_stage33_safety_oversight_hardening.md`, ML-DSA-65 signed; explainer `research/stage-explainers/STAGE_33/`).
**The longest-lived open safety item — G-075 — is CLOSED** (open through CTO #4/#5/#6). Shipped + verified:
**capability tokens** (`safety/capability_token.py`) — `validate()` mints an unforgeable, action-bound, time-limited
HMAC token on every ALLOW (over canonical decision + `action_hash` + nonce + issued_at); `sil_bridge.execute()` now
actuates ONLY via (a) authoritative RE-VALIDATION from contract+world_state OR (b) a valid+FRESH token bound to THIS
action — a forged `Decision(allow=True)` (no token/contract), a stale/replay token (TOCTOU), a wrong-action token, and
a tampered token are ALL rejected (`SafetyBypassError`). **C6-R3:** the Stage-31 behavioural monitor is now an
always-on runtime hook (`run_incident`, `RUNTIME_BEHAVIOR_MONITOR=1`, off by default, off the hot path, honest-degrading;
determinism holds off). **C6-R4:** risk register refreshed for Stages 29–33 + G-075 CLOSED; defence-in-depth wording
narrowed to the accurate guarantee. **Also fixed a latent Stage-29 honest-empty bug** (off-topic questions grounded on
arbitrary decision traces once the DB filled — Rule 11b). **7 new capability-token tests + regression (safety 33 /
runtime 13 / security 30 / conversation 25) pass; audit holds 3** (`--no-baseline-drop`: additive; token uses stdlib
hmac/os.urandom not `random`); `verify-audit-chain.py` exit 0 (10,477 rows). **New deps: none.** Independent review
**PASS (different agent, ADVERSARIAL — wrote its OWN bypass harness: 17/17 correct, 15 bypass attempts ALL BLOCKED, 0
bypasses [forged/wrong-action/stale/future-dated/tampered/cross-field-copy/attacker-key-HMAC all rejected]; confirmed
`_SECRET=os.urandom` per-process, not forgeable across the trust boundary — cleared to close)**. G-075 RESOLVED; KB_17
+ risk register updated. **The next executable task is a further CTO-#6 in-house item** — C6-R2 dependency-refresh
(langchain-core 1.x + a2a-sdk, its own pin-blocked increment) or C6-R5 (frontend real-data wiring) — **or a real-world
engagement** (pilot G-035/G-043, cert G-011, scale G-066 — buyer/accredited-body-blocked). The build remains
theatre-free (project fabrication = 0); what most moves the needle now is a real pilot.

**Prior snapshot (2026-07-13, after CTO Checkpoint #6 — the post-Stage-28 arc is COMPLETE):** **CTO #6 is DONE**
(`audits/CTO_6_review.md` + `CTO_6_remediation_map.json`) — the read-only every-10 checkpoint across **Stages 25–32**
by a fresh independent `cto-reviewer` agent (DYNAMIC, live-verified on the Docker stack). **VERDICT: ON TRACK** — "the
arc is honest, deep, and theatre-free; the system is pilot-DEPLOYABLE but still pilot-UNPROVEN." Every headline number
reproduced live to the digit and is honestly labelled sim/benchmark/single-corpus (repair −47.9% CI [7696,12733];
supply −51%/−98%; detector 0.9935→1.0/FPR→0 held-out "NOT train-on-test"; GraphRAG 1.0; active-diagnosis math
re-derived); **audit.sh = 3** (real project fabrication = 0 both languages — the residual 3 is the documented G-052
false-positive); `verify-audit-chain.py` exit 0 (10,469 rows); 51 tests pass; all four arc ADRs ML-DSA-65 signed;
**no Hard-Rule violation found** (Rule 3 survived NL-injection + repair dispatch; Rule 1a improved; Rule 9 held — only
new deps in 8 stages were spiffe/spiffe-tls). **Independence verified — all 8 stages reviewed by a different agent,
several re-deriving math / re-running A/Bs / running a refuting control-arm experiment (strongest independence posture
in the project's history).** CTO #5 scorecard: 2 honored / 3 partial (real-half buyer-blocked) / 2 honestly deferred /
0 skipped/faked. **9 remediations routed** — the standout in-house one is **C6-R1: harden `sil_bridge` against Decision
forgery/TOCTOU (G-075) as code NOW** (longest-lived open safety item, deferred through CTO #4/#5/#6), plus C6-R2
dependency-refresh, C6-R3 always-on behavioural-monitor hook + multi-turn memory, C6-R4 risk-register refresh — all
→ Stage 33; and the real-world set (C6-R6 pilot G-035/G-043, C6-R7 cert G-011, C6-R8 scale G-066) which is
buyer/accredited-body-blocked. **The operator-chosen post-Stage-28 arc (29→30→31→32→CTO #6) is COMPLETE. The defining
limitation, stated plainly: the discipline is production-grade; the evidence is not yet real-world — the single
highest-leverage next action is a REAL pilot, not more building.** The next executable free/local task, if the operator
chooses to continue building, is **Stage 33** (the routed in-house hygiene: G-075 hardening + dep-refresh + monitor
hook + risk-register refresh); otherwise the path is a real engagement.

**Prior snapshot (2026-07-13, after Stage 32 — Pilot-readiness package):** **Stage 32 is CLOSED** — the FOURTH and FINAL
build stage of the operator-chosen post-Stage-28 arc (29 conversational → 30 live-wire → 31 detector hardening →
32 pilot-prep → **CTO #6 next**; research §43; ADR `2026-07-13_stage32_pilot_readiness_package.md`, ML-DSA-65 signed;
explainer `research/stage-explainers/STAGE_32/`). **Docs-only — the buildable half of the real pilot is now COMPLETE.**
Shipped: **Pilot Charter template** (`compliance/pilot-charter-template.md` — predefined per-capability success
criteria + thresholds, two HARD gates [0 unsafe actuations; audit chain verifies], 4–6-week window, Art-26 oversight,
and the **Scale/Iterate/Pivot/Stop** decision gates — the discipline ~60% of AI pilots skip); **capability-readiness
matrix** (`capability-readiness-matrix.md` — the honest sim-vs-real inventory: every capability's REAL measured number
cited to its stage + its real-data dependency [G-035] + its pilot A/B hypothesis; headline sims the pilot will test:
repair −47.9% CI [7696,12733]s, supply stockouts −51%/bullwhip −98%, detector 0.9935→1.0/FPR→0, GraphRAG 1.0, C-MAPSS
RMSE 13.80); **A/B protocol** (`pilot-ab-protocol.md` — baseline/paired-test/CI design + 5 per-capability hypotheses +
2 hard gates, reusing the Stage-6/26/30 harnesses); base **onboarding kit extended §6** (data-intake for the
Stages-26–31 capabilities). **NO real-world number is presented as a deployment result** — every figure labelled
sim/benchmark + cited; the real pilot + published A/B + re-fits stay buyer-blocked (G-035/G-043). **Audit holds 3**
(`--no-baseline-drop`: docs-only, no code touched); **new deps: none**. Independent review **PASS (different agent,
number-provenance audit — VERIFIED every headline number traces EXACTLY to a closed-stage results file [recomputed
supply −50.9%/−98.4% from supply_ab.json matching to the digit; repair/detector/C-MAPSS/GraphRAG/RL/demand all match];
NO sim number presented as a real-world result; charter has predefined criteria + all four gates + both hard gates;
docs-only confirmed, audit 3, no new deps — cleared to close)**. KB_26 §13 + ledger note the buildable pilot-prep is
COMPLETE. **The four post-Stage-28 build stages (29–32) are COMPLETE. The next executable task is CTO Checkpoint #6**
(`tasks/STAGE_32_5_*` or run `scripts/cto-review.sh` — the read-only every-10 review across Stages 29–32; the operator
sequenced it AFTER the four stages). **After CTO #6, what remains is a real-world engagement (real pilot G-035/G-043 +
accredited certification G-011 + scale G-066), not more free/local building.**

**Prior snapshot (2026-07-13, after Stage 31 — Detector / eval hardening):** **Stage 31 is CLOSED** — the THIRD of the
operator-chosen post-Stage-28 arc (29 conversational → 30 live-wire → 31 detector hardening → 32 pilot-prep → CTO #6;
research §42; ADR `2026-07-13_stage31_detector_eval_hardening.md`, ML-DSA-65 signed; explainer
`research/stage-explainers/STAGE_31/`). **The red-team defences are now hardened — and every number is held-out,
not train-on-test.** Shipped + verified: **G-077 learned injection tier** (`security/injection_classifier.py` — a
LogisticRegression over bge-small embeddings, trained on the real 217-example OWASP-LLM01 corpus) becomes the PRIMARY
calibrated semantic decision in `prompt_guard.inspect()` (kNN kept as honest fallback) + an optional free-LLM judge
escalation (`use_judge=True`) — **held-out STRATIFIED 5-fold CV: combined detector detection 0.9935 → 1.0, FPR
0.0156 → 0.0** (caught the 1 indirect miss AND removed the 1 benign FP; `training/evals/results/detector_hardening.json`
+ `models/injection_classifier.{joblib,metrics.json}` + `compliance/model-cards/injection_classifier.md`). **G-064-tail
continuous behavioural monitor** (`security/behavioral_monitor.py`) — the ONLINE counterpart of the Stage-25 nightly
sweep: rolling robust-Z (median/MAD) over real per-incident behavioural features + trajectory checks (loops/redundant/
invalid-tool-args/actuation>decisions), signed `behavior.anomaly` rows, honest `insufficient_history` below warmup,
`features_from_run()` consumes a real `run_incident` result (labelled eval 1.0/0.0). **CTO-#5 R5:** the honest deep-eval
artefact persisted. **12 new tests + regression 30 passed** (security + red-team; Stage-20 floors hold); **audit holds 3**
(`--no-baseline-drop`: additive; the learned tier reduces the real FPR); `verify-audit-chain.py` exit 0 (10,469 rows).
**New deps: none** (sklearn/sentence-transformers present). Independent review **PASS (different agent, fresh
adversarial — RE-IMPLEMENTED the held-out CV FROM SCRATCH across 3 seeds, all reproduce 0.9935/0.0; confirmed
StratifiedKFold trains on train-fold only [NOT train-on-test]; confirmed the FPR drop is real [benign question now
passes at LR proba 0.1149]; robust-Z monitor + honest degradation confirmed; 30/30 tests, chain exit 0, no new deps —
cleared to close)**. Honest caveat surfaced: the 217-example corpus is nearly separable in bge space (so the "1.0" is a
small single-corpus number; real-traffic/multilingual validation → pilot, G-035). G-077 + G-064-tail RESOLVED; KB_23
updated. **The next executable task is Stage 32 — pilot-prep** (`tasks/STAGE_32_TBD.md`; onboarding + data-intake kit +
A/B protocol against a real buyer's incidents — the buildable half; G-035/G-043 real pilot is buyer-blocked), then
**CTO #6** across Stages 29–32.

**Prior snapshot (2026-07-13, after Stage 30 — Live-wire the self-healing loop):** **Stage 30 is CLOSED** — the SECOND of
the operator-chosen post-Stage-28 arc (29 conversational → 30 live-wire → 31 detector hardening → 32 pilot-prep →
CTO #6; research §41; ADR `2026-07-12_stage30_live_wire_self_healing_loop.md`, ML-DSA-65 signed; explainer
`research/stage-explainers/STAGE_30/`). **The KB_25 loop now ACTS end-to-end — and every claim is measured, nothing
fabricated.** Shipped + verified: **G-005 repair-robot dispatch** (`agents/repair/dispatch.py` + `Stage.repair_assist`
interruptible SimPy repair + `SimWorld.request_repair`) — a broken machine triggers a deterministic Contract-Net award
over REAL robot state (availability/battery/queue; min-cost), safety-gated by the `repair_dispatch` contract (Hard
Rule 3) + signed audit row; the robot travels (real bid cost) and cuts the REMAINING downtime. **Paired A/B (10 seeds):
downtime −47.9% (mean 10,215s saved), 95% CI [7696,12733]s, excludes 0** (`training/evals/results/repair_ab.json`).
**G-025-tail RL shadow** (`agents/runtime/rl_shadow.py`, wired in the `decide` node behind `RUNTIME_RL_SHADOW=1`, off by
default) — the Stage-7 MaskablePPO runs on its own fleet-scheduling distribution (obs from real degrading/crack-proximity/
broken), emits an RL recommendation + RL-vs-rule agreement, and **NEVER actuates** (SOTA shadow-mode deploy; the
verifier/validator remain the shield; promotion is Stage-28 autonomy-ladder + HITL gated); honest-unavailable when SB3
absent. **G-036 demand forecaster SERVED** (`services/demand_forecast_service.py`) — the operator-facing 7-day forecast
now serves the real LSTM (schema history → daily, bounds from the model's real MAE 32.9) / empirical stats / an honestly
LABELLED baseline; **the legacy fabricated per-day `confidence` (a Rule-1a audit-invisible constant) is REMOVED** and the
state carries `demand_forecast_source`/`_served`. **13 new tests + regression 74 passed / 1 skipped / 0 failed**
(sim/runtime[determinism holds, shadow off]/supply/repair/services); **audit holds 3** (`--no-baseline-drop`: additive
real code + an audit-invisible fabrication removed); `verify-audit-chain.py` exit 0 (10,469 rows). **New deps: none**
(Rule 9). Independent review **PASS (different agent, fresh adversarial — RE-RAN the A/B [48.2% saved, CI excludes 0,
reproducing −47.9%]; interruptible-repair mechanism genuine + passive path byte-equivalent to legacy; Hard Rule 3 intact;
RL shadow genuinely runs [SB3 present] and never acts; fabricated `confidence` deletion confirmed via git diff; no new
deps — cleared to close; one minor non-blocking t-value nit FIXED in-stage)**. G-005/G-025-tail/G-036 RESOLVED; KB_25/05/07
updated. Deferred honestly (all G-035, buyer-blocked): real-fleet repair validation + physical-proximity routing; RL
shadow→active promotion on real data; real hourly-demand re-fit. **The next executable task is Stage 31 — detector/eval
hardening** (`tasks/STAGE_31_TBD.md`; G-077 prompt_guard learned/LLM-judge tier + G-064-tail continuous runtime anomaly
detection + CTO-#5 R5 deep-eval gate polish), then 32 (pilot-prep), then CTO #6.

**Prior snapshot (2026-07-12, after Stage 29 — Conversational Factory Intelligence):** **Stage 29 is CLOSED** — the FIRST of
the operator-chosen post-Stage-28 arc (29 conversational → 30 live-wire loop → 31 detector hardening → 32 pilot-prep →
CTO #6; research §40; ADR `2026-07-12_stage29_conversational_factory_intelligence.md`, ML-DSA-65 signed; explainer
`research/stage-explainers/STAGE_29/`). **The factory is now INTERACTIVE — and every surface is grounded in real
evidence or honestly abstains.** Shipped + verified: **G-022 "ask the factory"** (`backend/conversation/{evidence,ask}.py`
+ `POST /factory/ask`) — grounded operational QA + "why did X happen?" answered ONLY from real evidence (Art-12
`decision.trace` rows via a new read-only `audit_chain.read_recent` + Stage-28 GraphRAG + live sim), each claim carrying
a citable handle; **Verifier honest-empty** ("I have no evidence for that") when nothing grounds it; free-LLM
(Groq→Ollama) synthesis constrained to the evidence + cites handles, deterministic digest when no LLM (verified live:
Groq cited `[sop:SOP-001]` + real seqs 424/426). **G-023 NL problem injection** (`nl_inject.py` + `POST /factory/inject`)
— NL → strict Pydantic `InjectedIncident` (LLM structured output + re-ask; deterministic keyword fallback; honest
ABSTAIN) → the SAME validator-gated self-healing loop; **Hard Rule 3 preserved** (the LLM never actuates — the sole
emitter stays `master.dispatch_order`; verified live: "welding cell 3 vibrating/overheating, urgent" → machine_crack/3/
critical/0.9). **G-026 active diagnosis** (`active_diagnosis.py` + `POST /factory/diagnose`) — KB_25 §1b no-op → a real
**information-gain (entropy-reduction) probe policy**: belief over fault hypotheses, select the `diagnose.request` with
max mutual information, read the `diagnose.report` (real health vector; timeout ⇒ fault), EXACT Bayes update, COMMIT
above threshold else ABSTAIN (localizes the true fault @ ~0.87–0.97 conf in ~3–4 probes — VARIES by stage/tpr, proving
it's derived not constant; abstains when tpr≈fpr). **25 tests** (23 offline + 2 live-Groq) + regression **53 passed / 0
failed**; **audit holds 3** (`--no-baseline-drop`: additive real subsystem, zero new theatre); `verify-audit-chain.py`
exit 0 (10,076 rows). **New deps: none** (Rule 9). Independent review **PASS (different agent — reproduced the diagnosis
math FROM SCRATCH [entropy 0.881291 / MI 0.531004 match, confidence varies across faults proving derived-not-hardcoded];
live Groq re-run cited only REAL handles, zero invented; Hard Rule 3 confirmed — no actuator emitter in any conversation
file; NO theatre/bypass/fabrication — cleared to close)**. G-022/G-023/G-026 RESOLVED; KB_06/07/25 updated. Deferred
honestly: real-user conversational + adoption validation needs a pilot (G-035/G-043, buyer-blocked); multi-turn dialogue
memory is incremental (endpoints single-turn). **The next executable task is Stage 30 — live-wire the self-healing loop**
(`tasks/STAGE_30_TBD.md`; G-005 cross-fleet repair dispatch + G-025-tail live RL-intervention + G-036 demand_forecaster
into the live path), then 31 (detector hardening) + 32 (pilot-prep), then CTO #6.

**Prior snapshot (2026-07-12, after Stage 28 — GraphRAG grounding + adoption UX + G-082 de-mock):** **Stage 28 is CLOSED** —
the THIRD (final) roadmap-extension build stage (research §39 + §35.7/§35.8; ADR
`2026-07-04_stage28_graphrag_adoption_ux.md`, ML-DSA-65 signed; explainer `research/stage-explainers/STAGE_28/`).
**The stage that finally drove the audit baseline DOWN — and the project is now theatre-free.** Shipped + verified:
**GraphRAG grounding** (`backend/knowledge_graph/graphrag.py`) — a lean free/local VectorCypher-style retriever
(bge-small over a 4-SOP corpus + a 1-2-hop ISA-95 Neo4j neighbourhood → grounded context with EXPLICIT citations;
**honest-empty** off-topic at bge-threshold 0.6 [measured on-topic 0.67-0.90 vs off-topic ≤0.51; a naive 0.35 falsely
grounded "meaning of life"]) wired into the runtime `explain` node → the **Art-12 signed trace now carries the
grounding** (eval: grounded-answer 1.0 / honest-empty 1.0 / citation-precision 1.0; 8/8 tests). **Adoption UX**
(`backend/api/adoption_routes.py` + `TrustCalibration.tsx`/`AutonomySlider.tsx`/`app/adoption/page.tsx`, §35.8):
trust calibration (`/recommendation` — confidence **DERIVED from the real retrieval cosine** + uncertainty band +
counterfactual + GraphRAG citation, never a bare score; off-topic → 0.0 conf + HITL), progressive autonomy
(shadow→…→autonomous, safety/HITL-gated), WIIFM/loss-aversion (prevented stockouts from the REAL Stage-26 A/B),
persona-shaped — all real data / honest-empty (5/5 tests). **G-082 RESOLVED — 0 `random.*` in the project backend +
0 `Math.random` in `frontend-nextjs/src`:** state_manager/realtime_ingestion/demo-agents → DETERMINISTIC id/tick-derived;
neural_networks → real `defect_classifier` or honest-unavailable; api_integrations → honest-unavailable (Rule 9); the
primary dashboard → real `useLiveState`/`GET /api/simulation/state` + honest empty-state; 5 bespoke pages →
deterministic seeded generator; `generateMockState` removed. **G-085 honesty finding (surfaced + fixed):** `audit.sh`
was counting the gitignored, untracked `backend/venv/` (third-party numpy/scipy/sklearn) — ~209-212 of the old "364"
was never project source → venv/node_modules/site-packages added to the whitelist. **Baseline 364 → 3** (genuine
strict decrease — venv-scoping fix + real de-mock; decomposed for the reviewer: ~209-212 venv + ~59 python + ~87
frontend + residual 3 = `_generate_heuristic_actions`, a documented G-052 name-pattern false-positive; **real project
fabrication = 0**). New deps: **none** (bge-small/neo4j already present, Rule 9). Regression **49 passed / 1 skipped /
0 failed** (knowledge_graph + adoption + health + ws-smoke + agents); `verify-audit-chain.py` exit 0 (10,076 rows).
Independent review **PASS-WITH-GAPS (different agent — reproduced the 364→3 decomposition to the number, confirmed the
baseline change is LEGITIMATE hygiene + real de-mock NOT gaming, real fabrication genuinely 0 in both languages; the 3
minor gaps [ADR table figure, grounded-confidence-from-cosine, unused import] were all fixed in-stage + re-verified)**.
Deferred honestly: the 5 bespoke visual pages use deterministic demo layout over the real backend (primary dashboard is
fully real; per-visual real-data wiring is incremental); real-corpus GraphRAG + real-user adoption validation need a
pilot (G-035, buyer-blocked); pre-existing frontend loose-typing (`ignoreBuildErrors:true`) out of scope. **The three
roadmap-extension build stages (26 supply-chain / 27 resilience / 28 GraphRAG+adoption) are COMPLETE.** What remains is
a real-world engagement (pilot / accredited cert, buyer-blocked) + any further increments; CTO #6 at the Stage-30
cadence. **The next executable task is a pilot engagement or Stage 29+ per the roadmap** (no build stage is blocking).

**Prior snapshot (2026-07-04, after Stage 27 — resilience & anti-fragility):** **Stage 27 is CLOSED** — the second
roadmap-extension build stage (research §38; ADR `2026-07-04_stage27_resilience_antifragility.md`; explainer
`research/stage-explainers/STAGE_27/`). Shipped + verified live: **DUAL-IDENTITY model** (SPIFFE X509-SVID =
transport auth, SPIRE-rotated; ML-DSA-65 = evidence signing) — SPIRE server+agent LIVE (`docker/docker-compose.spire.yml`),
real SVIDs issued; **A2A AUTHENTICATION — R4/G-4 CLOSED on the mTLS path** (`a2a/server.py` extracts the peer SPIFFE
ID from the verified client cert [XFCC], trust-domain/allowlist-checks it → authenticated peer_id; foreign-domain
REJECTED; anonymous fallback named honestly-weaker); **Kagenti/A2A-spec AgentCard export** (`a2a/agent_card_cnstyle.py`,
dual-identity binding — channel-fit into CNCF/IBM watsonx Orchestrate); **durable-execution primitives**
(`agents/runtime/durable/`: EffectLedger at-most-once, CircuitBreaker CLOSED/OPEN/HALF_OPEN raising CircuitOpenError
[honest, no fabrication] with signed transition rows, Saga per-step-idempotency + reverse compensation + STUCK
surfacing). **Drills:** SVID rotation (new serial, SAME identity — zero-downtime) + circuit-breaker chaos (3 real
failures→OPEN→recover; signed rows; chain verifies). **G-083 PAID** (disruption-monitor episode-quiet-window expiry).
**24 new tests + full suite 413 passed / 5 skipped / 0 failed; audit holds 364** (`--no-baseline-drop`: additive
real code — legacy de-mock is Stage 28). New deps: `spiffe==0.3.0` + `spiffe-tls==0.4.0` (Apache-2.0, free).
Independent review **PASS (different agent, DYNAMIC — no theatre; real SVID [issuer O=SPIFFE], drill PASS, chain
exit 0; G-084 [SPIRE 1h-TTL operational note] ledgered)**. Deferred honestly: Istio mesh + production node
attestation (pilot/K8s); Temporal/Restate engine (ledgered); durable-primitive retrofit into every effect call-site
(actuator/order priority). **The next executable task is Stage 28 — GraphRAG grounding + design-thinking/behavioural
adoption UX** (`tasks/STAGE_28_graphrag_adoption_ux.md`) — the stage that finally moves 364 DOWN (frontend de-mock +
G-082 legacy path). CTO #6 at the Stage-30 cadence.

**Prior snapshot (2026-07-04, after Stage 26 — complete supply-chain automation):** **Stage 26 is CLOSED** — the first
roadmap-extension build stage (research §37; ADR `2026-07-03_stage26_supply_chain_automation.md`; explainer
`research/stage-explainers/STAGE_26/`). Shipped + verified: **`backend/agents/supply_chain/`** — the KB_25 loop
extended to a SECOND domain: five observed-signal role agents (demand = real `demand_forecaster.pt` or labelled
empirical stats; inventory = (s,S) with the full stochastic-lead ROP, z=2.33; scheduling/logistics/supplier proxies;
abstention over invention everywhere) + **deterministic Contract-Net** (sealed-bid min-cost awards + counter-based
exploration rounds; every award safety-gated through the `supply_chain_order` contract [Hard Rule 3] + signed audit
row + span) + **disruption monitoring** (supplier-failure→quarantine; latency via the **overdue-pending** expediting
rule [4 refuted-and-redesigned iterations; fleet-pooled threshold when own history is thin]; stockout; demand spike)
→ incidents via the Stage-25 exactly-once router. **The material loop was closed IN the sim** (`Supplier.order(on_fulfil)`
+ `SimWorld.deliver_material` — real backpressure). **A/B (10 paired seeds × 160 ticks, mid-run disruption):
stockouts −51% (106.3→52.2), bullwhip −98% (74.3→1.21), material −73% (4918→1305), equal holding — all CIs exclude 0**
(`supply_ab.json`; HONEST: SimWorld study, G-035 unchanged). **CONTROLLED drill** (injection vs same-seed no-injection
control): 10×-median freeze detected DURING the freeze, clean control, **PASS seeds 42/7/13**; sensitivity floor
(≈6.4× median at 3.5σ) disclosed. Independent review **PASS-WITH-GAPS (different agent — reproduced the A/B to the
digit, NO THEATRE; its control-arm refutation of the first drill claim + the Neo4j crash-loop root cause [corrupt GDS
jar in the plugins volume, 742 restarts — deleted, grounding verified live: 6 supplier nodes in the graph] were both
PAID before close; claims corrected in task doc/ADR/explainer)**. **19/19 stage tests; full suite 389 passed / 5 skipped / 0 failed (graph-gated tests now live);
audit holds 364** (`--no-baseline-drop`: additive real code — the legacy de-mock is Stage 28). New deps: none. G-083
(detector episode-reset polish) → Stage 27. **The next executable task is Stage 27 — resilience & anti-fragility**
(`tasks/STAGE_27_resilience_antifragility.md`), then 28 (GraphRAG + adoption UX). CTO #6 at the Stage-30 cadence.

**Prior snapshot (2026-07-03, after Stage 25 — post-GA operations):** **Stage 25 is CLOSED** — the first post-GA build
increment (research §36; ADR `2026-07-02_stage25_post_ga_ops.md`; explainer `research/stage-explainers/STAGE_25/`).
Shipped + verified live: the **EU-AI-Act Art-72 post-market loop OPERATIONAL** (nightly `post_market_anomaly_sweep.py` —
robust-Z + IsolationForest over per-day audit_chain features, honest-`insufficient_history` below 14 days, signed
`post_market.sweep` row seq 427 + `compliance/post-market-monitoring/2026-Q3.md` [REHEARSAL-labelled]); **PQC identity
rotation drilled live** (marker seq 428; chain green before/after, all 349 post-cutover sigs); **pgaudit live (G-060
RESOLVED)**; **G-066 scale FOOTHOLD** (`agents/runtime/shard_router.py` — sha256 sharding + advisory lock + at-most-once
ledger + warm-first; load test **8 exactly-once + 4 suppressed**; the test CAUGHT 2 real defects — worker-thread
import-lock deadlock + sequential re-run — fixed in-stage); **G-021 RESOLVED** (`/ops/cascade` + `/ops/post-market` on
the real chain, honest-503); **G-061 RESOLVED** (DVC skill); **G-067 RESOLVED** (Langfuse v3.203.3 UI verified live —
4 real overlay config gaps fixed incl. MinIO S3 + worker); nightly `crypto-deep-openssl35` gate (fixed per review:
availability-skip anchor + minimal dep set — 18 passed/1 legit skip proven); dep-refresh drill (G-070 + G-055/56 remain
pin-blocked → dedicated increment). **Full suite 365 passed / 10 skipped / 0 failed; audit holds 364**
(`--no-baseline-drop`: additive ops stage — the legacy de-mock is Stage 28). Independent review **PASS-WITH-GAPS
(different agent, DYNAMIC — every number reproduced; NO THEATRE; all 4 must-fix findings fixed in-stage + re-proven)**.
Honest deferrals (buyer-blocked): real pilot + A/B (R1/G-035/G-043), go-live mTLS + sil_bridge wiring (R2), accredited
cert (R3/G-011), EU provider obligations (R4), external federation partner, G-077 detector tier. **The next executable
task is Stage 26 — complete supply-chain automation** (`tasks/STAGE_26_supply_chain_automation.md`), then 27
(resilience & anti-fragility), 28 (GraphRAG + adoption UX). CTO #6 lands at the Stage-30 cadence.

**Prior snapshot (2026-07-02, out-of-band post-GA strategic audit + roadmap extension):** After the 2026-06-29 honesty sweep
(ledgered **G-082** — the GA'd LangGraph runtime is fabrication-free, but the *superseded legacy FastAPI demo path* still
fabricates and is the bulk of the 364 baseline; explainer `research/honesty-sweep-2026-06-29/`), an operator-requested
**strategic reset** ran: full-system production-readiness audit + competitive intelligence + positioning/perceptual maps +
honest gamechanger verdict + fresh SOTA web research (Kagenti/kagent, IBM watsonx Orchestrate + ACP→A2A, durable-execution,
competitors, NVIDIA physical AI, EU-AI-Act **high-risk deadline extended to 2 Dec 2027**, GraphRAG, adoption science) →
`research/initial-research.md §35` + `research/strategic-audit-2026-07/index.html` + KB_26 §12 + ADR
`2026-07-02_strategic_audit_and_post_ga_roadmap.md` (ML-DSA-65 signed) + out-of-band KB_TASK_LOG entry. **Honest verdict:**
credible gamechanger *candidate* in-niche, not proven — production-grade *discipline* + pilot-*deployable* but NOT
production-*scaled*; convert by closing, in order, real pilot (G-035/043) → scale (G-066) → certification (G-011) →
adoption UX. **Roadmap extended with three free/local build stages (task docs seeded):** **Stage 26** complete
supply-chain automation (multi-agent consensus + disruption monitoring), **Stage 27** resilience & anti-fragility
(SPIFFE/SPIRE identity + mesh mTLS + Kagenti-compatible AgentCard + durable-execution hardening + chaos; closes
R4/G-4/G-064-network + G-066 foothold), **Stage 28** GraphRAG grounding + design-thinking/behavioural adoption UX (moves
364 DOWN + de-mocks G-082). No code touched; audit baseline held at **364**. The next executable task is **Stage 25**
(post-GA ops) or **Stage 26** (supply-chain automation) — both seeded; Stage 25 remains the live-ops exercise, 26–28 the
new build increments. The build through GA is complete; what remains is a real-world engagement + these adoption/resilience
increments.

**Prior snapshot (2026-06-29, after Stage 24.5 — CTO #5, BUILD COMPLETE):** Stages 0–24 + all five CTO checkpoints
(**10.5/14.5/21.5/24.5** + the early 3.5) are **closed** — **24 build stages, every stage independently reviewed by a
different agent, audit baseline held at 364 throughout (no theatre across the entire build), GA at v1.0.0**. **Stage 24.5**
was the FINAL read-only CTO checkpoint (Stages 22–24) by a fresh different agent with live verification
(`audits/CTO_5_review.md` + `CTO_5_remediation_map.json`). **Verdict: ON TRACK — GA IS REAL AND HONEST; cleanest of all
five checkpoints, the FIRST with NO must-fix gap.** CTO #4 scorecard **8 honored / 4 honestly-deferred / 0 skipped**;
governance live-enforced + chain green confirmed live; production-grade criteria **6 MET / 4 PARTIAL / 0 hidden-deferred**;
**no theatre found** (`mock_detections 0`). Honesty note named precisely by the CTO: the Stage-24 A2A governance is
**authorization/confinement + audit, NOT authentication** (mTLS authentication = G-4/R4, deferred to pilot go-live). **7
remediations → Stage 25 / real engagement** (R1 real pilot+A/B G-035/G-043, R2 go-live safety/identity wiring, R3
accredited cert G-011, R4 EU provider obligations, R5 deep-eval gate + detector polish, R6 horizontal scale G-066, R7
low-severity ledger G-060/G-067/G-070). **Audit holds 364.** **The next executable task is Stage 25 — post-GA operations**
(`tasks/STAGE_25_post_ga.md`; carries the CTO #5 remediations). The remaining big items are buyer/accredited-body/
legal-entity-provider blocked (real pilot, certification, CE marking + EU-database registration) — correctly deferred,
not faked. **The build is complete; what remains is a real-world engagement, not more building.**

**Prior snapshot (2026-06-29, after Stage 24 — GA v1.0.0):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC)**, **13.5 (PQC foundations)**, **14 (A2A)**, **14.5 (CTO #3)**,
**15 (OT/IT)**, **16 (VDA 5050)**, **17 (functional safety)**, **18 (PQC Wave 2)**, **19 (governance evidence)**,
**20 (red-team evals)**, **21 (DR/HA)**, **21.5 (CTO #4)**, **22 (pilot runbook)**, **23 (conformity dry-run)**, and
**24 (GA release v1.0.0)** are **closed**. **Stage 24** GA'd the OSS platform + wired the Stage-23 governance layer into
LIVE enforcement (**G-080 RESOLVED**): `rbac.check_function_access` + `mac.can_read` (no-read-up) gate the A2A capability
boundary (`a2a/server.py::a2a_rpc` — external caller = L0 peer confined to `a2a_capability`, ≤"internal" clearance,
audited, composes with the peer-key gate), and `traceability.record_decision_trace` appends the Art-12 pre/post snapshot
in the runtime `log` node. **Verified live (different agent, DYNAMIC PASS):** a `run_incident` wrote a `decision.trace`
row (seq 425); the live `audit_chain` carries `decision.trace`+`rbac.check`+`mac.read`; chain green (426 rows, all 347
post-cutover verify); a2a/governance/runtime tests pass. **ISO-42001 NC-1** (clause-9.3 management review) **+ NC-2**
(ISO-42005 impact assessment) **closed**; **EU provider readiness** rehearsed (`eu-declaration-of-conformity.md`
[Annex-V template, internal-control/Annex-VI route, no notified body], `ga-release-checklist.md` mapping Art-16);
`RELEASE_NOTES_v1.0.0.md` (semver 1.0.0, stable contract). **Audit holds 364**; new deps: **none**. **Honest:** GA of the
free/OSS platform — conformity-assessment-READY, **NOT** certified/CE-marked/EU-registered/piloted/sold. **The next
executable task is Stage 24.5 — CTO Checkpoint #5** (`tasks/STAGE_24_5_cto_checkpoint_5.md`; final read-only every-10
review across Stages 22–24; run `scripts/cto-review.sh`). Still owed (ledgered, post-GA — need a buyer/accredited
body/legal-entity provider): the real pilot + published A/B (G-035/G-043), accredited cert + CE/registration (G-011),
NC-3 customer records; G-066 (scale), G-060 (pgaudit), G-067 (Langfuse-UI), G-070 (a2a-sdk).

**Prior snapshot (2026-06-22, after Stage 23):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**, **14 (A2A)**,
**14.5 (CTO #3)**, **15 (OT/IT)**, **16 (VDA 5050)**, **17 (functional safety)**, **18 (PQC Wave 2)**, **19 (governance
evidence)**, **20 (red-team evals)**, **21 (DR/HA)**, **21.5 (CTO #4)**, **22 (pilot runbook)**, and **23 (conformity
dry-run)** are **closed**. **Stage 23** rehearsed an external conformity assessment + shipped the KB_18 governance
access-control layer (CTO #4 R10 + G-028/029/030): **`backend/governance/`** — `mac.py` (Bell-LaPadula confidentiality
MAC: no-read-up / no-write-down, dominance+containment; safety wrapper = Biba dual), `rbac.py` (agent-hierarchy
L3→L0 function-scoped least-privilege RBAC; L0 peer confined, assume-breach), `traceability.py` (state_snapshot pre/post +
decision → signed `audit_chain`, Art-12) — pure/deterministic, **9/9 tests**, honest audit-degradation. Conformity docs:
`compliance/iso-10218-risk-assessment.md` (ISO 10218-2:2025 §6 + the **G-011 cert path** at the certified-PLC `sil_bridge`
seam), `compliance/iso-42001-internal-audit/2026-Q4_audit.md` (9 Annex-A objectives: 7 Conformant / 2 Partial / 0 major
NC; 3 minor NCs → 24), `compliance/annex-iv-packs/2026-06-22_dry_run.pdf` (Annex-VI internal-control file, signed).
**Honest framing (research §33.1):** our Annex-III category is points 2-8 → EU-AI-Act **internal-control (Annex VI)** route,
NO notified body mandated; no harmonised AI standard published → no presumption of conformity; this is a SELF-AUDIT
dry-run, NOT certification. New deps: **none**. **Audit holds 364**; mock notified-body assessment (`audits/
STAGE_23_external_review.md`) = **SUBSTANTIALLY CONFORMANT** (pre-cert); independent review **PASS-WITH-GAPS (different
agent — Bell-LaPadula logic verified correct, 9/9 tests, theatre-clean, no overclaim)**. **The next executable task is
Stage 24 — GA release** (`tasks/STAGE_24_TBD.md`; name via `start-task.sh 24 <slug>`). Still owed (ledgered): **G-080**
(wire governance to a live enforcement call site), **G-081** (regenerate the final Annex-IV pack with DB up), NC-1/2/3
(mgmt-review record / ISO-42005 impact doc / customer records) — all → Stage 24; G-011 actual cert + G-035/G-043 real
pilot (need an accredited body/buyer). (Roadmap CTO #5 = Stage 24.5.)

**Prior snapshot (2026-06-22, after Stage 22):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A)**, **14.5 (CTO #3)**, **15 (OT/IT bridge)**, **16 (VDA 5050)**, **17 (functional safety)**, **18 (PQC Wave 2)**,
**19 (governance evidence)**, **20 (red-team evals)**, **21 (DR/HA)**, **21.5 (CTO #4)**, and **22 (pilot deployment
runbook)** are **closed**. **Stage 22** made the system pilot-DEPLOYABLE (free/OSS/local) + paid the doable CTO #4
Stage-22 remediations, phased A→D: **R8/G-076 RESOLVED** (migration `0009` → `mem0_app` non-superuser LOGIN role; the
adapter connects AS it so Postgres FORCE RLS is enforced by the CONNECTION ROLE, not best-effort `SET ROLE`; live: direct
client ns-unset→0/right→1, non-superuser); **R1/G-1 RESOLVED** (durable audit-chain test-isolation — `_dsn` prefers
`AUDIT_CHAIN_DATABASE_URL` + a conftest fixture runs the chain on a throwaway DB during tests; real chain head **421
unchanged across the full suite**; `verify-audit-chain` exit 0); **R6** (new CI job `crypto-openssl35` on
`debian:trixie-slim`/OpenSSL-3.5.6 GATE-enforces `tests/crypto/` — hybrid-TLS/SLH-DSA/ML-KEM/ML-DSA — that skip on the
OpenSSL-3.0 ubuntu runners; verified 17 passed in-container); **R2** (risk-register refreshed); **R3** verified
already-clean (one blocking `sbom` job — the CTO finding was stale; recorded honestly). Docs: `compliance/
pilot-deployment-runbook.md` (SRE PRR gate + shadow→assisted→supervised canary + rollback + **EU-AI-Act Art-26 deployer
checklist** + §4 go-live wiring of R4/R5), `compliance/post-market-monitoring-plan.md` (**Art-72** — ingested into the
Annex IV pack §11), `compliance/pilot-onboarding-kit.md` (data-intake + A/B protocol + real-fleet re-fit plan — buildable
half of R11). New deps: **none**. **Full suite 335 passed / 10 skipped / 0 failed; audit holds 364**; independent review
**PASS (DYNAMIC, different agent — R8/R1/R6 reproduced live, deferrals honest, no new gaps)**. **DEFERRED (honest,
ledgered, need a buyer/real fleet — Rule 9):** the REAL customer pilot + published A/B (R11/G-035/G-043); R4 A2A
live-mTLS + R5 first-real-PLC `sil_bridge` hardening (wire AS the pilot goes live, runbook §4); R7 cascade UI (G-021);
R9 continuous anomaly detection (G-064 tail); R12 carry-forward (G-066 scale, G-060 pgaudit, G-067, G-070). Conformity is
NOT certified. **The next executable task is Stage 23 — conformity dry-run** (`tasks/STAGE_23_conformity_dryrun.md`;
carries CTO #4 R10 = mock notified-body assessment + the KB_18 governance wishlist G-028/G-029/G-030). (Roadmap CTO #5 =
Stage 24.5.)

**Prior snapshot (2026-06-22, after Stage 21.5):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, **14.5 (CTO Checkpoint #3)**, **15 (OT/IT bridge)**, **16 (VDA 5050 robot fleet)**,
**17 (functional safety wrapper)**, **18 (PQC Wave 2)**, **19 (governance evidence pipeline)**, **20 (red-team eval
harness)**, **21 (DR/HA & backups)**, and **21.5 (CTO Checkpoint #4)** are **closed**. **Stage 21.5** was the read-only
every-10 CTO review across Stages 15–21 by a FRESH different agent with LIVE verification (`audits/CTO_4_review.md` +
`CTO_4_remediation_map.json`). **Verdict: ON TRACK — hardest wave kept honest; every headline number reproduced**
(canonical protobuf/VDA-2.1.0 schemas, load-bearing safety trace-pairing, real FIPS-203/204/205 crypto, 14-section signed
Annex IV pack, load-bearing audit-chain verifier, OWASP-LLM01 **0.9935** hybrid reproduced to the digit, tested DR
restore). **CTO #3 scorecard: 10 honored / 1 not-yet-due / 0 skipped**; independence fully maintained. **"Notified body
tomorrow?" — NOT YET, but honest** (evidence machinery real + self-attesting; conformity = Stage 23 + notified body).
**Critical live finding G-1 FIXED NOW:** the live `audit_chain` was broken (121 post-cutover rows failed ML-DSA-65 verify
— recurring dev test-key pollution) → `back-sign-legacy-rows.py --confirm` re-attested them → `verify-audit-chain.py`
exit 0 (417 rows, all 338 post-cutover sigs verify); durable test-isolation fix → Stage 22 (R1). **12 remediations routed**
(R1–R9/R11/R12 → Stage 22, R10 → Stage 23). **Audit holds 364** (read-only checkpoint). **The next executable task is
Stage 22 — pilot deployment runbook** (`tasks/STAGE_22_TBD.md`; name via `start-task.sh 22 <slug>`; folds in the 11 CTO #4
Stage-22 remediations — gate on G-1 chain-green [done] + G-2 register refresh + making G-075 sil_bridge / G-4 A2A-mTLS
load-bearing as the pilot goes live). Still owed (ledgered): G-067, G-068, G-075, G-076, G-077, G-066 horizontal-scale,
audit_chain test-isolation (R1), KB_18 governance wishlist (G-028/029/030 → 23).

**Prior snapshot (2026-06-22, after Stage 21):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, **14.5 (CTO Checkpoint #3)**, **15 (OT/IT bridge)**, **16 (VDA 5050 robot fleet)**,
**17 (functional safety wrapper)**, **18 (PQC Wave 2)**, **19 (governance evidence pipeline)**, **20 (red-team eval
harness)**, and **21 (DR/HA & backups)** are **closed**. **Stage 21** built the free/OSS/local disaster-recovery layer
for the stateful tier (`scripts/backup/` + `scripts/restore/` + `scripts/chaos/`; research §31): `pg_dump -Fc` +
`pg_basebackup` (PITR anchor) + Neo4j Community **offline** dump (`neo4j`+`system`) + Redis RDB, orchestrated by
`backup-all.sh` with a SHA-256 manifest + retention + 3-2-1 layout (`BACKUP_ROOT_2` second medium + config-only off-site,
Rule 9). The **binding deliverable** is `restore-verify.sh` — restores the latest dump into a SCRATCH DB and ASSERTS
per-table row-count + `audit_chain` head parity, exits nonzero on mismatch (**RTO ~4 s** live; independently proven to
catch drift + corruption). `kill-postgres-drill.sh` is a chaos drill (kills PG → honest degradation, no fabrication →
recovery). `compliance/dr-runbook.md` (RPO ≤60 s w/ PITR / RTO, recovery steps, scope boundary). CTO #3 remediation:
`test_runtime_determinism.py` (identical trajectory+decisions across two runs). CI gate `dr-backup-restore`. New deps:
**none**. **Audit holds 364**; independent review **PASS-WITH-GAPS (DYNAMIC, different agent — restore-verify proven to
exit 1 on drift AND corruption; backups/chaos/determinism all real)**. **G-066 DR-half RESOLVED** + **G-004 (chaos)
RESOLVED**; two review-found gaps **G-078** (neo4j restart not verified) + **G-079** (chaos secondary leg not load-bearing)
were **fixed in-stage + re-verified**. PITR WAL-archiving + multi-node HA + live off-site are honestly deferred to
pilot/cloud (Rule 9). **The next executable task is Stage 21.5 — CTO Checkpoint #4** (`tasks/STAGE_21_5_cto_checkpoint_4.md`;
read-only every-10 review across Stages 15–21; run `scripts/cto-review.sh`). Still owed (all ledgered, deferred-by-design):
G-067 (Langfuse UI); G-068 (pgoutput WAL); G-075 (sil_bridge real-caller hardening); G-076 (mem0 RLS non-superuser role);
G-077 (detector hardening); G-066 horizontal-scale (→ pilot); audit_chain dev-row re-attestation (G-073 follow-up).

**Prior snapshot (2026-06-22, after Stage 20):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, **14.5 (CTO Checkpoint #3)**, **15 (OT/IT bridge)**, **16 (VDA 5050 robot fleet)**,
**17 (functional safety wrapper)**, **18 (PQC Wave 2)**, **19 (governance evidence pipeline)**, and
**20 (red-team eval harness)** are **closed**. **Stage 20** built the automated red-team / adversarial eval harness
(`backend/training/evals/` + `backend/security/prompt_guard.py`) that scores the system's REAL defences — every number
measured against live code (Rule 1a / KB_23), never hand-set: **`prompt_guard.py`** is a hybrid prompt-injection detector
(16 heuristic patterns over the OWASP-LLM01 taxonomy + a bge-small semantic-kNN layer with honest degradation), wired
into `agents/llm_client.generate()` on **100%-traffic**; the deterministic **corpus** (`generate_corpus.py`) is **217
OWASP-LLM01** (153 attacks + 64 benign controls) + 14 NIST-RMF-Agentic probes + 8 industry-safety scenarios (attack
strings are inert defensive fixtures, `expect_blocked:true`, never executed); **`runner.py`** scores each suite against
the real defence (prompt_guard / `mem0._authorize`+RLS / `tool_manifest` / `safety.validator`); **`agentic_metrics.py`**
(G-008) computes tool-selection/action-completion/reasoning-coherence over the REAL LangGraph trajectory. **Measured live:**
OWASP-LLM01 **0.9935 detection / 0.0156 FPR** (hybrid; 0.758 heuristic CI), NIST **14/14**, industry input-tier 0.875,
agentic **1.0/1.0/1.0**; eval tests **10/10**. CI **`phoenix-evals`** (deterministic subset, every PR, fails on a
`thresholds.yaml` breach) + **`nightly-evals.yml`** (full hybrid + live runtime, enforces ≥99% OWASP target); results feed
the Annex IV pack. New deps: **none** (bge-small already present). **Audit holds 364**; independent review **PASS (DYNAMIC,
different agent — every number reproduced, gate is load-bearing, no circularity/theatre)**. **G-008 RESOLVED**, **G-064
Stage-20 tail RESOLVED**; new **G-077** (detector residuals: 1 indirect miss, FPR 0.0156, industry input-tier 0.875 —
binding gate is the validator, not a live breach). Honesty note: caught + fixed a stale-`results.json` from an
invalid-regex import crash hidden by `grep >/dev/null` (research §30.5). **The next executable task is Stage 21 — DR/HA &
backups** (`tasks/STAGE_21_TBD.md`; name via `start-task.sh 21 <slug>`). Still owed (all ledgered, deferred-by-design):
G-067 (Langfuse UI render); G-068 (pgoutput WAL); G-075 (sil_bridge real-caller hardening, → first real PLC caller);
G-076 (mem0 RLS non-superuser app role, → multi-tenant stage); G-077 (detector hardening + continuous anomaly detection).
(G-001 Stage-3 re-audit and G-031 CTO #1 independent pass were **RESOLVED 2026-06-12** — earlier snapshots that listed
them as "still owed" were stale.) (Roadmap CTO #4 = Stage 21.5.)

**Prior snapshot (2026-06-21, after Stage 19):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, **14.5 (CTO Checkpoint #3)**, **15 (OT/IT bridge)**, **16 (VDA 5050 robot fleet)**,
**17 (functional safety wrapper)**, **18 (PQC Wave 2)**, and **19 (governance evidence pipeline)** are **closed**.
**Stage 19** built the **EU AI Act Annex IV** technical-documentation pack generator + paid 4 CTO #3 remediations:
`scripts/generate-annex-iv-doc.py` assembles all **14 KB_18 sections** from live repo evidence → HTML bundle + PDF
(`fpdf2`) with an **ML-DSA-65-signed conformity-declaration footer** (HONEST: conformity-assessment-READY, NOT a
certificate — ISO 42001 unharmonised, no harmonised AI-Act standard published; actual conformity = Stage 23 + notified
body); `compliance/ai-policy.md` (ISO 42001 A.6.1); CI gate `annex-iv-pack-builds` (blocking). **G-073 RESOLVED** —
`scripts/verify-audit-chain.py` rewritten **LOAD-BEARING** (verifies every post-cutover ML-DSA-65 row, **exits 1 on any
failure**, reports the placeholder→ML-DSA cutover seq); it caught dev rows signed by ephemeral test-isolation keystores
→ `scripts/back-sign-legacy-rows.py` re-attests them under the current key (hashes unchanged; signed marker); chain
verifies exit 0 (79 placeholders @ cutover seq 80 + all post-cutover ML-DSA rows). **G-074 RESOLVED** — `a2a/server.py`
emits `a2a.rpc.<method>` spans + a signed `audit_chain` row per capability call; per-model `ml.inference.*` spans
(world_model/diagnose/explain/decide) + a `cdc.ingest` span. **mem0 RLS** — migration `0008` FORCE row-level security +
non-superuser `mem0_app` role (the adapter `SET ROLE`s + `set_config`s the namespace; a direct SQL client is now
**fail-closed**, verified — behind the Python `_authorize` first gate). New dep: `fpdf2==2.8.7`. **Tests: compliance 4 +
memory 13 + a2a 9 + runtime 7 pass; audit holds 364**; independent review **PASS-WITH-GAPS (DYNAMIC, different agent)** —
RLS fail-closed proven independently, G-073 exits 1 on a tampered row; new **G-076** (RLS depends on best-effort
`SET ROLE` because the app DB user is a superuser → harden with a non-superuser app role at the multi-tenant stage).
Scope: the KB_18 wishlist (Policy DSL / Bell-LaPadula MAC / PII filter / ISO 42005 — G-028/G-029/G-030) was not in the
task-doc ACs → ledgered for a later governance stage. **The next executable task is Stage 20 — red-team eval harness**
(`tasks/STAGE_20_redteam_eval.md`; pays **G-008** agentic evals + OWASP LLM Top-10 / prompt-injection). Still owed:
G-031 (CTO #1), G-001 (Stage 3 re-audit); G-067; G-068; G-075 (sil_bridge real-caller hardening); G-076 (mem0 RLS
non-superuser role); G-063/G-064 (zero-trust → 20). (Roadmap CTO #4 = Stage 21.5.)

**Prior snapshot (2026-06-21, after Stage 18):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, **14.5 (CTO Checkpoint #3)**, **15 (OT/IT bridge)**, **16 (VDA 5050 robot fleet)**,
**17 (functional safety wrapper)**, and **18 (PQC Wave 2)** are **closed**. **Stage 18** put every external boundary on
**hybrid ML-KEM-768+X25519 TLS** + added **SLH-DSA-SHA2-128s** long-trust signing — all REAL on the host's
**OpenSSL 3.5.4** (native ML-KEM/ML-DSA/SLH-DSA + `X25519MLKEM768`, so the oqs-provider build is obsolete):
`backend/crypto/pqc_kem.py` (ML-KEM-768 via **kyber-py**, pure-Python), `backend/crypto/pqc_slh_dsa.py`
(SLH-DSA-SHA2-128s via OpenSSL 3.5 CLI), a **live X25519MLKEM768 handshake with an ML-DSA-65 cert** verified by
`tests/crypto/test_hybrid_tls.py`, **all 7 model cards SLH-DSA-signed** (self-verifiable footers),
`scripts/{sign-firmware-bundle.py,gen-pqc-tls-cert.sh}`, a **fixed** `rotate-pqc-keys.sh` (real `key_manager` CLI,
4 key types × `--mode` × `--dry-run`), an `audit.sh` **classical-crypto gate**, and **G-065** (CycloneDX SBOM +
`compliance/dependency-exceptions.md` + blocking CI `sbom` job; bandit blocking). New deps: `kyber-py==1.2.0`,
`cyclonedx-bom==7.3.0`. **18 crypto tests pass; audit holds 364**; independent review **PASS (DYNAMIC, different agent)** —
5 findings (sbom YAML-duplicate-key, version drift, a test assertion, risk-register wording) **fixed in-stage**. Honest
residual: the containerised sidecar deploy + live A2A mTLS-client-cert→peer_state binding are deploy-wiring on the
verified KEX/cert layer; CI runners are OpenSSL 3.0 so the SLH-DSA/hybrid-TLS tests **skip in CI** (host-verified;
KEM runs in CI). **The next executable task is Stage 19 — evidence pipeline** (`tasks/STAGE_19_evidence_pipeline.md`:
pays **G-073** [make `verify-audit-chain.py` signature-verify load-bearing + back-sign the 79 legacy placeholder rows]
+ **G-074** [A2A spans/audit rows] + RLS for mem0 [G-073-adjacent]). Still owed: G-031 (CTO #1), G-001 (Stage 3
re-audit); G-067; G-068; G-073/G-074 (→19); G-075 (sil_bridge real-caller hardening); G-008 (→20 red-team evals).

**Prior snapshot (2026-06-21, after Stage 17):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, **14.5 (CTO Checkpoint #3)**, **15 (OT/IT bridge)**, **16 (VDA 5050 robot fleet)**, and
**17 (functional safety wrapper)** are **closed**. **Stage 17** built the **LLM-planner / SIL-rated-executor** safety
wrapper (`backend/safety/`): the Pydantic safety-contract DSL + 5 contracts; `validator.validate()` (precondition/
invariant gate → SIL routing); `sil_bridge` (the ONLY `actuator.*` emitter — refuses non-allowing/mis-routed Decisions,
**self-validating** when given contract+world_state per G-075); `sto_ss1` (STO/SS1 + signed audit rows); `sil_pl_map`
(IEC 61508 SIL ↔ ISO 13849-1 PL). **Trace-pairing CI invariant** (`scripts/check-safety-trace-pairing.py`, gate
`safety-contract-tests`): every `actuator.*` span preceded by `safety.validate.*` (wired on `master.dispatch_order` +
runtime `execute`). **Self-healing** (`safety/self_healing/`): rolling-Z torque anomaly → behaviour-tree
self_diagnose_calibrate → resume (validator-gated) OR STO+quarantine. **CTO #3 zero-trust** (`backend/security/`):
NIST SP 800-207 (+ CSA Agentic Trust/MAESTRO/OWASP NHI) named + 5 pillars; **per-agent ML-DSA-65 identity**; MCP tool
authz + arg-sanitisation + rate-limit + **signed tool manifest** — **G-063 RESOLVED, G-064 MOSTLY** (A2A live mTLS→18).
Fixed a cross-platform keystore bug (alias `:`→sanitised dir). New deps: **none**. **34 safety/security + 7 runtime
tests pass LIVE**; audit holds **364**; independent review **PASS (DYNAMIC, different agent)** — it caught **G-075**
(sil_bridge trusted a Decision's fields without provenance → forgeable; NOT a live breach [no real caller], wording
narrowed + self-validation hardening added; full hardening → Stage 18). **The next executable task is Stage 18 — PQC
Wave 2** (`tasks/STAGE_18_pqc_wave2.md`: the hybrid ML-KEM-768+X25519 mTLS sidecar — pays the A2A live-mTLS / ZT
Network+Device pillars / OPC-UA+broker mTLS deferrals, and the G-075 first-real-`sil_bridge`-caller hardening).
Still owed: G-031 (CTO #1), G-001 (Stage 3 re-audit); G-067; G-068; G-073/G-074 (→19); G-075 (→18);
G-008 (→20 red-team evals). 

**Prior snapshot (2026-06-21, after Stage 16):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, **14.5 (CTO Checkpoint #3)**, **15 (OT/IT bridge)**, and **16 (VDA 5050 robot fleet)** are
**closed**. **Stage 16** built the multi-vendor AGV/AMR fleet boundary (`backend/integrations/vda5050/`): the **real
v2.1.0 JSON schemas** vendored from the VDA5050 repo at git **tag `2.1.0`** (MIT — NOT `main`, which is v3.0.0: caught
because v3 `state` uses `powerSupply` vs v2.1.0 `batteryState`) → **generated Pydantic `models/`** (datamodel-code-generator);
`master.py` (`Vda5050Master` — subscribes state/connection/factsheet/visualization, publishes order/instantActions,
**verifies connection ONLINE+fresh before any dispatch** [anti-spoof] + routes every dispatch through
`backend/safety/validator.py`); `topics.py`; `actions.py` (decision→VDA order graph). **`backend/safety/validator.py`**
= the Stage-16 structural+freshness gate emitting the `safety.validate` span (SIL-rated contract validator + STO/SS1 =
Stage 17). `policy_query.recommend_action` returns VDA-shaped routing when a `fleet` block is present. **CTO #3
remediations RESOLVED:** **G-059** (runtime `orient` routes its prediction through `model_inference_server` over MCP
stdio when `RUNTIME_MCP_MEDIATED=1` — genuinely MCP-mediated; observed live MCP server log) + **R11** (Groq→Ollama
free-cost fallback **proven LIVE both legs** — real Groq call + Groq-fails→real-local-Ollama-returns-content via a
Docker `ollama/ollama` + `qwen2.5:0.5b`; all-providers-fail → raises, no fabrication). New deps:
`datamodel-code-generator` (build-time). **12 VDA + 6 remediation tests pass LIVE**; CI gate `vda5050-schema-validate`;
audit holds **364**; independent review **PASS (DYNAMIC, different agent — schemas byte-faithful to upstream tag 2.1.0)**.
**The next executable task is Stage 17 — functional safety wrapper** (`tasks/STAGE_17_functional_safety_wrapper.md`:
the SIL-rated contract-DSL validator + sil_bridge + STO/SS1; the `safety.validate`-before-actuator CI invariant goes
live). Still owed: G-031 (CTO #1), G-001 (Stage 3 re-audit); G-067; G-068; G-070; G-073/G-074 (→19);
G-008/G-063/G-064 (agentic evals + ZT → 17/20).

**Prior snapshot (2026-06-20, after Stage 15):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, **14.5 (CTO Checkpoint #3)**, and **15 (OT/IT bridge)** are **closed**. **Stage 15** built the
open-standards bridge to customer OT/IT (`backend/integrations/`): **OPC UA** (asyncua 1.1.5 — `opcua/server.py`
ISA-95 tree + `opcua/client.py` subscribe-only browse/read/subscribe; interim Aes256Sha256RsaPss armed-when-certs,
PQC overlay @18); **MQTT Sparkplug B v3.0** (`sparkplug/` — REAL protobuf from the canonical Eclipse `sparkplug_b.proto`
[grpcio-tools, NOT mqtt-spb-wrapper], full lifecycle NDEATH-LWT/NBIRTH-seq0-bdSeq/seq-0-255-wrap/NCMD-Rebirth, every
payload **HMAC-SHA-384** MAC'd + verified); **ISA-95 population** (`graph_isa95.populate_from_ot_event` MERGEs Equipment
from inbound OPC UA/Sparkplug events). Dep tension resolved (grpcio-tools 1.62.3 + protobuf `<5` — TF-2.15-safe;
research §25.4). New deps: `asyncua==1.1.5`, `grpcio-tools==1.62.3`, protobuf pin. **8 integration tests pass LIVE**
(Mosquitto + Neo4j + OPC-UA-over-TCP); CI gate `opcua-sparkplug-integration`; audit holds **364**; independent review
**PASS (DYNAMIC, different agent — confirmed the protobuf is byte-identical to the canonical Eclipse proto)**. **CTO #3
remediations done:** **G-062 RESOLVED** (formal different-agent Stage-12 indep review → PASS; namespace isolation
code-enforced) + risk-register **refreshed** (G-064/G-073/G-074 + OT rows). Actuator/write paths (VDA 5050 orders,
PLC writes, `safety.validate` gate) deferred to **Stage 16/17** (KB_17); live mTLS/PQC overlay @18. **The next
executable task is Stage 16 — VDA 5050 robot fleet** (`tasks/STAGE_16_vda5050_robot_fleet.md`; carries CTO #3 R3 =
wire the runtime to consume MCP tools [G-059] + R11 = prove Groq→Ollama fallback). Still owed: G-031 (CTO #1), G-001
(Stage 3 re-audit); G-059 (→16); G-067; G-068; G-070; G-073/G-074 (→19); G-008/G-063/G-064 (→17/20).

**Prior snapshot (2026-06-20, after Stage 14.5):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**,
**14 (A2A protocol)**, and **14.5 (CTO Checkpoint #3)** are **closed**. **Stage 14.5** was the read-only every-N
CTO review across Stages 11–14, done by a **fresh, different agent with LIVE verification** on the up Docker stack
(so — unlike CTO #2's caveated self-review — no separate independent pass was owed): outputs `audits/CTO_3_review.md`
+ `audits/CTO_3_remediation_map.json`. **Verdict: ON TRACK, strongest checkpoint yet.** CTO #2 scorecard **6 honoured
/ 2 not-yet-due / 0 skipped** (R8 real-ML-DSA-65 signing cryptographically verified). 12 remediations routed → Stages
15–22 (10 appended; 2 retained for unseeded 21/22). **New gaps: G-073** (`verify-audit-chain.py` sig-verify is
`try/except: pass` — attests hash linkage only; 79/110 rows legacy placeholder-sha256) **+ G-074** (A2A boundary
emits no spans/audit rows) → both Stage 19. Top immediate gaps routed: G-059 (runtime not yet consuming its own MCP
tools)→16, G-063/G-064 (zero-trust/identity, HIGH)→17. **Audit holds 364** (read-only checkpoint, `--no-baseline-drop`).
**The next executable task is Stage 15 — OT/IT bridge** (`tasks/STAGE_15_ot_it_bridge.md`; folds in CTO #3 R1/R2 =
G-062 formal Stage-12 indep review + risk-register refresh). Still owed: G-031 (CTO #1), G-001 (Stage 3 re-audit);
G-059 (→16); G-062 (→15); G-067; G-068; G-070; G-073/G-074 (→19); G-008/G-063/G-064 (agentic evals + ZT → 17/20).

**Prior snapshot (2026-06-15, after Stage 14):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, **13.5 (PQC foundations)**, and
**14 (A2A protocol)** are **closed**. **Stage 14** built the external agent-to-agent boundary (`backend/a2a/`):
ML-DSA-65-**signed agent cards** (`agent_card.py` — JCS RFC-8785 canonical, via the Stage-13.5 KeyProvider) served at
`/.well-known/agent.json`; a **JSON-RPC 2.0** capability endpoint `/a2a/v1/rpc` (`server.py`) that exposes ONLY the
deliberate capability subset (`skills/forecast_oee`) and **refuses MCP tools with -32601** (the KB_16 trust
asymmetry — verified); `revocation.py` (5-min poller) + `peer_state.py` (active/quarantine/revoked) + migration
`0007_a2a_peers`. **Hand-rolled** (a2a-sdk needs httpx≥0.28.1 vs our pinned 0.27.2 — research §24; G-070). Hybrid
ML-KEM-768 mTLS stays **Stage 18** (KB_13); `transport_tls.py`+`docker-compose.pqc.yml` are the scaffold (live TLS
not claimed). New deps: **none** (jcs already present). 9 A2A tests; **audit holds 364**; independent review
**PASS (DYNAMIC, different agent)**. **The next executable task is Stage 14.5 — CTO Checkpoint #3** (audits
Stages 11–14: runtime + MCP + memory + observability + CDC + PQC + A2A; run `scripts/cto-review.sh`).
**Docker-gated G-069 + G-071 are RESOLVED (2026-06-20, Docker back up):** the Stage-13.5 audit_chain ML-DSA-65 DB
round-trip runs (14 DB-gated tests pass), `verify-audit-chain.py` → "Audit chain OK (84 rows verified)", the full
live suite (PG@5544 + Neo4j@7687 + Redis) → **252 passed / 3 skipped**, and the A2A two-instance federation passes
**over real HTTP** (two distinct ML-DSA-65 identities; trust boundary holds on the wire). Still owed:
G-031 (CTO #1), G-001 (Stage 3 re-audit); G-059 (MCP-tool routing); G-062 (Stage-12 formal indep review);
G-067 (Langfuse UI); G-068 (pgoutput WAL→15); G-070 (a2a-sdk); G-008/G-063/G-064 (agentic evals + ZT + MCP hardening).

**Prior snapshot (2026-06-15, after Stage 13.5):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, **13 (CDC ingestion)**, and **13.5 (PQC foundations)** are
**closed**. **Stage 13.5** wired **real FIPS-204 ML-DSA-65** signing behind KB_13's pluggable **KeyProvider** ABC
(`backend/crypto/`: `key_provider` factory + `software_provider` [dilithium-py — Windows-native, no liboqs build;
verified sizes pk1952/sk4032/sig3309] + honest `pkcs11`/`vault` stubs + `pqc_signing`/`key_manager`/`hmac_sha384`).
The `audit_chain` **placeholder signatures are replaced** — rows now sign with real ML-DSA-65 (`audit_chain._sign()`
already hooked `crypto.pqc_signing`, so no change needed); **all 33 ADRs batch re-signed** (`sign-decision-log.py`,
`agent-identity:v1`) — the CTO remediation. dilithium-py chosen because liboqs won't build on Windows + PyCA
cryptography 46's OpenSSL wheels don't expose ML-DSA (research §23); production swaps to HSM/Vault by config. No
RSA/ECDSA in `backend/crypto/` (hook + `pqc-crypto-tests` CI gate). New deps: `dilithium-py==1.4.0`, `jcs==0.2.1`.
8 crypto tests; **audit holds 364**; independent review **PASS (DYNAMIC, different agent)**. **G-069**: the host
Docker Desktop was DOWN at close → the DB-gated audit_chain round-trip + full live suite re-run are owed when Docker
is up (the ML-DSA-65 wiring is proven infra-free). **The next executable task is Stage 14 — A2A protocol** (agent
cards signed by the `agent-identity` ML-DSA-65 key; mTLS trust boundary; begins paying G-059/G-064). Still owed:
G-031 (CTO #1), G-001 (Stage 3 re-audit); G-059 (MCP-tool routing); G-062 (Stage-12 formal indep review);
G-067 (Langfuse UI); G-068 (pgoutput WAL→15); G-069 (Stage-13.5 DB round-trip when Docker up).

**Prior snapshot (2026-06-15, after Stage 13):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, **12.5 (observability)**, and **13 (CDC ingestion)** are **closed**. **Stage 13** built the
DB-write→agent loop: a `cdc_emit()` trigger on `incidents`/`stages.status` → durable `cdc_outbox` + `pg_notify` →
`backend/ingestion/cdc_listener.py` (a **sync-psycopg background thread** — psycopg async can't use the Windows
Proactor loop the MCP stdio path needs; `LISTEN cdc_events` + drain-on-connect + `change_to_inject`) → `SimWorld.inject()`.
**Transactional outbox + NOTIFY + drain** (research §22), NOT Supabase Realtime (Debezium is EOL; that's a heavy
Elixir server; test_decoding "avoid in prod"; pgoutput needs fragile parsing; wal2json not in the image). PG
container restarted with `wal_level=logical` (data preserved). No new deps. 6 CDC tests; full suite **234 passed /
2 skipped, audit 364**; independent review **PASS (DYNAMIC, different agent)**. **The next executable task is
Stage 13.5 — PQC Foundations** (KeyProvider + ML-DSA-65 signing via `backend/crypto/pqc_signing.py` — replaces the
`audit_chain` placeholder signatures with real post-quantum signatures; begins the zero-trust agent-identity work,
G-064). Still owed: G-031 (CTO #1), G-001 (Stage 3 re-audit); G-059 (MCP-tool routing→14); G-062 (formal indep
review of Stage 12); G-067 (Langfuse-UI render); G-068 (pgoutput WAL→15); G-008/G-063/G-064 (agentic evals + ZT).

**Prior snapshot (2026-06-15, after Stage 12.5):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**,
**12 (agent memory)**, and **12.5 (observability)** are **closed**. Plus an out-of-band **security + zero-trust +
survivability review** (research §20; HTMLs `security-zero-trust-2026-06`, `survivability-analysis-2026-06`; ledger
G-063…G-066). **Stage 12.5** wired the observability pipeline (KB_15): `backend/observability/` (OTel SDK + env-gated
OTLP exporter + `traced_span` wrapper + FastAPI auto-instrumentation, honest-when-unconfigured; `evidence_sink` →
`audit_chain`; langfuse/phoenix sinks); spans `langgraph.node.*` / `mcp.tool.*` / `memory.mem0.*` /
`ml.inference.*` / `audit_chain.append`; overlay `docker-compose.observability.yml` + collector config; CI
`observability-smoke` (+ fixed the `mcp-conformance` Postgres image → pgvector for the 0005 migration). New deps:
aligned `opentelemetry-*` 1.42.1/0.63b1. **Verified:** 7 span tests + **live OTLP→collector confirmed** + full suite
**228 passed / 2 skipped, audit 364**; independent review **PASS (DYNAMIC, different agent)**. **The next executable
task is Stage 13 — CDC ingestion** (the task doc is `STAGE_13_TBD.md`; name it via `start-task.sh 13 <slug>`). Still
owed: G-031 (CTO #1), G-001 (Stage 3 re-audit); G-059 (MCP-tool routing → 14); G-062 (formal indep review of Stage
12); G-067 (Langfuse-UI render, low); G-008/G-063/G-064 (agentic evals + ZT + MCP hardening → 14/17/20).

**Prior snapshot (2026-06-15, after Stage 12):** Stages 0–10, **10.5 (CTO #2)**, **11**, **11.5 (MCP servers)**, and
**12 (agent memory)** are **closed**. **Stage 12** built KB_14's memory layers: `audit_chain` (append-only,
SHA-256 hash-chained, DB immutability triggers, placeholder sig → real ML-DSA-65 at 13.5), `mem0_adapter`
(episodic/semantic on **Postgres + pgvector HNSW**, namespace-isolated, real sentence-transformers embeddings),
`graph_isa95` (idempotent Neo4j ISA-95 + PG mirror), `letta_adapter` (opt-in, flagged off). The Docker PG image was
swapped `postgres:15-alpine → pgvector/pgvector:pg15` on the SAME volume (data preserved). The runtime graph now
writes `audit_chain` per decision + recalls/remembers via Mem0 (verified run-2 recalls run-1). New deps:
`pgvector==0.3.6`, `sentence-transformers==5.5.1`. 13 memory tests; **full suite 221 passed / 2 skipped; audit 364**;
`verify-audit-chain.py` OK (29 rows). Independent review **caveated** (the fresh `task-auditor` agent hit the session
limit twice → dynamic implementing-session verification + adversarial code reads; formal different-agent pass owed,
**G-062**). An early ADR/KB G-059 over-claim was caught + corrected before close (Rule 1a). **The next executable task
is Stage 12.5 — observability/evidence pipeline** (OTel + Langfuse + Phoenix; traces show memory I/O); fold in G-004
(chaos), G-009/G-021 (observability), G-060 (pgaudit). Still owed: G-031 (CTO #1), G-001 (Stage 3 re-audit); G-059
(MCP-tool routing → Stage 14); G-051 (Stage-6 VERIFY → 7/17); G-055/G-056/G-057/G-058/G-061/G-062 (low/medium).

**Prior snapshot (2026-06-15, after Stage 11.5):** Stages 0–10, **10.5 (CTO #2)**, **11 (LangGraph runtime)**, and
**11.5 (MCP server suite)** are **closed**. **Stage 11.5** built five FastMCP servers (`backend/mcp_servers/`:
sim_world, kpi_query, decision_log, model_inference, policy_query — 14 tools) wrapping the real models / sim / KPI
math / Postgres `decisions` ledger with honest-unavailable; a multiprocess+watchdog supervisor (streamable-HTTP); and
a runtime mount via a thin in-house **stdio bridge** (`agents/runtime/mcp_mount.py::MCPToolMount`) — NOT
`langchain-mcp-adapters` (needs langchain-core>=1.0, off our frozen 0.3.28; deferred G-056). 22 conformance tests
(real stdio + a real Postgres round-trip + the 14-tool mount) + CI gate `mcp-conformance`; **full backend suite
208 passed / 2 skipped, audit 364**. Independent review PASS (DYNAMIC). Three stdio defects found+fixed by running
the real path (worker-thread import-lock deadlock → top-level warm imports; background-thread SimWorld → synchronous
`env.run`; minimal subprocess env → full env). New deps: `mcp==1.27.2`, `starlette==0.41.3` (cap for fastapi),
pydantic→2.13.4. **The next executable task is Stage 12 — agent memory** (Mem0/pgvector + Neo4j ISA-95 + audit_chain);
fold in G-059 (wire the MCP tools into a graph node so runtime decisions are MCP-mediated), G-005/G-021/G-022/G-023.
Still owed: G-031 (CTO #1), G-001 (Stage 3 re-audit); G-051 (Stage-6 no-op VERIFY) → Stage 7/17; G-055/G-056/G-057/G-058 (deps/integration, low).

**Prior snapshot (2026-06-15, after Stage 11):** Stages 0–10, **10.5 (CTO #2)**, and **11 (LangGraph runtime)** are **closed**. The
**Stages 6–10 DEPTH-HARDENING pass** (5/5 increments, 2026-06-14) is complete — measured, honest: **Stage 8**
Transformer RUL on real C-MAPSS (RMSE 13.80, beats CNN/LSTM) + learned causal discovery (PC, F1 0.75) +
neuro-symbolic plan verifier; **Stage 9** ResNet18 transfer learning 88.2%→99.3% on NEU-CLS; **Stage 7** SB3
MaskablePPO genuinely beats the best rule (−125.1 vs −137.4, CI [6.0,18.71]); **Stage 10** DiCE counterfactuals +
global SHAP; **Stage 6** the deepened loop wired end-to-end with a richer A/B (−182 min downtime, CI [93,274]).
**Stage 11** migrated coordination to a durable, deterministic **LangGraph `StateGraph`** (KB_25 self-healing loop),
**verified end-to-end against the real Docker stack** (Postgres durable checkpointer @5544 + Neo4j @7687 + Redis):
**full suite 186 passed / 1 skipped, audit 364**. Independent review PASS. The full-infra run discharged the G-049/G-050
**R-IND** caveat (shell-denied static reviews now re-run live) and surfaced + fixed two real production defects:
**G-053** (`ws_broker.stop()` deadlock → bounded `get_message` polling + time-boxed stop) and **G-054**
(`ExternalAPIClient` background-task leak). `.audit-baseline` = **364** (held throughout; depth + runtime increments
additive, Rule 1a audit-invisible de-mocks). New deps (free OSS): causal-learn, dice-ml, stable-baselines3,
sb3-contrib, gymnasium, langgraph(+checkpoint/-postgres), psycopg[binary], langfuse, pytest-timeout; pandas pinned
2.2.3. Research §16/§17. Hard Rules 1a + 11 + 11a + 11b in force. **The next executable task is Stage 11.5 — MCP
servers** (mount the Stage-4-10 models + runtime tools as MCP tool servers). Still owed: G-031 (CTO #1), G-001
(Stage 3 re-audit); G-051 (Stage-6 no-op VERIFY gate, partially paid by the runtime's binding verifier) → Stage 7/17;
G-055 (langgraph version-skew, low) → dependency-refresh.

Future stages (6.5 energy, 7 RL intervene, 8 world model + causal diagnose, 9 vision/defect, 10 explainability,
10.5 CTO #2, 11 production slice, 11.5 MCP servers, 12 memory, 12.5 observability, 13 CDC, 13.5 PQC foundations,
14 A2A, 14.5 CTO #3, 15 OT/IT bridge, 16 VDA 5050 + OpenRobOps/Open-RMF integration, 17 functional safety,
18 PQC Wave 2, 19 evidence pipeline, 20 red-team evals, 21 DR/HA, 21.5 CTO #4, 22 pilot, 23 conformity dry-run,
24 GA, 24.5 CTO #5, 25 post-GA) have task docs in `tasks/` — template-seeded bodies fill in when their turn
comes. Roadmap detail: PRD v3 §18.
