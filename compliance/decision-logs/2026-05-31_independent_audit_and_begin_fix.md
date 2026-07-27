# ADR — Independent per-stage audit (separate agent) + /begin state-detection fix (2026-05-31)

**Status**: accepted
**Stage**: cross-cutting (process/governance)
**Author**: agentic-governance-engineer persona (Claude session, 2026-05-31); operator-directed
**Related task doc**: n/a (process change) — applied alongside Stage 3 work
**KB updates**: CLAUDE.md §3/§5/§6, SKILLS.md, scripts/audit-task.sh; new `.claude/skills/task-auditor/SKILL.md`, `scripts/independent-audit.sh`

---

## D1 — Independent audit by a DIFFERENT agent at every code-touching stage

**Context.** The operator observed that the same agent which builds a stage should not audit it: a builder
has an incentive (conscious or not) to rubber-stamp, bypass, or fake its own audit. The existing controls
were `scripts/audit-task.sh` (mechanical: counts fakery patterns + missing artefacts) and the every-10-stages
`cto-reviewer` (whole-system). Neither provides per-stage *independent* verification by a separate agent.

**Decision.** Introduce a read-only `task-auditor` persona and `scripts/independent-audit.sh <stage>`:
- `task-auditor` (`.claude/skills/task-auditor/SKILL.md`) is a fresh agent that did NOT build the stage. It
  re-runs the stage's tests/verification commands itself, reads the new/modified code adversarially for
  theatre/bypass/faked tests, checks every acceptance criterion against real evidence, and writes
  `audits/STAGE_<NN>_independent_review.md` with a PASS / PASS-WITH-GAPS / FAIL verdict. It edits nothing else.
- `independent-audit.sh` runs the mechanical `audit-task.sh` (phase 1) then spawns a FRESH `claude` subprocess
  with the `task-auditor` skill (phase 2) — mirroring `cto-review.sh`. If the `claude` CLI is unavailable, it
  prints a manual fallback (open a fresh session / spawn a separate subagent via the Agent tool).
- CLAUDE.md §5 (lifecycle) inserts the independent-audit step after `rectify-task.sh`; §6 makes it an
  invariant ("every code-touching stage gets an independent audit by a different agent before close; a PASS is
  required"); §3 adds the `task-auditor` row; `audit-task.sh` prints a banner mandating it; SKILLS.md indexes it.

**Why.** Separation of duties. The mechanical count gate is necessary but not sufficient — a passing
`audit.sh` count says "no known fakery patterns," not "the acceptance criteria are genuinely met." An
independent agent with no authorship and fresh context is far more likely to catch a self-serving pass.

**Consequences.** Each stage close now has three gates: mechanical audit (count), independent review (PASS),
and the closure ritual. Slightly more process per stage; the payoff is trustworthy evidence (also strengthens
the EU AI Act Art. 12 / ISO 42001 audit trail). The independent review is distinct from — and complementary
to — the every-10-stages CTO checkpoint.

**How demonstrated this session.** A separate auditor agent (fresh context, did not build the broker) was
spawned to review the Stage 3 WebSocket-broker work; its findings are recorded in
`audits/STAGE_03_independent_review.md`.

## D2 — `/begin` state-detection fix (numeric stage ordering)

**Context.** `/begin` (via `.claude/hooks/lib/context_loader.py::find_current_task`) reported the next task as
the not-started Stage 3.5 CTO checkpoint while Stage 3 was in-progress. Root cause: it sorted task docs by
filename string, and `STAGE_03_5_cto...` sorts before `STAGE_03_ws_broker...` because `'5' < 'w'` — so a
not-started half-stage was picked ahead of the in-progress whole-stage.

**Decision.** Sort candidates by the parsed NUMERIC stage value (`_stage_sort_key`: `03`→3.0, `03_5`→3.5) so
3.0 precedes 3.5 and an in-progress task always takes precedence over a higher-numbered not-started one.

**Why.** `/begin` must reflect the truth — the active in-progress task — or it sends the next session to the
wrong stage. Verified post-fix: `/begin` now reports `State: in-progress | Stage: 03`.

**Consequences.** `find_current_task` is correct for all whole/half-stage combinations. (The bash
`highest_closed_stage` fallback in `next-task.sh` retains a string sort; it is only used when `--from` is
absent, which the closure path always supplies — flagged for a future cleanup, not blocking.)

## Risk register references
- Strengthens mitigation of "theatre-shipped stage" risk (independent verification before close).
- No new high-risk surface introduced.


<!-- ML-DSA-65 SIGNATURE FOOTER (do not edit by hand; managed by scripts/sign-decision-log.py) -->
<!-- algorithm: ML-DSA-65 -->
<!-- key_id:    agent-identity:v1 -->
<!-- signed_at: 2026-06-19T14:36:03+00:00 -->
<!-- signature: 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 -->
