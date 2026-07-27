"""Stage 2 — POST /api/simulation/inject payload validation tests.

Acceptance criterion (Stage 2 task doc):
  > Malformed `/inject` payload returns 400 with a Pydantic error body --
  > no partial state mutation.

These tests exercise the Pydantic `InjectRequest` schema directly so they
run fast (no SimPy, no Postgres, no HTTP roundtrip) and give high signal
on the contract boundary.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from simulation.entities import InjectRequest, validate_inject_payload


class TestInjectRequestSchema:
    """All six incident types validate correctly with sensible defaults."""

    def test_machine_crack_with_target(self):
        req = InjectRequest(type="machine_crack", target_id=4)
        assert req.target_id == 4
        assert req.details["eta_minutes"] == 12.0  # default from EVENT_IMPACT

    def test_robot_down_with_target(self):
        req = InjectRequest(type="robot_down", target_id=7)
        assert req.target_id == 7

    def test_late_delivery_with_target(self):
        req = InjectRequest(type="late_delivery", target_id=2)
        assert req.target_id == 2
        assert req.details["delay_minutes"] == 25.0

    def test_demand_spike_no_target_needed(self):
        req = InjectRequest(type="demand_spike", details={"sku": "SKU-42"})
        assert req.target_id is None
        assert req.details["sku"] == "SKU-42"
        assert req.details["multiplier"] == 3.0  # default
        assert req.details["duration_minutes"] == 20.0  # default

    def test_defect_surge_with_target(self):
        req = InjectRequest(type="defect_surge", target_id=3)
        assert req.target_id == 3
        assert req.details["rate_increase"] == 6.0

    def test_power_dip_no_target_needed(self):
        req = InjectRequest(type="power_dip")
        assert req.details["max_throughput_pct"] == 0.6


class TestRejection:
    """Malformed payloads raise ValidationError (-> 400 at REST boundary)."""

    def test_unknown_type_rejected(self):
        with pytest.raises(ValidationError):
            InjectRequest(type="kaboom", target_id=1)

    def test_machine_crack_without_target_rejected(self):
        with pytest.raises(ValidationError):
            InjectRequest(type="machine_crack")

    def test_robot_down_without_target_rejected(self):
        with pytest.raises(ValidationError):
            InjectRequest(type="robot_down")

    def test_late_delivery_without_target_rejected(self):
        with pytest.raises(ValidationError):
            InjectRequest(type="late_delivery")

    def test_defect_surge_without_target_rejected(self):
        with pytest.raises(ValidationError):
            InjectRequest(type="defect_surge")

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError):
            InjectRequest(type="power_dip", severity="catastrophic")  # not in info|warning|critical


class TestValidateHelper:
    """`validate_inject_payload(raw_dict)` is the REST entry point."""

    def test_accepts_dict_with_defaults_applied(self):
        req = validate_inject_payload({"type": "machine_crack", "target_id": 5})
        assert req.severity == "warning"
        assert req.details["eta_minutes"] == 12.0

    def test_rejects_dict_with_bad_type(self):
        with pytest.raises(ValidationError):
            validate_inject_payload({"type": "invalid_type"})

    def test_user_provided_details_override_defaults(self):
        req = validate_inject_payload(
            {
                "type": "machine_crack",
                "target_id": 1,
                "details": {"eta_minutes": 3.5, "custom_field": "ok"},
            }
        )
        assert req.details["eta_minutes"] == 3.5
        assert req.details["custom_field"] == "ok"
