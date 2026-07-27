"""Stage 29 (G-023) — NL problem-injection tests: deterministic parser correctness + honest abstention +
Hard-Rule-3 preservation (the parser produces a *proposed structured incident*, never an actuator command)."""
from __future__ import annotations

import asyncio

from conversation.nl_inject import (
    INCIDENT_TYPES, InjectedIncident, parse_deterministic, parse_incident,
)


def test_deterministic_parser_maps_common_reports():
    cases = {
        "the welder on stage 3 is overheating - critical": ("machine_crack", 3, "critical"),
        "robot 2 is down": ("robot_down", 2, "warning"),
        "supplier shipment is late again": ("late_delivery", None, "warning"),
        "huge demand spike on the line": ("demand_spike", None, "warning"),
        "defect rate is surging, lots of scrap": ("defect_surge", None, "warning"),
        "power dip / voltage brownout": ("power_dip", None, "warning"),
    }
    for text, (etype, tid, sev) in cases.items():
        inc = parse_deterministic(text)
        assert inc is not None, text
        assert inc.type == etype and inc.type in INCIDENT_TYPES
        assert inc.target_id == tid
        assert inc.severity == sev


def test_deterministic_parser_abstains_on_unknown():
    for text in ["what is the meaning of life", "how many orders shipped today", ""]:
        assert parse_deterministic(text) is None      # never guesses a type


def test_injected_incident_schema_validates_domain():
    ok = InjectedIncident(type="machine_crack", severity="critical", confidence=0.8)
    ok.validate_domain()                               # no raise
    bad_type = InjectedIncident(type="meltdown")
    try:
        bad_type.validate_domain()
        assert False, "expected a domain validation error"
    except ValueError:
        pass


def test_parse_incident_falls_back_to_deterministic_without_llm():
    inc, method = asyncio.run(parse_incident("robot 4 is down hard", use_llm=False))
    assert method == "deterministic"
    assert inc is not None and inc.type == "robot_down" and inc.target_id == 4


def test_parse_incident_abstains_end_to_end():
    inc, method = asyncio.run(parse_incident("what's for lunch", use_llm=False))
    assert inc is None and method == "abstain"


def test_confidence_is_bounded():
    inc = parse_deterministic("stage 1 bearing seized, critical")
    assert 0.0 <= inc.confidence <= 1.0
