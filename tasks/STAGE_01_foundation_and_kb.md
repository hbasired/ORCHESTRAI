# Task: Stage 1 — Foundation Hardening & Knowledge Base Bootstrap

**Status**: done (closed 2026-05-11; see `knowledge-base/KB_TASK_LOG.md` Stage 1 entry and `compliance/decision-logs/2026-05-11_stage_01_close.md` for deferrals)
**KB files this stage updates**: KB_01, KB_02, KB_03, KB_04, KB_10, KB_TASK_LOG
**Pre-requisites**:
- Stage 0 refresh complete (this stage cannot start until `KB_TASK_LOG.md` has the 2026-05-11 Stage-0 entry — already present).
- Docker Desktop running on the operator's machine.
- Python 3.11 and Node 20 LTS installed locally.
- Groq + Gemini API keys in the operator's password manager (not yet in repo).
- Existing `knowledge-base/`, `compliance/`, `scripts/audit.sh` artifacts present (created Stage 0 — confirm via `ls`).

## Goal of this stage

Replace every piece of repo-level theatrics that we can fix *before* training any model, so subsequent stages (which add real models) land on a foundation that doesn't lie about its own state. Concretely: real migration framework, real secrets handling, real CI, real test harness, real LFS for weights, real datasets-as-DVC, and the audit script locked in as a baseline.

**No new ML training happens in this stage.** That's Stage 4 onward.

## Acceptance criteria

Each is independently testable.

- [ ] `docker compose -f docker/docker-compose.yml config` validates without errors. Hardcoded passwords (`aiagent2026` etc.) are gone; every credential references `${VAR_NAME}` from `.env.local`.
- [ ] `docker compose up -d` brings all services healthy; **Alembic auto-applies migration `0001_init` on supabase-postgres on first boot**. (The Supabase compose template is added; if it proves unstable, fallback is plain Postgres + Realtime container — documented in the risk register.)
- [ ] `cd backend && alembic current` reports `0001_init (head)`.
- [ ] `cd backend && pytest -q` passes — at minimum `test_health.py` and `test_websocket_smoke.py` green.
- [ ] `cd frontend-nextjs && npm test -- --watchAll=false` passes the smoke test (`__tests__/smoke.test.tsx` mounts the app shell under Zustand mock).
- [ ] Running `bash scripts/audit.sh` from the repo root reports a **lower** total than the Stage-0 baseline (the Stage-0 baseline is established by running `bash scripts/audit.sh --baseline` once at the start of Stage 1 to capture pre-Stage-1 state). The reduction comes from deleting hardcoded demo dictionaries in `backend/api/metrics_routes.py` and the hardcoded MODELS array in `frontend-nextjs/src/app/model-metrics/page.tsx`.
- [ ] `.gitattributes` tracks `*.pt`, `*.pth`, `*.h5`, `*.onnx`, `*.pkl`, `*.joblib`, `*.safetensors` via LFS; verified by `git check-attr -a backend/yolov8n.pt | grep filter=lfs`.
- [ ] CI workflow `.github/workflows/ci.yml` runs on PR; blocks merge on red lint / red tests / failing audit / gitleaks hit.
- [ ] `gitleaks detect --source . --no-banner` exits 0 (no secrets in tree or recent history; baseline file allowed if pre-stage scan reveals existing false positives).
- [ ] `frontend/` (Vite, legacy) directory is removed; git history preserves it.
- [ ] `.env.example` exists at repo root with every required variable documented; `docker/secrets/.gitkeep` placeholder; `.env.local` is git-ignored.
- [ ] Hardcoded fakery deleted: `backend/api/metrics_routes.py:192-310` and `:313-343` are gone; endpoints return `503 Service Unavailable` with a clear body until Stage 4 ships real metrics. `backend/data/supabase_service.py:78-149` schema-in-comments header is gone; the file references Alembic migrations.
- [ ] All 13 KB files exist (already created in Stage 0); the `Last-updated` frontmatter on at least KB_01, KB_02, KB_03, KB_04, KB_10 is bumped to the Stage-1 close date; `KB_TASK_LOG.md` has a new Stage-1 entry per the closure ritual.
- [ ] `README.md` is updated: the marketing claim "SYSTEM IS CURRENTLY RUNNING ✅" is replaced with an audit-truthful status that points to KB_01 for the real architecture.

## Files to CREATE

| Path | Purpose |
|---|---|
| `.gitattributes` | Git LFS rules: `*.pt`, `*.pth`, `*.h5`, `*.onnx`, `*.pkl`, `*.joblib`, `*.safetensors filter=lfs diff=lfs merge=lfs -text` |
| `.env.example` | Every var the compose file references, with `REPLACE_ME` stubs and inline doc comments |
| `docker/secrets/.gitkeep` | placeholder; secrets manager integration in Stage 14 |
| `backend/alembic.ini` | Alembic config; SQLAlchemy URL pulled from env |
| `backend/alembic/env.py` | Alembic env: imports model metadata, autogenerates against the DB URL |
| `backend/alembic/script.py.mako` | Default Alembic template |
| `backend/alembic/versions/0001_init.py` | First migration: recreates current `database/schema.sql` tables + adds new `incidents` and `decision_logs` tables (per `KB_04_Data_Schema.md`) |
| `backend/tests/__init__.py` | empty |
| `backend/tests/conftest.py` | pytest fixtures: app client, mock LLM, sample state |
| `backend/tests/test_health.py` | GET `/health` returns 200 + expected JSON shape |
| `backend/tests/test_websocket_smoke.py` | WS connect, send ping, receive `state_snapshot` envelope, assert envelope shape per KB_04 |
| `frontend-nextjs/__tests__/smoke.test.tsx` | Mount app shell with Zustand mock provider; assert dashboard renders without crash |
| `frontend-nextjs/playwright.config.ts` | Playwright config; one smoke test that loads `/` |
| `frontend-nextjs/e2e/dashboard.spec.ts` | Playwright spec: loads `/`, asserts KPI cards render |
| `backend/training/.gitkeep` | placeholder; Stage 4+ adds Colab notebooks here |
| `data/datasets/.gitkeep` | placeholder for DVC-tracked datasets |
| `data/datasets/CARD.template.md` | Template every dataset CARD.md follows (per KB_03 versioning protocol) |
| `dvc.yaml`, `.dvc/config` | DVC initialization; local remote for now |
| `.github/workflows/ci.yml` | CI workflow: lint, types, tests, audit, gitleaks, Docker build, KB-diff check |
| `.github/workflows/scripts/check-kb-diff.sh` | Script that asserts any PR touching `backend/` or `frontend-nextjs/` also touches `knowledge-base/` |
| `.github/workflows/scripts/check-model-cards.sh` | Script that asserts any new `*.pt`/`*.onnx` has sibling `*.metrics.json` + `*.card.md` |
| `.gitleaks.toml` | gitleaks config + allowlist (if needed for known false positives) |

## Files to MODIFY

| Path | Change |
|---|---|
| `docker/docker-compose.yml` | Add Supabase services (`supabase-postgres`, `supabase-realtime`, `supabase-studio`, `supabase-meta`, `supabase-rest`); remove plain `postgres`; replace every hardcoded password with `${VAR}`; set Postgres `wal_level=logical` for Stage 13's CDC. Add Alembic init container or entrypoint hook that runs `alembic upgrade head` on backend startup. **Pin Next 15.x LTS / React 18.3 / Tailwind 3 LTS in the frontend build image if the compose builds the frontend (otherwise just document the pin in `frontend-nextjs/package.json`).** |
| `backend/api/metrics_routes.py` | **Delete lines 192–310 (`_get_demo_metrics` helper) and lines 313–343 (`_get_demo_system_metrics` helper)**. Both endpoints (`/api/metrics/models`, `/api/metrics/system`) return `HTTPException(status_code=503, detail="Real model metrics not yet available. See KB_02_Models_Inventory.md for status.")` |
| `backend/data/supabase_service.py` | Delete lines 78–149 (the schema-in-SQL-comments). Replace with a one-line comment pointing to `backend/alembic/versions/0001_init.py` as the schema source of truth. |
| `backend/requirements.txt` | Pin every dep with `==`. Add: `alembic==1.13.*`, `dvc[s3]==3.*`, `pytest==8.*`, `pytest-asyncio==0.23.*`, `httpx==0.27.*`. Confirm `uvloop` is present and pinned. |
| `frontend-nextjs/package.json` | Downgrade: `next` → `^15.0.0`, `react` → `18.3.x`, `react-dom` → `18.3.x`, `tailwindcss` → `^3.4.x` (and update `postcss.config.js` / `tailwind.config.js` for v3 syntax). Lock with `npm install` regenerating `package-lock.json`. **Verify all 8 pages still render after downgrade** (manual + Playwright smoke). |
| `README.md` | Replace "SYSTEM IS CURRENTLY RUNNING ✅" / "FULLY OPERATIONAL" claims with an audit-truthful status section that points to `knowledge-base/KB_01_System_Architecture.md`. Keep the quick-start commands. |
| `PROJECT_STATUS.md` | Similar honesty pass; mark explicitly which models are still untrained (cross-link `KB_02_Models_Inventory.md`). |

## Files to DELETE

| Path | Why |
|---|---|
| `frontend/` (entire Vite directory) | Abandoned in favor of `frontend-nextjs/`; git history preserves it. Decision confirmed in original plan. |

## Verification commands

Run from repo root:

```bash
# 1. Lock the Stage-0 baseline BEFORE any Stage-1 work begins:
bash scripts/audit.sh --baseline

# 2. After Stage 1 work:
docker compose -f docker/docker-compose.yml config
docker compose up -d
docker compose ps                     # all services healthy
cd backend && alembic current         # 0001_init (head)
cd backend && pytest -q               # green
cd ../frontend-nextjs && npm test -- --watchAll=false  # green
cd ../frontend-nextjs && npx playwright test e2e/dashboard.spec.ts  # green
cd ..
bash scripts/audit.sh                 # must report TOTAL < Stage-0 baseline
gitleaks detect --source . --no-banner  # exit 0
git check-attr -a backend/yolov8n.pt | grep filter=lfs  # confirms LFS tracking
test ! -d frontend/                   # Vite frontend deleted
```

## KB updates expected (filled out at stage close)

- `KB_01_System_Architecture.md` — replace pre-Stage-1 "current state" with the new post-Supabase / post-Alembic / post-secret-sweep state; update the Mermaid diagram to include the Supabase services; bump `Last-updated`.
- `KB_02_Models_Inventory.md` — bump `Last-updated`; confirm "untrained" status for every model (no models trained in Stage 1).
- `KB_03_Datasets_Catalog.md` — bump `Last-updated`; document the DVC commands actually used (real, not template); set "Status" of every dataset to whatever state Stage 1 reaches (likely still "not-downloaded").
- `KB_04_Data_Schema.md` — add the actual SQL DDL from `0001_init.py` to the body; confirm the `incidents` and `decision_logs` tables are present.
- `KB_10_Production_Hardening.md` — bump `Last-updated`; add a one-line note that secrets policy + CI gate + LFS rules + audit baseline are in effect as of this stage.
- `KB_TASK_LOG.md` — new entry with the date Stage 1 closed: Shipped / Skipped / Learned / Next-stage adjustments. The "Next-stage adjustments" line writes the input for `tasks/STAGE_02_simpy_simulator.md`.

## Closure ritual (run before declaring Stage 1 done)

1. `bash scripts/audit.sh` — confirm baseline regression check is green (count strictly less than the locked baseline).
2. `bash scripts/audit.sh --baseline` — overwrite the baseline with the new lower number so Stage 2 has a higher bar.
3. Bump KB files listed above.
4. Append `KB_TASK_LOG.md` Stage-1 entry.
5. Write `compliance/decision-logs/<date>_stage_01_close.md` ADR for any non-trivial architectural decisions made (e.g. "Supabase compose template proved unstable, fell back to plain Postgres + standalone Realtime").
6. Write `tasks/STAGE_02_simpy_simulator.md` using the template in `tasks/TASKS_README.md`. Pre-requisites reference Stage-1 KB updates.
7. Open the PR. CI gate enforces every check above.

## Risks / unknowns

- **Self-hosted Supabase compose template instability**: the Supabase stack has multiple moving parts (Realtime, Studio, Meta, REST). If the official `docker-compose.yml` from the Supabase repo doesn't behave on Windows + Docker Desktop, **fallback is plain Postgres 15 with `wal_level=logical` + standalone Realtime container**. Document the fallback in `compliance/decision-logs/` and the risk-register.
- **Cutting-edge frontend stack regressions on LTS downgrade**: Next 16 / React 19 / Tailwind 4 → Next 15 / React 18.3 / Tailwind 3 might break Framer Motion 12.31, R3F 9.5, or other deps. Mitigation: branch and test before merging; if a critical dep is incompatible, document the exception and roll back the pin for that dep only.
- **gitleaks false positives on the existing repo**: the repo has older docs that may reference fake/placeholder credentials. Mitigation: run pre-stage scan, build `.gitleaks.toml` allowlist for known false positives, only fail CI on new hits.
- **Alembic autogeneration vs hand-written 0001_init**: I'm proposing a hand-written first migration because `database/schema.sql` is the source today and we want exact reproduction plus new tables. Alembic's autogenerate is brittle for an initial migration.
- **`frontend/` (Vite) deletion may break something we haven't traced**: confirm via `grep -r "frontend/" --include="*.{md,yml,json,toml,sh}"` that no script / CI / doc references the Vite folder before deleting.

## Hand-off to Stage 2

When Stage 1 closes, Stage 2 (SimPy simulator) starts with:
- A real DB it can write events to (Alembic-applied schema with `incidents` + `decision_logs` tables).
- A real CI that will reject Stage-2 PRs unless `KB_05_Simulation_Spec.md` is updated and the audit count drops further.
- LTS-pinned frontend so the demo UI doesn't break under simulator output changes.
- DVC ready so Stage 4's first dataset upload isn't blocked on tooling.
- The audit baseline reset to a lower number; Stage 2 must drop it further (e.g. by replacing `random.random()` injection at `backend/simulation/engine.py:268-300` with real SimPy events).
