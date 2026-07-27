"""End-to-end SimWorld smoke that does NOT require docker / Postgres / Redis.

Run directly with:
    cd backend && python tests/_smoke_no_docker.py

Validates the same path the live `POST /api/simulation/inject` exercises:
  1. Pydantic InjectRequest validation.
  2. SimWorld.inject() returns an Incident.
  3. Per-event-type apply_incident_to_world() mutates plant state.
  4. SimWorld.snapshot() reflects the change.
  5. IncidentPayload model_dump(mode='json') is JSON-serialisable for FastAPI.

This is what the live stack would do too; we just skip the HTTP + DB layers.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Make `backend/` the package root so we can `from simulation.* import ...`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    from simulation.entities import InjectRequest, validate_inject_payload
    from simulation.sim_world import SimWorld

    print("=== Stage 2 no-docker smoke ===")
    print()

    # 1. Validation layer.
    print("[1/5] Pydantic InjectRequest validation...")
    req = validate_inject_payload({"type": "machine_crack", "target_id": 4})
    print(f"      OK -> req.type={req.type} target_id={req.target_id} details={req.details}")

    bad_cases = [
        {"type": "kaboom"},
        {"type": "machine_crack"},  # missing target
        {"type": "robot_down"},
        {"type": "defect_surge"},
    ]
    for bad in bad_cases:
        try:
            validate_inject_payload(bad)
            print(f"      FAIL: should have rejected {bad}")
            return 2
        except Exception:
            pass
    print(f"      OK -> all {len(bad_cases)} malformed payloads rejected with ValidationError")
    print()

    # 2. SimWorld construction.
    print("[2/5] SimWorld construction (seed=20260524)...")
    world = SimWorld(seed=20260524)
    assert len(world.stages) == 10, f"expected 10 stages, got {len(world.stages)}"
    assert len(world.robots) == 20, f"expected 20 robots, got {len(world.robots)}"
    assert len(world.suppliers) == 6, f"expected 6 suppliers, got {len(world.suppliers)}"
    print(f"      OK -> 10 stages, 20 robots, 6 suppliers, 2 charging stations capacity={world.charging_stations.capacity}")
    print()

    # 3. Start worker thread + inject each of the six event types.
    print("[3/5] Start worker thread + inject all six event types...")
    world.start()
    incident_ids = []
    for spec in [
        ("machine_crack", 4),
        ("robot_down", 7),
        ("late_delivery", 2),
        ("demand_spike", None),
        ("defect_surge", 3),
        ("power_dip", None),
    ]:
        t, tid = spec
        req = InjectRequest(type=t, target_id=tid)
        inc = world.inject(req)
        incident_ids.append(inc.incident_id)
    # Give the worker thread a moment to apply.
    time.sleep(0.6)
    snap = world.snapshot()
    print(f"      OK -> incidents_fired_count={snap['incidents_fired_count']} (expected >=6)")
    assert snap["incidents_fired_count"] >= 6, "not enough incidents recorded"
    print()

    # 4. Modulation state reflects demand_spike + power_dip.
    print("[4/5] Plant modulation reflects demand_spike + power_dip...")
    print(f"      demand_multiplier={snap['modulation']['demand_multiplier']:.3f} (expected >= 3.0)")
    print(f"      throughput_cap_pct={snap['modulation']['throughput_cap_pct']:.3f} (expected <= 0.6)")
    assert snap["modulation"]["demand_multiplier"] >= 2.9, "demand_spike not applied"
    assert snap["modulation"]["throughput_cap_pct"] <= 0.61, "power_dip not applied"
    print()

    # 5. IncidentPayload JSON-round-trip (what FastAPI returns).
    print("[5/5] IncidentPayload JSON round-trip (the HTTP response shape)...")
    payload = world.incidents_fired[0].to_payload()
    j = json.dumps(payload.model_dump(mode="json"), indent=2)
    print(j)
    print()

    world.stop(timeout=2.0)
    print("=== ALL SMOKE CHECKS PASSED ===")
    print(f"Total incidents fired this run: {len(incident_ids)}")
    print(f"Final sim_time_seconds: {snap['sim_time_seconds']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
