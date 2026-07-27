"""Stage 14 — A2A-exposed capabilities (the DELIBERATE subset external peers may call; KB_16 §"use cases").

Each skill has a Pydantic-validated input + a handler. The `SKILLS` registry is what `server.py`'s JSON-RPC dispatch
exposes — and it is NOT the MCP tool surface (KB_16 trust asymmetry: external peers get capabilities, not tools).
"""
from __future__ import annotations

from typing import Any, Callable

from a2a.skills.forecast_oee import forecast_oee

# capability name -> handler(params: dict) -> dict
SKILLS: dict[str, Callable[[dict], dict]] = {
    "forecast_oee": forecast_oee,
}

# The capability list advertised in the agent card.
CAPABILITIES: list[str] = sorted(SKILLS.keys())

__all__ = ["SKILLS", "CAPABILITIES"]
