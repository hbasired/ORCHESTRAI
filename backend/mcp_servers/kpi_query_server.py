"""MCP server: kpi_query — throughput · oee · utilization · queue_depth.

Computes REAL KPIs from a plant snapshot (the shape returned by `sim_world_server.query_state`, i.e.
`SimWorld.snapshot()`). If no `state` is supplied, the tool computes from this process's own deterministic local
SimWorld (a real SimPy engine). OEE is the genuine Availability x Performance x Quality, where the ideal cycle time
comes from the real stage calibration (`cycle_mu_log_seconds`) — no fabricated performance term (Rule 1a).
"""
from __future__ import annotations

import math
from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_servers._common import ok, run_server, unavailable

# Warm heavy imports on the MAIN thread at server startup (FastMCP runs sync tools in an anyio worker thread; a
# first-time `import simulation`/numpy there deadlocks on the CPython import lock in a subprocess).
import simulation.calibration  # noqa: E402,F401
import simulation.sim_world  # noqa: E402,F401

mcp = FastMCP("kpi_query")


def _snapshot(state: Optional[dict]) -> dict:
    """Return the supplied snapshot, or build one from the local deterministic SimWorld."""
    if state:
        return state
    from mcp_servers._common import get_local_sim
    return get_local_sim().snapshot()


def _ideal_cycle_seconds() -> dict[int, float]:
    """Per-stage ideal cycle time (seconds) from the real calibration (mean of the lognormal)."""
    from simulation.calibration import STAGES
    return {s.stage_id: math.exp(s.cycle_mu_log_seconds) for s in STAGES}


@mcp.tool()
def throughput(state: Optional[dict] = None) -> dict:
    """Plant + per-stage throughput (units/hour). Source: the snapshot's cumulative aggregate.

    Returns {available, plant_units_per_hour, per_stage: [{stage_id, name, units_produced}], elapsed_seconds}.
    """
    try:
        snap = _snapshot(state)
    except Exception as e:  # noqa: BLE001
        return unavailable(f"no snapshot available: {e}")
    stages = snap.get("stages", [])
    return ok({
        "plant_units_per_hour": float(snap.get("throughput_units_per_hour", 0.0)),
        "elapsed_seconds": float(snap.get("sim_time_seconds", 0.0)),
        "per_stage": [{"stage_id": s["stage_id"], "name": s.get("name"),
                       "units_produced": s.get("units_produced", 0)} for s in stages],
    })


@mcp.tool()
def oee(state: Optional[dict] = None, stage_id: Optional[int] = None) -> dict:
    """Overall Equipment Effectiveness = Availability x Performance x Quality.

    Availability = uptime/elapsed (from time_broken+time_maintenance); Performance = (ideal_cycle x units)/uptime
    (ideal_cycle from the real stage calibration); Quality = good/total. Per-stage + plant average; one stage if
    `stage_id` is given. Returns {available, plant_oee, per_stage:[{stage_id, oee, availability, performance, quality}]}.
    """
    try:
        snap = _snapshot(state)
    except Exception as e:  # noqa: BLE001
        return unavailable(f"no snapshot available: {e}")
    elapsed = float(snap.get("sim_time_seconds", 0.0))
    if elapsed <= 0:
        return unavailable("elapsed sim time is zero; OEE undefined")
    ideal = _ideal_cycle_seconds()
    rows = []
    for s in snap.get("stages", []):
        sid = int(s["stage_id"])
        if stage_id is not None and sid != int(stage_id):
            continue
        broken = float(s.get("time_broken_seconds", 0.0))
        maint = float(s.get("time_maintenance_seconds", 0.0))
        uptime = max(elapsed - broken - maint, 1e-6)
        produced = int(s.get("units_produced", 0))
        defective = int(s.get("units_defective", 0))
        availability = max(0.0, min(1.0, uptime / elapsed))
        performance = min(1.0, (ideal.get(sid, 0.0) * produced) / uptime) if produced else 0.0
        quality = ((produced - defective) / produced) if produced else 0.0
        rows.append({"stage_id": sid, "name": s.get("name"),
                     "oee": round(availability * performance * quality, 4),
                     "availability": round(availability, 4),
                     "performance": round(performance, 4),
                     "quality": round(quality, 4),
                     "units_produced": produced})
    if not rows:
        return unavailable(f"no stage matched stage_id={stage_id}")
    plant = round(sum(r["oee"] for r in rows) / len(rows), 4)
    return ok({"plant_oee": plant, "per_stage": rows})


@mcp.tool()
def utilization(state: Optional[dict] = None, unit: Optional[int] = None) -> dict:
    """AMR fleet utilization (0..1). Plant aggregate + per-robot; one robot if `unit` given.

    Returns {available, fleet_utilization, per_robot:[{id, utilization}]}.
    """
    try:
        snap = _snapshot(state)
    except Exception as e:  # noqa: BLE001
        return unavailable(f"no snapshot available: {e}")
    robots = snap.get("robots", [])
    rows = [{"id": r.get("id"), "utilization": float(r.get("utilization", 0.0))}
            for r in robots if unit is None or r.get("id") == unit]
    if unit is not None and not rows:
        return unavailable(f"no robot with id={unit}")
    return ok({"fleet_utilization": float(snap.get("amr_utilization", 0.0)), "per_robot": rows})


@mcp.tool()
def queue_depth(state: Optional[dict] = None, stage_id: Optional[int] = None) -> dict:
    """Per-stage queue depth (WIP). One stage if `stage_id` is given.

    Returns {available, total_wip, per_stage:[{stage_id, name, queue_depth}]}.
    """
    try:
        snap = _snapshot(state)
    except Exception as e:  # noqa: BLE001
        return unavailable(f"no snapshot available: {e}")
    rows = [{"stage_id": s["stage_id"], "name": s.get("name"), "queue_depth": int(s.get("queue_depth", 0))}
            for s in snap.get("stages", []) if stage_id is None or int(s["stage_id"]) == int(stage_id)]
    if stage_id is not None and not rows:
        return unavailable(f"no stage with stage_id={stage_id}")
    return ok({"total_wip": sum(r["queue_depth"] for r in rows), "per_stage": rows})


if __name__ == "__main__":
    run_server(mcp, "kpi_query_server")
