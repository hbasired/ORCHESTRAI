"""Stage 38 — Facilities / Energy head-agent (G-018): the KB_25 loop extended to industrial energy management.

Peak-shaving + load-shifting against a documented ToU + demand-charge tariff, formulated as a REAL MILP (HiGHS) over
the sim's REAL per-stage `nominal_kw`, validator-gated (Hard Rule 3) and audit-signed (Art-12). Research §49.
"""
from agents.facilities.optimizer import EnergyPlan, baseline_plan, optimize_energy
from agents.facilities.orchestrator import ENERGY_LOAD_SHIFT_CONTRACT, EnergyCycleResult, EnergyOrchestrator
from agents.facilities.signals import FacilityProfile, StageLoad, observe_from_calibration
from agents.facilities.tariff import Tariff

__all__ = [
    "Tariff", "StageLoad", "FacilityProfile", "observe_from_calibration",
    "EnergyPlan", "optimize_energy", "baseline_plan",
    "EnergyOrchestrator", "EnergyCycleResult", "ENERGY_LOAD_SHIFT_CONTRACT",
]
