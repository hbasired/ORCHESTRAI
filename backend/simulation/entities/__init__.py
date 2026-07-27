"""SimPy entity processes for the plant simulator.

Each entity owns a small piece of plant state and a SimPy process that
advances that state over simulated time. The orchestrator is
`backend/simulation/sim_world.py`.
"""
from __future__ import annotations

from .incident import (
    Incident,
    IncidentPayload,
    InjectRequest,
    apply_incident_to_world,
    validate_inject_payload,
)
from .robot import Robot, Task
from .stage import Stage
from .supplier import Supplier

__all__ = [
    "Incident",
    "IncidentPayload",
    "InjectRequest",
    "Robot",
    "Stage",
    "Supplier",
    "Task",
    "apply_incident_to_world",
    "validate_inject_payload",
]
