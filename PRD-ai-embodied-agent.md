# PRODUCT REQUIREMENTS DOCUMENT (PRD)
## AI Embodied Agent for Multi-Domain Manufacturing Optimization
### Option 5C: Robotics + Manufacturing + Supply Chain Integration

**Document Version**: 1.0  
**Date**: January 2026  
**Target Users**: Manufacturing Engineers, Operations Managers, AI Researchers  
**Deployment**: Cloud (Google Cloud Run) + Edge (Factory Servers)  
**Tech Stack**: Python 3.10, FastAPI, React 18, TensorFlow 2.13, PyTorch, Docker  
**Free APIs & Services**: ✅ (0 licensing cost)

---

## 1. PRODUCT OVERVIEW

### 1.1 Vision Statement
Create an **intelligent AI agent** that perceives an entire manufacturing ecosystem (robotics fleet + production stages + supply chain) and makes coordinated decisions to maximize efficiency, sustainability, and profitability.

### 1.2 Problem Definition
**Current State (Broken):**
- Robotics system: Independently optimizes robot paths (ignores manufacturing delays, supply issues)
- Manufacturing system: Independently schedules stages (ignores robot battery, inventory)
- Supply chain system: Independently forecasts demand (ignores factory bottlenecks, disruptions)
- Result: **Misaligned decisions, 25-35% efficiency loss**

**Desired State:**
- Single AI agent views entire ecosystem in real-time
- Makes cross-domain decisions: "Delay Stage 4 output → pre-stage materials at Robot 5 → adjust supplier order timing"
- Decisions are **coordinated and explainable**
- Enables 25-35% efficiency gain + sustainability improvements

### 1.3 Success Criteria
- ✅ **Efficiency**: 25-30% reduction in cycle time (vs. baseline)
- ✅ **Sustainability**: 15-20% carbon reduction (optimized energy usage)
- ✅ **Responsiveness**: <500ms decision latency for new disruptions
- ✅ **Reliability**: 99.5% uptime for inference engine
- ✅ **Explainability**: Every decision has 3+ explanations (why it was chosen)
- ✅ **Scalability**: Handles 20+ robots, 50+ stages, 100+ suppliers

---

## 2. DETAILED FEATURE SPECIFICATIONS

### 2.1 Core Features

#### Feature 2.1.1: Real-Time System Perception
**Description**: Agent continuously perceives all system components

**Sub-features:**
1. **Robotics Tracking**
   - Input: Video feed from warehouse ceiling camera (2K @ 30fps)
   - Processing: YOLOv8 object detection → Robot ID + position + velocity + battery level
   - Output: JSON stream with 50ms refresh rate
   - Accuracy target: 99% robot detection, <10cm position error

2. **Manufacturing Stage Monitoring**
   - Input: PLC (Programmable Logic Controller) telemetry via MQTT
   - Monitored signals: Stage queue depth, machine status, energy consumption, defect rate
   - Output: Real-time dashboard update
   - Latency: <100ms

3. **Supply Chain Visibility**
   - Input: ERP system API calls (Shopify, SAP API, or custom)
   - Monitored: Incoming orders, supplier inventory, shipping status
   - Output: Demand forecast + disruption alerts
   - Update frequency: Every 5 minutes

4. **External Context**
   - Weather API integration (affects logistics, renewable energy)
   - Grid carbon intensity API (OpenWeather, EIA)
   - News/disruption alerts (rare but high-impact events)

**Technical Stack:**
- OpenCV + YOLOv8 (vision)
- MQTT client (manufacturing telemetry)
- REST API clients (supply chain)
- Streaming aggregator (Python asyncio)

---

#### Feature 2.1.2: World Model (Internal State Representation)
**Description**: Agent maintains an up-to-date "mental model" of the system

**Sub-features:**
1. **State Encoding**
   - Robots: Position (x, y), battery level (%), task queue, moving speed
   - Stages: Queue depth, cycle time, throughput, defect rate, energy, idle time
   - Supply: Incoming demand (next 1-7 days), supplier lead times, inventory buffers
   - System: Overall throughput, energy consumption, carbon footprint, disruption status

2. **Temporal Dynamics**
   - LSTM-based model predicts system state 5-60 minutes ahead
   - Accounts for: Robot motion, stage delays, supplier lead times, demand variability
   - Uncertainty quantification: Confidence intervals on all predictions

3. **Causal Relationships**
   - Learns dependencies: Stage delay → Robot queue buildup → Energy spike → Supplier impact
   - Uses attention mechanism to identify which factors influence which decisions

**Technical Stack:**
- LSTM (PyTorch) for temporal prediction
- Transformer attention for causal inference
- State representation: Sparse tensor (for scalability)

---

#### Feature 2.1.3: Decision Maker (RL Policy)
**Description**: Agent decides optimal actions across all domains

**Sub-features:**
1. **Action Space**
   - **Robotics Actions**: Route each robot to task destination, set speed (efficiency vs. speed tradeoff)
   - **Manufacturing Actions**: Set throughput for each stage (0-100%), reorder task queue, adjust energy usage
   - **Supply Chain Actions**: Adjust supplier orders (timing, quantity), trigger emergency procurement, adjust inventory buffers
   - **System Actions**: Switch to efficiency mode vs. speed mode, pause non-critical stages

2. **Reward Function** (Multi-objective RL)
   - Maximize: `+Throughput + Quality - Energy - Carbon - Disruption_Risk - Excess_Inventory`
   - Weights: Dynamic, based on business objectives (can be adjusted via UI)
   - Example: 50% throughput, 20% carbon, 15% quality, 15% cost

3. **Policy Learning**
   - Algorithm: PPO (Proximal Policy Optimization) or TRPO (Trust Region Policy Optimization)
   - Training data: 6-12 months of historical operation (replayed in simulation)
   - Continuous learning: Every week, retrain on new data patterns

**Technical Stack:**
- PyTorch Stable-Baselines3 (RL algorithms)
- Custom environment wrapper (gym-compatible)
- Distributed training (Ray RLlib optional)

---

#### Feature 2.1.4: Explainability & Human Oversight
**Description**: Every decision is transparent and human-checkable

**Sub-features:**
1. **Decision Explanation Panel**
   - For each decision: Show "Why?" in 3 forms:
     - **Natural language**: "Delaying Stage 4 because: (1) Inventory buffer full, (2) Robot 8 at 15% battery, (3) Demand forecast shows dip in 30 min"
     - **Visualization**: Attention heatmap showing which factors influenced decision
     - **Metrics**: "Expected improvement: +2% throughput, −1% energy"

2. **Confidence Score**
   - Each decision rated 0-100% confidence
   - Low confidence (<70%): Flag for human review
   - Option for human to override decision

3. **Counterfactual Analysis**
   - "What if we did X instead?" → Shows predicted outcomes
   - Helps operators understand decision tradeoffs

**Technical Stack:**
- SHAP (SHapley Additive exPlanations) for model interpretability
- Attention visualization (PyTorch hooks)
- Counterfactual generation (optional: causal inference library)

---

### 2.2 Frontend Interface

#### 2.2.1 Main Dashboard
- **Layout**: 4 quadrants (Robotics | Manufacturing | Supply Chain | Metrics)
- **Robotics Quadrant**:
  - Top-down warehouse view (Leaflet/Three.js)
  - 20 robot icons, color-coded by status (idle=green, working=blue, low-battery=red)
  - Heatmap overlay: Task density, congestion zones
  - Click robot → Details: Battery, task queue, position history

- **Manufacturing Quadrant**:
  - 10 stage boxes in a pipeline, color-coded (green=normal, yellow=warning, red=bottleneck)
  - Each stage shows: Queue depth, cycle time, throughput
  - Click stage → Drill-down: Detailed metrics, quality issues, energy consumption

- **Supply Chain Quadrant**:
  - Demand forecast graph (next 7 days with confidence bands)
  - Supplier status (on-time, delayed, risk)
  - Inventory buffer visualization (green=healthy, red=depleted)

- **Metrics Quadrant**:
  - KPIs: Throughput (units/hour), Quality rate (%), Energy (kWh/unit), Carbon (kg CO₂/unit), Uptime (%)
  - Trend charts (last 24 hours)
  - Comparison to baseline (% improvement)

#### 2.2.2 AI Decision Panel
- **Live Feed**: Every 30 seconds, new decision appears
- **Decision Card**: Shows decision + explanation + confidence + expected impact
- **Expandable**: Click to see full reasoning, counterfactual analysis
- **Override Button**: Human can override with custom action + reason

#### 2.2.3 Optimization Control Panel
- **Sliders**:
  - Throughput vs. Energy tradeoff (0=min energy, 100=max throughput)
  - Quality vs. Speed (0=speed, 100=quality)
  - Carbon penalty (0=ignore, 100=prioritize sustainability)
  
- **Buttons**:
  - "Emergency Mode" (switch to max speed, ignore carbon)
  - "Sustainability Mode" (prioritize carbon reduction)
  - "Simulation Mode" (test decisions without affecting real system)

#### 2.2.4 Alerts & Warnings
- **Critical**: System-level anomalies (e.g., cascading failure detected)
- **Warning**: Threshold approaching (e.g., inventory running low)
- **Info**: Routine decisions (agent explaining its choice)
- **Each alert**: Actionable (with 2-3 recommended responses)

---

### 2.3 Backend API Specification

#### 2.3.1 Core Endpoints

**1. GET /api/system-state**
- Returns: Current state of all robots, stages, supply chain
- Response time: <100ms
- Format:
```json
{
  "timestamp": "2026-01-07T09:15:30Z",
  "robots": [
    {"id": 1, "position": [10.2, 5.5], "battery": 75, "task": "go to stage 7", "status": "working"},
    {"id": 2, "position": [8.1, 3.2], "battery": 15, "task": "go to charging", "status": "warning"}
  ],
  "stages": [
    {"id": 1, "queue_depth": 5, "throughput": 12, "status": "normal"},
    {"id": 7, "queue_depth": 20, "throughput": 8, "status": "bottleneck"}
  ],
  "supply_chain": {
    "demand_forecast": [...],
    "supplier_status": [...],
    "inventory": [...]
  }
}
```

**2. POST /api/decision**
- Triggers agent to compute next decision
- Input: `{"constraints": ["avoid stage 7"], "priority": "throughput"}`
- Output:
```json
{
  "decision_id": "dec_001",
  "actions": [
    {"target": "stage_4", "action": "reduce_throughput", "value": 75},
    {"target": "robot_5", "action": "navigate_to", "destination": "pre_stage_buffer"},
    {"target": "supplier_2", "action": "advance_order", "units": 50}
  ],
  "reasoning": "Stage 7 bottleneck detected. Pre-staging materials will unlock 12% efficiency gain.",
  "confidence": 0.87,
  "expected_impact": {"throughput_gain": "+2.5%", "energy_impact": "−1.2%", "carbon_impact": "−0.8%"}
}
```

**3. POST /api/override**
- Human overrides agent decision
- Input: `{"decision_id": "dec_001", "action": "reject", "reason": "safety constraint violated"}`
- System learns from override (feedback for continuous improvement)

**4. GET /api/prediction**
- Returns: System state prediction (5-60 min ahead)
- Input: `{"horizon_minutes": 30}`
- Output: Predicted stage queues, robot battery levels, demand forecast

**5. GET /api/explainability/{decision_id}**
- Deep dive into a specific decision
- Returns: Attention heatmap, SHAP values, counterfactual analysis

---

### 2.4 Data Pipeline

#### 2.4.1 Data Ingestion
- **Source 1**: Factory sensors (MQTT broker)
  - Topic: `factory/robots/{robot_id}/telemetry` → 10Hz
  - Topic: `factory/stages/{stage_id}/metrics` → 1Hz

- **Source 2**: Video feed (ceiling camera)
  - Upload: 2K @ 30fps to object storage
  - Processing: YOLOv8 inference every frame

- **Source 3**: ERP system
  - Pull orders: Every 5 minutes
  - Supplier status: Every 30 minutes

- **Source 4**: External APIs
  - Weather: Every 30 minutes
  - Grid carbon: Every 1 hour

#### 2.4.2 Data Processing
- **Stream Processing**: Apache Kafka or Pub/Sub
- **State Management**: Redis (fast lookups) + Supabase (persistent storage)
- **Feature Engineering**: Real-time aggregations (5-min rolling windows, hourly summaries)

#### 2.4.3 Storage Schema
```
TABLE robots (
  id INT PRIMARY KEY,
  position_x FLOAT, position_y FLOAT,
  battery_pct INT,
  task TEXT,
  status ENUM(idle, working, warning, charging),
  last_update TIMESTAMP
)

TABLE stages (
  id INT PRIMARY KEY,
  queue_depth INT,
  cycle_time_sec FLOAT,
  throughput_units_per_hour FLOAT,
  defect_rate FLOAT,
  energy_consumption_kw FLOAT,
  status ENUM(normal, warning, bottleneck),
  last_update TIMESTAMP
)

TABLE decisions (
  id TEXT PRIMARY KEY,
  timestamp TIMESTAMP,
  actions JSONB,
  reasoning TEXT,
  confidence FLOAT,
  expected_impact JSONB,
  actual_impact JSONB,
  human_feedback TEXT
)

TABLE supply_orders (
  id INT PRIMARY KEY,
  supplier_id INT,
  quantity INT,
  due_date DATE,
  status ENUM(confirmed, delayed, received),
  carbon_footprint_kg FLOAT
)
```

---

## 3. DEEP LEARNING MODEL SPECIFICATIONS

### 3.1 Vision Model (Robot Detection)
- **Architecture**: YOLOv8 (pre-trained on COCO, fine-tuned on factory videos)
- **Input**: 2K video (2560×1440) @ 30fps → 30 frames/sec
- **Output**: Robot detections (ID, position, confidence)
- **Optimization**: Run on GPU; batch processing for efficiency
- **Parameters to Tune**:
  - Confidence threshold: 0.5 → 0.7 (tradeoff: false positives vs. missed detections)
  - IoU threshold: 0.4 → 0.6

### 3.2 Temporal Prediction Model (World Model)
- **Architecture**: LSTM (or Temporal CNN)
- **Input**: State history (30 past timesteps) → Position, battery, queue depth, stage metrics
- **Output**: Predicted state (5, 15, 30 min ahead)
- **Hidden layers**: 2-4 layers, 256-512 hidden dims
- **Dropout**: 0.2-0.4 (regularization)
- **Parameters to Tune**:
  - Hidden dimensions: 128 → 256 → 512
  - Number of LSTM layers: 1 → 2 → 4
  - Dropout rate: 0.1 → 0.3 → 0.5
  - Sequence length: 10 → 30 → 60 timesteps
  - Learning rate: 1e-3 → 1e-4 → 1e-5 (with ADAM optimizer)

### 3.3 Policy Network (RL Decision Maker)
- **Algorithm**: PPO (Proximal Policy Optimization)
- **Architecture**:
  - Actor network: Transformer encoder (8 attention heads, 4 layers) → 50 action outputs
  - Critic network: MLP (3 layers, 256 hidden) → Value prediction
  
- **State representation**:
  - Concatenate all robot states, stage states, supply chain data
  - Total state size: ~500 dimensions (flattened)
  
- **Action space**: 50 continuous actions (robot speed setpoints, stage throughputs, order quantities)

- **Training procedure**:
  - Rollout policy in simulation: 10,000 timesteps per update
  - PPO update: 10 epochs, mini-batch size 256
  - Loss: Actor loss + Critic loss + Entropy regularization

- **Parameters to Tune**:
  - Learning rate: 3e-4 → 1e-4 → 3e-5
  - Gamma (discount factor): 0.95 → 0.99 → 0.999
  - Gae lambda: 0.95 → 0.98
  - Clip ratio (PPO): 0.1 → 0.2 → 0.3
  - Entropy coefficient: 0.01 → 0.001
  - Number of attention heads: 4 → 8 → 16
  - Transformer depth: 2 → 4 → 6 layers

### 3.4 Explainability Models
- **SHAP (SHapley Additive exPlanations)**: Decompose each decision into feature contributions
- **Attention Visualization**: Show which inputs the policy focused on
- **Counterfactual Generation**: Sample alternative decisions and show outcomes

---

## 4. IMPLEMENTATION PHASES

### Phase 1: MVP (Weeks 1-2)
- ✅ Robot detection (YOLOv8) on sample video
- ✅ Simple LSTM prediction model
- ✅ React dashboard (basic layout)
- ✅ FastAPI backend (basic endpoints)

### Phase 2: Core Features (Weeks 3-4)
- ✅ Full data pipeline (sensors + APIs)
- ✅ LSTM + Transformer hybrid model
- ✅ PPO RL policy training (in simulation)
- ✅ Decision panel + explainability

### Phase 3: Polish & Deploy (Weeks 5-6)
- ✅ Comprehensive testing
- ✅ Docker containerization
- ✅ Deploy to Google Cloud Run
- ✅ Performance optimization
- ✅ Documentation + demo video

### Phase 4: Production Hardening (Week 7+)
- ✅ Monitoring + alerting
- ✅ Continuous learning pipeline
- ✅ Human feedback integration
- ✅ Rollout to additional factories

---

## 5. SUCCESS METRICS & KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Cycle Time Reduction** | 25-30% | Production logs (units/hour) |
| **Carbon Footprint Reduction** | 15-20% | Energy consumption (kWh/unit) |
| **Decision Latency** | <500ms | API response time |
| **System Uptime** | 99.5% | Monitoring dashboard |
| **Inference Accuracy** | 95%+ | Predicted vs. actual outcomes |
| **Human Override Rate** | <5% | Decision logs |
| **Model Retraining** | Weekly | Automated pipeline |

---

## 6. DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│              Factory (On-Premise)                       │
├─────────────────────────────────────────────────────────┤
│ • MQTT Broker (robot/stage telemetry)                  │
│ • Camera + Edge GPU (YOLOv8 inference)                │
│ • PLC / Manufacturing controllers                      │
│ • ERP system integration                               │
└───────────────┬─────────────────────────────────────────┘
                │ (HTTPS encrypted)
┌───────────────▼─────────────────────────────────────────┐
│        Google Cloud Run (Serverless Backend)            │
├─────────────────────────────────────────────────────────┤
│ • FastAPI server                                        │
│ • LSTM + Transformer models (GPU VM for training)      │
│ • PPO RL policy inference                              │
│ • REST API endpoints                                    │
└───────────────┬─────────────────────────────────────────┘
                │
         ┌──────┴──────┐
         │             │
    ┌────▼─────┐  ┌────▼─────┐
    │ Firestore│  │  Storage  │
    │(Real-time│  │(Video     │
    │ telemetry│  │ logs)     │
    └──────────┘  └───────────┘
         │
    ┌────▼─────────────────┐
    │  React Frontend       │
    │  (Vercel Hosting)     │
    └──────────────────────┘
```

---

## 7. OPEN QUESTIONS FOR REFINEMENT

1. **Simulation vs. Real Data**: Should we train on synthetic data (faster, cheaper) or wait for real factory data?
2. **Continuous Learning**: How often should the policy retrain? Weekly? Daily?
3. **Multi-Factory Deployment**: How do we transfer the policy to new factories with different configurations?
4. **Safety Constraints**: What hard constraints must the agent never violate? (e.g., never exceed stage capacity)
5. **Human-in-the-Loop**: Should operators be able to interactively guide the agent?

---

## NEXT STEPS

→ **Confirm PRD** with stakeholders  
→ **Create TRD** (Technical Requirements Document) with detailed architecture  
→ **Begin Antigravity Prompt Engineering** for code generation  
→ **Start MVP development** (Week 1)

---

**PRD Status**: ✅ Ready for feedback → TRD coming next week