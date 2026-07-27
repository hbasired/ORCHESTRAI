"""Stage 38 — Facilities / Energy head-agent API (G-018, research §49).

  * POST /facilities/optimize-energy — run the KB_25 energy loop: observe real per-stage kW → diagnose an approaching
    demand-charge breach → optimise (MILP peak-shaving / load-shifting) → VERIFY through the safety validator
    (Hard Rule 3) → return the gated plan + measured peak/cost reduction (signed to the audit chain, Art-12).

Free/local (scipy HiGHS MILP, no new deps). Honest: a fully-constrained facility that cannot shift returns a plan with
0% reduction — never a fabricated saving.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/facilities", tags=["Facilities / Energy (Stage 38)"])


class OptimizeEnergyRequest(BaseModel):
    required_slots: int = Field(default=6, ge=1, le=24, description="run-hours each stage needs in the day")
    horizon_slots: int = Field(default=24, ge=1, le=48)
    demand_cap_kw: Optional[float] = Field(default=None, description="contracted demand cap; a baseline peak above it is diagnosed as a breach")
    window_start: Optional[int] = Field(default=None, ge=0, le=47)
    window_end: Optional[int] = Field(default=None, ge=0, le=47)


@router.post("/optimize-energy")
async def optimize_energy_route(req: OptimizeEnergyRequest) -> dict[str, Any]:
    """Peak-shaving / load-shifting energy optimisation over the facility's real per-stage kW (validator-gated)."""
    import asyncio as _asyncio

    from agents.facilities.orchestrator import EnergyOrchestrator
    from agents.facilities.signals import observe_from_calibration
    from agents.facilities.tariff import Tariff

    window = None
    if req.window_start is not None and req.window_end is not None:
        window = (req.window_start, req.window_end)

    def _run() -> dict[str, Any]:
        profile = observe_from_calibration(horizon_slots=req.horizon_slots,
                                           required_slots=req.required_slots, window=window)
        tariff = Tariff(horizon_slots=req.horizon_slots)
        orch = EnergyOrchestrator(demand_cap_kw=req.demand_cap_kw)
        result = orch.run_cycle(profile, tariff, required_slots=req.required_slots)
        out = result.to_dict()
        out["note"] = ("KB_25 energy loop: observe real per-stage kW -> diagnose -> MILP peak-shave/load-shift -> "
                       "VERIFY via safety.validator (Hard Rule 3: the agent proposes; it never actuates directly) -> "
                       "signed audit_chain row (Art-12). A fully-constrained facility returns 0% reduction, not a fake saving.")
        return out

    return await _asyncio.to_thread(_run)


__all__ = ["router"]
