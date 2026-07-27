"""Stage 38 — facility energy observation (research §49).

Reads the REAL per-stage power model from the sim (`simulation/calibration.py::StageCalibration.nominal_kw` — the
same kW the live `manufacturing_agent` reports) and builds a schedulable-load view of the facility for the optimiser.
No fabrication: every stage's kW is its real calibrated `nominal_kw`; a stage's daily run-hours come from its required
production; the facility baseline (HVAC / lighting) is a documented, explicitly-labelled fraction of the process load,
NOT a stage that can be shifted.

Pure/deterministic; the only "I/O" is reading the in-process calibration table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Facility baseline (HVAC + lighting + IT) as a fraction of total process capacity — a documented planning ratio
# (industrial facilities typically carry a 15-25% non-process base load). Non-schedulable: it runs every slot.
BASE_LOAD_FRACTION = 0.20


@dataclass(frozen=True)
class StageLoad:
    """A schedulable stage energy load over the day."""
    stage_id: int
    name: str
    kw: float                       # the stage's real calibrated nominal_kw (kW while running)
    required_slots: int             # how many slots (hours) of run the stage needs this day to meet production
    earliest_slot: int              # start of the allowed window (inclusive)
    latest_slot: int                # end of the allowed window (inclusive) — the batch must finish by here
    schedulable: bool = True        # False → a fixed must-run load (e.g. a continuous process)

    def window(self, horizon: int) -> list[int]:
        lo = max(0, self.earliest_slot)
        hi = min(horizon - 1, self.latest_slot)
        return list(range(lo, hi + 1))


@dataclass
class FacilityProfile:
    """The facility's schedulable loads + a non-schedulable per-slot baseline (HVAC/lighting)."""
    horizon_slots: int
    loads: list[StageLoad]
    base_kw: float = 0.0            # constant non-schedulable baseline drawn EVERY slot
    meta: dict = field(default_factory=dict)

    def base_by_slot(self) -> list[float]:
        return [self.base_kw] * self.horizon_slots

    def total_required_kwh(self) -> float:
        """Total schedulable energy that MUST be delivered (the production floor the optimiser cannot cut)."""
        return sum(l.kw * l.required_slots for l in self.loads)


def observe_from_calibration(calibration=None, *, horizon_slots: int = 24,
                             required_slots: int = 6, window: Optional[tuple[int, int]] = None) -> FacilityProfile:
    """Build a FacilityProfile from the sim's REAL per-stage `nominal_kw`.

    Each stage becomes a schedulable load needing `required_slots` hours of run within `window` (default: the whole
    day, i.e. maximally shiftable). `base_kw` = BASE_LOAD_FRACTION × total process capacity (documented, labelled).
    """
    if calibration is None:
        from simulation.calibration import STAGES
        calibration = STAGES
    stages = list(getattr(calibration, "stages", calibration))
    lo, hi = window or (0, horizon_slots - 1)
    loads = [StageLoad(stage_id=c.stage_id, name=c.name, kw=float(c.nominal_kw),
                       required_slots=required_slots, earliest_slot=lo, latest_slot=hi)
             for c in stages]
    total_capacity_kw = sum(l.kw for l in loads)
    base_kw = round(BASE_LOAD_FRACTION * total_capacity_kw, 4)
    return FacilityProfile(horizon_slots=horizon_slots, loads=loads, base_kw=base_kw,
                           meta={"n_stages": len(loads), "base_load_fraction": BASE_LOAD_FRACTION,
                                 "total_process_kw": round(total_capacity_kw, 3)})


__all__ = ["StageLoad", "FacilityProfile", "observe_from_calibration", "BASE_LOAD_FRACTION"]
