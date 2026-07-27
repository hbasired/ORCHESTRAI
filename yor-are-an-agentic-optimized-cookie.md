# Production-Grade AI Embodied Agent — Master Implementation Plan

## Context

You are building an embodied AI agent that coordinates three sub-agents (Robotics, Manufacturing, Supply Chain) inside a manufacturing/warehouse plant. The system perceives plant state, predicts the next 5–60 minutes, detects emerging issues (machine cracking, robot battery, late delivery, defects, bottlenecks), and instructs sub-agents to re-plan so the plant absorbs the disruption with minimal loss. The end goal is a fundable, pilot-ready product targeted at Amazon, DHL, Siemens, Bosch, Huawei, and similar manufacturing/logistics primes.

**Honest audit of current state** (so the plan is grounded in reality, not the README):

| Layer | Reality |
|---|---|
| FastAPI backend, sub-agent coordination logic, LLM client (Groq/Gemini), WebSocket infra | **Real and functional** |
| YOLOv8 vision (`backend/yolov8n.pt`), Hindi/Telugu Piper TTS ONNX | **Real weights present** |
| `frontend-nextjs/` 8 pages with animations | **Real UI, but data is `Math.random()` from `generateMockState()`; never calls backend** |
| LSTM world model, PPO policy, ANN demand/energy, CNN defect/obstacle | **PyTorch classes exist; no trained weights; all fall back to `random.uniform` or hardcoded heuristics** |
| SHAP explainability | **Mocked with `random.uniform(0.3, 0.5)`** |
| `/voice` page | **String-matching against a hardcoded `RESPONSES` dict; no STT/LLM/TTS calls** |
| `/api/metrics/models` | **Returns hardcoded "demo" MAE/R²/accuracy strings** |
| Database (`database/schema.sql`) | **Schema exists in a single SQL file; never auto-applied; data is ephemeral** |
| Simulation engine | **Real state machine, but bottlenecks/collisions are randomly injected on a tick counter** |
| Vite `frontend/` | **Abandoned in favor of `frontend-nextjs/`** |

The reason this matters: a single VC technical due-diligence call will catch any of these. The plan below replaces every fake with a real, trained, observable component, in a sequence where each stage produces a demonstrable artifact.

The plan is intentionally split into 15 stages with a task document per stage. After each stage completes, we re-audit, update the knowledge base, and write the next task document — so the build stays aligned with reality.

---

## Critical Files Already In Place (will be reused, not rewritten)

- `backend/main.py` — FastAPI app + WebSocket broadcast loop (works, will be extended)
- `backend/agents/embodied_agent.py` — coordinator (logic real, ML stubs to replace)
- `backend/agents/{robotics,manufacturing,supply_chain}_agent.py` — sub-agents (OODA loop real)
- `backend/agents/llm_client.py` — Groq/Gemini/Ollama client (production quality)
- `backend/ml/{vision_model,neural_networks,rl_policy,world_model,explainability}.py` — model class skeletons (keep classes, replace fallbacks with loaded weights)
- `backend/simulation/engine.py` — replace internals with SimPy; keep the public interface
- `backend/data/supabase_service.py` — the schema-in-comments needs to become real migrations
- `database/schema.sql` — promote to versioned Alembic migrations
- `docker/docker-compose.yml` — solid; needs secret hygiene
- `frontend-nextjs/src/lib/api.ts` — endpoint declarations exist; mock fallbacks need to become last-resort
- `models/*.onnx` — Piper TTS weights stay
- `backend/yolov8n.pt` — pretrained YOLO baseline stays; will be fine-tuned later

## Files/Folders to Retire

- `frontend/` (Vite) — **delete in Stage 1** (decision confirmed); git history preserves it
- All `generateMockState()` / `generateRobots()` etc. functions in `frontend-nextjs/src/app/**/page.tsx` — to be replaced by WebSocket subscription in Stage 3
- Hardcoded demo dictionaries in `backend/api/metrics_routes.py:192-310` and `:313-343` — deleted in Stage 1
- Hardcoded `RESPONSES` dict in `frontend-nextjs/src/app/voice/page.tsx:277-295` — deleted in Stage 11

## Confirmed Decisions

- **Trained model weights**: stored in **Git LFS** in this repo. `.gitattributes` will track `*.pt`, `*.pth`, `*.h5`, `*.onnx`, `*.pkl`, `*.joblib`. Each weights file ships with a sibling `.metrics.json` and `.card.md` (training git SHA, dataset hash, eval metrics).
- **Supabase**: **self-hosted in `docker/docker-compose.yml`** — adds `supabase-postgres`, `supabase-realtime`, `supabase-studio`, `supabase-meta`, `supabase-rest` services. No customer data leaves the box; matches what industrial buyers will require.
- **Vite frontend**: **deleted** in Stage 1.

---

## Stage 0 — This Plan (current)

**Output of this stage**: this plan file. On approval, execute Stage 1 of work which is "Create the knowledge base + Stage 1 task document."

---

## Knowledge Base Structure (created in Stage 1)

A `knowledge-base/` folder at repo root, written in Markdown so we can read it back into context every session. Each file has a fixed shape (Purpose / Source-of-truth / Last-updated / Body) so updates are mechanical.

| File | Purpose |
|---|---|
| `KB_README.md` | Master index; rules for updating the KB; "what changed when" pointer |
| `KB_01_System_Architecture.md` | The actual code architecture (services, data flow, deployment topology) — kept honest by reading from the repo, not from marketing docs |
| `KB_02_Models_Inventory.md` | Every model: class file path, weights file path, training script, dataset, status (untrained / trained / production), last metrics, hyperparameters |
| `KB_03_Datasets_Catalog.md` | Every approved dataset: source URL, license, size, download command, intended model, sanity-check notebook |
| `KB_04_Data_Schema.md` | Postgres schema, Redis keys, simulation entity model, WebSocket message envelopes, Pydantic schemas |
| `KB_05_Simulation_Spec.md` | SimPy entity definitions, scenario catalog, problem catalog (machine crack, late delivery, robot down, demand spike, defect surge, etc.) |
| `KB_06_Agent_Coordination_Protocol.md` | Embodied agent ↔ sub-agents message format, decision protocol, conflict resolution rules, override semantics |
| `KB_07_API_Contracts.md` | REST + WS endpoints with request/response schemas; the canonical contract between backend and frontend |
| `KB_08_Frontend_Pages_Spec.md` | Page-by-page: which API + WS topics it consumes, which interactions it produces, animation rules |
| `KB_09_UX_Scenarios.md` | Demo flow: 1-min normal operation → problem injection → embodied response → optimized re-state. Includes the chat interface and DB-driven problem flow. |
| `KB_10_Production_Hardening.md` | Secrets, MLOps, monitoring, CI/CD, drift detection, reliability targets |
| `KB_11_Pitch_Strategy.md` | Target customers (Amazon, DHL, Siemens, Bosch, Huawei), value props, demo storyboard, KPIs to show, ROI math, pilot integration playbook |
| `KB_TASK_LOG.md` | Append-only log: which task doc, what shipped, what didn't, what we learned, next-stage adjustments |

**Update rule**: at the end of every stage, the KB files touched by that stage MUST be updated before the task doc is marked complete. The `KB_TASK_LOG.md` gets a new entry. This is how we stay in sync across sessions.

---

## Stage 0.5 — Refresh Log (2026-05-11)

> Inserted during the Stage-0 stress-test refresh. The original Stage-1-through-Stage-15 text below is preserved verbatim; this section captures the twelve material developments since the plan was first written, with pointers to the stage that absorbs each. Each affected stage block below also carries an "**Update (2026-05-11)**" bullet with the concrete delta. Detailed research backing every line lives in `research/initial-research.md` §6.

| # | Finding | Lands in |
|---|---|---|
| 1 | EU AI Act high-risk deadline **2 Aug 2026** — manufacturing AI in scope (Annex III); Articles 9/11/12/14/16/26/49 obligations | Stage 14 (expanded) + Stage 1 (compliance/ scaffold) |
| 2 | NIST AI RMF **Agentic Profile** (Feb 2026) — prompt-injection-via-tool-outputs, cross-session memory persistence, tool-chain poisoning | Stage 11 + Stage 14 |
| 3 | **LangGraph won** the 2026 framework war; AutoGen in maintenance; LangSmith audit-trail integration | Decision in Stage 1; optional migration in Stage 11 |
| 4 | **MsFormer** multi-scale Transformer beats SOTA on industrial PdM; trend = "agentic PdM" | Stage 4 — added as third baseline |
| 5 | **LeWorldModel / JEPA-2026** — single-GPU, ~15M params, 48× faster planning than foundation-model approaches | Stage 8 — flagged as v2 swap behind stable interface |
| 6 | **OpenVLA / π0** VLAs still industrial-pilot stage; confirms v1 deferral | No v1 change; v2 candidate |
| 7 | **NVIDIA Isaac Sim Apache-2.0** — synthetic warehouse data; KION/Accenture/Siemens precedent | Stage 9 — now the primary track |
| 8 | **SALABIM** native 2D/3D animation; SimPy doesn't | Stage 2 — staying SimPy, SALABIM logged as v2 fallback |
| 9 | **FastAPI WS scaling** — uvloop mandatory; Redis pub/sub broker for multi-worker; async-only inside WS handlers | Stage 3 — added as acceptance criterion |
| 10 | **Funding**: Augment $85M, Pallet $27M, CoPallet; Series A AI avg $51.9M; Gartner 40% by EOY 2026; 80% warehouses unautomated | Stage 15 |
| 11 | **MVTec AD is research-only** — pilots need a commercial license; Real-IAD / KSDD2 / AITEX are commercial-friendly | Stage 5 — Real-IAD primary, MVTec secondary |
| 12 | **Latency budget** — PRD says <500ms; plan had no per-hop budget | Cross-cutting; lands in KB_10 |

**Cross-cutting additions (apply to every stage):**

1. **Latency budget** — Total p95 ≤205 ms across hops (WS in 5 + world-model 40 + PPO 15 + SHAP-cached 20 + LLM Groq 120 + WS out 5); ~295 ms headroom before 500 ms SLA breach. Owns: `KB_10_Production_Hardening.md`.
2. **Data versioning** — Every dataset has `<name>.dvc` + SHA + license + mirror URL + `CARD.md`. CI rejects un-versioned data in `data/`.
3. **Demo storyboard** — 60-sec auto-loop: 0–15s normal → 15–25s injection → 25–55s embodied response → 55–90s post-recovery KPIs. Owns: `KB_09_UX_Scenarios.md`.
4. **Test scaffolding** — pytest + httpx + pytest-asyncio + Playwright; coverage ≥60% from Stage 4 onward.
5. **Failure-mode fallbacks** — Colab dies → Kaggle mirror notebook; dataset 404 → HuggingFace Hub mirror; Groq outage → Ollama-local LLM; cutting-edge frontend churn → LTS pin.
6. **EU AI Act technical scaffolding** in `compliance/` — risk-register, model-cards/, decision-logs/, human-oversight, incident-playbook.
7. **NIST RMF agentic controls** — prompt-injection sanitizer on every tool output before LLM context; cross-session memory namespaced by `incident_id`; tool-chain provenance (caller, tool, input/output hash) on every action.

**Iterative cycle protocol (closes every stage):**
1. `scripts/audit.sh` — re-audit; mock-fallback count must strictly decrease vs prior stage.
2. **Metrics capture** — every model writes `weights.pt` + `weights.metrics.json` + `weights.card.md` (git SHA, dataset hash, eval metrics).
3. **KB update** — bump every KB file in the stage's "KB Updates Expected" list; bump `Last-updated` frontmatter; same PR as code.
4. **Task log append** — `knowledge-base/KB_TASK_LOG.md` entry: Shipped / Skipped / Learned / Next-stage adjustments.
5. **Decision log** — any architectural decision lands in `compliance/decision-logs/YYYY-MM-DD_<topic>.md` (doubles as EU AI Act Art. 12 evidence).
6. **Next-stage task doc** — `tasks/STAGE_NN_<slug>.md` written before the stage closes.
7. **CI gate** — merge blocked unless audit green + KB diff present + model-cards present for new weights + gitleaks clean.

---

## 15-Stage Roadmap

Each stage produces (a) a measurable demoable artifact, (b) updated KB files, (c) a wrap-up summary that becomes the input to the next stage's task document. A stage is **not done** until its KB updates land.

### Stage 1 — Foundation Hardening & Knowledge Base Bootstrap

**You do**: Nothing. This stage is all engineering setup.

**I do**:
1. Create the 12 KB files above with the audit findings as initial content.
2. Delete the Vite `frontend/` directory.
3. Promote `database/schema.sql` to Alembic migrations (`backend/alembic/`) so schema is created automatically on container start. Schema lives in versioned migration files; future changes go through `alembic revision`.
4. Add self-hosted Supabase services to `docker/docker-compose.yml` (`supabase-postgres`, `supabase-realtime`, `supabase-studio`, `supabase-meta`, `supabase-rest`). Replaces the standalone `postgres` service.
5. Move hardcoded passwords (`aiagent2026`, etc.) out of `docker-compose.yml` into a `.env.example` + `.env.local` pattern with secret rotation documented.
6. Initialize Git LFS, add `.gitattributes` for weights file extensions, document the LFS workflow for Colab → repo uploads.
7. Delete fabricated demo metrics from `backend/api/metrics_routes.py`. Endpoints return `503` until real metrics exist — no more theatre.
8. Create `backend/training/` folder structure with placeholder Colab notebook stubs (one per model: cmapss_lstm, ai4i_ann, neu_det_cnn, mvtec_ae, m5_demand, ppo_factory, world_model_lstm, yolo_finetune).
9. Add `.github/workflows/ci.yml` — lint (ruff/black for Py, eslint for TS), pytest, build Docker images, LFS bandwidth check.
10. Pin Python dependencies via `pip-tools` (`requirements.in` → `requirements.txt`); pin Node deps via `package-lock.json` audit.

**Demo artifact**: `docker compose up` brings up Postgres with auto-applied schema, Redis, Neo4j, MQTT, FastAPI; CI is green; KB files render in GitHub.

**Why this first**: every later stage assumes a real DB, a real CI, and a place to write its KB updates.

**Update (2026-05-11)**:
- Add `.env.example` + `docker/secrets/.gitkeep`; remove every hardcoded password from `docker-compose.yml`.
- Scaffold `backend/tests/` (pytest, pytest-asyncio, httpx) + `frontend-nextjs/__tests__/` (vitest/jest + Playwright).
- Pin **Next 15.x LTS + React 18.3 + Tailwind 3 LTS** (drop bleeding-edge Next 16/React 19/Tailwind 4 to avoid demo-day breakage; can re-bump in v2 after pilots).
- Create `compliance/` folder: `risk-register.md`, `model-cards/`, `decision-logs/`, `human-oversight.md`, `incident-playbook.md`.
- Add DVC remote + `data/datasets/CARD.template.md` for data versioning protocol.
- Record decision: bespoke coordinator now, optional LangGraph migration in Stage 11.
- Add `scripts/audit.sh` (the recurring re-audit used by the iterative cycle).

---

### Stage 2 — SimPy Physics-Based Factory Simulator

**You do**: Run the simulator locally, eyeball the event log, tell me if any plant dynamics feel wrong (we'll calibrate together).

**I do**:
1. Replace `backend/simulation/engine.py` internals with a SimPy discrete-event model:
   - Resources: 10 production stages (machines), conveyor segments, charging stations.
   - Processes: order arrivals (Poisson), product flow stage-by-stage with stochastic cycle times, robot fleet of 20 AMRs servicing inter-stage transport, MTBF/MTTR for each machine, supplier lead times.
   - Events: machine breakdown, robot low-battery, supplier delay, demand spike, defective batch, conveyor jam.
2. Emit every state transition to (a) Postgres for history, (b) Redis for hot state, (c) WebSocket for the frontend.
3. Expose `POST /api/simulation/inject` with a typed problem catalog (`machine_crack`, `robot_down`, `late_delivery`, `demand_spike`, `defect_surge`, `power_dip`).
4. Calibrate baseline so the "normal" run yields a reasonable throughput (~500 units/hr) and stable queues.

**Demo artifact**: `curl POST /api/simulation/inject {"type":"machine_crack","stage_id":4,"eta_minutes":15}` → DB rows, WS messages, agent reacts.

**Reference**: SimPy is the standard Python DES library; stable, single-process, fits inside the existing FastAPI process or a sidecar container.

**Update (2026-05-11)**:
- Decision logged: SimPy chosen for community size + tutorial base; SALABIM (native 2D/3D animation, more concise OO API) deferred to v2 fallback.
- Configure Postgres with `wal_level=logical` from the compose file — Stage 13's Realtime CDC needs this and discovering it later is painful.
- Persistence of every state transition must be **async** (no sync DB call ever blocks a SimPy event loop).

---

### Stage 3 — WebSocket End-to-End: Kill All Frontend Mocks

**You do**: Click around all 8 pages in the browser, confirm everything updates from real backend state.

**I do**:
1. Backend: ensure WS broadcasts include all entity types (robots, stages, inventory, suppliers, alerts, decisions) at 5–10 Hz.
2. Frontend: introduce a `useSimulationState` hook + Zustand store; subscribe to WS once at app shell level; remove every `setInterval(...generateMockState)` from `page.tsx`, `robotics/page.tsx`, `manufacturing/page.tsx`, `supply-chain/page.tsx`, `embodied-agent/page.tsx`.
3. Add a connection status indicator + auto-reconnect with backoff.
4. Make `getMockState()` in `frontend-nextjs/src/lib/api.ts` only fire when WS has been disconnected >5s, and show an "Offline" banner.

**Demo artifact**: stop the backend → frontend shows "Offline"; restart backend → animations resume from current sim state, not from a fresh random seed.

**Update (2026-05-11)**:
- Add **Redis pub/sub broker** in the WS broadcast layer even with a single worker, so multi-worker scaling becomes a config flip (NGINX `ip_hash` + N uvicorn workers) instead of a rewrite.
- **uvloop is mandatory** — single uvloop worker ≈ 10K concurrent WS connections; without it, half that.
- Add a CI lint rule (ast-grep or custom ruff plugin) that forbids any sync DB call inside a WS handler; one such call freezes the entire worker.
- `useSimulationState` hook spec includes explicit backpressure: drop stale frames when client falls behind rather than queueing unbounded.
- Acceptance criterion: WS p95 broadcast latency under 1K simulated clients ≤ 25 ms.

---

### Stage 4 — Predictive Maintenance: CMAPSS LSTM + AI4I 2020 ANN (Colab Training)

**You do**: Run two Colab notebooks I provide, tune learning rate / sequence length on a free T4, save `.pt` files, upload them back to repo via Git LFS or Supabase Storage.

**I do**:
1. Build dataset loaders + training scripts in `backend/training/predictive_maintenance/`:
   - **NASA C-MAPSS** (turbofan RUL): LSTM regression → predicts remaining useful life from 21 sensor channels. The standard benchmark for "machine will fail in N minutes." → maps to `machine_crack` warning in our system.
   - **AI4I 2020 Predictive Maintenance** (UCI, ~10K rows, 5 failure modes): ANN binary/multi-class classifier on tool wear, torque, temperature → early warning.
2. Hand you a Colab notebook per dataset that downloads, preprocesses, trains, evaluates, and pickles weights. Each notebook includes hyperparameter tuning grid (Optuna) and produces a metrics card we'll paste into `KB_02_Models_Inventory.md`.
3. After you upload the `.pt` files, wire them into `backend/ml/world_model.py` (LSTM) and `backend/ml/neural_networks.py` (ANN). Remove the random fallbacks. If a weight file is missing, the endpoint returns `503` — never fake data.
4. Add a "machine health" panel on `/manufacturing` showing real RUL bars per stage.

**Demo artifact**: Inject `machine_crack` at stage 4 → LSTM RUL panel for stage 4 drops in real time → embodied agent escalates → sub-agent re-routes flow.

**Datasets** (links go in `KB_03_Datasets_Catalog.md`):
- C-MAPSS: NASA Open Data Portal — CC0
- AI4I 2020: UCI ML Repo — CC BY 4.0

**Update (2026-05-11)**:
- Add **MsFormer (multi-scale Transformer)** as the third baseline — lightweight attention beats prior SOTA on C-MAPSS-class benchmarks and aligns with the "agentic PdM" narrative.
- All three baselines (LSTM RUL, ANN classifier, MsFormer) are tracked in **MLflow**; best-by-metric-card auto-selects the production weight.
- Every weight ships with `weights.metrics.json` + `weights.card.md` (training git SHA, dataset hash, eval metrics, training command) per the data-versioning protocol.
- Acceptance criterion: must not regress the cross-cutting latency budget (LSTM fwd ≤ 40 ms p95 on CPU).

---

### Stage 5 — CNN Defect & Anomaly Detection: NEU-DET + MVTec AD (Colab Training)

**You do**: Run two Colab notebooks, train CNNs on T4, save weights.

**I do**:
1. **NEU-DET** (1800 grayscale steel surface images, 6 classes: rolled-in scale, patches, crazing, pitted, inclusion, scratches): supervised CNN classifier (ResNet-18 transfer learning) → replace `CNNDefectDetector` random fallback in `backend/ml/neural_networks.py`.
2. **MVTec AD** (5000+ images, 15 categories, pixel-precise annotations): convolutional autoencoder for unsupervised anomaly detection → handles defect classes the supervised model has never seen.
3. Inference service exposes `POST /api/vision/inspect` taking an image; returns class + confidence + heatmap. Hook into simulator's "defective batch" event.
4. UI: live "defect feed" panel on `/manufacturing` showing the last N inspections with their heatmaps.

**Demo artifact**: Inject `defect_surge` → CNN classifies sample frames → defect rate per stage rises in real time → supply chain agent reorders affected stage's input materials.

**Datasets**: NEU-DET (Kaggle, public), MVTec AD (research-only, free for non-commercial; for commercial pilots we'll need their license — flag in pitch strategy).

**Update (2026-05-11)**:
- **Swap defect autoencoder primary dataset to Real-IAD** (commercial-friendly license, real industrial defects, 2024+ benchmark). Keep MVTec AD as a research-only secondary used to compare against published baselines, but never the primary for pilot deployment.
- Alternative commercial-friendly fallbacks documented in `KB_03`: **KSDD2** (small, fast Colab iteration) and **AITEX** (textile vertical).
- Acceptance criterion: F1 on Real-IAD must be within 5pp of the MVTec-trained baseline, or the gap is documented with mitigation in `KB_03`.

---

### Stage 6 — Demand Forecasting: M5 Walmart Hierarchical (Colab Training)

**You do**: Train an LSTM and a tiny Temporal Fusion Transformer (or simple Transformer) on M5 in Colab; pickle.

**I do**:
1. Pre-process M5 (3,049 product time-series × 5.4 yrs of daily sales) into our supply chain entity model. Map our 5 SKUs to top-N M5 products so we have a "real" history.
2. Train two models: LSTM seq-to-seq for 7-day forecast + Transformer with explanatory variables (calendar, price, promotions). Compare WRMSSE; pick winner.
3. Replace `ANNDemandPredictor` in `backend/ml/neural_networks.py`. Forecast feeds Q-learning supplier order policy.
4. UI: the `/supply-chain` 7-day forecast chart shows real predictions with confidence intervals (instead of the current `Math.random()` line).

**Demo artifact**: Inject `demand_spike` → forecast shifts → supplier orders advance → inventory bars rebalance.

**Update (2026-05-11)**:
- Add **Informer or PatchTST** Transformer baseline alongside the M5 LSTM; 2024–2026 results consistently show Transformer-with-explanatory-variables outperforming pure LSTM on horizon coverage and reliability.
- Selection metric is **WAPE**, not MAE alone, because Walmart hierarchical sales are heavily skewed and MAE under-weights the rare-but-expensive misses.
- Track LSTM, Informer, PatchTST in MLflow; pick winner by WAPE per the `KB_02_Models_Inventory.md` protocol.

---

### Stage 7 — PPO Decision Policy on Custom Gym Environment (Colab Training)

**You do**: Run the Colab notebook that wraps our SimPy simulator as a Gymnasium env and trains a PPO policy with Stable-Baselines3. ~2–4 hours on T4 for a starter policy. Iterate on reward shaping with me.

**I do**:
1. Build `backend/training/rl_env/factory_env.py`: Gymnasium-compatible env wrapping the SimPy simulator. Observation: ~500-dim state vector (robot positions/batteries, stage queues, inventory, demand forecast, current alerts). Action: continuous (50-dim) — robot setpoints, stage throughputs, supplier order adjustments.
2. Reward function: `+throughput +quality -energy -carbon -disruption_risk -excess_inventory`, weights configurable via UI sliders.
3. Train PPO with Stable-Baselines3 (`MultiInputPolicy` or `MlpPolicy`); checkpoint every 100K steps.
4. Replace `backend/ml/rl_policy.py` heuristic fallback with the trained policy. Expose via `POST /api/decision`.
5. Compare-mode: run two simulators in parallel, one with PPO policy and one with rule-based baseline, broadcast both — this is the "before/after" the embodied-agent page already pretends to show.

**Demo artifact**: side-by-side simulator runs over 60 seconds with same disruption injected — PPO version absorbs it with 25–30% less throughput loss.

**Reference**: PPO consistently outperforms dispatch heuristics by 6–9× optimality gap on JSSP benchmarks (recent 2025 research). This is the algorithm with the best track record for production scheduling.

**Update (2026-05-11)**:
- Add a **safety-constraint reward shaper** so the PPO policy cannot select actions that violate hard constraints (zero division, unsafe robot velocities, throughput beyond stage capacity). This is the NIST RMF Agentic Profile "excessive agency" mitigation (OWASP LLM08 analogue).
- Every PPO action is logged with `decision_id`, observation hash, action vector, predicted reward, actual reward — feeds the EU AI Act Art. 12 automatic-logging requirement directly.
- Reward weights are exposed via UI sliders **but bounded** — operators can prefer throughput vs energy vs carbon, but cannot zero out the safety term.

---

### Stage 8 — World Model LSTM Trained on Simulator Histories

**You do**: Run the Colab notebook on logs we generate from the SimPy simulator; pickle weights.

**I do**:
1. Generate 100K+ simulated steps of state-action-next-state tuples from Stage 2's simulator.
2. Train an LSTM (or 1D-CNN-LSTM hybrid, per the C-MAPSS literature) to predict the 5/15/30/60-minute-ahead state. Output includes uncertainty (heteroscedastic head).
3. Replace the random-perturbation fallback in `backend/ml/world_model.py`. Wire into `GET /api/prediction`.
4. UI: "5-min look-ahead" panel on `/embodied-agent` shows predicted vs actual rolling — credible.

**Demo artifact**: prediction 5 minutes before a synthetic bottleneck shows queues climbing, agent acts on the prediction not the symptom.

**Update (2026-05-11)**:
- Keep LSTM (or 1D-CNN-LSTM hybrid) as the v1 world model — Colab-trainable on simulator histories, fits the 40 ms latency budget.
- Flag **LeWorldModel / JEPA-2026** as the v2 swap once a paying pilot funds GPU time: ~15M params, single-GPU stable, 48× faster planning than foundation-model approaches.
- Implementation note: the world-model interface (`predict(state, horizon) -> (mean, std)`) stays stable, so swapping LSTM → JEPA is a substrate change, not a contract change.

---

### Stage 9 — YOLOv8 Robot Detection Fine-Tune (Optional / Vision Pilot)

**You do**: For now, run the existing pretrained `yolov8n.pt` on a sample logistics video. Later, fine-tune on a labeled warehouse top-down dataset (we'll source one).

**I do**:
1. Wire `backend/ml/vision_model.py` to a real video stream (file or RTSP). Remove the random-detection fallback.
2. Fine-tune on a curated logistics dataset (combination of public AGV/AMR datasets; actual sourcing tracked in `KB_03_Datasets_Catalog.md`).
3. Add a `/robotics` overlay showing real bounding boxes on a test video alongside the synthetic 2D map.

**Demo artifact**: Live camera feed → real robot detections → positions reconciled with simulator state.

**Update (2026-05-11)**:
- **Primary path is now NVIDIA Isaac Sim (Apache 2.0)** — generate synthetic top-down warehouse video + labels, fine-tune YOLOv8 on the synthetic set. Removes the "no canonical warehouse robot dataset" blocker called out in the original plan.
- Real-video fine-tune becomes optional and only happens if a pilot customer supplies labeled footage.
- Side benefit: namedropping Isaac Sim in the pitch deck = credibility with Siemens/KION/Accenture-style customers who use the same substrate for their digital twins.

---

### Stage 10 — Real SHAP / Integrated Gradients Explainability

**You do**: Sanity-check explanations on a few decisions; tell me which features humans expect to dominate.

**I do**:
1. Replace the `random.uniform(0.3, 0.5)` mock in `backend/ml/explainability.py` with:
   - `shap.GradientExplainer` for the LSTM world model and PPO policy network.
   - Captum `IntegratedGradients` for tabular ANN paths.
2. Cache explanations per decision_id in Redis; render via `GET /api/explainability/{decision_id}`.
3. UI: real SHAP waterfall + attention heatmap on every decision card.

**Demo artifact**: click any decision in the live feed → real per-feature attribution that updates as the model updates.

**Reference**: SHAP on LSTMs is known to be unstable; we'll combine it with Integrated Gradients per recent literature, which is more numerically stable for recurrent architectures.

**Update (2026-05-11)**:
- Add **counterfactual explanations (DiCE)** alongside SHAP + Captum IG. EU AI Act Art. 14 (human oversight) requires the system to support "why-not" reasoning ("what minimal change in inputs would have flipped this decision?"), not just "why" attribution.
- Explanation outputs feed `compliance/decision-logs/` directly — every decision in the live feed is auditable end-to-end (inputs → world-model prediction → PPO action → SHAP attribution → DiCE counterfactual → operator override if any).

---

### Stage 11 — Voice Pipeline End-to-End

**You do**: Speak into the mic on `/voice`; hear a real reply; tell me where it breaks.

**I do**:
1. Frontend: real `MediaRecorder` audio capture, send WAV blob to `POST /api/voice/process`.
2. Backend: real Whisper STT (already wired in `backend/voice/voice_interface.py`; just enforce no-fake-fallback), stream LLM reply via Groq, real Piper TTS (Hindi/Telugu ONNX already in repo + English).
3. Voice replies are grounded by RAG over the live system state — the LLM is given a system-state JSON snapshot in its context, so "what's wrong with stage 7?" gets a real answer.
4. Delete the `RESPONSES` dict and `getResponse()` string-matcher in `frontend-nextjs/src/app/voice/page.tsx`.

**Demo artifact**: ask "Are any robots low on battery right now?" → real answer reading from real Redis state.

**Update (2026-05-11)**:
- **Prompt-injection sanitizer** on every external/tool output before it reaches LLM context — NIST RMF Agentic Profile mitigation. A poisoned DB row must not be able to hijack the system prompt.
- **Cross-session memory namespacing** — agent memory is keyed by `incident_id` and cleared on session boundary. No state leaks between concurrent operator conversations.
- **Tool-chain provenance** — every tool call records caller, tool name, input hash, output hash. Doubles as EU AI Act Art. 12 evidence.
- **Ollama-local fallback LLM** — Stage 11 acceptance requires that the voice and chat pipeline degrades gracefully to a local LLM (Llama 3 or Qwen 2.5 via Ollama) if Groq is unreachable. A VC-demo Groq outage is otherwise terminal.
- **LangGraph migration evaluated here**: this stage is the highest-value migration point (audit-trail-grade observability via LangSmith, native checkpointing of state). Migration is a substrate change behind the existing coordinator interface; rollback path stays open.

---

### Stage 12 — Problem Injection UX (Buttons + Extra Chat Interface)

**You do**: Click the new buttons; type natural-language problems in the chat.

**I do**:
1. Add a "Disruption Console" panel (visible on `/`, `/manufacturing`, `/embodied-agent`) with one-click buttons for the 6 problem types in the simulator's catalog. Each button posts to `/api/simulation/inject`.
2. Add a second chat surface (separate from `/voice`) — text-in / text-out — that uses the LLM as a problem-translator: "machine 4 will fail in 15 minutes" → structured `inject` call. The LLM returns the parsed event for confirmation, then sends it.
3. Both surfaces show the agent's response trace: detection → 5-min prediction → cross-domain plan → executed actions, all tied back to a single `incident_id`.

**Demo artifact**: type "robot 8 is dying" in chat → simulator marks robot 8 unhealthy → embodied agent re-distributes its tasks → throughput dip is small.

**Update (2026-05-11)**:
- Every operator override (button click or chat-issued correction) writes a row to the decision-log table — EU AI Act Art. 14 (human oversight) evidence.
- The chat LLM's "translate operator intent → structured event" step uses the prompt-injection-sanitized pipeline from Stage 11; no raw operator string ever reaches a tool without sanitization.

---

### Stage 13 — DB-Driven Problem Detection (Supabase Realtime + Postgres Triggers)

**You do**: Open Supabase studio, manually edit a row (e.g. set a stage's `status='broken'` or push a bad inventory level); watch the system react.

**I do**:
1. Replicate our schema into Supabase (or run Supabase locally in compose). Configure Realtime subscriptions on `production_stages`, `robots`, `inventory`, `supply_orders`.
2. Backend listener subscribes to Realtime + Postgres triggers (`AFTER UPDATE` for status changes); converts row diffs into `inject` events; same downstream path as buttons/chat.
3. Webhook receiver as a fallback for systems that prefer push.
4. Document the schema-as-API in `KB_04_Data_Schema.md` so customers can integrate by writing rows.

**Demo artifact**: change a row in Supabase studio → frontend animates the disruption → agent responds.

**Why this matters for funding**: customers integrate over their existing ERPs/MES by writing to a table, not by adopting a new API. This is the "land and expand" wedge.

**Update (2026-05-11)**:
- Postgres triggers publish to **Redis pub/sub** in addition to Supabase Realtime — this gives non-Supabase customers (the ones running their own Postgres or a managed RDS instance) the same integration story without forcing the Supabase Realtime stack on them.
- Postgres `wal_level=logical` is configured in compose at Stage 2 (already noted there) so this stage's CDC works out of the box.

---

### Stage 14 — Observability, MLOps, Drift Detection

**You do**: Watch dashboards. We'll iterate on which alerts are actionable.

**I do**:
1. Prometheus already partially scaffolded; finish: per-endpoint latency, decision throughput, model inference time, queue lengths.
2. Grafana dashboards (provisioned) for system KPIs + ML metrics.
3. Structured logging via `structlog` to Loki.
4. Distributed tracing via OpenTelemetry; Jaeger in compose.
5. Model registry (MLflow or DVC) — every weights file has a hash, dataset hash, training git SHA, metrics card.
6. Drift detection: rolling KS test on production input distributions vs training; alerts when drift > threshold; auto-trigger retraining ticket.
7. Circuit breakers around external APIs (weather, carbon).

**Demo artifact**: Grafana board that an enterprise SRE would recognize.

**Update (2026-05-11)** — this stage is significantly expanded:
- **EU AI Act technical conformity** scaffolding fills out: Article-11 technical documentation generator pulls from `compliance/model-cards/*`, `KB_02`, `KB_03`, and `KB_04` into an Annex-IV-shaped output. Article-12 automatic logging is wired end-to-end (every decision/override has caller, inputs, outputs, predicted vs actual, retained ≥6 months). Article-49 EU database registration documented.
- **NIST RMF Agentic Profile controls** finalized: prompt-injection sanitizer (Stage 11) gets a per-PR test; cross-session memory namespacing (Stage 11) gets an integration test; tool-chain provenance hashes are queryable via API for audit.
- **Model serving layer** — promote in-process model loading to **Triton Inference Server** (or BentoML) behind the FastAPI app. Lets us scale models independently of the API, enables zero-downtime model swaps, and is the deployment story enterprise buyers expect.
- **Drift detection** — rolling KS test on production input distributions vs training distribution; alert + auto-retrain ticket when drift > threshold.
- **Backup / DR** — pgBackRest for Postgres; model-artifact retention policy in Git LFS; tested restore procedure.
- **Load test** — k6 or Locust scenario hitting 10K concurrent WS connections; p95 latency must stay under the cross-cutting 205 ms budget.
- **SBOM generation** — cyclonedx or syft on every Docker image build. EU Cyber Resilience Act + supply-chain hygiene.
- **OWASP LLM Top 10** — each item gets a control in `compliance/incident-playbook.md`.

---

### Stage 15 — Pilot Pack & Pitch Materials

**You do**: Take the artifacts to investor / pilot meetings.

**I do**:
1. 60-second auto-loop demo (Playwright-recorded) covering normal → injection → recovery.
2. ROI calculator: input plant size + cycle time + energy cost → projected savings range based on our measured 25–30% throughput improvement on simulated runs.
3. Pilot integration playbook: 2-week, 4-week, and 8-week onboarding patterns; customer writes to a Postgres-compatible schema (Stage 13's table) and gets value within a sprint.
4. Investor deck skeleton: problem ($5T+ manufacturing inefficiency), solution (cross-domain coordination), traction (real models + real metrics from Stages 4–8), moat (the world-model + RL combo trained per-customer), team, ask.
5. One-pagers for the named targets (Amazon = warehouse fleet coordination, DHL = sortation throughput, Siemens = MES coordination layer, Bosch = QA + predictive maintenance, Huawei = factory network operations).

**Demo artifact**: a folder you can hand to a VC.

**Update (2026-05-11)**:
- Add **EU AI Act compliance one-pager** to the pitch pack — EU primes (Siemens, Bosch, DHL) will ask for it on the first call.
- ROI calculator outputs **€-denominated** savings for the EU customer one-pagers (USD for US customers).
- New deck slide: **comparable startups** — Augment ($85M Series A logistics teammate), Pallet ($27M for CoPallet workflow agents). Anchors valuation expectations.
- New deck slide: **market sizing** — Gartner forecasts 40% of enterprise applications will feature task-specific AI agents by EOY 2026 (vs <5% in 2025); 80% of warehouses operate without any automation today. The wedge is huge and narrow at the same time.
- The 60-second Playwright demo is *already* scoped to the 0–15s normal / 15–25s injection / 25–55s embodied response / 55–90s post-recovery KPIs storyboard pre-locked in `KB_09_UX_Scenarios.md` (Stage 1).

---

## Verification Strategy (every stage)

Each stage's task document ends with a verification block. The shape:

```
Verify locally:
  docker compose up -d
  pytest backend/tests/<stage>/ -v
  curl http://localhost:8000/health
  open http://localhost:3000/<page>
  # Expected: <demo-artifact described above>

Verify metrics: <which Grafana panels should change, in what direction>
Verify in DB:   <which rows should land in which Postgres table>
Verify in KB:   <which KB files were updated and how>
```

We don't move to the next stage until the verification block passes end-to-end.

---

## Stage 1 Task Document (to be created on plan approval)

When this plan is approved, the first concrete deliverable is the file `tasks/STAGE_01_foundation_and_kb.md` — the executable task document for Stage 1 above. Subsequent stages get one task doc each at the end of the prior stage. Format:

```
# Task: Stage N — <name>
Status: not-started | in-progress | blocked | done
KB files this stage updates: [list]
Pre-requisites: [list]
Acceptance criteria: [bulleted, testable]
Hand-off: [what the next stage needs from this one]
You do: [user actions, with exact commands]
I do: [agent actions, with exact files/diffs]
Datasets / Colab notebooks: [links + checksums]
Verification block: [as above]
Risks / unknowns: [list]
KB updates: [what gets written where, post-completion]
```

---

## Datasets — Confirmed Real, Public, Trainable on Free Colab

(Full table with download commands and licenses goes in `KB_03_Datasets_Catalog.md`.)

| Dataset | Use | Source | License |
|---|---|---|---|
| NASA C-MAPSS | LSTM machine RUL prediction | NASA Open Data Portal | CC0 |
| AI4I 2020 | ANN machine failure prediction | UCI ML Repo (DOI 10.24432/C5HS5C) | CC BY 4.0 |
| SECOM | Optional: fault detection on highly-imbalanced sensor data | UCI ML Repo | UCI standard |
| NEU-DET | CNN steel surface defect classification (6 classes) | Kaggle / NEU | Public |
| MVTec AD | Convolutional autoencoder anomaly detection (15 categories, 5K imgs) | MVTec | Research-only (commercial license needed for pilots) |
| Bosch CNC Machining | CNC vibration anomaly (real industrial sensor data) | github.com/boschresearch/CNC_Machining | Open |
| M5 Walmart | Demand forecasting (3,049 products × 5.4 yrs) | Kaggle | Public |
| Logistics-curated YOLO | Optional: AMR/AGV detection fine-tuning | Aggregated public sets | Mixed; track per-source |

---

## What I'm not doing in this plan (and why)

- **DreamerV3 world model**: outperforms PPO across 150 domains, but training is too compute-heavy for free Colab and adds risk without clear funding-stage upside. Ship LSTM world model + PPO first; consider Dreamer in a v2.
- **Federated learning across plants**: a real moat, but premature; needed for ≥3 paying customers, not for a pitch.
- **Edge deployment / NVIDIA Jetson**: defer until we have a pilot customer asking for it. Our current target is cloud + on-prem container.
- **Custom IoT firmware**: out of scope; we integrate via MQTT, OPC-UA, and Postgres tables — formats every plant already speaks.

---

## What happens after you approve this plan

1. I exit plan mode.
2. I create the `knowledge-base/` folder and write the 12 KB files with current audit findings as initial content. (You read them; we correct anything I got wrong about your intent.)
3. I create `tasks/STAGE_01_foundation_and_kb.md` — the executable task doc for Stage 1.
4. I begin Stage 1 work: delete Vite frontend, add Alembic migrations, add self-hosted Supabase to compose, fix secrets, init Git LFS, kill fabricated metrics, scaffold `backend/training/`, add CI workflow.
5. At the end of Stage 1: KB updates land, `KB_TASK_LOG.md` gets its first entry, I write `tasks/STAGE_02_simpy_simulator.md`, and we re-sync.
6. Each subsequent stage: I do the engineering, you do the Colab training runs (Stages 4–9), we both verify the demo artifact, KB + task log get updated, next task doc is written.

This is a long arc — months, not weeks — and the plan is intentionally conservative on what each stage promises. The point is that every stage produces a real, demonstrable, fundable artifact, and we never claim a model is working when it's actually `random.uniform()`.

---

# APPENDIX A — Web Research Compendium (preserved verbatim)

> Captured during plan creation. Web search results are ephemeral in conversation context, so this appendix preserves the findings. On plan approval, this section is also written to `d:\ai-embodied-agent\research\initial-research.md` and its structured form becomes `knowledge-base/KB_03_Datasets_Catalog.md`.

## A.1 Datasets — full details

### A.1.1 NASA C-MAPSS Turbofan Engine Degradation (LSTM RUL prediction)

- **What it is**: NASA Commercial Modular Aero Propulsion System Simulation. Simulated turbofan engine sensor data from NASA's 2008 PHM competition. The benchmark for predictive-maintenance / Remaining Useful Life (RUL) algorithms.
- **Structure**: 100 engines run-to-failure (training) + 100 engines stopped mid-flight (test). Each engine has 21 sensors (temperature, pressure, vibration, etc.) plus 3 operational settings (altitude, Mach, throttle). 4 sub-datasets FD001–FD004 of increasing difficulty (FD001 simplest).
- **Task**: Predict the number of remaining operational cycles before failure. Standard LSTM benchmark; recent SOTA uses 1D-CNN-LSTM hybrids with change-point-detection labeling.
- **License**: CC0 (public domain).
- **Sources**:
  - NASA Open Data Portal: https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data
  - Kaggle mirror: https://www.kaggle.com/datasets/behrad3d/nasa-cmaps
  - Reference model code: https://github.com/kpeters/exploring-nasas-turbofan-dataset
- **Maps to in our system**: LSTM world-model component + per-stage RUL prediction → drives `machine_crack` early-warning panel on `/manufacturing`.
- **Colab feasibility**: Trains in <1 hour on free T4. Lightweight (~50 MB).

### A.1.2 AI4I 2020 Predictive Maintenance Dataset (ANN failure classifier)

- **What it is**: Synthetic but industrially-realistic dataset by Stephan Matzka (TH Wildau). Created because real predictive-maintenance datasets are hard to publish. Mimics CNC-machine sensor patterns.
- **Structure**: ~10,000 rows × 14 columns. Features: air temperature, process temperature, rotational speed, torque, tool wear. Target: machine failure (binary) + 5 failure-mode flags.
- **Failure modes**:
  - **TWF** (Tool Wear Failure): tool fails or is replaced between 200–240 minutes of wear.
  - **HDF** (Heat Dissipation Failure): air–process temperature delta < 8.6 K AND speed < 1380 rpm.
  - **PWF** (Power Failure): power outside 3,500–9,000 W envelope.
  - **OSF** (Overstrain Failure): tool_wear × torque exceeds product-class threshold (L: 11,000; M: 12,000; H: 13,000 minNm).
  - **RNF** (Random Failure): 0.1% baseline rate regardless of inputs (5 datapoints in dataset).
- **License**: CC BY 4.0 (commercial-friendly).
- **Sources**:
  - UCI ML Repo: https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset (DOI 10.24432/C5HS5C)
  - Kaggle mirror: https://www.kaggle.com/datasets/stephanmatzka/predictive-maintenance-dataset-ai4i-2020
- **Maps to**: ANN classifier in `backend/ml/neural_networks.py` → real-time failure-probability badge per machine.
- **Colab feasibility**: Trains in minutes on CPU. Trivial size (<5 MB).

### A.1.3 SECOM Semiconductor Manufacturing (optional, fault detection on imbalanced sensor data)

- **What it is**: Wafer fabrication line sensor data, classic UCI fault-detection benchmark.
- **Structure**: 1,567 examples × 591 features. **Heavily imbalanced**: only 104 fail cases (1:14 ratio). 4.54% missing values (41,951 NaNs). Time-stamped.
- **Why optional for us**: Best fit if we want to demo "high-dimensional sensor sea, find the bad wafer." Skewed enough that it teaches the system how to handle imbalanced classification.
- **Sources**:
  - UCI: https://archive.ics.uci.edu/ml/datasets/SECOM
  - Kaggle: https://www.kaggle.com/datasets/paresh2047/uci-semcom
  - Reference code: https://github.com/sharmaroshan/SECOM-Detecting-Defected-Items
  - Recent benchmark paper (time-series version with simulated DES): https://arxiv.org/html/2408.09307v1
- **License**: UCI standard (research use; redistribute with citation).

### A.1.4 NEU-DET Steel Surface Defect (CNN multiclass)

- **What it is**: Northeastern University hot-rolled steel-strip surface defect database. The standard public benchmark for steel defect classification.
- **Structure**: 1,800 grayscale images (300 per class). 6 classes: rolled-in scale (Rs), patches (Pa), crazing (Cr), pitted surface (Ps), inclusion (In), scratches (Sc). Two variants:
  - **NEU-CLS**: classification only.
  - **NEU-DET**: classification + bounding-box detection annotations.
- **SOTA**: ~96.24% classification accuracy (NEU-CLS-64 downsampled). Standard benchmark for Faster R-CNN, deformable DETR, RetinaNet, etc.
- **Sources**:
  - Kaggle (CLS): https://www.kaggle.com/datasets/fantacher/neu-metal-surface-defects-data
  - Kaggle (DET): https://www.kaggle.com/datasets/kaustubhdikshit/neu-surface-defect-database
  - U-Net reference repo: https://github.com/siddhartamukherjee/NEU-DET-Steel-Surface-Defect-Detection
- **License**: Public for research.
- **Maps to**: `CNNDefectDetector` in `backend/ml/neural_networks.py`. Transfer-learn ResNet-18.
- **Colab feasibility**: ~30–90 min on T4 with transfer learning.

### A.1.5 MVTec AD (convolutional autoencoder, unsupervised anomaly)

- **What it is**: MVTec AG's industrial inspection benchmark. The most cited unsupervised AD dataset.
- **Structure**: 5,000+ high-resolution images, 15 categories (10 objects + 5 textures). 70+ defect types: scratches, dents, contaminations, structural changes. **Pixel-precise** annotations.
- **Methods supported**: Convolutional autoencoders, GAN-based, pretrained-CNN feature descriptors, classical CV. Anomaly maps via per-pixel ℓ² or SSIM reconstruction error; texture: 64-px-stride patch reconstructions averaged.
- **Extended version**: **MVTec AD 2** (8,000+ images, 8 new scenarios) — more challenging; useful for v2.
- **License**: **Research-only**. Commercial pilots will need an MVTec license — flag in `KB_11_Pitch_Strategy.md`.
- **Sources**:
  - Official: https://www.mvtec.com/company/research/datasets/mvtec-ad
  - Paper PDF: https://www.mvtec.com/fileadmin/Redaktion/mvtec.com/company/research/datasets/mvtec_ad.pdf
  - Springer paper (IJCV): https://link.springer.com/article/10.1007/s11263-020-01400-4
  - Reference repo: https://github.com/CY-Jeong/anomaly-detection-mvtec
  - Benchmark leaderboard: https://paperswithcode.com/sota/anomaly-detection-on-mvtec-ad

### A.1.6 Bosch CNC Machining Dataset (real industrial vibration)

- **What it is**: **Real-world** (not synthetic) CNC milling vibration data from a Bosch brownfield production plant collected over 2 years (Oct 2018 – Aug 2021).
- **Structure**: 3 machines (M01, M02, M03) × 15 processes (OP00–OP14). Tri-axial accelerometer (Bosch CISS sensor) inside the machine, 2 kHz sampling, X/Y/Z axes. Stored as `.h5` arrays of shape (acc_values, n_channels). Labels: "good" / "bad".
- **Why this matters**: Most industrial datasets are synthetic. This is real plant data, which makes it credible in a Bosch/Siemens pitch ("we trained on Bosch's own publicly released production sensors").
- **Sources**:
  - GitHub: https://github.com/boschresearch/CNC_Machining
  - UCI mirror: https://archive.ics.uci.edu/dataset/752/bosch+cnc+machining+dataset
  - Paper: https://www.sciencedirect.com/science/article/pii/S2212827122002384
- **License**: Open (Bosch Research, permissive).
- **Maps to**: 1D-CNN or LSTM autoencoder for vibration anomaly. Extends Stage 5 with a real-data demo.

### A.1.7 M5 Walmart Forecasting (LSTM/Transformer demand)

- **What it is**: Walmart hierarchical retail-sales forecasting dataset, used in Kaggle's M5 Accuracy and M5 Uncertainty competitions.
- **Structure**: 3,049 product time series × 1,969 daily observations (2011-01-29 → 2016-06-19, ~5.4 years). 3 categories (Hobbies, Foods, Household), 10 stores, 3 US states (CA, TX, WI). Hierarchical: aggregate from product+store up to total sales.
- **Explanatory variables**: calendar (holidays, events), prices, SNAP food-stamp activity flags.
- **Findings from M5 results paper (Makridakis et al.)**: LightGBM dominated top-50; LSTMs/transformers competitive but harder to tune. Recent (2025) work shows transformers with explanatory variables outperform pure LSTM on horizon and reliability.
- **Sources**:
  - Kaggle: https://www.kaggle.com/competitions/m5-forecasting-accuracy
  - Results paper: https://www.sciencedirect.com/science/article/pii/S0169207021001874
  - LSTM walkthrough: https://medium.com/@ivyyuqian.yang/lstm-time-series-prediction-for-walmart-sales-data-e3a301dc6790
  - Transformer reference: https://www.preprints.org/manuscript/202502.0009/v1/download
- **License**: Public (Kaggle competition rules).
- **Maps to**: `ANNDemandPredictor` upgrade → real demand forecast feeding Q-learning supplier policy.
- **Colab feasibility**: LSTM on subset trains in 1–2 hr T4. Full hierarchical needs more memory; we'll subset to top-N products that map to our 5 SKUs.

### A.1.8 Logistics-curated YOLO datasets (AGV/AMR detection)

- **State**: No single canonical "warehouse top-down robot detection" dataset. Recent (2024–2025) work assembles their own from public sources.
- **Best aggregator**: a 2024 paper introducing a logistics-focused dataset combining aerial + warehouse + transportation imagery; provides comparative analysis across YOLO variants. Ref: PMC12031185 (https://pmc.ncbi.nlm.nih.gov/articles/PMC12031185/).
- **Survey**: https://www.sciencedirect.com/science/article/pii/S0952197625018883 (computer vision in warehouse automation, 2025).
- **AMR review** (broader context): https://arxiv.org/html/2406.08333v1
- **Plan for Stage 9**: Use existing pretrained `yolov8n.pt` as baseline. Fine-tune on the aggregated logistics dataset. If insufficient, generate synthetic top-down warehouse imagery via Unity / NVIDIA Isaac Sim (free for non-commercial).

### A.1.9 Industrial datasets master list (curated by Fraunhofer/DLR)

- **Fraunhofer**: https://www.bigdata-ai.fraunhofer.de/s/datasets/index.html
- **Curated GitHub list**: https://github.com/nicolasj92/industrial-ml-datasets
- **DLR review paper**: https://elib.dlr.de/211380/1/Review%20Publicly%20Available%20Datasets%20Manufacturing%20Systems.pdf
- **Use**: Stage 14+ when we want to source additional pilots / domain-adaptation data.

## A.2 Algorithms / architectures research

### A.2.1 PPO for job-shop scheduling — confirmed best track record (2025)

- PPO consistently beats traditional dispatching rules; **6–9× lower optimality gap** than heuristics on standard JSSP instances.
- Best 2025 results: PPO + Double Priority Experience Replay for dynamic JSSP. Reference: ScienceDirect S2210650226000647.
- Graph-Neural-Network + PPO formulations are SOTA when scheduling has complex precedence constraints. Reference: Park et al., IJPR 2021 — https://www.tandfonline.com/doi/abs/10.1080/00207543.2020.1870013
- Offline RL (learning from historical schedules) is a credible alternative. Reference: arXiv 2409.10589v4.
- **Decision for our build**: Stable-Baselines3 PPO, MlpPolicy, custom Gymnasium env wrapping our SimPy simulator. Mature, Colab-friendly, well-documented. Source: https://stable-baselines3.readthedocs.io/

### A.2.2 DreamerV3 — better but heavier (deferred to v2)

- Single algorithm masters 150+ diverse domains with one config. Outperforms PPO across all tested domains.
- Trains on a single A100. Free Colab T4 won't cut it for 200M-param default.
- Recent navigation extension (DreamerNav) shows it works for indoor robot navigation.
- References:
  - Repo: https://github.com/danijar/dreamerv3
  - Nature paper (2025): https://www.nature.com/articles/s41586-025-08744-2
  - Project page: https://danijar.com/project/dreamerv3/
- **Decision**: ship LSTM world model + PPO first (Stages 7–8). Consider Dreamer in v2 once we have GPU budget from a customer.

### A.2.3 SHAP / Integrated Gradients on LSTMs

- SHAP on LSTMs is **known unstable** with Deep SHAP / pure gradient explainers (recurrent architecture issue).
- Combine with **Integrated Gradients** (Captum) for stability — recent practice.
- For tabular ANN paths, KernelExplainer or TreeExplainer (if we ensemble with LightGBM on M5).
- References:
  - Combined SHAP+LIME on LSTM: https://jisem-journal.com/index.php/journal/article/view/2627
  - Multivariate-time-series XAI evaluation: https://arxiv.org/pdf/2104.04075
  - Energy-load explanability: https://arxiv.org/html/2507.22220
  - Springer review: https://link.springer.com/article/10.1007/s10489-021-02662-2
- **Decision for Stage 10**: `shap.GradientExplainer` + Captum `IntegratedGradients`, cached per `decision_id` in Redis.

### A.2.4 SimPy — confirmed for physics-based simulator

- Standard Python DES library, process-based via Python generators. Single-process, fits inside FastAPI or as sidecar.
- Real Python tutorial: https://realpython.com/simpy-simulating-with-python/
- Manufacturing tutorial repo: https://github.com/rayylin/Python_Simpy-Discrete_Event_Simulation/
- Docs: https://simpy.readthedocs.io/
- DataCamp course: https://www.datacamp.com/courses/discrete-event-simulation-in-python
- **Decision**: replace random-tick injection in `backend/simulation/engine.py` with SimPy resources/processes. Stage 2.

### A.2.5 Multi-agent system architecture (2026 best practices)

Key operational pillars from current MLOps/multi-agent literature:

- **State management**: agents need persistent memory; orchestrator maintains conversation history + state object across multi-session tasks. → Redis (hot) + Postgres (durable).
- **Security & governance**: RBAC mandatory; tool authentication via OIDC/OAuth; guardrails against prompt injection. → enforced at API layer in Stage 14.
- **Verification & control**: Critic / Validator / Red-team agents for built-in checks. → embodied agent already plays critic-of-sub-agents role.
- **Observability ≠ APM**: agents are non-deterministic with multi-step reasoning chains; need step-level trace visibility. → OpenTelemetry + Langfuse-style decision-trace store, Stage 14.
- **2026 trend**: MLOps + LLMOps converging — single platform handles both traditional ML models and LLMs.
- References:
  - MLOps roadmap 2026: https://medium.com/@sanjeebmeister/the-complete-mlops-llmops-roadmap-for-2026-building-production-grade-ai-systems-bdcca5ed2771
  - MLOps Community guide: https://home.mlops.community/public/blogs/architecting-the-ai-agent-platform-a-definitive-guide
  - Multi-agent architecture guide: https://www.clickittech.com/ai/multi-agent-system-architecture/
  - Frameworks comparison 2026: https://gurusup.com/blog/best-multi-agent-frameworks-2026
  - Observability platforms: https://www.getmaxim.ai/articles/top-5-ai-agent-observability-platforms-in-2026/

### A.2.6 Supabase Realtime + DB-driven event flow (Stage 13)

- **Three CDC modes**: database triggers, webhooks, Realtime subscriptions. We'll use **Realtime** for backend listening + **webhooks** as fallback for push-style integrations.
- Realtime: WebSocket-based, listens to Postgres logical replication, supports presence + broadcast + Postgres changes.
- Webhooks: fire-and-forget POST/GET on INSERT/UPDATE/DELETE, run in a Postgres background worker.
- References:
  - Webhooks docs: https://supabase.com/docs/guides/database/webhooks
  - Realtime repo: https://github.com/supabase/realtime
  - CDC comparison (Stacksync): https://www.stacksync.com/blog/supabase-cdc-options-triggers-webhooks-realtime-compared
- **Why this is the funding wedge**: customers integrate by writing rows to a table — no new API to learn — which makes the sales motion much shorter for big plant operators.

### A.2.7 Industrial AI competitive context (2026)

- **Siemens Digital Twin Composer** (mid-2026 launch) — Industrial Metaverse environments at scale; PepsiCo case study showed identifying up to 90% of potential issues before any physical modification.
- **Siemens Industrial Copilot ecosystem** continues expanding across discrete + process manufacturing.
- **Siemens × NVIDIA** partnership: building "Industrial AI Operating System" end-to-end.
- **Audi × Siemens**: virtual PLCs (vPLCs) running real production at Böllinger Höfe — first industrial deployment.
- **Funding climate**: 2025–2026 rewards companies with **deployed sensors and contracted revenue** over those still piloting. Implication: our pitch must show a clear pilot integration path (Stage 13 + Stage 15) and at least one paying-pilot LOI is worth more than another model improvement.
- References:
  - https://press.siemens.com/global/en/pressrelease/siemens-unveils-technologies-accelerate-industrial-ai-revolution-ces
  - https://news.siemens.com/en-us/digital-twin-composer-ces-2026/
  - https://press.siemens.com/global/en/pressrelease/siemens-and-nvidia-preview-industrial-tech-stack-ai-era-manufacturing
  - https://www.ellty.com/blog/digital-twin-investors

## A.3 Source rollup (for `KB_11_Pitch_Strategy.md` references)

### Datasets
- NASA C-MAPSS: https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data
- AI4I 2020: https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset
- SECOM: https://archive.ics.uci.edu/ml/datasets/SECOM
- NEU-DET: https://www.kaggle.com/datasets/kaustubhdikshit/neu-surface-defect-database
- MVTec AD: https://www.mvtec.com/company/research/datasets/mvtec-ad
- Bosch CNC: https://github.com/boschresearch/CNC_Machining
- M5 Walmart: https://www.kaggle.com/competitions/m5-forecasting-accuracy
- Industrial datasets aggregator: https://github.com/nicolasj92/industrial-ml-datasets

### Algorithms / frameworks
- Stable-Baselines3: https://stable-baselines3.readthedocs.io/
- DreamerV3: https://github.com/danijar/dreamerv3
- SimPy: https://simpy.readthedocs.io/
- Supabase Realtime: https://github.com/supabase/realtime

### Key papers
- Mastering diverse control tasks (DreamerV3, Nature 2025): https://www.nature.com/articles/s41586-025-08744-2
- M5 results synthesis: https://www.sciencedirect.com/science/article/pii/S0169207021001874
- MVTec AD (IJCV): https://link.springer.com/article/10.1007/s11263-020-01400-4
- Offline RL for JSSP: https://arxiv.org/abs/2409.10589v4
- Time-series XAI evaluation: https://arxiv.org/pdf/2104.04075

### Industry context
- Siemens CES 2026: https://news.siemens.com/en-us/siemens-unveils-technologies-to-accelerate-the-industrial-ai-revolution-at-ces-2026/
- Siemens × NVIDIA: https://press.siemens.com/global/en/pressrelease/siemens-and-nvidia-preview-industrial-tech-stack-ai-era-manufacturing
- Digital twin investor climate: https://www.ellty.com/blog/digital-twin-investors

---

# APPENDIX B — Audit Findings (preserved verbatim from initial codebase exploration)

> Same rationale as Appendix A: this is the input that shaped the plan; preserving it so future sessions don't have to re-derive it.

## B.1 Backend — what is real vs theatrical

| Component | Real code? | Real weights/data? | Fallback when unavailable |
|---|---|---|---|
| YOLOv8 vision | ✓ | ✓ (`backend/yolov8n.pt`) | Mock detections (random positions, 0.7–0.98 confidence) |
| ANN demand predictor | ✓ | ✗ | Statistical formula `mean × (1 + trend × 0.1)` |
| ANN energy predictor | ✓ | ✗ | Heuristic `5 + throughput × 0.1 + queue × 0.05` |
| CNN defect detector | ✓ | ✗ | `random.choice` with 8% defect probability |
| CNN obstacle detector | ✓ | ✗ | `random.choices` with fixed weight vector |
| LSTM world model | ✓ | ✗ | `random.uniform` perturbations ±5% around fixed baseline |
| PPO RL policy | ✓ | ✗ | Hardcoded heuristic rules (battery thresholds, queue thresholds) |
| SHAP explainer | ✓ (import) | ✗ | `random.uniform(0.3, 0.5)` importance scores |
| LLM client (Groq/Gemini/Ollama) | ✓ | ✓ (API keys) | Templated string responses |
| Whisper STT | ✓ | conditional | OpenAI API → error message |
| Piper TTS | ✓ | ✓ (Hindi/Telugu ONNX in `models/`) | Truncated in code |
| Supabase | ✓ (client) | ✗ (schema in comments) | N/A |
| Simulation engine | ✓ (state machine) | mock events | N/A |
| WebSocket broadcast | ✓ | real state | N/A |
| `/api/metrics/models` | ✓ (route) | ✗ | Hardcoded demo metrics (lines 192–310) |

**Critical files where fakery lives** (so we know what to surgically replace):
- `backend/ml/neural_networks.py` lines 114–124, 175–176, 289–307, 381–388
- `backend/ml/world_model.py` lines 216–247
- `backend/ml/rl_policy.py` lines 267–335
- `backend/ml/explainability.py` lines 73–147
- `backend/api/metrics_routes.py` lines 74, 192–310, 313–343
- `backend/simulation/engine.py` lines 268–300 (random injection of collisions/bottlenecks)
- `backend/data/supabase_service.py` lines 78–149 (schema in SQL comments, never executed)

## B.2 Frontend (`frontend-nextjs/`) — what is real vs theatrical

**Verdict**: 95% theatrical. Beautiful UI, zero backend integration.

| Layer | Reality |
|---|---|
| Stack: Next.js 16.1.6, React 19.2.3, Tailwind v4, R3F 9.5.0, Framer Motion 12.31.0 | Real |
| 8 pages render | Real |
| Data flow | All `setInterval` + `Math.random()` via `generateMockState()`, `generateRobots()`, etc. |
| `socket.io-client` 4.8.3 in `package.json` | **Never imported** anywhere |
| `connectWebSocket()` in `src/lib/api.ts:212` | Declared, never called |
| `getMockState()` fallback in `src/lib/api.ts` lines 233–358 | **Always wins** because real fetches are never called |
| `/voice` page | `RESPONSES` dict + `getResponse()` string-matcher (lines 277–295); no STT/LLM/TTS calls |
| Problem/Solution toggle | Just regenerates mock data with different random ranges; no backend call |
| Inject-problem buttons | **Do not exist** |
| Model metrics page | All MAE/R²/accuracy hardcoded as strings (lines 31–116) |
| DB connection | None — Supabase/Prisma/Firebase all absent |

**Where the frontend mocks live** (to surgically delete in Stage 3):
- `src/app/page.tsx` lines 75–142 (`generateMockState`), 521–531 (interval)
- `src/app/robotics/page.tsx` lines 66–192 (generators), 542–562 (interval)
- `src/app/manufacturing/page.tsx` lines 60–99
- `src/app/supply-chain/page.tsx` lines 63–97
- `src/app/embodied-agent/page.tsx` lines 46–163
- `src/app/knowledge-graph/page.tsx` lines 34–96 (static `NODES`/`EDGES`)
- `src/app/model-metrics/page.tsx` lines 31–116 (`MODELS` array)
- `src/app/voice/page.tsx` lines 277–351 (`RESPONSES`, `getResponse`, fake STT timeout)

## B.3 Infrastructure inventory

- **`docker/docker-compose.yml`**: Neo4j 5.15, Redis 7-alpine, Postgres 15-alpine, Mosquitto 2, FastAPI backend, simulation sidecar. Health checks configured. **Hardcoded passwords** (`aiagent2026`) — security issue.
- **`database/schema.sql`** (15.7 KB): Postgres-compatible. Tables: `robots`, `production_stages`, `decisions`, `supply_orders`, indexes for status/timestamps/queue depth. **No migration framework; one static file.**
- **`scripts/deploy.sh`**: GCP Cloud Run deploy skeleton, ~50 lines visible, pre-flight checks for gcloud + Docker.
- **`.kiro/specs/platform-completion/`**: Detailed design + requirements docs (~900 lines combined) — appears to be specs for an AI code-gen tool (Antigravity?). Useful as reference for animation/voice/external-API specs.
- **`models/`**: Hindi (`hi_IN-priyamvada-medium.onnx`, 63.5 MB) + Telugu (`te_IN-padmavathi-medium.onnx`, 63.5 MB) Piper TTS weights. Real, usable.
- **`backend/yolov8n.pt`**: Real pretrained YOLOv8 nano weights.
- **No** `.ipynb` training notebooks committed.
- **No** `.csv` / `.parquet` training datasets committed.
- **No** PPO / LSTM / ANN / CNN trained weights committed.

## B.4 Production readiness scorecard (per audit)

| File | Score (0–10) | Note |
|---|---|---|
| `backend/main.py` | 8 | Solid bootstrap |
| `backend/api/routes.py` | 8 | Clean endpoints, thoughtful fallbacks |
| `backend/api/metrics_routes.py` | 2 | Returns fabricated demo metrics |
| `backend/services/decision_engine.py` | 5 | Real logic, all ML fallbacks |
| `backend/ml/vision_model.py` | 7 | Real YOLOv8, mock fallback |
| `backend/ml/neural_networks.py` | 4 | Real code, all random fallbacks |
| `backend/ml/rl_policy.py` | 3 | Real code, heuristic fallbacks |
| `backend/ml/world_model.py` | 4 | Real code, random fallback |
| `backend/agents/embodied_agent.py` | 7 | Real coordination, ML stubs underneath |
| `backend/agents/llm_client.py` | 9 | Production-quality LLM integration |
| `backend/voice/voice_interface.py` | 7 | Real if Whisper+Piper installed |
| `backend/simulation/engine.py` | 7 | Real state machine, synthetic events |
| `backend/data/supabase_service.py` | 4 | Schema in comments, not auto-applied |
| `backend/config.py` | 9 | Well-designed settings |
| Frontend (overall) | 2 | UI real, data layer 100% theater |

**Aggregate**: 4/10 production-grade. Becomes 9/10 with this 15-stage plan.

---

# APPENDIX C — Update protocol for this research

When new research is added during later stages, append to:
1. `d:\ai-embodied-agent\research\initial-research.md` (canonical store)
2. The relevant `KB_*` file under `knowledge-base/`
3. A new entry in `KB_TASK_LOG.md`

Never delete from research files; only append, with date and stage tag (`[Stage 5, 2026-MM-DD]`). Outdated guidance gets a strikethrough, not a deletion — so we can see how our thinking evolved.
