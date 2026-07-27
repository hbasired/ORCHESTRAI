"""Shared helpers for the Stage 11.5 MCP servers.

- `unavailable()` — the canonical honest-unavailable tool result (no fabrication, Rule 1a).
- `run_server()` — uniform entrypoint: stdio by default, streamable-HTTP when MCP_TRANSPORT=http.
- `get_local_sim()` — a lazily-built, deterministic `SimWorld` for the sim_world / kpi servers (a REAL SimPy
  engine, seeded fixed; each server process owns its own instance — cross-process world sharing with the live app
  is a later integration concern, documented in the ADR).
"""
from __future__ import annotations

import os
import threading
from typing import Any


def unavailable(reason: str, **extra: Any) -> dict[str, Any]:
    """Honest 'model/resource not available' result — the truth, never a fake number."""
    return {"available": False, "reason": reason, **extra}


def ok(payload: dict[str, Any]) -> dict[str, Any]:
    """Mark a successful tool result available (keeps a uniform shape for callers/tests)."""
    return {"available": True, **payload}


# ---- deterministic SimWorld, advanced SYNCHRONOUSLY (sim_world_server + kpi_query_server) ----
#
# We DELIBERATELY do not use SimWorld.start() (its background SimPy worker thread + the realtime-pacing
# `time.sleep` deadlocks inside an MCP stdio server's tool worker-thread). Instead we drive `env.run(until=...)`
# synchronously in the calling thread — deterministic, fast (event-driven), and stdio-safe. Fixed seed →
# reproducible snapshots.

_sim_lock = threading.Lock()
_sim: Any = None
# How much sim-time (seconds) to warm the world to on first use so queries return a non-trivial plant state.
DEFAULT_WARM_SIM_SECONDS = float(os.environ.get("MCP_SIM_WARM_SECONDS", "1800"))


def _advance(sim: Any, to_sim_seconds: float) -> None:
    import simpy
    if sim.env.now >= to_sim_seconds:
        return
    try:
        sim.env.run(until=to_sim_seconds)
    except simpy.core.EmptySchedule:
        pass


def get_local_sim(min_sim_seconds: float = DEFAULT_WARM_SIM_SECONDS) -> Any:
    """Return this process's deterministic SimWorld, built once + advanced synchronously to >= min_sim_seconds.

    A real SimPy simulation (not a mock). Raises nothing it can't honestly raise — if SimPy/the sim package is
    unavailable the caller turns the ImportError into an `unavailable(...)` result.
    """
    global _sim
    with _sim_lock:
        if _sim is None:
            from simulation.sim_world import SimWorld
            seed = int(os.environ.get("MCP_SIM_SEED", "20260524"))
            _sim = SimWorld(seed=seed)
        _advance(_sim, float(min_sim_seconds))
        return _sim


def apply_inject(sim: Any, req: Any, advance_seconds: float = 120.0) -> Any:
    """Inject an incident + apply it SYNCHRONOUSLY (no worker thread), then advance the world so effects land."""
    import queue as _q
    inc = sim.inject(req)            # creates the Incident + enqueues it
    try:                             # drain the queue ourselves (the worker thread isn't running)
        while True:
            sim._handle_inject(sim._inject_queue.get_nowait())
    except _q.Empty:
        pass
    _advance(sim, sim.env.now + max(0.0, advance_seconds))
    return inc


def run_server(mcp: Any, name: str) -> None:
    """Uniform run entrypoint. stdio (default) | streamable-http (MCP_TRANSPORT=http, MCP_PORT=<port>)."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        # Port/host are read by FastMCP from its settings; set them before run.
        port = int(os.environ.get("MCP_PORT", "0")) or _default_port(name)
        mcp.settings.host = os.environ.get("MCP_HOST", "127.0.0.1")
        mcp.settings.port = port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()  # stdio


def _default_port(name: str) -> int:
    from mcp_servers import SERVER_REGISTRY
    return SERVER_REGISTRY.get(name, (None, 9100))[1]


__all__ = ["unavailable", "ok", "get_local_sim", "run_server"]
