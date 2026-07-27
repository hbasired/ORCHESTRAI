#!/usr/bin/env python3
"""Stage 17 — CI gate: every `actuator.*` span MUST be preceded by a `safety.validate.*` span (KB_17).

The functional-safety invariant in trace form: no actuator command may fire without first passing the validator. This
parses an OpenTelemetry span dump (JSON: a list of {name, start_time} or {"spans": [...]}), and fails (exit 1) if any
`actuator.*` span has no `safety.validate*` span starting before it.

Usage: python scripts/check-safety-trace-pairing.py [audits/STAGE_17_traces.json]
Tests import `check_pairing(spans)` directly (it returns the list of violating actuator span names).
"""
from __future__ import annotations

import json
import sys
from typing import Any

ACTUATOR_PREFIX = "actuator."
VALIDATE_PREFIX = "safety.validate"


def check_pairing(spans: list[dict[str, Any]]) -> list[str]:
    """Return the names of `actuator.*` spans that are NOT preceded by any `safety.validate*` span. Empty = OK."""
    ordered = sorted(spans, key=lambda s: s.get("start_time", 0) or 0)
    validate_starts = [s.get("start_time", 0) or 0 for s in ordered
                       if str(s.get("name", "")).startswith(VALIDATE_PREFIX)]
    violations: list[str] = []
    for s in ordered:
        name = str(s.get("name", ""))
        if name.startswith(ACTUATOR_PREFIX):
            t = s.get("start_time", 0) or 0
            if not any(vt <= t for vt in validate_starts):
                violations.append(name)
    return violations


def _load(path: str) -> list[dict[str, Any]]:
    data = json.load(open(path, encoding="utf-8"))
    return data.get("spans", []) if isinstance(data, dict) else data


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else "audits/STAGE_17_traces.json"
    try:
        spans = _load(path)
    except FileNotFoundError:
        print(f"REFUSE: trace file not found: {path}")
        return 2
    violations = check_pairing(spans)
    n_act = sum(1 for s in spans if str(s.get("name", "")).startswith(ACTUATOR_PREFIX))
    if violations:
        print(f"FAIL: {len(violations)} actuator span(s) without a preceding safety.validate: {violations}")
        return 1
    print(f"OK: all {n_act} actuator span(s) preceded by safety.validate ({len(spans)} spans checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
