"""Stage 12 — Letta (MemGPT) opt-in long-horizon episodic memory (KB_14).

Letta is the opt-in, per-pilot episodic backend for customers who need shift-persistent agent identity across days.
It is **feature-flagged OFF by default** (`LETTA_ENABLED` unset/false) and the `letta` package is not a default
dependency. This adapter is honest about its state: when disabled or uninstalled, `is_enabled()` returns False and
the memory layer uses Mem0 (the default episodic backend) — it NEVER silently pretends Letta is active.
"""
from __future__ import annotations

import os
from typing import Any, Optional


def is_enabled() -> bool:
    """True only when explicitly enabled AND the letta package is importable. Honest, no pretence."""
    if os.environ.get("LETTA_ENABLED", "").lower() not in ("1", "true", "yes"):
        return False
    try:
        import letta  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def status() -> dict[str, Any]:
    enabled = os.environ.get("LETTA_ENABLED", "").lower() in ("1", "true", "yes")
    try:
        import letta  # noqa: F401
        installed = True
    except Exception:  # noqa: BLE001
        installed = False
    return {"enabled_flag": enabled, "package_installed": installed, "active": enabled and installed,
            "default_backend": "mem0 (Letta is opt-in, per-pilot)"}


class LettaAdapter:
    """Thin wrapper around a Letta client. Constructed only when `is_enabled()` — else raises, by design."""

    def __init__(self) -> None:
        if not is_enabled():
            raise RuntimeError(
                "LettaAdapter requested but Letta is not active "
                f"(status={status()}). Set LETTA_ENABLED=1 and install `letta` to use it; "
                "otherwise the default episodic backend is Mem0 (memory/mem0_adapter.py).")
        from letta import LocalClient  # type: ignore  # imported only when active
        self._client = LocalClient()

    def client(self) -> Any:
        return self._client


__all__ = ["is_enabled", "status", "LettaAdapter"]
