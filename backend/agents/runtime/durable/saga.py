"""Stage 27 — saga orchestration with per-step idempotency + reverse compensation (research §38.3).

Sourced semantics (Temporal/Restate/Azure saga guidance): a saga is an ordered list of steps, each with an action
and a compensation; on a step failure, completed steps' compensations run in REVERSE order. The classic mistake is
API-level-only idempotency — here EVERY step claims its own effect-ledger key (`{saga_key}:{step}`), so an
orchestrator retry after a partial failure never double-executes a completed step (its claim raises
EffectAlreadyDone → the recorded response is reused).

A compensation that exhausts its retry budget leaves the saga **STUCK** — surfaced with a signed audit row and a
raised `SagaStuckError` naming exactly which compensations still owe manual intervention. Never silently swallowed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from agents.runtime.durable.idempotency import EffectAlreadyDone, EffectLedger


@dataclass
class SagaStep:
    name: str
    action: Callable[[dict], Any]                       # (context) -> response
    compensation: Optional[Callable[[dict], Any]] = None  # (context) -> None; None = nothing to undo
    compensation_retries: int = 2


class SagaStuckError(RuntimeError):
    """A compensation exhausted its retries — the saga needs OPERATOR intervention (named, never hidden)."""

    def __init__(self, saga_key: str, failed_step: str, stuck_compensations: list[str]):
        super().__init__(f"saga {saga_key!r} STUCK after step {failed_step!r} failed: "
                         f"compensations owing manual intervention: {stuck_compensations}")
        self.saga_key = saga_key
        self.failed_step = failed_step
        self.stuck_compensations = stuck_compensations


def _audit(action: str, payload: dict[str, Any]) -> None:
    try:
        from memory.audit_chain import append
        append("runtime:saga", action, payload)
    except Exception:  # noqa: BLE001
        pass


@dataclass
class Saga:
    key: str
    steps: list[SagaStep] = field(default_factory=list)
    ledger: EffectLedger = field(default_factory=EffectLedger)

    def add(self, name: str, action: Callable[[dict], Any],
            compensation: Optional[Callable[[dict], Any]] = None, compensation_retries: int = 2) -> "Saga":
        self.steps.append(SagaStep(name, action, compensation, compensation_retries))
        return self

    def run(self, context: Optional[dict] = None) -> dict[str, Any]:
        """Execute steps in order. Returns {step_name: response}. On failure: compensate in reverse and re-raise
        the step's exception (or SagaStuckError if a compensation itself fails past retries)."""
        context = context if context is not None else {}
        responses: dict[str, Any] = {}
        completed: list[SagaStep] = []
        for step in self.steps:
            step_key = f"{self.key}:{step.name}"
            try:
                claimed = self.ledger.claim(step_key)
            except EffectAlreadyDone as done:
                responses[step.name] = done.response   # replay: reuse the recorded outcome, do NOT re-execute
                completed.append(step)
                context[step.name] = done.response
                continue
            if not claimed:
                # Another worker is mid-flight on this step — the honest verdict is a named conflict, not a race.
                raise RuntimeError(f"saga step {step_key!r} is RUNNING elsewhere (concurrent saga execution)")
            try:
                resp = step.action(context)
            except Exception as e:
                self.ledger.release(step_key)          # failed step is retryable later
                _audit("saga.step_failed", {"saga": self.key, "step": step.name, "error": type(e).__name__})
                stuck = self._compensate(completed, context)
                if stuck:
                    _audit("saga.stuck", {"saga": self.key, "failed_step": step.name, "stuck": stuck})
                    raise SagaStuckError(self.key, step.name, stuck) from e
                _audit("saga.compensated", {"saga": self.key, "failed_step": step.name,
                                            "compensated": [s.name for s in completed]})
                raise
            self.ledger.complete(step_key, resp)
            responses[step.name] = resp
            context[step.name] = resp
            completed.append(step)
        _audit("saga.completed", {"saga": self.key, "steps": [s.name for s in self.steps]})
        return responses

    def _compensate(self, completed: list[SagaStep], context: dict) -> list[str]:
        """Run compensations in reverse. Returns the names of compensations that exhausted retries (STUCK)."""
        stuck: list[str] = []
        for step in reversed(completed):
            if step.compensation is None:
                continue
            comp_key = f"{self.key}:{step.name}:compensation"
            try:
                self.ledger.claim(comp_key)
            except EffectAlreadyDone:
                continue  # this compensation already ran (a prior partial unwind)
            done = False
            for _ in range(step.compensation_retries + 1):
                try:
                    step.compensation(context)
                    self.ledger.complete(comp_key, "compensated")
                    done = True
                    break
                except Exception:  # noqa: BLE001 — retry up to the budget
                    continue
            if not done:
                self.ledger.release(comp_key)
                stuck.append(step.name)
        return stuck


__all__ = ["Saga", "SagaStep", "SagaStuckError"]
