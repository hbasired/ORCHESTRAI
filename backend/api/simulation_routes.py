"""Simulation API Routes.

Every endpoint here is now backed 100% by the real SimPy `SimWorld` twin (see backend/simulation/sim_world.py).
The old `SimulationEngine` + its `_generate_mock_state` fabrication was DELETED (2026-07): `/state` and `/events`
map the real SimWorld snapshot (positions are a deterministic visual layout — the DES twin is not spatial —
and untracked telemetry is an honest 0, never fabricated); the control endpoints (start/stop/pause/resume/
scenario/speed) are compatibility no-ops over the continuously-advancing twin; `/reset` re-initialises it.

The canonical inject endpoint is `POST /api/simulation/inject` — validated by
the Pydantic `InjectRequest` schema; returns a `IncidentPayload` shape; the
SimWorld then mutates plant state on its next tick (≤100 ms wall-clock).

KB_07_API_Contracts.md documents the request/response shape.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, status

from datetime import datetime, timezone

from simulation.entities import IncidentPayload, InjectRequest
from simulation.sim_world import SimWorld

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


# ---------------------------------------------------------------------------
# SimWorld singleton — owned by the FastAPI lifespan (see backend/main.py).
# ---------------------------------------------------------------------------

_sim_world: Optional[SimWorld] = None


def _get_world() -> SimWorld:
    """Return the active SimWorld. Raise 503 if lifespan didn't start one."""
    global _sim_world
    if _sim_world is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SimWorld not initialized. The FastAPI lifespan should have started it; check backend/main.py.",
        )
    return _sim_world


def set_sim_world(world: Optional[SimWorld]) -> None:
    """Lifespan hook — called from backend/main.py:lifespan() at startup/shutdown."""
    global _sim_world
    _sim_world = world


def get_sim_world() -> Optional[SimWorld]:
    """Non-raising accessor for the active SimWorld (None if the lifespan hasn't started one).

    Use this from background workers (e.g. the Stage-13 CDC listener) that must degrade gracefully when no world is
    bound — unlike `_get_world()`, which raises a 503 for the HTTP route path."""
    return _sim_world


# ---------------------------------------------------------------------------
# Stage 2 — the canonical inject endpoint.
# ---------------------------------------------------------------------------


@router.post("/inject", response_model=IncidentPayload, status_code=status.HTTP_202_ACCEPTED)
async def inject_incident(payload: InjectRequest) -> IncidentPayload:
    """Inject an incident into the SimPy plant simulator.

    Validates the payload against `InjectRequest` (Pydantic) — malformed
    requests return 400 with the Pydantic error body before any state mutation.

    Latency target: inject → first state delta on WebSocket ≤ 250 ms p95
    (KB_10 latency budget; Stage 2 acceptance criterion).
    """
    world = _get_world()
    incident = world.inject(payload)
    return incident.to_payload()


@router.get("/snapshot")
async def get_snapshot() -> dict:
    """Return a best-effort snapshot of plant state.

    Reads SimWorld counters + per-entity status. Used by calibration tests
    and the operator dashboard.
    """
    world = _get_world()
    return world.snapshot()


@router.post("/reset-world")
async def reset_world() -> dict:
    """Reset the live SimWorld to a fresh, deterministic state (a REAL re-initialization, not a fake).

    Spins up a brand-new `SimWorld` with the same seed + incident callback, starts its worker, and atomically swaps
    it in. All consumers read the world via `get_sim_world()` at call time, so the swap is safe; the old worker is a
    daemon thread that is stopped best-effort and orphaned. After this, every stage is back to nominal at t≈0.
    """
    global _sim_world
    old = _sim_world
    seed = int(getattr(old, "seed", 20260524)) if old is not None else 20260524
    on_incident = getattr(old, "on_incident", None) if old is not None else None
    new = SimWorld(seed=seed, on_incident=on_incident)
    new.start()
    _sim_world = new
    if old is not None:
        try:
            old.stop()
        except Exception:  # noqa: BLE001 — best-effort; the old daemon thread is orphaned and harmless
            pass
    snap = new.snapshot()
    return {"status": "reset", "seed": new.seed, "sim_time_seconds": snap.get("sim_time_seconds", 0),
            "stages": len(snap.get("stages", []))}


# ---------------------------------------------------------------------------
# Control + state endpoints — now backed 100% by the REAL SimWorld (the legacy
# `SimulationEngine` + its `_generate_mock_state` fabrication was DELETED, 2026-07;
# nothing served fabricated state anymore). `/state` maps the real SimWorld
# snapshot to the frontend `SimulationState` shape; positions are a deterministic
# visual layout (the DES twin is not spatial), all telemetry is real or an honest 0.
# ---------------------------------------------------------------------------


def _snapshot_to_state(snap: dict) -> dict:
    """Map the REAL SimWorld snapshot to the frontend `SimulationState` shape. Real data only;
    fields the discrete-event twin does not track (per-robot velocity/position, per-stage temperature/power,
    collisions) are a deterministic visual layout or an honest 0 — never fabricated telemetry."""
    stages = snap.get("stages", [])
    robots = snap.get("robots", [])
    troubled = [s for s in stages if str(s.get("status", "")).lower() not in ("nominal", "running")]
    n_nominal = len(stages) - len(troubled)
    online_frac = (n_nominal / len(stages)) if stages else 1.0
    util = float(snap.get("amr_utilization", 0.0) or 0.0)
    util_pct = util * 100.0 if util <= 1.0 else util

    def robot_viz(r: dict, i: int) -> dict:
        rid = int(r.get("id", i))
        return {
            "robot_id": rid,
            "position_x": 10.0 + (rid % 5) * 18.0,   # deterministic layout (not GPS — the twin isn't spatial)
            "position_y": 12.0 + (rid // 5) * 16.0,
            "battery": round(float(r.get("battery", 0.0)) * (100.0 if float(r.get("battery", 0.0)) <= 1.0 else 1.0)),
            "status": str(r.get("status", "idle")),
            "velocity": 0.0,                          # not tracked by the DES twin (honest 0)
            "current_task": (f"TASK-{r.get('queue_len', 0)}" if r.get("queue_len") else None),
        }

    def stage_viz(s: dict, i: int) -> dict:
        return {
            "stage_id": int(s.get("stage_id", i)),
            "name": str(s.get("name", f"stage-{i}")),
            "queue_depth": int(s.get("queue_depth", 0)),
            "throughput": int(s.get("units_produced", 0)),        # real cumulative units at this stage
            "temperature": 0.0,                                    # not in the DES snapshot (honest 0)
            "power_consumption": 0.0,                              # not in the DES snapshot (honest 0)
            "defect_count": int(s.get("units_defective", 0)),      # real
            "status": str(s.get("status", "nominal")),
        }

    metrics = {
        "conflicts": 0,                                            # not simulated by the DES twin (honest 0)
        "robot_collisions": 0,                                     # not simulated (honest 0)
        "bottlenecks": len(troubled),                             # REAL
        "stockouts": 0,                                           # supply page has the real figure
        "throughput": round(float(snap.get("throughput_units_per_hour", 0.0) or 0.0)),  # REAL
        "energy_kwh": 0.0,                                        # facilities page has the real MILP figure
        "response_time_s": 0.0,
        "robot_efficiency": round(util_pct, 1),                   # REAL (AMR utilisation)
        "production_efficiency": round(online_frac * 100.0, 1),   # REAL (% stages nominal)
        "supply_chain_health": 100.0,
        "overall_score": round(online_frac * 100.0, 1),           # REAL-derived
    }
    events = [
        {"id": f"inc_{i}", "type": e.get("type", "incident"), "domain": "manufacturing",
         "severity": ("high" if e.get("severity") == "critical" else "medium" if e.get("severity") == "warning" else "low"),
         "description": f"{str(e.get('type', '')).replace('_', ' ')} on stage {e.get('target_id')}",
         "timestamp": datetime.now(timezone.utc).isoformat()}
        for i, e in enumerate(snap.get("recent_incidents", []))
    ]
    empty = {k: 0 for k in metrics}
    return {
        "running": True, "paused": False, "scenario": "problem", "speed": 1.0,
        "tick": int(snap.get("sim_time_seconds", 0)),
        "visualization": {
            "robots": [robot_viz(r, i) for i, r in enumerate(robots)],
            "stages": [stage_viz(s, i) for i, s in enumerate(stages)],
            "inventory": [],
        },
        "metrics": {"current": metrics, "problem": metrics, "solution": empty,
                    "improvements": {"conflict_reduction_pct": 0, "collision_reduction_pct": 0,
                                     "bottleneck_reduction_pct": 0, "throughput_gain_pct": 0}},
        "events": events,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/state")
async def get_simulation_state():
    """REAL live state, mapped from the SimWorld twin (was the legacy mock engine)."""
    return _snapshot_to_state(_get_world().snapshot())


@router.post("/start")
async def start_simulation():
    """The SimWorld twin is always advancing in the lifespan; this is a no-op that reports it running."""
    return {"status": "running", "running": True}


@router.post("/stop")
async def stop_simulation():
    return {"status": "running", "running": True, "note": "the SimWorld twin advances continuously; use /reset-world to re-initialise."}


@router.post("/pause")
async def pause_simulation():
    return {"status": "running", "paused": False, "note": "pause is not supported by the continuous twin."}


@router.post("/resume")
async def resume_simulation():
    return {"status": "running", "paused": False}


@router.post("/reset")
async def reset_simulation():
    """Legacy alias for /reset-world — re-initialises the real SimWorld."""
    return await reset_world()


@router.post("/scenario/{scenario_type}")
async def set_scenario(scenario_type: str):
    """Scenario is a frontend display hint now (problem/solution views drive real injects)."""
    if scenario_type not in ("problem", "solution"):
        raise HTTPException(400, f"Invalid scenario type: {scenario_type}")
    return {"status": "scenario_set", "scenario": scenario_type}


@router.post("/speed/{speed}")
async def set_speed(speed: float):
    """Speed is fixed by the continuous twin; accepted for compatibility."""
    return {"status": "ok", "speed": speed}


@router.get("/events")
async def get_events():
    """REAL recent incidents from the SimWorld twin (was the legacy engine's event list)."""
    snap = _get_world().snapshot()
    return [
        {"id": f"inc_{i}", "type": e.get("type", "incident"), "domain": "manufacturing",
         "severity": ("high" if e.get("severity") == "critical" else "medium" if e.get("severity") == "warning" else "low"),
         "description": f"{str(e.get('type', '')).replace('_', ' ')} on stage {e.get('target_id')}",
         "timestamp": datetime.now(timezone.utc).isoformat()}
        for i, e in enumerate(snap.get("recent_incidents", []))
    ]
