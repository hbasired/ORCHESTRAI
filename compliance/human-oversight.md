# Human Oversight Spec

> EU AI Act Article 14 evidence. Defines how a human operator monitors and intervenes in the system. Locked at Stage 1; reviewed every stage that touches the operator surface.

## Principles

1. **The operator is always able to stop the system.** A single button on `/embodied-agent` halts agent action and freezes the simulator at the current state. No agent action executes during a hold.
2. **The operator is always able to override a decision.** Every decision card on `/embodied-agent` has an "Override" button that opens a modal asking for `override_action` + `reason`. The override is what executes; the agent's recommendation is logged as "not taken".
3. **The agent surfaces its reasoning.** Every decision card shows: the inputs (current state snapshot + world-model prediction), the chosen action, the rationale (LLM-generated), SHAP attribution, DiCE counterfactual ("smallest change to inputs that would have flipped this"), and confidence.
4. **The operator can pause inbound integrations.** The DB-driven CDC inflow (Stage 13) can be paused from a single toggle. The chat and voice interfaces can be muted similarly.

## Override flow (technical)

1. Operator clicks "Override" on a decision card on `/embodied-agent`.
2. Frontend opens a modal pre-populated with the agent's chosen action; operator edits.
3. On confirm, frontend sends WS envelope `{type: "override", decision_id, override_action, reason}`.
4. Backend (Stage 12) writes a row to `decision_logs` with `operator_override=true` + the override action + the reason text.
5. The override action becomes the executed action. The agent's recommendation is recorded as "not taken" in the log.
6. The decision card UI updates to show "Overridden by operator at HH:MM" with a hover-tooltip showing the reason.

## Override scope

- The operator can override **any** agent action.
- The operator **cannot** modify the underlying world-model prediction or PPO policy — those are AI outputs, not operator-editable. (If the operator disagrees with a prediction, they can ignore it; the override surface acts on the *decision*, not the *prediction*.)
- The operator **cannot** bypass safety constraints (Stage 7 reward-shaping hard constraints). If they propose an action that violates one, the system rejects with an explanation.

## Hand-off UI

`/embodied-agent` always shows:
- A persistent "System mode" indicator at the top: **Autonomous** (default) / **Recommend-only** (agent surfaces decisions but does not execute) / **Halted** (no agent action; sim freezes).
- A persistent "Operator on duty" field where the current shift supervisor's name is recorded (Stage 12+).
- A persistent count of overrides in the current shift (helps spot patterns).

The system mode is set per-pilot in a config file; the default is **Recommend-only** for a fresh pilot deployment. Customers opt into **Autonomous** mode once they trust the system.

## Log shape (excerpted from `decision_logs`)

```sql
SELECT
  decision_id,
  incident_id,
  caller,                    -- e.g. "embodied_agent.coordinate"
  tool,                      -- e.g. "ppo_policy"
  inputs,                    -- JSONB
  outputs,                   -- JSONB (the chosen action)
  operator_override,         -- boolean
  override_reason,           -- text, null when no override
  timestamp,
  retained_until             -- timestamp + 6 months (Article 12)
FROM decision_logs
WHERE incident_id = $1
ORDER BY timestamp ASC;
```

A full incident's decision trail is one query. This is the form the EU AI Act notified body will ask to see.

## What the operator *does not* see (intentional)

- Raw model weights or hyperparameters (these are in `model-cards/`, not the operator UI; available to the compliance officer, not the shift supervisor).
- Training-data details (privacy + commercial sensitivity).
- Internal LLM prompts verbatim (the system shows the *reasoning summary*, not the system prompt — protects against prompt-extraction attacks).

## Failure modes (must remain operable for the operator)

- WS disconnect → frontend shows "Offline" banner; operator can still trigger a halt via REST.
- Backend down → operator can manually halt via direct simulator interface (Stage 14 documents); decision-log lookup remains available via Postgres directly.
- LLM outage → decision cards continue to render with SHAP + PPO action; rationale text falls back to a templated explanation; override surface is unaffected.

## Training

(Stage 15 deliverable.) Pilot operators are trained on:
- How to read a decision card.
- When to override (high-novelty incidents, low agent confidence, safety-adjacent actions).
- When *not* to override (routine actions in the agent's confidence zone — over-overriding erodes the learning signal).
- How to file an incident report via `incident-playbook.md` if something goes wrong.

## Review

This file is reviewed at every stage that touches the operator surface (Stages 3, 10, 11, 12, 13, 15). Each review adds a line at the bottom.

## LangGraph HITL interrupts (Stage 11+, PRD v2.0)

When the agent substrate migrates to LangGraph + Pydantic AI in Stage 11, the override surface extends with native HITL primitives:

- `langgraph.interrupt()` checkpoints: every decision node that would route a SIL 1+ action calls `interrupt()` to pause the graph and surface the proposed action to the operator. The graph resumes only after the operator accepts, edits, or rejects.
- `langgraph.checkpoint.postgres.PostgresSaver` persists the interrupted state; the operator can take minutes / hours / days to respond without the agent runtime holding a process.
- Resume modes: `accept` (run the proposed action), `edit` (operator-modified action), `reject` (no action; agent re-plans).
- Every resume choice writes to `audit_chain` with `actor=operator:<id>`, `action=hitl.{accept|edit|reject}`, payload containing the proposed action + the resume choice. ML-DSA-65 signed.

## Functional-safety override semantics (Stage 17+, PRD v2.0)

- The operator override surface is layered ABOVE the functional safety wrapper, not below it. An operator override that proposes a SIL 2+ actuator command must still pass through `backend/safety/validator.py` and the classical executor — the operator cannot bypass safety contracts.
- An operator-proposed action that VIOLATES a safety contract is rejected with an explanation (which safety contract, which clause). The rejection writes to `audit_chain` as `actor=operator:<id>`, `action=override.rejected_by_safety`, with the contract name and the failed precondition / invariant.
- STO (Safe Torque Off) / SS1 (Safe Stop 1) paths are ALWAYS available regardless of operator mode — including when system mode is `Autonomous`. A separate emergency-stop control in the UI calls `backend/safety/sto_ss1.py:trigger_sto()` directly.

## A2A operator-side controls (Stage 14+)

- The operator can pause / resume specific A2A peers from the operator UI (Stage 14 ships the peer-management view).
- Revoking a peer mid-session: operator action writes a revocation entry; the peer's agent card is added to the revocation list; in-flight requests from that peer are completed but no new requests accepted.
- Peer-side override echo: when a delegated action returns from a peer, it surfaces in the same decision-card UI as an internally-generated decision, with `caller=a2a:<peer>` clearly visible.

## Review history

- 2026-05-11 — Stage 0 refresh. Spec written; not yet wired to UI (Stages 10 + 12 implement).
- 2026-05-18 — PRD v2.0 expansion: added LangGraph HITL interrupts, functional-safety override semantics, A2A operator-side controls. Wired in Stages 11 (HITL), 14 (A2A peer mgmt), 17 (safety wrapper) respectively.
