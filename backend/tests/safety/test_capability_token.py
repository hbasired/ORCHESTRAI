"""Stage 33 (G-075) — unforgeable actuation capability tokens: a forged Decision can no longer actuate; a token is
bound to its exact action and expires. This is the fix for the longest-lived open safety item (CTO #4/#5/#6)."""
from __future__ import annotations

import time

import pytest

from safety.contract import Action, Decision, Precondition, SafetyContract
from safety.validator import validate
from safety import sil_bridge


def _contract(sil=2):
    return SafetyContract(name="cap_test", sil=sil, iso_clauses=[],
                          preconditions=[Precondition(name="safe", description="", check=lambda ws: bool(ws.get("safe")))],
                          invariants=[], fail_safe_path="STO")


def _act(actuator="robot.move", target="robot:1"):
    return Action(contract="cap_test", actuator=actuator, params={}, target=target)


def test_genuine_validate_then_execute_carries_a_token_and_actuates():
    c, a = _contract(), _act()
    d = validate(a, {"safe": True}, c)
    assert d.allow and d.token and d.nonce and d.issued_at        # a real token was minted
    assert sil_bridge.execute(a, d)["executed"] is True           # token path actuates


def test_forged_allow_decision_without_token_is_rejected():
    """The G-075 core: a hand-forged Decision(allow=True, route='sil_bridge') with no token + no contract is REFUSED."""
    forged = Decision(allow=True, route="sil_bridge", reason="forged", contract="cap_test", sil=2)
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(_act(), forged)                        # no token, no re-validation -> rejected


def test_token_is_bound_to_its_action_cannot_authorize_another():
    c = _contract()
    d = validate(_act("robot.move", "robot:1"), {"safe": True}, c)   # token for robot.move
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(_act("robot.grip", "robot:9"), d)         # different action -> hash mismatch -> rejected


def test_stale_token_is_rejected_toctou_replay():
    c, a = _contract(), _act()
    d = validate(a, {"safe": True}, c)
    time.sleep(0.02)
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(a, d, token_freshness_s=0.0)             # freshness window 0 -> stale -> rejected


def test_revalidation_path_ignores_a_forged_verdict_and_rechecks_live_state():
    c = _contract()
    forged = Decision(allow=True, route="sil_bridge", reason="forged", contract="cap_test", sil=2)
    # unsafe live state -> re-validation blocks despite the forged allow
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(_act(), forged, world_state={"safe": False}, contract=c)
    # safe live state -> re-validation re-derives an allowing decision -> actuates (forged verdict ignored)
    assert sil_bridge.execute(_act(), forged, world_state={"safe": True}, contract=c)["executed"] is True


def test_tampered_token_is_rejected():
    c, a = _contract(), _act()
    d = validate(a, {"safe": True}, c)
    d.token = (d.token or "")[:-2] + "00"                          # flip the last byte of the HMAC
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(a, d)


def test_blocked_decision_still_rejected_before_token_check():
    c = _contract()
    blocked = validate(_act(), {"safe": False}, c)                # allow=False
    assert blocked.allow is False
    with pytest.raises(sil_bridge.SafetyBypassError):
        sil_bridge.execute(_act(), blocked)
