"""MCP server: sim_world — inject_event · query_state · subscribe_events.

Drives + reads this process's deterministic local `SimWorld` (a REAL SimPy engine; fixed seed). Cross-process
sharing with the live FastAPI app's world is a later integration concern (documented in the ADR) — here the tools
expose a real, self-contained simulation the agent can drive and query. No fabrication: query results are the
engine's actual snapshot.
"""
from __future__ import annotations

from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from mcp_servers._common import apply_inject, get_local_sim, ok, run_server, unavailable

# Import the heavy deps at MODULE LOAD (main thread). FastMCP runs sync tools in an anyio worker thread; importing
# numpy/simpy/the simulation package for the FIRST time inside that worker thread (in a subprocess) deadlocks on the
# CPython import lock. Importing here, on the main thread before the event loop starts, makes the in-tool imports a
# cached no-op. (Same reason the other model servers warm their imports at module load.)
import simulation.sim_world  # noqa: E402,F401
import simulation.entities  # noqa: E402,F401

mcp = FastMCP("sim_world")

_ALLOWED = ("machine_crack", "robot_down", "late_delivery", "demand_spike", "defect_surge", "power_dip")


def _incident_to_dict(inc: Any) -> dict:
    if hasattr(inc, "model_dump"):
        try:
            return {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                    for k, v in inc.model_dump().items()}
        except Exception:  # noqa: BLE001
            pass
    return {k: getattr(inc, k) for k in ("incident_id", "type", "target_id", "severity") if hasattr(inc, k)}


@mcp.tool()
def inject_event(event_type: str, target_id: Optional[int] = None,
                 details: Optional[dict] = None, severity: str = "warning") -> dict:
    """Inject a simulator event into the local plant world.

    `event_type`: one of machine_crack, robot_down, late_delivery, demand_spike, defect_surge, power_dip.
    `target_id`: stage/robot/supplier id (required for machine_crack, defect_surge, robot_down, late_delivery).
    Returns {available, incident_id, type, target_id, severity} or {available: false, reason}.
    """
    if event_type not in _ALLOWED:
        return unavailable(f"unknown event_type {event_type!r}; allowed: {_ALLOWED}", input_error=True)
    try:
        from simulation.entities import InjectRequest
        sim = get_local_sim()
        req = InjectRequest(type=event_type, target_id=target_id, details=details or {}, severity=severity)
        inc = apply_inject(sim, req)  # synchronous apply + advance (no worker thread; stdio-safe)
        return ok(_incident_to_dict(inc))
    except Exception as e:  # noqa: BLE001
        if isinstance(e, (ValueError, KeyError)):
            return unavailable(f"bad input: {e}", input_error=True)
        if isinstance(e, ImportError):
            return unavailable(f"simulation unavailable: {e}")
        raise


@mcp.tool()
def query_state(scope: str = "all") -> dict:
    """Snapshot of the local plant world. `scope`: all | stages | robots | suppliers | summary.

    Returns {available, sim_time_seconds, stages?, robots?, suppliers?, throughput_units_per_hour, ...}.
    """
    try:
        snap = get_local_sim().snapshot()
    except ImportError as e:
        return unavailable(f"simulation unavailable: {e}")
    if scope == "all":
        return ok(snap)
    if scope == "summary":
        return ok({k: snap[k] for k in ("sim_time_seconds", "throughput_units_per_hour",
                                        "amr_utilization", "orders_complete", "incidents_fired_count")
                   if k in snap})
    if scope in ("stages", "robots", "suppliers"):
        return ok({"sim_time_seconds": snap.get("sim_time_seconds"), scope: snap.get(scope, [])})
    return unavailable(f"unknown scope {scope!r}", input_error=True)


@mcp.tool()
def subscribe_events(since_index: int = 0, event_type: Optional[str] = None) -> dict:
    """Poll incidents fired since `since_index` (a cursor). stdio MCP has no server push, so this is a
    poll — the honest equivalent of a subscription over stdio.

    Returns {available, events: [...], next_index} (filtered by `event_type` if given).
    """
    try:
        sim = get_local_sim()
    except ImportError as e:
        return unavailable(f"simulation unavailable: {e}")
    fired = list(getattr(sim, "incidents_fired", []))
    window = fired[max(0, int(since_index)):]
    events = [_incident_to_dict(i) for i in window]
    if event_type:
        events = [e for e in events if e.get("type") == event_type]
    return ok({"events": events, "next_index": len(fired)})


if __name__ == "__main__":
    run_server(mcp, "sim_world_server")
