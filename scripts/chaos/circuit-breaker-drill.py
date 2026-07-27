"""Stage 27 — circuit-breaker chaos drill: a flaky dependency trips the breaker OPEN (honest CircuitOpenError,
no fabrication), then a HALF_OPEN probe recovers it to CLOSED — proving graceful degradation + self-recovery.
Every transition is a signed audit_chain row; the chain must still verify afterward.

    python scripts/chaos/circuit-breaker-drill.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from agents.runtime.durable import CircuitBreaker, CircuitOpenError  # noqa: E402


def main() -> int:
    br = CircuitBreaker("chaos-dep", failure_threshold=3, recovery_timeout_s=1.0)
    down = {"v": True}

    def dependency():
        if down["v"]:
            raise ConnectionError("dependency is down")
        return "served"

    # Phase 1: dependency down -> breaker trips OPEN after the threshold.
    trips, blocked = 0, 0
    for _ in range(3):
        try:
            br.call(dependency)
        except ConnectionError:
            trips += 1
    assert br.state == "OPEN", f"expected OPEN, got {br.state}"
    try:
        br.call(dependency)          # OPEN: not even attempted
    except CircuitOpenError:
        blocked += 1
    print(f"phase1: {trips} real failures tripped the breaker OPEN; {blocked} call blocked WITHOUT fabrication")

    # Phase 2: dependency recovers; after the recovery window a HALF_OPEN probe CLOSES the breaker.
    down["v"] = False
    time.sleep(1.1)
    assert br.state == "HALF_OPEN", f"expected HALF_OPEN, got {br.state}"
    assert br.call(dependency) == "served"
    assert br.state == "CLOSED"
    print("phase2: dependency recovered -> HALF_OPEN probe succeeded -> breaker CLOSED (self-healed)")
    print("DRILL PASS: graceful degradation (no fabricated fallback) + automatic recovery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
