---
name: Frontend Pages Spec
description: Per-page spec — which API + WS topics each page consumes, which interactions it produces, animation rules
type: spec
last-updated: 2026-05-11
---

# KB_08 — Frontend Pages Spec

## Purpose
The 8-page Next.js frontend has been audited (`research/initial-research.md` §1.3–1.4) and confirmed 95% theatrical. This file specifies what each page must consume from the backend (after Stage 3 kills mocks) and what interactions it produces.

## Source of truth
- `frontend-nextjs/src/app/**/page.tsx`
- `frontend-nextjs/src/lib/api.ts`
- `KB_07_API_Contracts.md` (the contracts these pages bind to)

## Cross-cutting (Stage 3)

- Single `useSimulationState` hook + Zustand store; subscribes to `ws://{host}:8000/ws` once at app shell level.
- All pages read from the store; **no page may call `setInterval` + `Math.random()`** (post Stage 3 CI lint).
- Connection-status indicator + auto-reconnect with backoff.
- Pin **Next 15.x LTS + React 18.3 + Tailwind 3 LTS** (Stage 1 decision per refresh).

## Pages

### 1. `/` — Dashboard

**Consumes**: `state_snapshot`, `delta`, `incident`, `decision` envelopes.

**Renders**: KPI cards (throughput, energy, carbon, quality), domain summaries (robotics fleet status, stage queues, supplier health), decisions feed.

**Produces**:
- `POST /api/simulation/inject` via Disruption Console buttons (Stage 12).
- Mode toggle (Problem / Solution view).

**Stage 3 cleanup**: delete `generateMockState()` at `frontend-nextjs/src/app/page.tsx:75-142` and the `setInterval` at `:521-531`.

### 2. `/robotics`

**Consumes**: `delta` envelopes filtered to robot entities.

**Renders**: 2D warehouse with 20 animated robots; collision indicators; battery bars; PPO Navigation Model metrics card (real metrics after Stage 7).

**Produces**: per-robot click → focus card with details.

**Stage 3 cleanup**: delete generators at `frontend-nextjs/src/app/robotics/page.tsx:66-192` and interval at `:542-562`.

### 3. `/manufacturing`

**Consumes**: `delta` envelopes filtered to stage entities; `incident` envelopes of type `machine_crack` / `defect_surge`.

**Renders**: 10-stage production line with flow animation; queue-depth bars; LSTM/MsFormer health panel (real after Stage 4); CNN defect feed (real after Stage 5); ANN energy panel.

**Produces**: stage click → focus with detail + decision history.

**Stage 3 cleanup**: delete mocks at `frontend-nextjs/src/app/manufacturing/page.tsx:60-99` (current line range; may shift).

### 4. `/supply-chain`

**Consumes**: `delta` envelopes filtered to supplier / inventory entities; `incident` envelopes of type `late_delivery` / `demand_spike`.

**Renders**: inventory levels with reorder markers; 7-day demand forecast (real LSTM/Transformer after Stage 6); supplier status panel; Q-learning order-policy metrics.

**Produces**: supplier click → focus with lead-time history.

**Stage 3 cleanup**: delete mocks at `frontend-nextjs/src/app/supply-chain/page.tsx:63-97` (current line range; may shift).

### 5. `/embodied-agent`

**Consumes**: `state_snapshot`, `decision`, `explanation` envelopes.

**Renders**: domain-coordination viz (central brain connecting three sub-agents); current incident card; before/after comparison (PPO vs heuristic baseline from Stage 7); LLM thought-process display.

**Produces**: operator override clicks (Stage 12) → WS `override` envelope.

**Stage 3 cleanup**: delete `frontend-nextjs/src/app/embodied-agent/page.tsx:46-163` mocks.

### 6. `/knowledge-graph`

**Consumes**: dedicated `GET /api/graph` (Stage 1+ scope) → Neo4j-backed entity graph.

**Renders**: interactive node visualization (entities + relationships).

**Stage 3 cleanup**: delete static `NODES`/`EDGES` at `frontend-nextjs/src/app/knowledge-graph/page.tsx:34-96`.

### 7. `/model-metrics`

**Consumes**: `GET /api/metrics/models` (returns 503 until Stage 4).

**Renders**: per-model metrics cards (MAE / R² / accuracy / training git SHA / dataset hash / training command from each model's `<name>.card.md`).

**Stage 1 change**: deletes hardcoded `MODELS` array at `frontend-nextjs/src/app/model-metrics/page.tsx:31-116`; shows "Awaiting Stage 4 training run" placeholder while endpoint returns 503.

### 8. `/voice`

**Consumes**: `POST /api/voice/process` (real Whisper → Groq → Piper post Stage 11).

**Renders**: mic capture (real `MediaRecorder`), conversation transcript, language picker (English / Hindi / Telugu).

**Stage 11 cleanup**: delete `RESPONSES` dict, `getResponse()` string matcher, fake STT timeout at `frontend-nextjs/src/app/voice/page.tsx:277-351`.

## Animation rules

- All animations are state-driven, not time-driven. Framer Motion `layout` and `useSpring` interpolate between WS-delivered states; no animation runs in the absence of state updates.
- Frame rate is capped at 60 fps via Framer's `useReducedMotion` for accessibility.
- Demo storyboard (`KB_09`) drives the auto-loop for Stage 15's recorded demo.

## Test scaffolding (Stage 1)

- Vitest (or Jest) smoke tests per page that mount under a Zustand mock provider.
- Playwright E2E test running the 60-second demo storyboard from `KB_09`.

## Operator Command & Evidence Dashboard (added v2.1, 2026-05-31)

New first-class page `frontend-nextjs/src/app/operator/page.tsx` (PRD v2.1 §v2.1.4). It is the single surface
where an operator sees **agentic and non-agentic** activity together, with alarming + reporting. Telemetry
contract (event shape, alarm model) is in KB_15. Phased: Stage 3 lights up live data (WS broker); Stages 11–12.5
add agent trace + telemetry panes; Stage 17 adds the safety-gate pane; Stage 19 adds signed reporting + policy.

Panes (each driven by WS topics / REST, never mocks after its stage):
1. **Activity timeline** — unified feed; every event tagged `actor_class ∈ {agent,human,system,external}` + `sil`;
   filter agentic-only vs non-agentic-only. Consumes WS `activity` topic. (Art. 14 human-oversight enabler.)
2. **Agent reasoning** — live LangGraph node trace, MCP tool calls, confidence, HITL `interrupt()` prompts. WS `agent`.
3. **Plant / non-agentic** — robot/stage/supplier telemetry, queues, throughput, OEE, energy/carbon, PLC state. WS `state`.
4. **Safety gate** — `safety.validate` decisions (pass/fail, contract, SIL, fail-safe path), STO/SS1 events. WS `safety`.
5. **Audit-chain viewer** — append-only rows, chain-verify status, key version/algorithm, signer; one-click `verify`. REST `/api/audit/*`.
6. **A2A federation** — connected peers, card fingerprints, revocation status. REST `/api/a2a/peers`.
7. **Policy / governance** — active policies, budget caps, PII-filter actions, approvals pending. REST `/api/policy/*`.
8. **Alarms** — severity-ranked, ack/clear with audit; `safety_critical` never auto-clears (KB_15 alarm model). WS `alarms`.

Interactions produced: acknowledge alarm (→ `audit_chain`), confirm/deny HITL action, trigger report export
(signed), drill from a timeline event to its OTel trace + audit row via `correlation_id`. Activity-latency and
alarm-latency SLOs in PRD v2.1 §v2.1.2 §D.

## Last verified
- 2026-05-11 — Plan-mode session. Page list cross-checked against the explorer report; line ranges noted in §1.4 of `research/initial-research.md` may shift slightly under edits but the mock locations are intact.
- 2026-05-31 — Operator Command & Evidence Dashboard page spec added (PRD v2.1 §v2.1.4); not yet implemented — phased Stages 3→19.
