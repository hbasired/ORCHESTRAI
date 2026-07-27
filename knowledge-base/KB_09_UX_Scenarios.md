---
name: UX Scenarios
description: 60-second demo storyboard with timing; problem-injection flow; chat + DB-driven scenarios
type: spec
last-updated: 2026-05-11
---

# KB_09 — UX Scenarios

## Purpose
This file is what we are optimizing for. Every product decision (latency budget, animation choice, KPI surfacing) should map back to one of these scenarios.

## The canonical demo (60-second auto-loop)

The Playwright-recorded artifact in Stage 15. **Locking the storyboard early (Stage 1)** means every later stage knows what frame they're optimizing for.

| Time | What's on screen | Backend state | Why it matters |
|---|---|---|---|
| 0–5 s | Dashboard `/` in normal operation. Throughput counter ticks. 20 robots routing. Stage queues stable. | Simulator running baseline; no incidents. | Establishes the "normal" baseline. Audience sees this is a real system, not a static screenshot. |
| 5–15 s | Camera pans to `/manufacturing`. LSTM health bars per stage; one bar starts to dip mid-pan. | World-model LSTM (Stage 8) projects machine_crack at Stage 4 in ~3 min. | Predictive maintenance angle visible *before* the failure. This is the whole pitch in one frame. |
| 15–20 s | Disruption Console button click (or chat message): "Machine 4 will fail in 5 minutes". Embodied agent card flashes. | `POST /api/simulation/inject {type: machine_crack, stage_id: 4, eta_minutes: 5}`. | The interactive moment; demonstrates the integration surface. |
| 20–35 s | Camera pans to `/embodied-agent`. Three sub-agent proposals appear in parallel. LLM thought-process panel streams reasoning. SHAP attribution heatmap renders. | Embodied agent runs OODA cycle. PPO policy selects winning action set; sub-agents act. | Cross-domain coordination is the differentiator. |
| 35–50 s | Camera pans across `/manufacturing` → `/supply-chain` → `/robotics` showing the response: Stage 4 throttled, Stage 3 buffer built, supplier expedited, two robots redirected. | Sim executes the agent's actions. State propagates via WS deltas. | Shows the *embodied* part of "embodied agent" — multiple domains coordinated. |
| 50–60 s | Back to `/`. KPI bar at top shows: throughput dip = 8% (vs 25% baseline without coordination); recovery time = 90 s (vs 5 min without). Counterfactual side-by-side. | Compare-mode: PPO version vs rule-based baseline (Stage 7 acceptance). | Quantitative proof. This is what the investor remembers. |

(Stretch: 60–90 s post-recovery panel showing the steady-state KPIs, but the first 60 s is the locked artifact for VC decks.)

## Interactive scenarios (operator runtime)

### Scenario A: button-driven (Stage 12)

1. Operator views `/embodied-agent` during normal ops.
2. Clicks Disruption Console → "Robot 8 battery critical" button.
3. Sim receives inject; agent reacts within 250 ms.
4. Decision card appears; operator reviews; clicks through to SHAP attribution.

### Scenario B: chat-driven (Stage 12)

1. Operator types in chat: "machine 4 will fail in 15 minutes".
2. LLM parses → returns structured `{type: machine_crack, stage_id: 4, eta_minutes: 15}` for confirmation.
3. Operator confirms; same downstream flow as Scenario A.

### Scenario C: DB-driven (Stage 13)

1. External MES system writes a row to Supabase: `UPDATE production_stages SET status='broken' WHERE id=7`.
2. Supabase Realtime CDC fires → backend listener converts row diff to `inject` event.
3. Same downstream flow.
4. **No new API for the customer to learn.** This is the "land and expand" wedge.

### Scenario D: voice-driven (Stage 11)

1. Operator speaks (English / Hindi / Telugu): "Are any robots low on battery right now?"
2. Whisper STT → LLM with RAG over Redis hot state → Piper TTS reply.
3. LLM answer is grounded in real state, not the hardcoded dictionary that exists today.
4. Prompt-injection sanitizer ensures a poisoned DB row can't hijack the response.

## Override scenarios

Operator can override any agent decision via the decision card on `/embodied-agent`:
- Click "Override" → modal asks for `override_action` + `reason`.
- WS `override` envelope fires; agent records the override in `decision_logs`.
- This is the EU AI Act Art. 14 human-oversight surface.

## Failure scenarios (must remain demoable)

- **Backend goes down mid-demo** → frontend shows "Offline" banner; mock fallback kicks in *with* the offline indicator visible (no silent fake data).
- **Groq LLM outage** → voice / chat falls back to Ollama-local (Stage 11 acceptance); banner indicates degraded mode.
- **Frontend WS reconnect** → animations resume from current sim state, not from a fresh random seed.

## KPIs surfaced in the demo

| KPI | Target | Source |
|---|---|---|
| Throughput dip on disruption | <10% vs baseline | Sim (Stage 7 acceptance) |
| Recovery time | <120 s | Sim (Stage 7 acceptance) |
| Decision latency p95 | <500 ms (PRD) | Backend (KB_10 budget) |
| Explanation render | <1 s | Stage 10 acceptance |
| Voice round-trip | <2 s end-to-end | Stage 11 acceptance |

## Last verified
- 2026-05-11 — Plan-mode session. Storyboard drafted from the Stage 15 demo artifact spec in the master plan. Will be re-validated when Stage 5+ delivers the components that the storyboard depends on.
