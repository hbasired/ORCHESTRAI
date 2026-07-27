# tasks/ — Stage Task Documents

This folder holds the executable task document for each stage of the 25-stage roadmap (PRD v2.0 expansion, 2026-05-18). The original 15-stage plan in `yor-are-an-agentic-optimized-cookie.md` is preserved as the historical record; the v2 roadmap extends it. Exactly one task doc per stage: `STAGE_01_<slug>.md`, `STAGE_02_<slug>.md`, …, `STAGE_25_<slug>.md`, plus 5 CTO checkpoint docs (`STAGE_03_5_cto_checkpoint_1.md`, `STAGE_10_5_cto_checkpoint_2.md`, `STAGE_14_5_cto_checkpoint_3.md`, `STAGE_21_5_cto_checkpoint_4.md`, `STAGE_24_5_cto_checkpoint_5.md`).

## Lifecycle scripts (PRD v2.0)

Use these instead of running the cycle manually:

| Script | What it does |
|---|---|
| `bash scripts/start-task.sh <stage> <slug>` | Bootstraps a new task doc from `TASK_TEMPLATE.md`; emits context bundle; suggests role |
| `bash scripts/audit-task.sh <stage>` | Runs `scripts/audit.sh` + per-task gap report; writes `audits/STAGE_<NN>_audit.md` |
| `bash scripts/rectify-task.sh <stage>` | Lists open gaps as TODOs; loop back to implement |
| `bash scripts/seed-next-task.sh <stage>` | **(2026-05-31)** Seeds the NEXT stage's task doc at the END of THIS stage, **BEFORE** KB/.md updates. Run after rectify (zero gaps) + after authoring this stage's `## Hand-off` section. Idempotent (no-op if the doc exists). |
| `bash scripts/close-task.sh <stage> [--no-baseline-drop "reason"]` | Refuses if gaps open or KB_TASK_LOG missing entry; signs new ADRs; rewrites `.audit-baseline`; ensures next task doc exists (idempotent safety-net call to `next-task.sh`) |
| `bash scripts/next-task.sh [--from <stage>]` | Lower-level generator used by the two scripts above; can be run manually. Seeds the next stage's task doc with hand-off pre-filled; no-op if it already exists |
| `bash scripts/cto-review.sh` | Every 10 stages: spawns fresh Claude Code subprocess with `cto-reviewer` skill; writes `audits/CTO_<N>_review.md` |
| `bash scripts/generate-remediation-tasks.sh <map.json>` | Routes CTO future-task remediations into upcoming task docs as acceptance criteria |

## CTO checkpoint cadence

After every 10 task closures (stages 10, 20, 30, …) the `cto-reviewer` skill audits the whole system for critical gaps, vulnerabilities, missing implementations, cross-cutting risks. The output `audits/CTO_<N>_review.md` is paired with `audits/CTO_<N>_remediation_map.json` (machine-readable mapping of remediations to target stages). The next `agentic-governance-engineer` session addresses immediate gaps; future-task items are appended as acceptance criteria to upcoming task docs by `generate-remediation-tasks.sh`.

CTO checkpoint stages: 3.5, 10.5, 14.5, 21.5, 24.5 (these have dedicated task docs, but the actual review is triggered by the script).

## Templates

- `tasks/TASK_TEMPLATE.md` — canonical task doc shape (status, pre-reqs, acceptance criteria, files to create/modify/delete, KB updates, verification commands, audit target, role, risks, hand-off).
- `tasks/AUDIT_TEMPLATE.md` — per-task audit report shape (mirrored in `audits/TASK_TEMPLATE_audit.md`).
- `tasks/CTO_REVIEW_TEMPLATE.md` — CTO checkpoint review shape (mirrored in `audits/CTO_TEMPLATE_review.md`).

## The iterative cycle (every stage runs this loop)

```
                ┌─────────────────────────────┐
                │  read tasks/STAGE_NN_*.md   │
                │  for pre-reqs + acceptance  │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  do the stage work          │
                │  (code + KB updates)        │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  run scripts/audit.sh       │
                │  fakery count MUST decrease │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  metrics capture            │
                │  every new weight has       │
                │  .pt + .metrics.json + .card.md│
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  seed next stage task doc   │
                │  scripts/seed-next-task.sh  │
                │  BEFORE KB/.md updates      │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  KB update                  │
                │  bump every KB file listed  │
                │  in stage's KB-updates block│
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  task log append            │
                │  KB_TASK_LOG.md entry:      │
                │  Shipped/Skipped/Learned/Next│
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  decision log               │
                │  any ADR → compliance/      │
                │  decision-logs/YYYY-MM-DD_*│
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  CI gate                    │
                │  merge ONLY if audit green  │
                │  + KB diff present          │
                │  + model-cards for weights  │
                │  + gitleaks clean           │
                └─────────────────────────────┘
```

## Task doc template (every file in this folder follows it)

```markdown
# Task: Stage N — <name>
Status: not-started | in-progress | blocked | done
KB files this stage updates: [list of KB_NN file names]
Pre-requisites: [list of prior-stage outputs this stage needs]

## Acceptance criteria
- <bulleted, testable criterion 1>
- <bulleted, testable criterion 2>
- ...

## Files to CREATE
- <path/to/file> — <one-line purpose>
- ...

## Files to MODIFY
- <path/to/file> — <one-line description of the change>
- ...

## Files to DELETE
- <path/to/file or folder> — <why>
- ...

## Verification commands
```
<exact shell commands the operator runs to confirm the acceptance criteria>
```

## KB updates expected
- KB_NN: <what gets written here>
- ...

## Risks / unknowns
- <one per line>
- ...
```

## Status discipline

- `not-started` — task doc exists; no PRs opened.
- `in-progress` — at least one PR open; merge gate not yet green.
- `blocked` — external dependency, prior-stage handoff missing, or open question; details in the doc.
- `done` — all acceptance criteria satisfied; KB updates merged; `KB_TASK_LOG.md` entry written; baseline locked via `scripts/audit.sh --baseline`.

Only one stage is in-progress at a time. Subsequent stages wait until the prior stage is `done`.

## How a future Claude session picks up the project

1. Read `knowledge-base/KB_TASK_LOG.md` top entry — what just shipped.
2. Read `tasks/STAGE_NN_*.md` for the next-in-line stage.
3. Read every KB file listed in that stage's "KB Updates Expected" block.
4. Run `scripts/audit.sh` to confirm the current baseline.
5. Execute.

This loop is how the build stays aligned across sessions, weeks, and engineers.
