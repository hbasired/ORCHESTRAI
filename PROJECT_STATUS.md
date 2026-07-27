# AI Embodied Agent Platform — Current Status

> **PRD repositioning (2026-05-18):** v2.0 lives at
> [`PRD-ai-embodied-agent-v2.md`](PRD-ai-embodied-agent-v2.md). The 15-stage
> roadmap from v1 has been extended to **25 stages** with CTO checkpoints every
> 10 task closures. Stage 2 (SimPy DES) is unchanged and remains the next
> executable stage. New stages cover: LangGraph + MCP + agent memory +
> observability (pulled forward to Stages 11–12.5), PQC foundations + Wave 2,
> A2A protocol surface, OT/IT bridge (OPC UA + Sparkplug B + ISA-95), VDA 5050
> robot fleet adapter, functional-safety wrapper, governance evidence pipeline,
> red-team eval harness, conformity dry-run, post-GA crypto-rotation drill.
>
> Repositioning ADR: [`compliance/decision-logs/2026-05-18_prd_v2_repositioning.md`](compliance/decision-logs/2026-05-18_prd_v2_repositioning.md).
>
> Claude Code sessions: start at [`CLAUDE.md`](CLAUDE.md); the SessionStart hook
> loads the KB index, the next task doc, the last audit, the last decision log,
> and the suggested role persona.

> This file used to say "FULLY OPERATIONAL ✅". As of **Stage 1 (2026-05-11)**
> the truth is more limited: the FastAPI app boots, the Next.js frontend
> renders all 8 pages, and the WebSocket loop functions — but the data
> flowing through the system is largely theatrical and most ML models are
> untrained. The 25-stage roadmap in [`PRD-ai-embodied-agent-v2.md`](PRD-ai-embodied-agent-v2.md)
> §10 exists to close that gap (extends the original 15-stage plan in
> [`yor-are-an-agentic-optimized-cookie.md`](yor-are-an-agentic-optimized-cookie.md)).
>
> For the per-component picture, the source of truth is the
> [`knowledge-base/`](knowledge-base/) folder. Read
> [`KB_01_System_Architecture.md`](knowledge-base/KB_01_System_Architecture.md)
> for "what runs now," [`KB_02_Models_Inventory.md`](knowledge-base/KB_02_Models_Inventory.md)
> for "which models are trained," and [`KB_TASK_LOG.md`](knowledge-base/KB_TASK_LOG.md)
> for stage-by-stage history.

## What is real (Stage 1 baseline)

| Component | State |
|---|---|
| FastAPI app + WebSocket loop (`backend/main.py`) | Real. Boots; broadcasts at 5–10 Hz. |
| Embodied agent coordinator (`backend/agents/`) | Real coordination logic. |
| LLM client (Groq / Gemini / Ollama) | Real, multi-provider. |
| YOLOv8 vision (`backend/ml/vision_model.py` + `yolov8n.pt`) | Real pretrained weights. |
| Whisper STT / Piper TTS | Real when packages installed; graceful fallback otherwise. |
| Postgres schema | Owned by Alembic `0001_init` from Stage 1 onward. |
| Docker compose stack | Env-var swept; runs Neo4j + Redis + Postgres + Mosquitto + backend + simulation. |
| CI gate | `audit.sh` regression gate + KB-diff + gitleaks + model-card check. |

## What is theatrical (will be replaced)

| Component | Where | Replaced by stage |
|---|---|---|
| ANN demand predictor | `backend/ml/neural_networks.py:114-124` | Stage 6 (M5 forecasting) |
| ANN energy predictor | `backend/ml/neural_networks.py:175-176` | Stage 6 |
| CNN defect detector | `backend/ml/neural_networks.py:289-307` | Stage 5 (NEU-DET + Real-IAD) |
| CNN obstacle detector | `backend/ml/neural_networks.py:381-388` | Stage 9 |
| LSTM world model | `backend/ml/world_model.py:216-247` | Stage 8 |
| PPO RL policy | `backend/ml/rl_policy.py:267-335` | Stage 7 (Isaac Sim) |
| SHAP explainer | `backend/ml/explainability.py:73-147` | Stage 10 |
| Frontend mock-state generators | `frontend-nextjs/src/lib/api.ts` | Stages 4–10 incrementally |
| `/voice` page (RESPONSES dict) | `frontend-nextjs/src/app/voice/page.tsx` | Stage 11 (real STT-LLM-TTS) |
| `/knowledge-graph` static nodes | `frontend-nextjs/src/app/knowledge-graph/page.tsx` | Stage 11 |

`scripts/audit.sh` enforces that this list only shrinks from one stage to
the next. Stage-0 baseline: **441 theatrical occurrences**; Stage-1 close:
**439** (locked in `.audit-baseline`).

## What was removed in Stage 1

- Hardcoded passwords in `docker/docker-compose.yml` (now `${VAR}`).
- `_get_demo_metrics` / `_get_demo_embodied_metrics` helpers in
  `backend/api/metrics_routes.py`. Both endpoints now return HTTP 503
  with an explanatory body until Stage 4.
- `_ensure_schema` SQL-in-comments header in
  `backend/data/supabase_service.py`. Schema is now Alembic-owned.

## How to launch (dev)

1. Copy `.env.example` → `.env.local`, fill in real values for Postgres,
   Neo4j, Groq, Gemini.
2. From the repo root: `docker compose -f docker/docker-compose.yml up -d`.
   The `migrate` init container runs `alembic upgrade head` before the
   backend starts.
3. Backend at <http://localhost:8000>, frontend at <http://localhost:3000>.

For local-only (no compose):

```bash
# Backend
cd backend && python -m venv venv && venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# Frontend
cd frontend-nextjs && npm install && npm run dev
```

## How to verify Stage 1

Run from the repo root:

```bash
bash scripts/audit.sh                          # TOTAL must be < 441
docker compose -f docker/docker-compose.yml config   # validates env vars
cd backend && alembic current                  # 0001_init (head)
cd backend && pytest -q                        # health + ws smoke green
```

## Where to look next

- [`CLAUDE.md`](CLAUDE.md) — Claude Code session entrypoint (role personas,
  context-load directives, hard rules).
- [`SKILLS.md`](SKILLS.md) — role persona index.
- [`PRD-ai-embodied-agent-v2.md`](PRD-ai-embodied-agent-v2.md) — repositioned
  v2 PRD with 25-stage roadmap.
- [`tasks/STAGE_02_simpy_simulator.md`](tasks/STAGE_02_simpy_simulator.md) —
  the next executable task doc (unchanged by v2 expansion).
- [`tasks/TASKS_README.md`](tasks/TASKS_README.md) — the iterative
  build → audit → fix → KB-update → next-task cycle.
- [`compliance/decision-logs/2026-05-18_prd_v2_repositioning.md`](compliance/decision-logs/2026-05-18_prd_v2_repositioning.md)
  — ADR for the PRD v2 repositioning + roadmap expansion (this session).
- [`compliance/decision-logs/2026-05-11_stage_01_close.md`](compliance/decision-logs/2026-05-11_stage_01_close.md)
  — ADR for the Stage 1 close (Supabase deferral, frontend LTS downgrade, etc.).
