"""Stage 17 — the CI trace-pairing invariant: every actuator.* span is preceded by a safety.validate.* span (KB_17).

Captures REAL spans via the OTel in-memory exporter from a validate→execute flow, runs the CI gate's `check_pairing`,
and asserts (a) the real flow passes, (b) a deliberately-unpaired actuator span FAILS, and (c) writes a sample trace
to `audits/STAGE_17_traces.json` so `scripts/check-safety-trace-pairing.py` can run standalone.
"""
import importlib.util
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]


def _load_gate():
    spec = importlib.util.spec_from_file_location("safety_trace_gate", _REPO / "scripts" / "check-safety-trace-pairing.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _spans_to_dicts(spans):
    return [{"name": s.name, "start_time": s.start_time} for s in spans]


def test_real_validate_then_actuator_flow_is_paired():
    from observability.otel_init import use_in_memory_exporter
    from safety.contract import Action
    from safety.contracts import get_contract
    from safety.validator import validate
    from safety import sil_bridge

    exporter = use_in_memory_exporter()
    c = get_contract("start_conveyor_segment")
    action = Action(contract=c.name, actuator="conveyor", target="S1")
    decision = validate(action, {"light_curtain_intact": True, "person_in_vicinity": False}, c)   # safety.validate span
    assert decision.allow
    sil_bridge.execute(action, decision, world_state={"light_curtain_intact": True})              # actuator.* span

    spans = _spans_to_dicts(exporter.get_finished_spans())
    names = [s["name"] for s in spans]
    assert any(n.startswith("safety.validate") for n in names)
    assert any(n.startswith("actuator.") for n in names)

    gate = _load_gate()
    assert gate.check_pairing(spans) == []   # every actuator span is preceded by a safety.validate span

    # write a sample trace for the standalone CI gate / verification command
    out = _REPO / "audits" / "STAGE_17_traces.json"
    out.write_text(json.dumps({"spans": spans}, indent=2), encoding="utf-8")
    assert out.exists()


def test_unpaired_actuator_span_is_flagged():
    """A negative control: an actuator span with NO preceding safety.validate must be reported as a violation."""
    gate = _load_gate()
    bad = [{"name": "actuator.conveyor", "start_time": 100},
           {"name": "some.other.span", "start_time": 50}]
    assert gate.check_pairing(bad) == ["actuator.conveyor"]


def test_validate_before_actuator_ordering_enforced():
    """An actuator span that STARTS before the only safety.validate span is a violation (ordering matters)."""
    gate = _load_gate()
    spans = [{"name": "actuator.x", "start_time": 10}, {"name": "safety.validate", "start_time": 20}]
    assert gate.check_pairing(spans) == ["actuator.x"]
