"""Stage 27 — durable-execution primitives (research §38.3).

The three primitives that make external effects safe under crash/retry/partial failure:
  * `idempotency` — a PG effect-ledger (key PK + cached response): an effect runs AT MOST ONCE; replays return
    the recorded outcome. Extends the Stage-25 `incident_processed` claim-table pattern to arbitrary effects.
  * `circuit_breaker` — CLOSED/OPEN/HALF_OPEN per dependency; OPEN raises `CircuitOpenError` (honest degradation —
    never a fabricated fallback value).
  * `saga` — orchestrated steps with per-step idempotency keys and reverse-order compensation; a compensation that
    exhausts retries surfaces STUCK (signed audit row) — never silently swallowed.

The event-sourced spine remains LangGraph's PostgresSaver + the append-only ML-DSA-signed audit_chain (§35.3);
these primitives guard the EFFECT boundary (actuator / A2A / OT / order dispatch).

NOTE (task-doc deviation, recorded): the doc named `backend/runtime/durable/`; the runtime package lives at
`backend/agents/runtime/`, so the primitives live here — one runtime namespace, not two.
"""
from agents.runtime.durable.idempotency import EffectLedger, EffectAlreadyDone
from agents.runtime.durable.circuit_breaker import CircuitBreaker, CircuitOpenError, get_breaker
from agents.runtime.durable.saga import Saga, SagaStep, SagaStuckError

__all__ = ["EffectLedger", "EffectAlreadyDone", "CircuitBreaker", "CircuitOpenError", "get_breaker",
           "Saga", "SagaStep", "SagaStuckError"]
