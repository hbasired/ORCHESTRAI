"""Incident dataclass + Pydantic inject-request schema + per-type behaviour.

The six event types come from KB_05_Simulation_Spec.md and are constrained by
the Postgres `incidents.type` CHECK constraint
(backend/alembic/versions/0001_init.py).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from ..calibration import EVENT_IMPACT, INCIDENT_TYPES, IncidentType

if TYPE_CHECKING:
    from ..sim_world import SimWorld


Severity = Literal["info", "warning", "critical"]


# ---------------------------------------------------------------------------
# Pydantic inject schema (REST contract for POST /api/simulation/inject)
# ---------------------------------------------------------------------------


class InjectRequest(BaseModel):
    """Validated payload for POST /api/simulation/inject.

    Matches KB_05 §"Triggers" and KB_07 §"API Contracts" (added at Stage 2 close).
    """

    type: IncidentType = Field(..., description="One of the six allowed event types.")
    target_id: Optional[int] = Field(
        default=None,
        description=(
            "Numeric id of the affected entity. Meaning depends on `type`: "
            "machine_crack/defect_surge → stage_id; robot_down → robot_id; "
            "late_delivery → supplier_id; demand_spike/power_dip → optional/none."
        ),
    )
    details: dict[str, Any] = Field(default_factory=dict, description="Event-specific payload.")
    severity: Severity = Field(default="warning", description="Operator-facing severity.")

    @model_validator(mode="after")
    def _sanity_per_type(self) -> "InjectRequest":
        t = self.type
        d = self.details
        if t in ("machine_crack", "defect_surge") and self.target_id is None:
            raise ValueError(f"target_id (stage_id) is required for type='{t}'")
        if t == "robot_down" and self.target_id is None:
            raise ValueError("target_id (robot_id) is required for type='robot_down'")
        if t == "late_delivery" and self.target_id is None:
            raise ValueError("target_id (supplier_id) is required for type='late_delivery'")
        if t == "machine_crack":
            d.setdefault("eta_minutes", EVENT_IMPACT.machine_crack_default_eta_minutes)
        elif t == "late_delivery":
            d.setdefault("delay_minutes", EVENT_IMPACT.late_delivery_default_delay_minutes)
        elif t == "demand_spike":
            d.setdefault("multiplier", EVENT_IMPACT.demand_spike_default_multiplier)
            d.setdefault("duration_minutes", EVENT_IMPACT.demand_spike_default_duration_minutes)
            d.setdefault("sku", "default")
        elif t == "defect_surge":
            d.setdefault("rate_increase", EVENT_IMPACT.defect_surge_default_multiplier)
            d.setdefault("duration_minutes", EVENT_IMPACT.defect_surge_default_duration_minutes)
        elif t == "power_dip":
            d.setdefault("max_throughput_pct", EVENT_IMPACT.power_dip_default_pct)
            d.setdefault("duration_minutes", EVENT_IMPACT.power_dip_default_duration_minutes)
        return self


class IncidentPayload(BaseModel):
    """Outbound WebSocket / persistence-layer shape for an Incident.

    Mirrors the row written to the Postgres `incidents` table plus the
    transient fields needed by the WebSocket envelope.
    """

    incident_id: str
    type: IncidentType
    target_id: Optional[int] = None
    details: dict[str, Any] = Field(default_factory=dict)
    severity: Severity = "warning"
    started_at: datetime
    ended_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Internal Incident dataclass + per-type behaviour
# ---------------------------------------------------------------------------


@dataclass
class Incident:
    """In-process record of an active or recently-closed incident."""

    incident_id: str
    type: IncidentType
    target_id: Optional[int]
    details: dict[str, Any]
    severity: Severity
    started_at: datetime
    ended_at: Optional[datetime] = None
    # Per-incident SimPy bookkeeping (set during apply, read by tests).
    _was_serialized_after: Optional[str] = field(default=None, repr=False)

    @classmethod
    def from_request(cls, req: InjectRequest) -> "Incident":
        return cls(
            incident_id=str(uuid.uuid4()),
            type=req.type,
            target_id=req.target_id,
            details=dict(req.details),
            severity=req.severity,
            started_at=datetime.now(timezone.utc),
        )

    def to_payload(self) -> IncidentPayload:
        return IncidentPayload(
            incident_id=self.incident_id,
            type=self.type,
            target_id=self.target_id,
            details=self.details,
            severity=self.severity,
            started_at=self.started_at,
            ended_at=self.ended_at,
        )


def validate_inject_payload(raw: dict[str, Any]) -> InjectRequest:
    """Validate-only entry point used by the REST route + tests."""
    return InjectRequest.model_validate(raw)


def apply_incident_to_world(world: "SimWorld", incident: Incident) -> None:
    """Mutate `world` state according to the incident type.

    Called from inside the SimPy worker thread (which holds the world lock).
    Returns nothing; effects are visible via subsequent ticks.
    """
    t = incident.type
    if t == "machine_crack":
        stage = world.stages.get(incident.target_id)
        if stage is not None:
            stage.schedule_crack(eta_seconds=float(incident.details.get("eta_minutes", EVENT_IMPACT.machine_crack_default_eta_minutes)) * 60.0)
    elif t == "robot_down":
        robot = world.robots.get(incident.target_id)
        if robot is not None:
            robot.force_down(recovery_seconds=EVENT_IMPACT.robot_down_recovery_seconds)
    elif t == "late_delivery":
        supplier = world.suppliers.get(incident.target_id)
        if supplier is not None:
            supplier.delay_next_delivery(seconds=float(incident.details.get("delay_minutes", EVENT_IMPACT.late_delivery_default_delay_minutes)) * 60.0)
    elif t == "demand_spike":
        world.activate_demand_spike(
            multiplier=float(incident.details.get("multiplier", EVENT_IMPACT.demand_spike_default_multiplier)),
            duration_seconds=float(incident.details.get("duration_minutes", EVENT_IMPACT.demand_spike_default_duration_minutes)) * 60.0,
        )
    elif t == "defect_surge":
        stage = world.stages.get(incident.target_id)
        if stage is not None:
            stage.activate_defect_surge(
                multiplier=float(incident.details.get("rate_increase", EVENT_IMPACT.defect_surge_default_multiplier)),
                duration_seconds=float(incident.details.get("duration_minutes", EVENT_IMPACT.defect_surge_default_duration_minutes)) * 60.0,
            )
    elif t == "power_dip":
        world.activate_power_dip(
            max_throughput_pct=float(incident.details.get("max_throughput_pct", EVENT_IMPACT.power_dip_default_pct)),
            duration_seconds=float(incident.details.get("duration_minutes", EVENT_IMPACT.power_dip_default_duration_minutes)) * 60.0,
        )
    else:
        raise ValueError(f"Unknown incident type: {t}")


__all__ = [
    "Incident",
    "IncidentPayload",
    "InjectRequest",
    "INCIDENT_TYPES",
    "apply_incident_to_world",
    "validate_inject_payload",
]
