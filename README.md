# 🤖 Industrial Agent Control Plane

> **As of 2026-05-18**, the project has been repositioned (PRD v2.0). One-liner:
>
> *A vendor-neutral, EU-AI-Act-grade, post-quantum-ready agent control plane for industrial robot and OT fleets — warehouse-first, then discrete manufacturing, then process industries.*
>
> See [PRD-ai-embodied-agent-v2.md](PRD-ai-embodied-agent-v2.md) for the full v2 spec. The original [PRD-ai-embodied-agent.md](PRD-ai-embodied-agent.md) (v1.0, January 2026) is preserved as archival reference.
>
> Claude Code sessions: read [CLAUDE.md](CLAUDE.md) first; it auto-loads at session start and points at the current task, the role persona, and the mandatory KB reads. [SKILLS.md](SKILLS.md) is the role index.

An open-source agent control plane for autonomous mobile robots (AMRs), manufacturing stages, and supply chain operations. Built on LangGraph + Pydantic AI runtime; speaks MCP internally and A2A across organisations; signs every agent action with ML-DSA-65; carries an EU AI Act Article 11/12 evidence pipeline out of the box.

![Status](https://img.shields.io/badge/status-PRD%20v2.0%20expansion-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![Next.js](https://img.shields.io/badge/next.js-15%20LTS-black)
![React](https://img.shields.io/badge/react-18.3-blue)
![PQC](https://img.shields.io/badge/PQC-ML--DSA--65%20%2B%20ML--KEM--768-purple)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## 🎯 What v2 ships

**Cross-domain operations** (carried over from v1):
- Real-time tracking of 20+ AMRs with 3D visualization
- AI-driven bottleneck detection and throughput optimization
- Demand forecasting with 7-day horizon
- Multi-objective RL (throughput, energy, carbon, quality)
- SHAP + DiCE counterfactual explanations
- Operator-in-the-loop override with feedback learning

**v2 additions** (PRD v2.0):
- **LangGraph + Pydantic AI** runtime with deterministic graph execution and HITL interrupts
- **MCP server suite** (FastMCP) for internal agent→tools — `sim_world`, `kpi_query`, `decision_log`, `model_inference`, `policy_query`
- **A2A protocol surface** for cross-org / cross-vendor agent delegation, with **ML-DSA-65 signed agent cards** and **ML-KEM-768 + X25519 hybrid TLS** at every external boundary
- **VDA 5050 v2.1.0** master controller for multi-vendor AGV/AMR fleets
- **OPC UA + MQTT Sparkplug B v3.0 + ISA-95 Part 2** OT/IT bridge
- **Functional safety wrapper** — LLM plans only; classical SIL-rated controller executes; formal contract gates every actuator command (ISO 10218 / IEC 61508 / ISO 13849-1 / IEC 62061)
- **EU AI Act Annex IV doc-pack generator** + append-only ML-DSA-signed `audit_chain` for Article 12 record-keeping
- **Agent memory** stack: Mem0 + pgvector (episodic, default), Letta (opt-in), Neo4j ISA-95 graph (semantic), DVC (procedural), `audit_chain` (immutable evidence)
- **OpenTelemetry GenAI semconv** + Langfuse self-hosted + Arize Phoenix evals — observability and immutable evidence sinks separated by design
- **Zero paid SaaS.** Apache 2.0 / MIT throughout.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Robotics │ │ Mfg      │ │ Supply   │ │ Decision │           │
│  │ 3D View  │ │ Pipeline │ │ Chain    │ │ Panel    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ WebSocket / REST
┌───────────────────────────┴─────────────────────────────────────┐
│                    FastAPI Backend                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ State    │ │ Decision │ │ ML       │ │ Data     │           │
│  │ Manager  │ │ Engine   │ │ Models   │ │ Pipeline │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
   ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
   │ YOLOv8    │  │ LSTM      │  │ PPO       │  │ SHAP      │
   │ Vision    │  │ World     │  │ Policy    │  │ Explainer │
   └───────────┘  └───────────┘  └───────────┘  └───────────┘
```

## ⚠️ Honest current status (Stage 1, 2026-05-11)

This repo is **mid-build**. The frontend renders all 8 pages but reads
exclusively from in-process mock generators; the backend has a healthy
FastAPI app and WebSocket loop but most ML inference paths still fall
back to `random.uniform` / `random.choice`. Do not mistake "it boots and
renders" for "it works."

For the authoritative picture of what is real vs theatrical and the
15-stage path to a real system, read:

- [`knowledge-base/KB_01_System_Architecture.md`](knowledge-base/KB_01_System_Architecture.md) — what is actually running.
- [`knowledge-base/KB_02_Models_Inventory.md`](knowledge-base/KB_02_Models_Inventory.md) — which models are trained vs. stubbed.
- [`knowledge-base/KB_TASK_LOG.md`](knowledge-base/KB_TASK_LOG.md) — append-only log of every stage's outcome (read top-to-bottom for the freshest reality).
- [`tasks/`](tasks/) — the executable task doc for the next-in-line stage.

CI gates (`.github/workflows/ci.yml`) enforce a strictly-decreasing
"theatrical-fallback count" from `scripts/audit.sh`, so the gap between
the README and reality can only shrink, never grow.

## 🚀 Quick Start

- Python 3.11
- Node.js 20 LTS
- Docker Desktop (for the compose stack)

#### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Or simply double-click: `start_backend.bat`

#### Frontend Setup

```bash
cd frontend-nextjs
npm install
npm run dev
```

Or simply double-click: `start_frontend.bat`

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Docker Setup

```bash
cd docker
docker-compose up -d
```

## 📁 Project Structure

```
ai-embodied-agent/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Pydantic settings
│   ├── api/
│   │   ├── routes.py        # REST endpoints
│   │   └── schemas.py       # Pydantic models
│   ├── services/
│   │   ├── state_manager.py # System state management
│   │   └── decision_engine.py # AI decision orchestration
│   ├── ml/
│   │   ├── vision_model.py  # YOLOv8 wrapper
│   │   ├── world_model.py   # LSTM prediction
│   │   ├── rl_policy.py     # PPO policy
│   │   └── explainability.py # SHAP + attention
│   ├── pipeline/
│   │   ├── mqtt_listener.py # MQTT telemetry
│   │   ├── video_processor.py # Video inference
│   │   └── api_integrations.py # External APIs
│   └── tests/
├── frontend-nextjs/             # Next.js 15 LTS (active frontend)
├── frontend/                    # Vite, legacy — slated for deletion in Stage 1
├── database/
│   └── schema.sql               # Archival; Alembic owns the schema from Stage 1 forward
├── backend/alembic/
│   └── versions/0001_init.py    # Authoritative schema (Stage 1)
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── knowledge-base/              # Spec & state of truth (read before changing code)
├── compliance/                  # Risk register, model cards, ADRs
├── tasks/                       # Per-stage executable task docs
├── scripts/
│   ├── audit.sh                 # CI-enforced anti-theater gate
│   └── deploy.sh                # Cloud Run deployment
└── .github/workflows/ci.yml     # CI gate: audit / KB-diff / gitleaks / tests
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/system-state` | GET | Current system state |
| `/api/decision` | POST | Trigger AI decision |
| `/api/prediction` | GET | Future state prediction |
| `/api/explainability/{id}` | GET | Decision explanation |
| `/api/override` | POST | Human override |
| `/api/optimization/weights` | GET/POST | Optimization weights |
| `/ws` | WebSocket | Real-time updates |

## ⚙️ Configuration

Copy `.env.example` to `.env.local` at the repo root and fill in the values.
`docker-compose.yml` reads every variable from there; `.env.local` is
git-ignored. Required keys include Postgres credentials, Neo4j credentials,
and at least one of `GROQ_API_KEY` / `GEMINI_API_KEY` (Ollama local is the
fallback path).

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

## 🚢 Deployment

### Google Cloud Run

```bash
export GCP_PROJECT_ID=your-project-id
./scripts/deploy.sh deploy
```

### Vercel (Frontend)

```bash
cd frontend-nextjs
vercel --prod
```

## 📊 Performance Targets

| Metric | Target |
|--------|--------|
| ML Model Size | < 500MB |
| Inference Latency | < 500ms |
| Docker Image | < 2GB |
| WebSocket Update | < 100ms |

## 🛠️ Tech Stack (target)

**Backend:** FastAPI, PyTorch, Ultralytics, Alembic (migrations), DVC (datasets)  
**Frontend:** Next.js 15 LTS, React 18.3, Tailwind v3, R3F, Framer Motion  
**Database:** Self-hosted Supabase (Postgres + Realtime), Neo4j, Redis  
**Agent orchestration:** LangGraph + Groq / Gemini / Ollama (failover)  
**ML Models:** YOLOv8 (real), CNN defect / LSTM / PPO / SHAP (Stage 4–10)  
**DevOps:** Docker Compose, GitHub Actions CI, gitleaks, Git LFS  

See [`knowledge-base/KB_01_System_Architecture.md`](knowledge-base/KB_01_System_Architecture.md) for the live picture of which pieces are real, stubbed, or planned.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with ❤️ for manufacturing optimization
