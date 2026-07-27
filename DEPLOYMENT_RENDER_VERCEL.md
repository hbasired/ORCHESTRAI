# ORCHESTRAI — Deployment Guide: Render (backend) + Vercel (frontend)

A step-by-step, copy-pasteable runbook to put the platform online: the **FastAPI backend on Render**, the
**Next.js frontend on Vercel**, with managed Postgres + Redis on Render and Neo4j on Aura Free.

> **Honesty note (matches the project's discipline).** The backend is a **heavy ML service** (PyTorch, Transformers,
> scikit-learn, SB3, etc. — see `backend/requirements.txt`, 167 deps). It will **not** fit Render's free instance
> (512 MB RAM, spins down) — so on Render you need a **Standard instance (2 GB RAM)**, which costs money.
>
> **➜ Want a genuinely FREE backend? Use Hugging Face Spaces instead of Render — see [§9](#9-free-backend-alternative--hugging-face-spaces-16-gb-ram).**
> HF Spaces' free tier gives **2 vCPU / 16 GB RAM**, which comfortably fits this ML stack (it's more RAM than Render's
> *paid* Standard plan). The trade-offs are honest and fine for a demo/investor link or a light pilot: 2 vCPU (limited
> concurrency), the Space **sleeps after ~48 h idle** (cold start on the next hit), and you still bring your own free
> datastores. This guide covers **both** paths — Render (§2–§4) and Hugging Face (§9) — and the frontend on Vercel (§4)
> is identical for either.
>
> Everything else (Postgres, Redis, Neo4j Aura, Vercel) has a usable free tier. The app **degrades gracefully** — it
> boots and serves the API even if Neo4j, the DB, or a model weight is missing (features that need them report
> "unavailable", never fake data) — so you can bring services up incrementally.

---

## 0. Architecture of the deployment

```
        ┌─────────────────────────┐         ┌──────────────────────────────┐
        │  Vercel                 │  HTTPS   │  Render — Web Service         │
        │  Next.js frontend       │ ───────▶ │  FastAPI (uvicorn) :$PORT     │
        │  NEXT_PUBLIC_API_URL ───┼── WSS ──▶ │  /health  /api/*  /ws         │
        └─────────────────────────┘         └───────────┬──────────────────┘
                                                         │
                          ┌──────────────────────────────┼───────────────────────────┐
                          ▼                               ▼                           ▼
                 Render Postgres                  Render Key Value            Neo4j Aura Free
                 (+ pgvector ext)                 (Redis-compatible)          (ISA-95 graph)
                 DATABASE_URL                     REDIS_URL                   NEO4J_URI/USER/PASSWORD
```

**What each store is for:** Postgres = the system of record + `pgvector` memory + the signed `audit_chain` +
`decision_logs`; Redis = the WebSocket broker / live fan-out; Neo4j = the ISA-95 equipment graph + GraphRAG grounding.
The one LLM key you need is **`GROQ_API_KEY`** (free tier) — the default reasoning provider.

---

## 1. Prerequisites (once)

- A **GitHub repo** with this code pushed, **including the Git-LFS weights** in `models/` (`*.pt`, `*.joblib`,
  `*.onnx` are LFS-tracked per `.gitattributes`). Verify before you push:
  ```bash
  git lfs install
  git lfs ls-files | head          # should list models/*.pt etc.
  git add .gitattributes models/ && git commit -m "ensure LFS weights tracked" && git push
  ```
  > Render and Vercel both check out Git LFS automatically. If the weights are **not** in LFS, the ML features (PdM,
  > vision, RUL, injection detector) will report unavailable — the API still runs.
- Accounts: **Render**, **Vercel**, **Neo4j Aura** (aura.neo4j.io), **Groq** (console.groq.com → free API key).

---

## 2. Provision the datastores

### 2a. Postgres on Render (+ pgvector)
1. Render dashboard → **New → Postgres**. Name `orchestrai-db`, region close to your web service, plan **Free** works
   to start (upgrade later for retention/size). Create.
2. Copy the **Internal Database URL** (starts `postgresql://…`) — you'll use it as `DATABASE_URL` (internal URL = free,
   same-region traffic).
3. Enable the vector extension. Render Postgres supports it — connect with the **External URL** via `psql` and run:
   ```bash
   psql "<EXTERNAL_DATABASE_URL>" -c "CREATE EXTENSION IF NOT EXISTS vector;"
   psql "<EXTERNAL_DATABASE_URL>" -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
   ```
   (`uuid-ossp` backs `decision_logs.decision_id`'s `uuid_generate_v4()` default.)

### 2b. Redis on Render (Key Value)
1. Render → **New → Key Value** (Render's Redis-compatible store). Name `orchestrai-redis`, **Free** plan, same region.
2. Copy its **Internal connection URL** (`redis://…`) → this is `REDIS_URL`. Set **maxmemory-policy** to `noeviction`
   or `allkeys-lru` (either is fine — the broker is transient).

### 2c. Neo4j on Aura Free (Render has no managed Neo4j)
1. aura.neo4j.io → **New Instance → AuraDB Free**. On creation it shows a **generated password once** — save it.
2. Note the **Connection URI** — it looks like `neo4j+s://xxxx.databases.neo4j.io` (the `+s` = TLS; use it as-is).
3. You'll set `NEO4J_URI` / `NEO4J_USER=neo4j` / `NEO4J_PASSWORD=<generated>`.
   > Alternative (self-host): run `neo4j:5.15-community` as a Render **Private Service** with a persistent disk. Aura
   > Free is simpler and free; use it unless you have a reason not to.

---

## 3. Deploy the backend on Render (native Python runtime — recommended)

> **Why native Python, not the Docker image?** The repo's `docker/Dockerfile` is tuned for Cloud Run and copies only
> `backend/` — but the model weights live in the repo-root `models/` dir (`backend/ml/*.py` resolve `parents[2]/models`).
> The native runtime checks out the **whole repo** (so `models/` is present) and handles LFS — fewer moving parts.
> A Docker path is given in §7 if you prefer it.

1. Render → **New → Web Service** → connect your GitHub repo → select the branch (`main`).
2. Configure:
   | Field | Value |
   |---|---|
   | **Runtime** | `Python 3` |
   | **Root Directory** | *(leave blank — repo root, so `models/` is available)* |
   | **Build Command** | `pip install --upgrade pip && pip install -r backend/requirements.txt` |
   | **Start Command** | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | **Standard** (2 GB) or larger — torch needs the RAM |
   | **Health Check Path** | `/health` |
3. Pin the Python version: add an env var **`PYTHON_VERSION`** = `3.10.14` (the code targets 3.10; the Dockerfile uses
   `python:3.10-slim`).
4. Add the **environment variables** (Render → Environment):
   ```ini
   DATABASE_URL          = <Render Postgres INTERNAL url>
   REDIS_URL             = <Render Key Value INTERNAL url>
   NEO4J_URI             = neo4j+s://xxxx.databases.neo4j.io
   NEO4J_USER            = neo4j
   NEO4J_PASSWORD        = <Aura generated password>
   GROQ_API_KEY          = <your Groq free key>
   DEFAULT_LLM_PROVIDER  = groq
   CORS_ORIGINS          = ["https://<your-vercel-app>.vercel.app"]
   PYTHON_VERSION        = 3.10.14
   HF_HUB_DISABLE_XET    = 1
   ```
   - `CORS_ORIGINS` is parsed as JSON list — keep the `[ "…" ]` brackets and quotes. Add your custom domain later as a
     second element.
   - Leave `PORT` **unset** — Render injects it; the start command binds `$PORT`.
   - **`GROQ_API_KEY`:** your key is already in `backend/.env` (starts `gsk_…`; get it with
     `Get-Content backend\.env | Select-String GROQ_API_KEY`). It goes **here on the backend only** — **never** on
     Vercel, and never as a `NEXT_PUBLIC_*` var (that ships it to every browser). Full map: `CREDENTIALS.md`.
   - The `sentence-transformers` embedder (`BAAI/bge-small-en-v1.5`) downloads on first use; `HF_HUB_DISABLE_XET=1`
     avoids a flaky transfer backend. Optionally set `MEM0_EMBED_MODEL=BAAI/bge-small-en-v1.5` / `MEM0_EMBED_DIM=384`
     to pin it.
5. **Create the service.** The first build is slow (torch + transformers ≈ a few GB) — that's expected.

### 3a. Run the database migrations (Alembic)
The schema (incidents, decision_logs, audit_chain, cdc_outbox + triggers, pgvector tables, mem0 RLS role) is created by
Alembic. Set it as a Render **Pre-Deploy Command** (Settings → Pre-Deploy Command) so it runs on every deploy:
```bash
cd backend && alembic upgrade head
```
`backend/alembic/env.py` reads `DATABASE_URL` from the environment, so no extra config is needed. First run creates all
tables through migration `0010_cdc_value_changes`.

### 3b. Verify the backend
```bash
curl -s https://<your-service>.onrender.com/health        # -> {"status":"ok", ...}
curl -s https://<your-service>.onrender.com/               # -> service banner
curl -s https://<your-service>.onrender.com/docs           # -> FastAPI Swagger UI (open in a browser)
```
Note the public URL `https://<your-service>.onrender.com` — the frontend needs it next.

---

## 4. Deploy the frontend on Vercel

1. Vercel → **Add New → Project** → import the same GitHub repo.
2. In the import screen:
   | Field | Value |
   |---|---|
   | **Framework Preset** | Next.js (auto-detected) |
   | **Root Directory** | `frontend-nextjs` |
   | **Build Command** | `next build` (default) |
   | **Node version** | 20.x (project requires `>=20 <23`) |
3. Add the **Environment Variable** (Project → Settings → Environment Variables), for all environments:
   ```ini
   NEXT_PUBLIC_API_URL = https://<your-service>.onrender.com
   ```
   > One variable covers everything: the app derives the WebSocket URL from it automatically —
   > `lib/api.ts` does `API_BASE.replace("http","ws") + "/ws"`, so `https://…onrender.com` → `wss://…onrender.com/ws`.
   > (`NEXT_PUBLIC_*` is exposed to the browser by design — it's only the public API URL, no secret.)
   > **Do not add `GROQ_API_KEY` or any database URL to Vercel** — those are backend secrets (§3.4). Vercel gets this
   > one public value and nothing else.
4. **Deploy.** Vercel runs `next build` with strict type-checking (the project ships `ignoreBuildErrors:false` after
   Stage 34, so a type error fails the build — that's intended).
5. Copy the Vercel URL (`https://<app>.vercel.app`).

### 4a. Close the CORS loop
Go back to Render → the backend's `CORS_ORIGINS` env var → set it to your real Vercel URL and redeploy:
```ini
CORS_ORIGINS = ["https://<app>.vercel.app"]
```
(Add a preview-wildcard or your custom domain as extra list elements as needed.)

---

## 5. Smoke test the full stack
1. Open `https://<app>.vercel.app` — the dashboard loads.
2. It should fetch live state from the backend (`GET /api/simulation/state`) and open the WebSocket (`wss://…/ws`) with
   no CORS errors in the browser console.
3. Try an API-backed page (metrics / adoption) — real data or an honest empty-state, never fabricated.
4. Exercise the self-healing surfaces (optional, via `…onrender.com/docs`): `POST /factory/ask`, `POST /factory/inject`,
   `POST /facilities/optimize-energy`.

---

## 6. Production hardening checklist (do before a real pilot)
- [ ] **Upgrade Postgres** off Free (Free has a 90-day expiry + size cap); enable automated backups (the repo ships a
      DR runbook + `scripts/backup/`).
- [ ] **Custom domains** on both Vercel and Render; add the domain to `CORS_ORIGINS`.
- [ ] **Secrets**: never commit keys; keep `GROQ_API_KEY`, `NEO4J_PASSWORD` only in the platform's env store.
- [ ] **Scale**: raise the Render instance (torch inference is CPU-bound); set `workers` via a `WORKERS` env if you add
      one, or run a second instance behind Render's load balancer.
- [ ] **Observability** (optional): the OTel/Langfuse/Phoenix overlay (`docker/docker-compose.observability.yml`) is a
      separate deploy — set `OTEL_EXPORTER_OTLP_ENDPOINT` on the backend to ship traces to a collector you host.
- [ ] **mTLS / PQC / SPIRE** (`docker-compose.pqc.yml`, `docker-compose.spire.yml`) are for a real OT/pilot go-live, not
      a first cloud deploy — see the pilot runbook.
- [ ] **The physical safety path** (`sil_bridge`) is sim-only until a certified PLC is wired — do **not** connect it to
      a real actuator without the functional-safety certification path (see the risk register).

---

## 7. Alternative: deploy the backend as a Docker image on Render
If you prefer the container path, add a **models copy** so the weights land in the image, then deploy the Dockerfile.

1. Create `render.Dockerfile` at the repo root (so the build context is the repo root, not `backend/`):
   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   RUN apt-get update && apt-get install -y --no-install-recommends \
       build-essential curl libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
       && rm -rf /var/lib/apt/lists/*
   COPY backend/requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY backend/ /app/
   COPY models/ /models/            # <-- the weights the root-relative loaders expect (parents[2]/models)
   ENV PYTHONUNBUFFERED=1
   # Render injects $PORT; bind it (do NOT hardcode 8080 as docker/Dockerfile does)
   CMD ["sh", "-c", "alembic upgrade head; uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
   ```
2. Render → New → Web Service → **Runtime: Docker**, **Dockerfile Path**: `render.Dockerfile`, **Docker Build Context
   Directory**: `.` (repo root). Same env vars as §3.4, same health path `/health`.
   > The stock `docker/Dockerfile` won't work as-is on Render: it copies only `backend/` (misses root `models/`) and
   > hardcodes port 8080 instead of `$PORT`. The `render.Dockerfile` above fixes both.

---

## 8. Common issues & fixes
| Symptom | Cause | Fix |
|---|---|---|
| Build OOM / killed | torch on a small instance | Use **Standard (2 GB)+**; the free tier can't build/run torch |
| `vector type does not exist` on migrate | pgvector extension not enabled | Run `CREATE EXTENSION vector;` (§2a) before `alembic upgrade head` |
| CORS error in browser console | `CORS_ORIGINS` missing the Vercel URL | Set it to `["https://<app>.vercel.app"]` and redeploy (§4a) |
| WebSocket won't connect | `NEXT_PUBLIC_API_URL` uses `http` but page is `https` | Use the **https** Render URL; the app maps it to `wss://…/ws` |
| ML endpoints say "unavailable" | weights not checked out via LFS | Confirm `git lfs ls-files` lists `models/*.pt`; re-push with LFS |
| Neo4j / GraphRAG features off | Aura URI/creds wrong | Use the `neo4j+s://…` URI + the one-time generated password |
| App boots but DB features 503 | `DATABASE_URL` unset/incorrect | Use the Render **internal** Postgres URL; re-run migrations |
| First request very slow | embedder model downloading | One-time `bge-small` download on first semantic call; warms after |

---

**That's the whole path:** Postgres + Redis (Render) + Neo4j (Aura) → backend Web Service (Render, native Python, bind
`$PORT`, `alembic upgrade head` pre-deploy) → frontend (Vercel, `NEXT_PUBLIC_API_URL` → Render) → close CORS. Free/low
tiers get you a working demo; the §6 checklist is the path to a pilot-grade deployment.

---

## 9. Free backend alternative — Hugging Face Spaces (16 GB RAM)

**Short answer: yes, and it fits better than Render's free tier.** A free HF **Docker Space** gives **2 vCPU / 16 GB
RAM / ~50 GB disk** — the RAM is exactly what Render free lacked, so the PyTorch + Transformers + sentence-transformers
stack loads fine. It's the recommended **zero-cost** way to stand the backend up for a demo, an investor link, or a
light pilot.

> ⚠️ Verify current numbers on Hugging Face's Spaces hardware page before you rely on them — free-tier specs change.
> The figures here reflect the long-standing "CPU basic — free" tier.

### Will it handle it? — the honest breakdown
| Dimension | Verdict |
|---|---|
| **RAM (16 GB)** | ✅ Comfortably fits torch + transformers + the 8 models (weights total **166 MB**). This is the win over Render free. |
| **CPU (2 vCPU)** | ✅ Fine for a demo / a handful of concurrent users / light pilot. ❌ Not high-concurrency production — inference is CPU-bound. |
| **Uptime** | ⚠️ Free Spaces **sleep after ~48 h of inactivity** → a slow cold start on the next request. Fine for a shared link; upgrade or ping it to keep it warm. |
| **Storage** | ⚠️ Ephemeral filesystem (resets on rebuild). ✅ **Not a problem here** — all state (audit chain, memory, decisions) lives in the **external** Postgres, and weights are read-only in the image. |
| **Datastores** | ❌ HF bundles **no** Postgres/Redis/Neo4j — bring your own free ones (below). |
| **WebSockets** | ✅ Supported — the live `/ws` feed works over `wss://…hf.space/ws`. |

### 9a. Provision free external datastores
HF Spaces don't include databases, so use these free tiers (all better than Render's ephemeral free DB):
- **Postgres + pgvector → [Neon](https://neon.tech)** (free serverless Postgres). New project → copy the **pooled**
  connection string → run once:
  `psql "<neon-url>" -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"`
  → that's your `DATABASE_URL`. *(Supabase's free Postgres also works and has pgvector.)*
- **Redis → [Upstash](https://upstash.com)** (free serverless Redis). Create a database → copy the `rediss://…` URL →
  that's your `REDIS_URL` (TLS — `redis-py` handles `rediss://`).
- **Neo4j → Aura Free** — exactly as in §2c.

### 9b. Create the Space
1. huggingface.co → your profile → **New → Space**.
2. Name `orchestrai-backend`, **License** Apache-2.0, **SDK = Docker** (blank template), **Hardware = CPU basic (free)**,
   visibility **Public** (free; your code is Apache-2.0 anyway — secrets stay hidden regardless). Create.

### 9c. Add the Space config + Dockerfile
A Space is its own git repo. Add three things: a `README.md` with the Space metadata, a `Dockerfile`, and the app +
weights.

**`README.md`** — the YAML front-matter is how HF configures the Space; **`app_port` must equal the port the app binds**:

    ---
    title: ORCHESTRAI Backend
    emoji: 🏭
    colorFrom: blue
    colorTo: green
    sdk: docker
    app_port: 7860
    pinned: false
    ---
    ORCHESTRAI control-plane backend (FastAPI). API docs at `/docs`, health at `/health`.

**`Dockerfile`** — HF Spaces run as uid **1000**; opencv/YOLO need `libgl`; the root-relative `models/` loaders expect
the weights at `parents[2]/models`, which in this layout is `/home/user/models`:

    FROM python:3.10-slim

    # system deps: build + opencv/YOLO runtime libs + git-lfs for the weights
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl git git-lfs libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
        && rm -rf /var/lib/apt/lists/*

    # HF Spaces run containers as uid 1000 — create that user and a writable home
    RUN useradd -m -u 1000 user
    USER user
    ENV HOME=/home/user \
        PATH=/home/user/.local/bin:$PATH \
        PYTHONUNBUFFERED=1 \
        HF_HUB_DISABLE_XET=1
    WORKDIR /home/user/app

    # install deps first (layer cache)
    COPY --chown=user backend/requirements.txt .
    RUN pip install --no-cache-dir --user -r requirements.txt

    # app -> /home/user/app  (so backend/ml/*.py resolve parents[2]/models = /home/user/models)
    COPY --chown=user backend/ /home/user/app/
    COPY --chown=user models/  /home/user/models/

    EXPOSE 7860
    # migrate then serve, bound to the app_port HF proxies to
    CMD ["sh", "-c", "alembic upgrade head; uvicorn main:app --host 0.0.0.0 --port 7860"]

### 9d. Push the app + weights (Git LFS)
From your machine, copy the needed files into the cloned Space repo and push. The weights **must** go via LFS:

    git clone https://huggingface.co/spaces/<you>/orchestrai-backend hf-space
    cd hf-space
    git lfs install
    cp -r ../ai-embodied-agent/backend ./backend
    cp -r ../ai-embodied-agent/models  ./models
    # (add the README.md and Dockerfile from 9c)
    git lfs track "*.pt" "*.onnx" "*.pkl" "*.joblib"
    git add .gitattributes README.md Dockerfile backend models
    git commit -m "ORCHESTRAI backend on HF Spaces"
    git push

> **Do NOT copy any `.env`, keys, or `backend/venv/`.** Secrets go in the Space settings (next), never in git. The push
> triggers the Docker build on HF (slow the first time — torch is multi-GB; that's normal).

### 9e. Set the environment as Space secrets
Space → **Settings → Variables and secrets** → add (as **secrets** for the sensitive ones):

    DATABASE_URL          = <Neon pooled connection string>
    REDIS_URL             = <Upstash rediss:// url>
    NEO4J_URI             = neo4j+s://xxxx.databases.neo4j.io
    NEO4J_USER            = neo4j
    NEO4J_PASSWORD        = <Aura password>
    GROQ_API_KEY          = <your Groq free key>
    DEFAULT_LLM_PROVIDER  = groq
    CORS_ORIGINS          = ["https://<your-vercel-app>.vercel.app"]

Saving secrets restarts the Space. Watch the **Logs** tab: you want `alembic upgrade head` to finish, then
`Uvicorn running on http://0.0.0.0:7860`.

### 9f. Point the frontend at the Space + verify
- Your backend URL is now `https://<you>-orchestrai-backend.hf.space`.
- On **Vercel**, set `NEXT_PUBLIC_API_URL = https://<you>-orchestrai-backend.hf.space` (the app derives
  `wss://…hf.space/ws` from it automatically) and redeploy.
- Make sure the Space's `CORS_ORIGINS` secret contains your exact Vercel URL.
- Verify:
  ```bash
  curl -s https://<you>-orchestrai-backend.hf.space/health   # -> {"status":"ok", ...}
  # open https://<you>-orchestrai-backend.hf.space/docs in a browser
  ```

### 9g. Render vs Hugging Face — pick one
| | **Render** (§2–§4) | **Hugging Face Spaces** (§9) |
|---|---|---|
| Free RAM | 512 MB (too small for torch) | **16 GB** (fits) |
| Cost for this stack | ~Standard plan (paid) | **Free** |
| Bundled Postgres/Redis | Yes (Render-managed) | No → Neon + Upstash (free) |
| Always-on | Yes (paid) / spins down (free) | Sleeps after ~48 h idle (free) |
| Port | `$PORT` (injected) | `app_port: 7860` (README) |
| Best for | steady / always-on pilot | **free demo / investor link / light pilot** |

### 9h. HF-specific gotchas
| Symptom | Fix |
|---|---|
| Space shows "Configuration error" | `app_port` in `README.md` must equal the uvicorn `--port` (7860) |
| Permission denied writing files | Run as `USER user` (uid 1000); keep writes under `/home/user` (the Dockerfile does) |
| `libGL.so.1` not found | Keep `libgl1 libglib2.0-0` in the apt install (opencv/YOLO need them) |
| ML endpoints "unavailable" | Weights not pushed via LFS — `git lfs ls-files` in the Space must list `models/*.pt` |
| First request very slow / 503 | Space was asleep (48 h idle) or still building — wait for the cold start / build |
| CORS error | `CORS_ORIGINS` secret must contain the exact `https://<app>.vercel.app` |

**Net:** Hugging Face Spaces is the right **free** home for this backend (16 GB RAM fits the ML stack); pair it with
Neon + Upstash + Aura (all free) and Vercel (free) for a genuinely zero-cost full-stack demo. Move to Render + the §6
hardening checklist when you need always-on uptime, higher concurrency, or a pilot SLA.
