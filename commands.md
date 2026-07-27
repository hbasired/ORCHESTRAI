# ORCHESTRAI — Local Run & Demo Commands (Windows / PowerShell)

Everything you need to start the **databases (Docker)**, the **backend**, and the **frontend** on your own machine and
demo the product. Written for **Windows PowerShell** (your shell). Docker Desktop must be running.

> **Two ways to run it:**
> - **Option A — full demo (recommended):** databases in Docker, backend + frontend run natively on your machine.
>   This is the only way you get the **ML features** (predictive maintenance, RUL, vision, energy MILP) because the
>   model weights live in your local `models/` folder — and a native backend reads them directly.
> - **Option B — everything in Docker:** one command brings up the databases + backend. Simpler, but the Docker
>   backend does **not** see `models/` (they're gitignored + not baked into the image), so ML endpoints will honestly
>   report "unavailable". Fine for showing the API/live-sim/agents; use Option A to show the ML.

---

## 0. One-time prerequisites
- **Docker Desktop** (running) — for the databases.
- **Python 3.10 or 3.11** — for the backend. Check: `python --version`
- **Node.js 20.x** — for the frontend. Check: `node --version`
- A free **Groq API key** (console.groq.com) for the LLM features (optional — the system degrades honestly without it).
- Your **model weights** in `models/` (they're already on your disk — 7 `.pt/.joblib` files + `backend/yolov8n.pt`).

---

## Option A — Full demo (DBs in Docker · backend & frontend native)

### A1. Create the environment files (once)
The Docker Compose stack reads **`.env.local`** at the repo root; the native backend reads **`backend/.env`**.

**`.env.local`** (repo root — for Docker). Copy the example and fill the passwords:
```powershell
Copy-Item .env.example .env.local
notepad .env.local
```
Set at least these (any throwaway values are fine for local — they only exist inside Docker):
```ini
POSTGRES_USER=aiagent
POSTGRES_PASSWORD=devpass2026
POSTGRES_DB=manufacturing
NEO4J_USER=neo4j
NEO4J_PASSWORD=devpass2026
CORS_ORIGINS=["http://localhost:3000"]
GROQ_API_KEY=<your-groq-key-or-leave-blank>
```

**`backend/.env`** (for the native backend — it must point at **localhost**, since the Docker service names only
resolve inside Docker). It already exists; make sure it contains:
```ini
DATABASE_URL=postgresql://aiagent:devpass2026@localhost:5432/manufacturing
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devpass2026
REDIS_URL=redis://localhost:6379
GROQ_API_KEY=<your-groq-key>
DEFAULT_LLM_PROVIDER=groq
CORS_ORIGINS=["http://localhost:3000"]
MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5
MEM0_EMBED_DIM=384
HF_HUB_DISABLE_XET=1
```

**`frontend-nextjs/.env.local`** already has `NEXT_PUBLIC_API_URL=http://localhost:8000` — nothing to change.

> **Port note:** the compose maps Postgres to host **5432**. If you already run a local Postgres on 5432, either stop
> it, or edit `docker/docker-compose.yml` to `"5544:5432"` and change `backend/.env`'s `DATABASE_URL` to
> `...@localhost:5544/...`.

### A2. Start ONLY the databases in Docker
```powershell
docker compose -f docker/docker-compose.yml up -d postgres neo4j redis
```
Wait ~20 s for them to go healthy, then confirm:
```powershell
docker compose -f docker/docker-compose.yml ps
```
(You can add `mqtt` to that list if you want the OT/Sparkplug demo: `... up -d postgres neo4j redis mqtt`.)

### A3. Enable pgvector + run the database migrations (once)
```powershell
# enable the vector extension the memory layer needs
docker exec -it ai-agent-postgres psql -U aiagent -d manufacturing -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS ""uuid-ossp"";"

# create all tables (incidents, decision_logs, audit_chain, cdc triggers, pgvector, ...)
cd backend
python -m pip install -r requirements.txt        # heavy, one-time (torch etc.)
python -m alembic upgrade head
cd ..
```

### A4. Start the backend (native → full ML)
```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Leave this window running. It will load the models from `..\models`. Verify in a second terminal:
```powershell
Invoke-RestMethod http://localhost:8000/health
Start-Process http://localhost:8000/docs      # opens the interactive API in your browser
```

### A5. Start the frontend (native)
In a **new** PowerShell window:
```powershell
cd frontend-nextjs
npm install        # one-time
npm run dev
Start-Process http://localhost:3000
```

### A6. Demo it
- **Dashboard:** http://localhost:3000 — live state + the WebSocket incident feed (`ws://localhost:8000/ws`).
- **API playground:** http://localhost:8000/docs — try these live self-healing surfaces:
```powershell
# Ask the factory (grounded QA — honest-empty if no evidence)
Invoke-RestMethod -Method Post http://localhost:8000/factory/ask -ContentType application/json -Body '{"question":"why did welding cell 3 need maintenance?"}'

# Inject a problem in natural language -> validated incident -> self-healing loop (Hard Rule 3: LLM never actuates)
Invoke-RestMethod -Method Post http://localhost:8000/factory/inject -ContentType application/json -Body '{"report":"welding cell 3 is overheating and vibrating, urgent","run_loop":true}'

# Energy optimiser (real MILP peak-shaving)
Invoke-RestMethod -Method Post http://localhost:8000/facilities/optimize-energy -ContentType application/json -Body '{"required_slots":6,"demand_cap_kw":100}'

# Bidirectional CDC: edit a DB value -> the engine diagnoses the induced problem
Invoke-RestMethod -Method Post http://localhost:8000/factory/db-edit -ContentType application/json -Body '{"table":"stages","column":"defect_rate","old_value":0.02,"new_value":0.15,"target_id":3}'
```
> Tip: keep the **interactive scenario** open (`research/system-deep-dive-2026-07/index.html` → "▶ Live Scenario") as
> your talking track while you fire these calls — the story matches what the endpoints do.

---

## Option B — Everything in Docker (simplest, ML degrades honestly)
```powershell
# builds the backend image, runs migrations, starts DBs + backend (host :8000 -> container :8080)
docker compose -f docker/docker-compose.yml up -d --build postgres neo4j redis migrate backend
docker compose -f docker/docker-compose.yml logs -f backend      # watch it come up
Invoke-RestMethod http://localhost:8000/health
```
Then run the frontend natively (A5). **To get the ML models inside the Docker backend too**, add a bind-mount so the
container can see your weights — edit the `backend:` service `volumes:` in `docker/docker-compose.yml`:
```yaml
    volumes:
      - ../backend:/app
      - ../models:/models        # <-- add this line (the loaders look at /models)
```
then `docker compose ... up -d --build backend`.

---

## Everyday commands
```powershell
# see what's running
docker compose -f docker/docker-compose.yml ps

# tail logs (all, or one service)
docker compose -f docker/docker-compose.yml logs -f
docker compose -f docker/docker-compose.yml logs -f postgres

# stop everything (keeps data)
docker compose -f docker/docker-compose.yml down

# stop AND wipe the databases (fresh start — deletes volumes)
docker compose -f docker/docker-compose.yml down -v

# open a psql shell
docker exec -it ai-agent-postgres psql -U aiagent -d manufacturing

# verify the signed audit chain (EU-AI-Act evidence integrity)
$env:DATABASE_URL="postgresql://aiagent:devpass2026@localhost:5432/manufacturing"; python scripts/verify-audit-chain.py

# run the backend test suite (with the DBs up)
cd backend; python -m pytest -q; cd ..
```

---

## PowerShell gotchas (you already hit one)
| You tried (Unix) | Use instead (PowerShell) |
|---|---|
| `git lfs ls-files \| head` | `git lfs ls-files \| Select-Object -First 10` |
| `cp -r src dst` | `Copy-Item -Recurse src dst` |
| `export VAR=x` | `$env:VAR = "x"` |
| `curl localhost:8000/health` | `Invoke-RestMethod http://localhost:8000/health` (or `curl.exe ...`) |
| `cat file` | `Get-Content file` |
| `VAR=x cmd` (inline) | `$env:VAR="x"; cmd` |

---

## What "healthy" looks like
- `docker compose ps` → `postgres`, `neo4j`, `redis` all **healthy**.
- `http://localhost:8000/health` → `{"status":"ok", ...}`.
- `http://localhost:8000/docs` → the FastAPI Swagger page lists `/factory/*`, `/facilities/*`, `/api/*`.
- `http://localhost:3000` → the dashboard renders and the browser console shows the WebSocket connected.
- The backend log shows the models loading (Option A) — e.g. the PdM predictor + RUL Transformer available, not
  "ModelUnavailableError".
