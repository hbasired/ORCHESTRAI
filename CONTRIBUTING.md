# Contributing

> If you are a future Claude session, the entry point you actually need
> is [`knowledge-base/KB_TASK_LOG.md`](knowledge-base/KB_TASK_LOG.md) (top
> entry = current reality) and [`tasks/`](tasks/) (executable next-step
> doc). Read those before this file. This file documents the *contract*;
> the task log documents the *state*.

This repository is built stage-by-stage on a hard rule: **the
theatrical-fallback count, measured by `scripts/audit.sh`, must
strictly decrease from one merged PR to the next.** That rule is the
spine of the project. Everything below is in service of it.

## The iterative cycle

Every stage runs the same loop:

1. Read `tasks/STAGE_NN_*.md` — pre-requisites + acceptance criteria.
2. Do the work. Code changes land alongside KB changes in the same PR.
3. `scripts/audit.sh` — must drop the count vs. `.audit-baseline`.
4. Every new weight file ships with `.metrics.json` + `.card.md`
   siblings (KB_02 versioning protocol).
5. Bump the KB files listed in the stage doc's "KB Updates Expected"
   block.
6. Append a `KB_TASK_LOG.md` entry: Shipped / Skipped / Learned / Next.
7. Any non-trivial decision becomes an ADR in
   `compliance/decision-logs/<date>_*.md`.
8. Write the *next* stage's task doc.
9. Open the PR — CI gate enforces every check.

See [`tasks/TASKS_README.md`](tasks/TASKS_README.md) for the full ASCII
flowchart.

## What gates the PR (CI)

`.github/workflows/ci.yml` runs:

| Job | Hard requirement |
|---|---|
| `audit` | `bash scripts/audit.sh` exit 0 — count not above `.audit-baseline`. |
| `kb-diff` | Any change under `backend/` or `frontend-nextjs/` is accompanied by a change under `knowledge-base/`. |
| `model-cards` | Every new `*.pt` / `*.onnx` / `*.pth` / `*.safetensors` has sibling `.metrics.json` + `.card.md`. |
| `gitleaks` | No new secrets in the diff; `.gitleaks.toml` allowlist covers known false positives. |
| `backend` | Python 3.11, pinned `requirements.txt`, `pytest -q` green. |
| `frontend` | Node 20 LTS, `npm ci`, `npm run build` green. |

A merged PR with a regressing audit count is treated the same as a
revert.

## Local setup (operator)

```bash
# 1. Tools — pin versions exactly:
#    - Python 3.11
#    - Node 20 LTS
#    - Docker Desktop (Compose v2)
#    - Git LFS (>= 3.5)
git lfs install --skip-smudge

# 2. Repo bootstrap
cp .env.example .env.local && $EDITOR .env.local
make up                       # docker compose; Alembic migration runs in init container
make migrate                  # alternative: run from host shell

# 3. Iterate
make test                     # pytest + jest
make audit                    # confirm count not regressed
```

If you don't have `make`, every target in the `Makefile` has the
underlying shell command spelled out — they're meant to be copy-paste
runnable.

## Code style

### Python (backend)

- Type-hint public functions. The codebase is gradually moving toward
  full coverage; new code should not regress this.
- Pydantic for boundaries (HTTP request/response, WebSocket envelopes,
  external API DTOs). No bare dicts at boundaries.
- Logging via `structlog`. No `print()` in committed code.
- Tests live in `backend/tests/`. Async fixtures via
  `pytest-asyncio`.
- New ML models follow the
  [KB_02 versioning protocol](knowledge-base/KB_02_Models_Inventory.md#update-protocol)
  — weights file + sibling `.metrics.json` + `.card.md`.

### TypeScript (frontend)

- Strict mode is on at the tsconfig level; `next.config.ts` currently
  suppresses build errors as a Stage-11 cleanup target. New code should
  not add to this debt.
- Functional components only. State via Zustand for cross-component
  state; component-local state is fine for the rest.
- Real network calls go through `frontend-nextjs/src/lib/api.ts`. Mock
  state generators are a transitional smell; replace at each frontend
  refactor stage.

## Branching + commits

- Branch from `main`. One stage = one PR (or a small chain of PRs).
- Commits in conventional-commit form: `feat(scope): ...`,
  `fix(scope): ...`, `chore(scope): ...`, `docs(scope): ...`.
- Squash on merge unless the chain genuinely tells a useful story.
- PR titles reference the stage:
  `feat(stage-2): SimPy simulator + incident table wiring`.

## Architecture decisions

Any decision worth disagreeing with in six months goes in
`compliance/decision-logs/<YYYY-MM-DD>_<short_slug>.md` as an ADR.
Cheap to write, expensive to skip. The Stage-1 ADR is the example to
follow.

## Secrets

- Never commit a real secret. `.gitleaks.toml` enforces this.
- All env vars enter via `.env.local` (git-ignored) → docker compose →
  process env. `.env.example` is the schema.
- Stage 14 plans the move to a managed secrets manager (Doppler /
  Vault / Cloud KMS). Until then, `docker/secrets/` is a placeholder.

## Compliance posture

This repo carries scaffolding for:

- **EU AI Act** (Aug 2026 high-risk system deadline) — see
  `compliance/risk-register.md`, `KB_10_Production_Hardening.md`,
  the `incidents` + `decision_logs` Postgres tables for Art. 12
  evidence.
- **NIST RMF Agentic Profile (Feb 2026)** — mapped in
  `compliance/risk-register.md`. Stage 11 addresses the named attack
  vectors before any external pilot.
- **GDPR** — currently low-risk (no PII in v1); revisited if a pilot
  involves operator face recognition or voice samples.

## Getting unstuck

Order of operations when something doesn't make sense:

1. Read the top entry of `KB_TASK_LOG.md`.
2. Read the matching `tasks/STAGE_NN_*.md`.
3. Read the relevant KB body file (KB_01 for architecture, KB_02 for
   models, etc.).
4. If still stuck, write a one-line entry in the next stage's "Risks /
   unknowns" block and bring it to the team instead of guessing.

Build this the way you would for a system that has to keep running
**after** you've left.
