"""Stage 8C — neuro-symbolic plan verifier tests (VERIFY step, KB_25 step 3).

Pure-unit, deterministic. Verifies that the symbolic constraint engine APPROVES safe plans and
REJECTS plans that violate the crew/throughput/redundancy/precondition contracts.
"""
from __future__ import annotations

from services.plan_verifier import (
    PlannedAction, PlantState, verify, from_decisions,
    PREVENTIVE_MAINTENANCE, MONITOR, HARD,
)


def _state(**ov) -> PlantState:
    stages = {
        1: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0},
        2: {"status": "degraded", "at_risk": True, "crack_proximity": 0.5},
        3: {"status": "degraded", "at_risk": True, "crack_proximity": 0.9},
        4: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0},
        5: {"status": "nominal", "at_risk": False, "crack_proximity": 0.0},
    }
    base = dict(stages=stages, available_crew=1, throughput_floor_frac=0.6,
                critical_proximity=0.85, max_concurrent_critical_offline=1)
    base.update(ov)
    return PlantState(**base)


def test_approves_single_valid_maintenance():
    plan = [PlannedAction(PREVENTIVE_MAINTENANCE, 2, "wear")]
    r = verify(plan, _state())
    assert r.approved is True
    assert not [v for v in r.violations if v.severity == HARD]


def test_rejects_crew_over_capacity():
    # two simultaneous maintenances but only one crew
    plan = [PlannedAction(PREVENTIVE_MAINTENANCE, 2), PlannedAction(PREVENTIVE_MAINTENANCE, 3)]
    r = verify(plan, _state(available_crew=1))
    assert r.approved is False
    assert any(v.constraint == "crew_capacity" and v.severity == HARD for v in r.violations)


def test_rejects_maintenance_on_broken_machine():
    st = _state()
    st.stages[2]["status"] = "broken"
    r = verify([PlannedAction(PREVENTIVE_MAINTENANCE, 2)], st)
    assert r.approved is False
    assert any(v.constraint == "maintenance_precondition" for v in r.violations)


def test_rejects_throughput_floor_breach():
    # floor 0.6 over 5 stages => need >=3 online; down 3 of the 5 online -> only 2 online -> reject.
    st = _state(available_crew=3)
    plan = [PlannedAction(PREVENTIVE_MAINTENANCE, s) for s in (2, 3, 4)]
    r = verify(plan, st)
    assert r.approved is False
    assert any(v.constraint == "throughput_floor" for v in r.violations)


def test_rejects_two_critical_offline():
    # stage 3 is critical (0.9). Make stage 2 critical too and down both -> SIL contract violation.
    st = _state(available_crew=2)
    st.stages[2]["crack_proximity"] = 0.9
    plan = [PlannedAction(PREVENTIVE_MAINTENANCE, 2), PlannedAction(PREVENTIVE_MAINTENANCE, 3)]
    r = verify(plan, st)
    assert r.approved is False
    assert any(v.constraint == "critical_redundancy" for v in r.violations)


def test_soft_violation_does_not_reject():
    # maintaining a healthy machine is a SOFT warning, not a rejection.
    plan = [PlannedAction(PREVENTIVE_MAINTENANCE, 1)]  # stage 1 not at-risk
    r = verify(plan, _state())
    assert r.approved is True
    assert any(v.constraint == "act_on_risk_only" and v.severity == "soft" for v in r.violations)


def test_monitor_actions_are_free():
    # MONITOR / non-offline actions consume no crew/capacity and always pass.
    plan = [PlannedAction(MONITOR, 1), PlannedAction(MONITOR, 4)]
    r = verify(plan, _state(available_crew=0))
    assert r.approved is True


def test_from_decisions_adapter():
    from services.intervention_policy import InterventionDecision
    dec = InterventionDecision(stage_id=2, kind=PREVENTIVE_MAINTENANCE, rationale="wear", diagnosis={})
    plan = from_decisions([dec])
    assert plan[0].stage_id == 2 and plan[0].kind == PREVENTIVE_MAINTENANCE
    assert verify(plan, _state()).approved is True
