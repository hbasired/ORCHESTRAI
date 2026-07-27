"""Stage 14 — A2A capability `forecast_oee` (KB_16 use case: a customer MES queries our agent for an OEE forecast).

Computes a REAL plant OEE = Availability × Performance × Quality from the live SimWorld snapshot (ideal cycle time
from the real stage calibration — same math as the Stage-11.5 kpi server). Honest: no live world → `available:false`
(never a fabricated number). This is the deliberate external capability; it does NOT expose the internal MCP tools.
"""
from __future__ import annotations

import math
from typing import Any


def _plant_oee_from_snapshot(snap: dict) -> dict:
    from simulation.calibration import STAGES
    ideal = {s.stage_id: math.exp(s.cycle_mu_log_seconds) for s in STAGES}
    elapsed = float(snap.get("sim_time_seconds", 0.0))
    if elapsed <= 0:
        return {"available": False, "reason": "elapsed sim time is zero; OEE undefined"}
    rows = []
    for s in snap.get("stages", []):
        sid = int(s["stage_id"])
        broken = float(s.get("time_broken_seconds", 0.0)) + float(s.get("time_maintenance_seconds", 0.0))
        uptime = max(elapsed - broken, 1e-6)
        produced = int(s.get("units_produced", 0))
        defective = int(s.get("units_defective", 0))
        availability = max(0.0, min(1.0, uptime / elapsed))
        performance = min(1.0, (ideal.get(sid, 0.0) * produced) / uptime) if produced else 0.0
        quality = ((produced - defective) / produced) if produced else 0.0
        rows.append(round(availability * performance * quality, 4))
    if not rows:
        return {"available": False, "reason": "no stages in snapshot"}
    return {"available": True, "plant_oee": round(sum(rows) / len(rows), 4), "n_stages": len(rows),
            "elapsed_seconds": elapsed}


def forecast_oee(params: dict) -> dict:
    """A2A capability: return the plant OEE from the live SimWorld (honest-unavailable if no world is bound).

    `params`: optional {state: <snapshot>} to compute from a supplied snapshot instead of the live world.
    Returns {available, plant_oee, n_stages, elapsed_seconds} or {available: false, reason}.
    """
    snap = params.get("state") if isinstance(params, dict) else None
    if snap is None:
        try:
            from api.simulation_routes import get_sim_world
            sw = get_sim_world()
        except Exception:  # noqa: BLE001
            sw = None
        if sw is None:
            return {"available": False, "reason": "no live SimWorld bound; supply `state` or run the app"}
        snap = sw.snapshot()
    return _plant_oee_from_snapshot(snap)


__all__ = ["forecast_oee"]
