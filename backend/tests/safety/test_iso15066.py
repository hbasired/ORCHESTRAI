"""Stage 17 — ISO/TS 15066 collaborative speed/separation limits enforced as contract invariants (KB_17)."""
from safety.contract import Action
from safety.contracts import get_contract
from safety.validator import validate


def _act(name: str) -> Action:
    return Action(contract=name, actuator="amr.move", target="AMR-1")


def _base_ws(**over):
    ws = {"battery_pct": 80.0, "path_clear_vision": True, "path_clear_lidar": True, "zone_restricted": False,
          "zone_speed_limit_mps": 0.25}
    ws.update(over)
    return ws


def test_speed_within_zone_limit_allowed():
    c = get_contract("move_amr_to_charging_station")
    d = validate(_act(c.name), _base_ws(planned_speed_mps=0.20), c)
    assert d.allow is True and d.route == "sil_bridge"


def test_speed_over_zone_limit_blocked_by_invariant():
    c = get_contract("move_amr_to_charging_station")
    d = validate(_act(c.name), _base_ws(planned_speed_mps=0.9), c)   # 0.9 > 0.25 ISO/TS 15066 zone limit
    assert d.allow is False
    assert any("speed_within_zone_limit" in f for f in d.failed_checks)
    assert d.fail_safe_path == "SS1"


def test_default_collab_speed_cap_applied_when_no_zone_limit():
    """With no explicit zone limit, the conservative ISO/TS 15066 collaborative cap (0.25 m/s) applies."""
    c = get_contract("dispatch_amr_to_zone")
    ws = {"zone_known": True, "zone_occupancy": 0, "zone_capacity": 3, "amr_status": "idle", "planned_speed_mps": 0.5}
    d = validate(_act(c.name), ws, c)   # no zone_speed_limit_mps -> default 0.25 cap -> 0.5 violates
    assert d.allow is False and any("speed_within_zone_limit" in f for f in d.failed_checks)


def test_path_must_be_clear_vision_and_lidar_agree():
    c = get_contract("move_amr_to_charging_station")
    d = validate(_act(c.name), _base_ws(planned_speed_mps=0.2, path_clear_lidar=False), c)
    assert d.allow is False and any("path_clear" in f for f in d.failed_checks)
