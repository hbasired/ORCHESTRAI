# ORCHESTRAI — Complete Project Navigation Guide

A map of the **entire** system so you can move around it confidently, run it, and explain any part. Three layers:
**databases**, **backend**, **frontend** — plus how they connect and where every piece of information lives.

> New here? Read in this order: (1) **The live stack** below to see it running, (2) **Databases**, (3) **Backend map**,
> (4) **Frontend map**, (5) **Where to find X**. For the deep *concepts* (models, RL, EU AI Act, competitors) open
> `research/system-deep-dive-2026-07/index.html`. To run it yourself, see `commands.md`.

---

## 0. The live stack (running on your machine right now)
| Service | URL / port | What it is |
|---|---|---|
| **Frontend** (Next.js) | **http://localhost:3000** | The dashboard/UI |
| **Backend API** (FastAPI) | **http://localhost:8000** | The control plane |
| **API docs (Swagger)** | **http://localhost:8000/docs** | Try every endpoint interactively |
| **Health** | http://localhost:8000/health | `{"status":"healthy"}` |
| **Neo4j browser** | http://localhost:7474 | Graph DB UI (user `neo4j` / pass `devpass2026`) |
| **Postgres** | localhost:**5544** | (via `docker exec ai-agent-postgres psql -U aiagent -d manufacturing`) |
| **Redis** | localhost:6379 | (Docker) |

Repo top level:
```
ai-embodied-agent/
├── backend/            ← the FastAPI control plane (Python) — §2
├── frontend-nextjs/    ← the Next.js UI (TypeScript) — §3
├── docker/             ← docker-compose.yml + Dockerfiles (the DBs + optional overlays)
├── knowledge-base/     ← KB_01..KB_26: the "what/why" docs (design, models, datasets, standards)
├── compliance/         ← model cards, decision-log ADRs, risk register, EU-AI-Act packs
├── research/           ← SOTA research + the HTML explainers, pitch deck, deep-dive, scenario
├── audits/             ← per-stage independent reviews + the 7 CTO checkpoints + gaps ledger
├── tasks/              ← the 39 stage task docs (what each stage set out to build)
├── scripts/            ← lifecycle + ops scripts (audit, close-task, verify-audit-chain, backups)
├── models/             ← trained ML weights (*.pt/*.joblib) — on disk, gitignored (§2 note)
└── *.md                ← this guide, commands.md, the two deployment guides
```

---

## 1. Databases — what, where, why

The system uses **three** databases (all local via Docker now; all have free cloud tiers for deployment). They are
started by `docker/docker-compose.yml`.

| DB | Runs at | Why this database is used | Where the schema/wiring lives |
|---|---|---|---|
| **PostgreSQL** (+ `pgvector`) | localhost **5544** (container `ai-agent-postgres`) | The **system of record**: the append-only, hash-chained, ML-DSA-65-signed **`audit_chain`** (EU-AI-Act Art-12 evidence), the **`decision_logs`** ledger, incidents, the **`cdc_outbox`** (DB→agent triggers), A2A peers, and the **episodic/semantic memory** (pgvector similarity search). Postgres because it's transactional + `pgvector` gives vector search in the same store. | Tables/triggers are defined by **Alembic migrations** in `backend/alembic/versions/0001…0010_*.py` (the source of truth). Access code in `backend/memory/` (`audit_chain.py`, `mem0_adapter.py`) + `backend/data/`. |
| **Neo4j** (5.15) | localhost **7687** (bolt), **7474** (browser); container `ai-agent-neo4j` | The **equipment knowledge graph** — the ISA-95 plant hierarchy (site→area→line→cell→equipment) + the relationships GraphRAG walks to ground answers. A graph DB because plant topology and 1–2-hop neighbourhood queries are natural in Cypher, awkward in SQL. | `backend/memory/graph_isa95.py` (populate/query) + `backend/knowledge_graph/graphrag.py` (grounding). |
| **Redis** (7) | localhost **6379** (container `ai-agent-redis`) | The **live WebSocket broker** — the backend PUBLISHes simulator incidents to Redis pub/sub and fans them out to `/ws` clients. Also transient caching. Redis because pub/sub fan-out to many browser clients must be instant. | `backend/services/ws_broker.py` + the `/ws` endpoint in `backend/main.py`. |

> **You do not load data into these by hand.** Alembic builds every Postgres table on first start (`alembic upgrade
> head`); Neo4j and the memory tables are populated by the app as it runs. The only manual step ever is enabling the
> `vector` extension once (done for you locally).

**Inspect them:**
```powershell
docker exec -it ai-agent-postgres psql -U aiagent -d manufacturing    # then: \dt  to list tables
# Neo4j: open http://localhost:7474  (neo4j / devpass2026)
docker exec -it ai-agent-redis redis-cli    # then: PING
```

---

## 2. Backend — the FastAPI control plane (`backend/`)

**Entry points:** `main.py` (the FastAPI app + all routers + the WebSocket broker + the lifespan that builds the
LangGraph runtime), `config.py` (**every environment variable / parameter** — DB URLs, ports, `GROQ_API_KEY`,
`DEFAULT_LLM_PROVIDER`, CORS, embedder model). Read `config.py` first to see every knob.

**Run it:** `cd backend; uvicorn main:app --port 8000 --reload`   ·   **Test it:** `cd backend; python -m pytest -q`

### 2.1 Package map — what each folder does & where to look
| Package | What it does | Start reading at |
|---|---|---|
| **`api/`** | The HTTP surface — FastAPI routers. Every URL the frontend/curl hits. | `simulation_routes.py`, `conversation_routes.py` (`/factory/*`), `facilities_routes.py` (`/facilities/*`), `metrics_routes.py`, `adoption_routes.py`, `auth`, `inventory`, `ops` |
| **`agents/`** | The agents + the runtime. | `runtime/graph.py` = the **LangGraph self-healing loop** (predict→diagnose→verify→intervene); `runtime/nodes.py` = each loop step; `supply_chain/` = Contract-Net replenishment; `facilities/` = the **energy MILP** (`optimizer.py`, `orchestrator.py`, `tariff.py`); `repair/dispatch.py`; `runtime/durable/` = circuit-breaker/saga/effect-ledger |
| **`ml/`** | The trained models + inference. | `failure_predictor.py` (XGBoost PdM), `rul_transformer.py` (C-MAPSS RUL), `world_model.py` (TTF), `defect_classifier.py` (ResNet-18), `vision_model.py` (YOLOv8), `intervention_rl.py` + `group_scheduler_rl.py` (RL), `causal_discovery.py` (PC), `explainability.py`/`failure_explainer.py` (SHAP/DiCE), `demand_forecaster.py` (LSTM), `injection_classifier.py` |
| **`safety/`** | The functional-safety wrapper — an LLM never actuates un-gated. | `validator.py` (the gate), `sil_bridge.py` (the **only** actuator emitter), `capability_token.py` (unforgeable auth), `contract.py` + `contracts/` (the safety-contract DSL), `sto_ss1.py`, `sil_pl_map.py`, `self_healing/` |
| **`crypto/`** | Post-quantum cryptography. | `pqc_signing.py` (ML-DSA-65), `pqc_kem.py` (ML-KEM-768), `pqc_slh_dsa.py` (SLH-DSA), `key_provider.py`/`key_manager.py` |
| **`memory/`** | The five memory layers. | `audit_chain.py` (signed hash chain), `mem0_adapter.py` (pgvector episodic/semantic), `graph_isa95.py` (Neo4j), `letta_adapter.py` |
| **`conversation/`** | "Ask the factory" + NL problem injection + active diagnosis (Stages 29/35). | `ask.py`, `evidence.py`, `nl_inject.py`, `active_diagnosis.py`, `session_store.py` |
| **`ingestion/`** | Change-Data-Capture: DB edits drive the agent. | `cdc_listener.py` (Stage 13), `cdc_reasoner.py` (Stage 37 bidirectional — diagnoses a value edit) |
| **`integrations/`** | Open industrial standards (talk to real OT). | `vda5050/` (AGV/AMR fleet), `opcua/` (OPC UA), `sparkplug/` (MQTT Sparkplug B) |
| **`governance/`** | EU-AI-Act access control + traceability. | `mac.py` (Bell-LaPadula), `rbac.py`, `traceability.py` (Art-12 decision traces) |
| **`security/`** | Zero-trust + red-team defences. | `prompt_guard.py` (injection detection), `behavioral_monitor.py`, agent identity, `tool_manifest.py` |
| **`a2a/`** | The external Agent-to-Agent boundary. | `server.py` (JSON-RPC), `agent_card.py` (signed card at `/.well-known/agent.json`), `agent_card_cnstyle.py` (Kagenti export) |
| **`mcp_servers/`** | 5 MCP tool servers the runtime consumes. | `sim_world_server.py`, `kpi_query_server.py`, `decision_log_server.py`, `model_inference_server.py`, `policy_query_server.py` |
| **`knowledge_graph/`** | GraphRAG grounding. | `graphrag.py` |
| **`observability/`** | OpenTelemetry tracing → evidence. | `otel_init.py` (spans, `evidence_sink`) |
| **`simulation/`** | The SimPy digital twin (the "factory"). | `sim_world.py` (the world), `calibration.py` (**all physics parameters**: per-stage cycle time, MTBF/MTTR, defect rate, `nominal_kw`), `entities/` (`stage.py`, `robot.py`, `supplier.py`, `incident.py`) |
| **`services/`** | Cross-cutting services. | `decision_engine.py`, `state_manager.py`, `ws_broker.py`, `plan_verifier.py` (neuro-symbolic verify), `slice_runner.py` (the Stage-6 loop), `intervention_policy.py`, `diagnosis.py` |
| **`training/`** | Model training scripts + eval results. | `stage_07_rl_intervention/`, `stage_08_world_model/`, `stage_09_defect/`, `evals/results/*.json` (every A/B number) |
| **`voice/`** | Operator voice interface. | `voice_interface.py` (Whisper STT + Piper TTS) |
| **`jobs/`** | Scheduled jobs. | `post_market_anomaly_sweep.py` (EU-AI-Act Art-72 post-market monitoring) |
| **`alembic/`** | Database schema (migrations). | `versions/0001_init.py … 0010_cdc_value_changes.py` |
| **`tests/`** | The test suite (mirrors the package layout). | `tests/facilities/`, `tests/ingestion/`, `tests/safety/`, `tests/conversation/`, … |

### 2.2 The core request path (how a self-healing decision happens)
```
sensor/CDC/NL report → incident → agents/runtime/graph.py (LangGraph)
   → PREDICT (ml/rul_transformer, ml/world_model)
   → DIAGNOSE (ml/causal_discovery, services/diagnosis)
   → VERIFY  (services/plan_verifier — can REJECT)
   → INTERVENE (safety/validator → safety/sil_bridge — the only actuator path; capability token)
   → PROVE (memory/audit_chain — ML-DSA-65 signed row)   ← every step also emits an OTel span
```

### 2.3 Model parameters & "why" — where to find them
- **Hyperparameters + dataset + metrics for every model:** `compliance/model-cards/*.md` (one card per model) and the
  sibling `models/*.metrics.json`. Summary table: `knowledge-base/KB_02_Models_Inventory.md`.
- **Datasets (what/why/licence):** `knowledge-base/KB_03_Datasets_Catalog.md`.
- **Simulation physics parameters:** `backend/simulation/calibration.py`.
- **Every runtime env var / knob:** `backend/config.py` (+ `.env.example`).

> **Note on `models/`:** the 7 weight files are on your disk but **gitignored**, so they're not in the GitHub repo.
> To add them (via Git LFS): `git add -f models/; git commit -m "Add ML weights (LFS)"; git push`.

---

## 3. Frontend — the Next.js UI (`frontend-nextjs/`)

**Stack:** Next.js 15 (App Router) · React 18 · TypeScript (strict). **Run:** `cd frontend-nextjs; npm install; npm run
dev` → http://localhost:3000. **Config:** `.env.local` → `NEXT_PUBLIC_API_URL` (points at the backend; everything,
including the WebSocket URL, derives from it).

**The API client — the one file that talks to the backend:** `src/lib/api.ts` (all `fetch` calls + the `/ws`
WebSocket; every page imports from here). If you want to know what data any page uses, trace it back to `lib/api.ts`.

### 3.1 Page map (`src/app/<route>/page.tsx`) — each route is a page
| Route (`localhost:3000/…`) | What it shows | Backed by |
|---|---|---|
| `/` , `/landing` | Landing / entry | static |
| `/dashboard` | **Primary live dashboard** — real system state + the live incident feed | `GET /api/simulation/state` + `/ws` |
| `/simulation` | 3D-ish factory line + robots, live state | `GET /api/simulation/state` |
| `/factory` | "Ask the factory" / NL inject console (Stage 29) | `/factory/ask`, `/factory/inject`, `/factory/diagnose` |
| `/supply-chain` | Supply-chain agents view | supply-chain endpoints |
| `/manufacturing`, `/robotics`, `/embodied-agent` | Domain views of the agents | simulation/agent endpoints |
| `/metrics`, `/model-metrics` | KPI + real model metrics (honest empty-state if none) | `/api/metrics/*` |
| `/adoption` | Trust-calibration + autonomy-slider UX (Stage 28) | `/adoption/*` |
| `/knowledge-graph` | ISA-95 graph view | Neo4j-backed endpoints |
| `/problem`, `/solution` | Narrative problem/solution pages | static |
| `/voice` | Voice operator interface | `voice` endpoints |
| `/login` | Auth (incl. face login) | `/api/auth/*` |

### 3.2 Components (`src/components/`)
| Component | Purpose |
|---|---|
| `Navigation.tsx` | The top/side nav across pages |
| `AuthCheck.tsx` | Guards authenticated routes |
| `TrustCalibration.tsx` | The adoption trust widget (confidence + counterfactual + citation) |
| `AutonomySlider.tsx` | The shadow→autonomous progressive-autonomy control |

> **Honesty note:** the primary dashboard + metrics/adoption pages read **real** backend data (or show an honest
> empty-state). A few bespoke visual pages use a labelled deterministic demo layout over the real backend (documented
> in the Stage-28/34 notes). `next build` runs with strict TypeScript (no `ignoreBuildErrors`).

---

## 4. How the three layers connect (end-to-end)
```
Browser (localhost:3000, Next.js)
   │  fetch + WebSocket  (NEXT_PUBLIC_API_URL → localhost:8000)
   ▼
FastAPI backend (localhost:8000)
   ├── writes/reads  ─────────────▶ Postgres 5544   (audit_chain, decision_logs, memory, incidents, cdc_outbox)
   ├── graph queries ─────────────▶ Neo4j 7687      (ISA-95 + GraphRAG)
   └── publishes incidents ───────▶ Redis 6379 ──▶ fans out to the browser via /ws
```

---

## 5. Where to find X (quick lookup)
| I want to… | Go to |
|---|---|
| Understand the whole product visually | `research/system-deep-dive-2026-07/index.html` (+ the "▶ Live Scenario" section) |
| Pitch it | `research/pitch-deck-2026-07/index.html` |
| Run it locally | `commands.md` |
| Deploy it free | `DEPLOY_HUGGINGFACE_VERCEL.md` (or `DEPLOYMENT_RENDER_VERCEL.md`) |
| See what a stage built | `tasks/STAGE_NN_*.md` + `research/stage-explainers/STAGE_NN/index.html` + `knowledge-base/KB_TASK_LOG.md` |
| Know why a decision was made | `compliance/decision-logs/*.md` (ADRs) |
| See model hyperparameters/datasets | `compliance/model-cards/*.md`, `knowledge-base/KB_02`/`KB_03` |
| Check open risks / gaps | `compliance/risk-register.md`, `audits/OPEN_GAPS_LEDGER.md` |
| Read the architecture | `knowledge-base/KB_01_System_Architecture.md`, `KB_24_System_Design_HLD_LLD.md` |
| Understand the self-healing engine | `knowledge-base/KB_25_Causal_SelfHealing_Engine.md` |
| Verify the evidence chain | `python scripts/verify-audit-chain.py` |
| See every API endpoint | http://localhost:8000/docs |

---

## 6. Stop / restart the local stack
```powershell
# stop the DBs (keeps data)
docker stop ai-agent-postgres ai-agent-neo4j ai-agent-redis ai-agent-mqtt
# start them again
docker start ai-agent-postgres ai-agent-neo4j ai-agent-redis ai-agent-mqtt
# the backend + frontend are dev servers you started in terminals — Ctrl+C to stop, re-run per commands.md
```
