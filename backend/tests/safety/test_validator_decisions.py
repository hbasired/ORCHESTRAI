"""Stage 17 — the SIL-rated validator decision matrix + SIL routing + no-bypass + SIL↔PL (KB_17)."""
import pytest

from safety.contract import Action
from safety.contracts import CONTRACTS, get_contract
from safety.sil_pl_map import meets_robot_class, pl_to_sil, sil_to_pl
from safety.validator import validate
from safety import sil_bridge


def _act(contract_name: str) -> Action:
    return Action(contract=contract_name, actuator="test", params={}, target="t1")


def test_all_five_named_contracts_present():
    """The AC's 5 named contracts exist."""
    for name in ["move_amr_to_charging_station", "start_conveyor_segment", "expedite_supplier_order",
                 "change_machine_state", "dispatch_amr_to_zone"]:
        assert name in CONTRACTS


def test_precondition_fail_blocks_and_names_fail_safe():
    c = get_contract("start_conveyor_segment")          # SIL 2, fail-safe STO
    d = validate(_act(c.name), {"light_curtain_intact": False, "person_in_vicinity": True}, c)
    assert d.allow is False and d.route == "blocked"
    assert d.fail_safe_path == "STO"
    assert any("light_curtain" in f for f in d.failed_checks)


def test_sil2_allow_routes_to_sil_bridge():
    c = get_contract("start_conveyor_segment")
    d = validate(_act(c.name), {"light_curtain_intact": True, "person_in_vicinity": False}, c)
    assert d.allow is True and d.route == "sil_bridge" and d.sil == 2


def test_sil1_routes_to_operator_confirm():
    # craft a SIL-1 contract on the fly via the DSL
    from safety.contract import Precondition, SafetyContract
    c = SafetyContract(name="advisory_reroute", sil=1, fail_safe_path="operator_confirm",
                       preconditions=[Precondition(name="ok", description="", check=lambda ws: True)])
    d = validate(_act(c.name), {}, c)
    assert d.allow is True and d.route == "operator_confirm"


def test_sil0_routes_direct():
    c = get_contract("expedite_supplier_order")
    d = validate(_act(c.name), {"supplier_reachable": True}, c)
    assert d.allow is True and d.route == "direct" and d.sil == 0


def test_sil_bridge_refuses_blocked_or_misrouted_decision():
    """Defence-in-depth: even if a caller skipped the gate, the bridge re-checks (no bypass — KB_17)."""
    c = get_contract("start_conveyor_segment")
    blocked = validate(_act(c.name), {"light_curtain_intact": False, "person_in_vicinity": True}, c)
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(_act(c.name), blocked)
    # a SIL-0 'direct' decision is also refused by the SIL bridge (it only executes SIL≥2 routed actions)
    s0 = validate(_act("expedite_supplier_order"), {"supplier_reachable": True}, get_contract("expedite_supplier_order"))
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(_act("expedite_supplier_order"), s0)


def test_sil_bridge_self_validates_and_rejects_a_forged_decision():
    """G-075 hardening: when given the contract+world_state, sil_bridge RE-RUNS validate() and ignores a forged
    Decision — so `Decision(allow=True, route='sil_bridge')` cannot actuate against an unsafe world_state."""
    from safety.contract import Decision
    c = get_contract("start_conveyor_segment")
    forged = Decision(allow=True, route="sil_bridge", reason="forged", contract=c.name, sil=2)
    # unsafe world_state (light curtain broken) → self-validation blocks despite the forged allow
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(_act(c.name), forged, world_state={"light_curtain_intact": False}, contract=c)
    # safe world_state + the same forged object → self-validation re-derives an allowing decision → executes
    res = sil_bridge.execute(_act(c.name), forged,
                             world_state={"light_curtain_intact": True, "person_in_vicinity": False}, contract=c)
    assert res["executed"] is True


def test_sil_bridge_executes_allowed_sil2_and_emits_result():
    c = get_contract("start_conveyor_segment")
    ok = validate(_act(c.name), {"light_curtain_intact": True, "person_in_vicinity": False}, c)
    res = sil_bridge.execute(_act(c.name), ok, world_state={"light_curtain_intact": True})
    assert res["executed"] is True and res["via"] == "sil_bridge" and "placeholder" in res["sil_controller"]


def test_check_exception_is_failsafe():
    """A check that raises is treated as FAILED (fail-safe), never crashes the gate."""
    from safety.contract import Precondition, SafetyContract
    c = SafetyContract(name="boom", sil=2, fail_safe_path="STO",
                       preconditions=[Precondition(name="explodes", description="",
                                                   check=lambda ws: 1 / 0)])  # noqa
    d = validate(_act(c.name), {}, c)
    assert d.allow is False and "precondition:explodes" in d.failed_checks


def test_sil_pl_mapping():
    assert sil_to_pl(2) == "d" and pl_to_sil("d") == 2 and pl_to_sil("e") == 3
    assert meets_robot_class("II", 2) is True and meets_robot_class("II", 1) is False
    assert meets_robot_class("I", 1) is True
