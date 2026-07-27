"""Stage 16 — VDA 5050 v2.1.0 schema conformance: canned payloads validate against the REAL upstream schemas
(vendored from the VDA5050 repo @ tag 2.1.0) AND parse into the generated Pydantic models. An invalid payload MUST
fail validation (proves the validation is real, not a no-op)."""
import json
from pathlib import Path

import jsonschema
import pytest

_SCHEMAS = Path(__file__).resolve().parents[1].parent / "integrations" / "vda5050" / "schemas"
_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "vda5050"


def _schema(name: str) -> dict:
    return json.loads((_SCHEMAS / f"{name}.json").read_text(encoding="utf-8"))


def _fixture(name: str) -> dict:
    return json.loads((_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_schemas_are_v2_1_0():
    """The vendored schemas are v2.1.0 (state uses batteryState, not the v3.0.0 powerSupply)."""
    req = _schema("state").get("required", [])
    assert "batteryState" in req and "powerSupply" not in req


@pytest.mark.parametrize("topic", ["order", "state", "connection"])
def test_fixture_validates_against_real_schema(topic):
    jsonschema.validate(_fixture(topic), _schema(topic))


def test_fixtures_parse_into_generated_pydantic_models():
    from integrations.vda5050.models import Connection, OrderMessage, State
    OrderMessage(**_fixture("order"))
    State(**_fixture("state"))
    Connection(**_fixture("connection"))


def test_invalid_order_is_rejected():
    """A real validation: an order missing the required orderId must fail (not silently pass)."""
    bad = _fixture("order")
    del bad["orderId"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema("order"))


def test_master_built_order_is_schema_valid():
    """The master controller's build_order produces a v2.1.0-schema-valid order."""
    from integrations.vda5050.master import Vda5050Master
    m = Vda5050Master()
    nodes = [{"nodeId": "n1", "sequenceId": 0, "released": True, "actions": []},
             {"nodeId": "n2", "sequenceId": 2, "released": True, "actions": []}]
    edges = [{"edgeId": "e1", "sequenceId": 1, "released": True,
              "startNodeId": "n1", "endNodeId": "n2", "actions": []}]
    order = m.build_order("ACME", "AGV-1", nodes, edges)
    jsonschema.validate(order, _schema("order"))


def test_policy_fleet_routing_builds_schema_valid_order():
    """policy_query's VDA-shaped routing → master.build_order → a schema-valid order (the Stage-16 fleet bridge)."""
    from integrations.vda5050.actions import recommend_fleet_order
    from integrations.vda5050.master import Vda5050Master
    routing = recommend_fleet_order(
        {"kind": "expedite", "stage_id": 3, "rationale": "queue backup"},
        {"manufacturer": "ACME", "serial_number": "AGV-1", "pickup_node": "P1", "dropoff_node": "D1"})
    m = Vda5050Master()
    order = m.build_order("ACME", "AGV-1", routing["nodes"], routing["edges"])
    jsonschema.validate(order, _schema("order"))
    assert order["nodes"][0]["actions"][0]["actionType"] == "pick"


def _predictor_available() -> bool:
    try:
        from ml.failure_predictor import get_failure_predictor
        return get_failure_predictor().is_available()
    except Exception:
        return False


@pytest.mark.skipif(not _predictor_available(), reason="failure predictor unavailable (honest skip)")
def test_policy_query_recommend_action_emits_vda_routing_only_with_fleet():
    """AC: the MCP tool `policy_query.recommend_action` returns VDA-5050-shaped routing WHEN a `fleet` block is
    present, and NOT otherwise. Exercises the real pipeline (predict → diagnose → intervene)."""
    from mcp_servers.policy_query_server import recommend_action
    fn = getattr(recommend_action, "fn", recommend_action)   # unwrap the @mcp.tool wrapper
    tele = {"stage_id": 3, "type_": "M", "air_temp_k": 301.0, "process_temp_k": 312.0,
            "rot_speed_rpm": 1300.0, "torque_nm": 68.0, "tool_wear_min": 240.0, "queue_depth": 5}
    with_fleet = fn({**tele, "fleet": {"manufacturer": "ACME", "serial_number": "AGV-1",
                                       "pickup_node": "P1", "dropoff_node": "D1"}})
    assert with_fleet.get("available") is True
    routing = with_fleet.get("vda5050_routing")
    assert routing and [n["nodeId"] for n in routing["nodes"]] == ["P1", "D1"]
    # the routing builds a schema-valid order
    from integrations.vda5050.master import Vda5050Master
    jsonschema.validate(Vda5050Master().build_order("ACME", "AGV-1", routing["nodes"], routing["edges"]),
                        _schema("order"))
    # no fleet block → no VDA routing (it's only emitted "when fleet routing is appropriate")
    assert "vda5050_routing" not in fn(tele)
