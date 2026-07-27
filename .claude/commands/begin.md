---
description: Project session init macro. Loads full context (KB_TASK_LOG, current task doc, role SKILL.md, latest audit + ADR), determines stage state, and prints explicit next-step recommendation. Use this at the start of every Claude Code session for this project.
argument-hint: "[--auto-route]"
allowed-tools: Bash(bash scripts/init.sh*), Bash(python scripts/load-context.py*), Read, Glob, Grep
---

# `/begin` — Industrial Agent Control Plane session init

> **Naming note:** Claude Code has a built-in `/init` slash command that *initializes a CLAUDE.md file* by analyzing the codebase. This project already has a hand-authored, production-grade [CLAUDE.md](../../CLAUDE.md), so the built-in `/init` is not what we want here. `/begin` is this project's session init macro — it loads context, determines stage state, and routes to the right next action.

## What `/begin` does

1. Runs pre-flight checks (python, git, CLAUDE.md, `.audit-baseline`, context loader script).
2. Emits the full context bundle:
   - Project identity
   - `.audit-baseline` value
   - Top entry of `knowledge-base/KB_TASK_LOG.md` (newest at bottom)
   - **STATE & DO THIS NEXT** section (the most important — state ∈ {no-task / not-started / in-progress / has-open-gaps / audit-clean-ready-to-close / done-needs-next-task})
   - Full current task doc
   - Suggested role + full `.claude/skills/<role>/SKILL.md`
   - KB files the task doc says it updates (head excerpts)
   - Latest audit report (full if for current stage)
   - Latest ADR (full)
   - CTO remediation items targeting this stage
   - Closing reminders
3. Prints the explicit next-step recommendation.

## How to use

```
/begin
```

Or, to also auto-route unambiguous states (e.g., seed the next task doc if the current is closed):

```
/begin --auto-route
```

## What you should do after `/begin` finishes

The bundle ends with a **"Do this next"** section. Follow it. Specifically:

1. **Read CLAUDE.md** if you have not already this session (it auto-loads, but read it consciously the first time).
2. **Read the suggested role's full SKILL.md** (printed in the bundle). Adopt that persona for this task.
3. **Read the full current task doc** (printed in the bundle).
4. **Open the KB files** the task doc lists (the bundle shows head excerpts; use `Read` for full content where you need it).
5. **Verify pre-requisites** named in the task doc are met (prior stages closed; required services running; baseline known).
6. **Begin implementation** under the role persona. Follow the role's Mission / Success criteria / Forbidden behaviors / Output contract / Tool preferences exactly.
7. **At any web-search / research moment**, immediately append a new dated section to `research/initial-research.md` (per `feedback_production_grade_no_shortcuts` rule — research is canonical, lose it and you lose the rationale).
8. **At any architectural decision moment**, write a new ADR at `compliance/decision-logs/YYYY-MM-DD_<slug>.md` (append-only — never edit existing).
9. **When ready to validate**: `bash scripts/audit-task.sh <stage>` writes the audit report.
10. **If gaps open**: `bash scripts/rectify-task.sh <stage>` lists them. Fix; re-audit; repeat.
11. **When clean**: append `KB_TASK_LOG.md` entry (Shipped / Skipped / Learned / Next-stage adjustments). Then `bash scripts/close-task.sh <stage>` — signs ADRs (Stage 13.5+), rewrites `.audit-baseline`, marks task `done`, seeds next stage's task doc via `scripts/next-task.sh`.
12. **Every 10 closures**: a CTO checkpoint task doc fires. Run `bash scripts/cto-review.sh` (spawns fresh Claude Code subprocess with `cto-reviewer` skill).

## Execute now

!bash scripts/init.sh $ARGUMENTS

## After the bundle

Based on the **State & Do This Next** section above:
- If state is `not-started` or `in-progress`: adopt the suggested role persona and proceed with implementation per the task doc.
- If state is `has-open-gaps`: do not start new work; fix the gaps first.
- If state is `audit-clean-ready-to-close`: do not start new work; append the `KB_TASK_LOG.md` entry, then close.
- If state is `done-needs-next-task` or `no-task`: run `bash scripts/next-task.sh` (or pass `--auto-route` to `/begin` to do this automatically).

Do not ask the user "what would you like to do?" — the State section tells you. Follow it.
