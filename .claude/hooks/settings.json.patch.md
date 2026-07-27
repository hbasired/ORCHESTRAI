# Hook registration patch for `.claude/settings.json`

> Plan-mode restriction: this expansion session does NOT modify `.claude/settings.local.json` (the existing project allowlist) or create `.claude/settings.json`. Apply this patch yourself once.

## How to apply

1. Create or open `.claude/settings.json` (project-scoped, not `settings.local.json`).
2. Merge the `hooks` block below into the existing JSON (or paste as-is if the file is empty).
3. Save. Claude Code picks up changes on the next session.

## The patch

> **SCHEMA NOTE (corrected 2026-06-22).** Current Claude Code requires each hook-event entry to wrap its command in a
> nested `"hooks": [ { "type": "command", "command": "..." } ]` array (optionally with a sibling `"matcher"`). The older
> flat `{ "command": ..., "description": ... }` form makes the loader reject the whole file with *"Expected array, but
> received undefined. Permission rules and other settings from this file are not in effect."* — use the form below. (The
> per-hook purpose, formerly in `description`, is documented in this file's comments + CLAUDE.md §9, not in the JSON.)

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "bash .claude/hooks/session_start.sh" } ] }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "bash .claude/hooks/user_prompt_submit.sh" } ] }
    ],
    "PreToolUse": [
      { "matcher": "Write|Edit|MultiEdit", "hooks": [ { "type": "command", "command": "bash .claude/hooks/pre_tool_use.sh" } ] },
      { "matcher": "WebSearch|WebFetch",  "hooks": [ { "type": "command", "command": "bash .claude/hooks/pre_web_search.sh" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Write|Edit|MultiEdit", "hooks": [ { "type": "command", "command": "bash .claude/hooks/post_tool_use_write.sh" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "bash .claude/hooks/stop.sh" } ] }
    ]
  }
}
```

Hook purposes: `session_start` loads the context bundle; `user_prompt_submit` re-injects the current task doc + lifecycle
hints; `pre_tool_use` blocks edits to finalized ADRs / `.audit-baseline` outside closure / frozen PRDs + warns on
`random.*` in backend & classical crypto in PQC paths; `pre_web_search` marks web-search-used so `stop` can warn if
`research/initial-research.md` wasn't appended; `post_tool_use_write` emits KB-update reminders + marks needs-audit;
`stop` warns on missing audit / KB_TASK_LOG entry / research append + runs the audit-chain quick-verify.

## What the hooks expect

- `bash` available on PATH (Git Bash on Windows, native bash on Linux/macOS).
- `python` (3.11+) on PATH.
- Working directory at Claude session start = repo root (Claude Code default).

## Verification (after applying)

1. Restart Claude Code in this repo.
2. You should see the SessionStart bundle in context: top of `KB_TASK_LOG.md`, current task doc, latest audit + ADR, suggested role, audit-baseline value.
3. Try to `Edit` a finalized decision log (e.g., `compliance/decision-logs/2026-05-11_stage_01_close.md`) — the PreToolUse hook should block with the "append-only" message.
4. Write a fresh file under `backend/services/foo.py`. The PostToolUse hook should print a KB reminder pointing at `KB_01_System_Architecture.md`.
5. Without running `bash scripts/audit-task.sh`, end the session. The Stop hook should warn that audit wasn't run.

## Hook env-var conventions

Hooks read from these environment variables Claude Code populates:
- `CLAUDE_USER_PROMPT` (UserPromptSubmit) — the user's submitted prompt text.
- `CLAUDE_TOOL_INPUT` (PreToolUse / PostToolUse) — JSON of the tool's input parameters.
- `CLAUDE_TOOL_FILE_PATH` (PreToolUse / PostToolUse, when present) — convenience: the target file path.
- `CLAUDE_HOOK_AUDIT_BASELINE_ALLOWED` — set by `scripts/close-task.sh` to allow `.audit-baseline` writes for one operation.

If Claude Code env-var names differ in your version, the hooks degrade gracefully (exit 0 = allow / nothing-to-do).
