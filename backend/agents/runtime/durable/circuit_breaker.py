"""Stage 27 — circuit breaker (research §38.3): CLOSED → OPEN → HALF_OPEN, per-dependency registry.

Sourced semantics (Nygard via oneuptime/pybreaker): consecutive failures past `failure_threshold` OPEN the
circuit; after `recovery_timeout_s` a bounded number of HALF_OPEN probe calls are allowed; a probe success CLOSES,
a probe failure re-OPENs. An OPEN circuit raises `CircuitOpenError` — the project's honest-degradation rule:
the caller gets a NAMED unavailability, never a fabricated fallback value.

Every state transition is recorded as a signed `audit_chain` row (best-effort, surfaced-failure pattern) — a
breaker trip is operational evidence, not just a log line. Monotonic clock (immune to wall-clock jumps).
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"


class CircuitOpenError(RuntimeError):
    """The dependency's circuit is OPEN — the call was NOT attempted (honest unavailability, no fabrication)."""

    def __init__(self, name: str, retry_after_s: float):
        super().__init__(f"circuit '{name}' is OPEN (retry after ~{retry_after_s:.0f}s)")
        self.name = name
        self.retry_after_s = retry_after_s


def _audit(name: str, old: str, new: str, detail: dict[str, Any]) -> None:
    try:
        from memory.audit_chain import append
        append("runtime:circuit_breaker", "circuit.transition",
               {"circuit": name, "from": old, "to": new, **detail})
    except Exception:  # noqa: BLE001 — audit best-effort; the transition stands regardless
        pass


class CircuitBreaker:
    def __init__(self, name: str, *, failure_threshold: int = 5, recovery_timeout_s: float = 30.0,
                 half_open_max_probes: int = 1):
        self.name = name
        self.failure_threshold = int(failure_threshold)
        self.recovery_timeout_s = float(recovery_timeout_s)
        self.half_open_max_probes = int(half_open_max_probes)
        self._state = CLOSED
        self._consecutive_failures = 0
        self._opened_at: Optional[float] = None
        self._half_open_inflight = 0
        self._mu = threading.Lock()
        self._pending_audits: list[tuple[str, str, str, dict[str, Any]]] = []

    def _flush_audits(self) -> None:
        while self._pending_audits:
            try:
                _audit(*self._pending_audits.pop(0))
            except Exception:  # noqa: BLE001
                break

    @property
    def state(self) -> str:
        with self._mu:
            self._maybe_half_open_locked()
            st = self._state
        self._flush_audits()
        return st

    def _maybe_half_open_locked(self) -> None:
        if self._state == OPEN and self._opened_at is not None \
                and (time.monotonic() - self._opened_at) >= self.recovery_timeout_s:
            self._transition_locked(HALF_OPEN, {"after_s": round(time.monotonic() - self._opened_at, 1)})

    def _transition_locked(self, new: str, detail: dict[str, Any]) -> None:
        old, self._state = self._state, new
        if new == OPEN:
            self._opened_at = time.monotonic()
        if new in (CLOSED, HALF_OPEN):
            self._half_open_inflight = 0
        if new == CLOSED:
            self._consecutive_failures = 0
        # Audit OUTSIDE the lock path: the append is a DB write — inside the lock it would serialize every
        # breaker call behind the audit DB (found by this stage's own tests: the in-lock append consumed the
        # recovery window). Transitions queue here; `call()`/`state` flush after releasing the lock.
        self._pending_audits.append((self.name, old, new, detail))

    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run fn through the breaker. OPEN → CircuitOpenError without attempting the call."""
        with self._mu:
            self._maybe_half_open_locked()
            if self._state == OPEN:
                remaining = self.recovery_timeout_s - (time.monotonic() - (self._opened_at or 0.0))
                raise CircuitOpenError(self.name, max(0.0, remaining))
            if self._state == HALF_OPEN:
                if self._half_open_inflight >= self.half_open_max_probes:
                    raise CircuitOpenError(self.name, self.recovery_timeout_s)
                self._half_open_inflight += 1
        self._flush_audits()
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            with self._mu:
                self._consecutive_failures += 1
                if self._state == HALF_OPEN:
                    self._transition_locked(OPEN, {"probe_failed": type(e).__name__})
                elif self._state == CLOSED and self._consecutive_failures >= self.failure_threshold:
                    self._transition_locked(OPEN, {"consecutive_failures": self._consecutive_failures,
                                                   "last_error": type(e).__name__})
            self._flush_audits()
            raise
        else:
            with self._mu:
                self._consecutive_failures = 0
                if self._state == HALF_OPEN:
                    self._transition_locked(CLOSED, {"probe": "success"})
            self._flush_audits()
            return result


_registry: dict[str, CircuitBreaker] = {}
_registry_mu = threading.Lock()


def get_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    """Per-dependency singleton registry (sourced best practice: one breaker per dependency, shared by callers)."""
    with _registry_mu:
        if name not in _registry:
            _registry[name] = CircuitBreaker(name, **kwargs)
        return _registry[name]


__all__ = ["CircuitBreaker", "CircuitOpenError", "get_breaker", "CLOSED", "OPEN", "HALF_OPEN"]
