# ORCHESTRAI — Free Deployment Guide: Databases → Hugging Face (backend) → Vercel (frontend)

A complete, beginner-friendly, click-by-click guide to put ORCHESTRAI online for **$0**, assuming you've never used any
of these platforms. Follow the parts **in order**. By the end you'll have a public URL you can send to anyone.

**What you'll end up with (all free tiers):**
```
   Vercel  ──HTTPS/WSS──▶  Hugging Face Space  ──▶  Neon (Postgres)
  (frontend)                (FastAPI backend)   ──▶  Upstash (Redis)
                                                ──▶  Neo4j Aura (graph)
```

> ### ⚠️ Read these two things first — they save you hours
>
> **1. You do NOT upload any data files to the databases.** This is the part people expect to be hard and it isn't.
> The backend **creates all its own tables automatically** the first time it starts (a step called "migrations" that
> runs on its own). The *only* manual database action in this whole guide is running **one line of SQL** in Neon's web
> editor to switch on an add-on. No CSVs, no dumps, no schema files — nothing to upload.
>
> **2. Run the backend steps (Part B) from the computer that has the `models/` folder** (your current machine). The
> trained model weights (`models/*.pt`) live on your disk and are **not** in the GitHub repo — Part B copies them from
> your disk into the Space. If you skip that, the app still runs but the ML features say "unavailable".
>
> **3. All credentials in one place:** `CREDENTIALS.md` (gitignored) lists every value, where it lives locally, and
> exactly which platform each one goes into. Keep it open alongside this guide.

---

# PART A — Create the three free databases

You'll create three databases and collect **five values** (below). Keep a notepad open and paste each one as you go.

| You need | From | Looks like |
|---|---|---|
| `DATABASE_URL` | Neon | `postgresql://user:pass@ep-xxx.aws.neon.tech/neondb?sslmode=require` |
| `REDIS_URL` | Upstash | `rediss://default:pass@xxx.upstash.io:6379` |
| `NEO4J_URI` | Neo4j Aura | `neo4j+s://xxxx.databases.neo4j.io` |
| `NEO4J_USER` | Neo4j Aura | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j Aura | (a generated string) |

## A1. Postgres database → Neon  (this stores everything: the signed audit trail, memory, decisions)
1. Go to **https://neon.tech** and click **Sign up** (use your GitHub or Google account — fastest).
2. It asks you to **create a project**. Name it `orchestrai`, choose the **region closest to you**, leave the Postgres
   version at the default. Click **Create project**.
3. You'll land on the project dashboard. There's a box labelled **Connection string** (sometimes under a
   **"Connect"** button). Click **Copy**. If it offers a **"Pooled connection"** toggle, turn it **on** and copy that
   one. → This is your **`DATABASE_URL`**. Paste it into your notepad.
4. **Turn on the two add-ons the app needs** (this is the one manual SQL step):
   - In the left sidebar click **SQL Editor**.
   - Paste this line and click **Run**:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
     ```
   - You should see "Success". That's it — you never touch SQL again.
   > Neon's free database "sleeps" when idle and wakes on the next connection (a fraction of a second). That's normal
   > and fine.

## A2. Redis database → Upstash  (this powers the live WebSocket feed)
1. Go to **https://upstash.com** and click **Sign up** (GitHub/Google).
2. In the console click **Create Database** (choose **Redis** if asked). Name it `orchestrai`, pick a **region**,
   choose the **free "Regional"** type, leave **TLS/SSL enabled**. Click **Create**.
3. On the database page, scroll to **"Connect to your database"**. Choose the **redis-cli** or **`.env`** tab — you're
   looking for the URL that starts with **`rediss://default:...`**. Click the copy icon.
   → This is your **`REDIS_URL`**. Paste it into your notepad.
   > If you only see a "REST URL", keep scrolling / switch tabs — you specifically want the `rediss://` one (that's the
   > real Redis protocol the app uses).

## A3. Neo4j graph database → Aura Free  (this stores the equipment graph + grounding)
1. Go to **https://neo4j.com/product/auradb/** → **Start free**, or straight to **https://console.neo4j.io** and sign up.
2. Click **New Instance** → choose **AuraDB Free** → **Create**.
3. A box pops up with the **username** (`neo4j`) and a **generated password**. **This password is shown only once** —
   click **Download** (it saves a `.txt`) and also copy the password into your notepad now.
   → `NEO4J_USER` = `neo4j`, `NEO4J_PASSWORD` = that generated string.
4. When the instance finishes starting, it shows a **Connection URI** like `neo4j+s://xxxx.databases.neo4j.io`.
   → This is your **`NEO4J_URI`**. Paste it into your notepad.

✅ **Checkpoint:** your notepad now has all five values. Nothing was uploaded — the backend fills these databases itself
in Part B.

---

# PART B — Deploy the backend on Hugging Face Spaces (free, 16 GB RAM)

A Hugging Face "Space" is a free container that will run your FastAPI backend. Its free tier has **16 GB RAM**, which
comfortably fits the ML models.

> Do these steps in **PowerShell** on the machine that has your project (and the `models/` folder).

## B1. Create the Space
1. Go to **https://huggingface.co** and sign up / log in.
2. Top-right avatar → **New Space**.
3. Fill in: **Owner** = you, **Space name** = `orchestrai-backend`, **License** = `apache-2.0`,
   **Select the Space SDK** = **Docker** → **Blank**, **Space hardware** = **CPU basic · Free**,
   **Visibility** = **Public**. Click **Create Space**.
4. HF shows you the Space's git URL: `https://huggingface.co/spaces/<your-username>/orchestrai-backend`. Note it.

## B2. Get the Space onto your machine and add the files
In PowerShell, from the folder that CONTAINS your `ai-embodied-agent` project (so `..\ai-embodied-agent` exists):
```powershell
# 1) log in to Hugging Face git (paste an access token from huggingface.co/settings/tokens when prompted)
git lfs install
git clone https://huggingface.co/spaces/<your-username>/orchestrai-backend hf-space
cd hf-space

# 2) copy the backend code + the model weights into the Space
Copy-Item -Recurse ..\ai-embodied-agent\backend .\backend
Copy-Item -Recurse ..\ai-embodied-agent\models  .\models

# 3) make sure the big weight files go up via Git LFS (not as broken text files)
git lfs track "*.pt" "*.onnx" "*.pkl" "*.joblib"
```
> Do **not** copy any `.env` file, API keys, or `backend\venv`. Secrets go in the Space settings (step B4).

## B3. Create the Space's `README.md` and `Dockerfile`
Still in the `hf-space` folder, create these two files (use `notepad README.md` etc. and paste).

**`README.md`** — the top part (between the `---` lines) is how Hugging Face configures the Space. Keep it exactly:

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

**`Dockerfile`** — paste exactly (it runs as the user HF requires, installs the vision libraries, puts the weights
where the code expects them, runs the migrations, then starts the server on port 7860):

    FROM python:3.10-slim

    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl git git-lfs libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
        && rm -rf /var/lib/apt/lists/*

    RUN useradd -m -u 1000 user
    USER user
    ENV HOME=/home/user \
        PATH=/home/user/.local/bin:$PATH \
        PYTHONUNBUFFERED=1 \
        HF_HUB_DISABLE_XET=1
    WORKDIR /home/user/app

    COPY --chown=user backend/requirements.txt .
    RUN pip install --no-cache-dir --user -r requirements.txt

    COPY --chown=user backend/ /home/user/app/
    COPY --chown=user models/  /home/user/models/

    EXPOSE 7860
    CMD ["sh", "-c", "alembic upgrade head; uvicorn main:app --host 0.0.0.0 --port 7860"]

## B4. Push to Hugging Face
```powershell
git add .gitattributes README.md Dockerfile backend models
git commit -m "ORCHESTRAI backend"
git push
```
The push triggers the build on Hugging Face. **The first build takes several minutes** (it installs PyTorch, which is
large) — that's normal. Watch progress on your Space's **"Building"** tab.

## B5. Add your secrets (the five database values + your Groq key)
1. On your Space page → **Settings** (top) → scroll to **Variables and secrets** → **New secret** for each:
   ```ini
   DATABASE_URL          = <the Neon value from A1>
   REDIS_URL             = <the Upstash value from A2>
   NEO4J_URI             = <the Aura value from A3>
   NEO4J_USER            = neo4j
   NEO4J_PASSWORD        = <the Aura password from A3>
   GROQ_API_KEY          = <your Groq key — see note below>
   DEFAULT_LLM_PROVIDER  = groq
   CORS_ORIGINS          = ["https://REPLACE-AFTER-PART-C.vercel.app"]
   ```
   (You'll fix `CORS_ORIGINS` with your real Vercel URL in Part D — put a placeholder for now.)

   > **🔑 Your Groq key is already in your project** at `backend/.env` (it starts `gsk_…`). Get it with, in PowerShell:
   > `Get-Content backend\.env | Select-String GROQ_API_KEY` — then paste the value here as a **Secret**.
   > **The Groq key goes ONLY on the backend (this Space). NEVER put it on Vercel and never name it `NEXT_PUBLIC_*`** —
   > that would ship it to every visitor's browser. Full map: `CREDENTIALS.md`.
2. Saving secrets restarts the Space. Open the **Logs** tab and wait until you see:
   `Uvicorn running on http://0.0.0.0:7860`.

## B6. Confirm the backend is live
Your backend URL is: **`https://<your-username>-orchestrai-backend.hf.space`**
```powershell
Invoke-RestMethod https://<your-username>-orchestrai-backend.hf.space/health
Start-Process https://<your-username>-orchestrai-backend.hf.space/docs
```
`/health` returning `{"status":"ok"}` means the backend + all three databases are connected. 🎉

---

# PART C — Deploy the frontend on Vercel (free)

1. Go to **https://vercel.com** → **Sign up** with GitHub.
2. **Add New… → Project** → **Import** your `ai-embodied-agent` GitHub repository.
   *(If it's not on GitHub yet: `git push` it to a GitHub repo first, then import.)*
3. On the configure screen:
   - **Root Directory** → click **Edit** → choose **`frontend-nextjs`**.
   - **Framework Preset** → it auto-detects **Next.js** (leave it).
   - Expand **Environment Variables** and add:
     - **Name:** `NEXT_PUBLIC_API_URL`
     - **Value:** `https://<your-username>-orchestrai-backend.hf.space`  *(your Part B URL — no trailing slash)*
   > This is the **only** variable Vercel needs, and it's **public by design** (`NEXT_PUBLIC_*` = shipped to the
   > browser). **Do not add `GROQ_API_KEY` or any database URL to Vercel** — those are backend secrets (Part B / §B5).
4. Click **Deploy**. Wait for it to finish, then copy your live URL: `https://<something>.vercel.app`.

> One variable is enough — the app builds the WebSocket URL from it automatically
> (`https://…hf.space` → `wss://…hf.space/ws`).

---

# PART D — Connect the two + final check

1. **Tell the backend to trust the frontend (CORS).** Go back to your Hugging Face Space → **Settings → Variables and
   secrets** → edit **`CORS_ORIGINS`** to your real Vercel URL:
   ```ini
   CORS_ORIGINS = ["https://<something>.vercel.app"]
   ```
   Keep the square brackets and quotes exactly. Save (the Space restarts).
2. Open your Vercel URL. The dashboard should load, pull live data from the backend, and open the live feed with **no
   red CORS errors** in the browser console (press F12 → Console to check).
3. Done — send the Vercel link to anyone. 🚀

---

# Troubleshooting (plain-language)
| What you see | What it means | Fix |
|---|---|---|
| Space page says **"Configuration error"** | `app_port` doesn't match the server port | In `README.md` it must say `app_port: 7860` (matches the Dockerfile) |
| Build fails on `git push` with a huge `.pt` diff | Weights went up as text, not LFS | In `hf-space`: `git lfs ls-files` must list `models/*.pt`; if not, `git lfs track "*.pt"` then re-add/commit/push |
| `/health` fails or Space keeps restarting | A database value is wrong | Re-check the three connection strings in **Secrets** (copy-paste again from the platform) |
| Browser console shows a **CORS** error | Backend doesn't trust the frontend URL | Set `CORS_ORIGINS` to the exact `https://<app>.vercel.app` (Part D) and let the Space restart |
| API works but ML endpoints say **"unavailable"** | The `models/` weights didn't get into the Space | Redo B2 step 2 (`Copy-Item -Recurse ...\models .\models`) + B4 push; confirm with `git lfs ls-files` |
| First request is very slow, then fine | The free Space **slept** after ~48 h idle | Normal — it wakes on the first hit; refresh once |
| `vector type does not exist` in the logs | pgvector add-on not enabled on Neon | Re-run the A1 step-4 SQL in Neon's SQL Editor |
| Neo4j / grounding features off | Aura URI or password wrong | Use the `neo4j+s://…` URI and the one-time generated password (from the downloaded file) |

---

**Recap of the whole flow:** three free databases (Neon + Upstash + Aura — you only ever copied connection strings and
ran one line of SQL) → backend on a free Hugging Face Space (you copied code + weights, pasted a Dockerfile, added the
secrets) → frontend on Vercel (one env var) → connected them with CORS. Total cost: **$0**. For an always-on, higher-
traffic, pilot-grade setup, see the Render path and the hardening checklist in `DEPLOYMENT_RENDER_VERCEL.md`.
