"""Stage 17 — the per-action safety contracts (KB_17 §"Safety contract DSL" examples).

Each contract is static + code-defined (the LLM never authors or edits one). Checks read a `world_state` dict whose
keys the runtime/integration layer populates from real telemetry (battery %, path-clear from YOLO+lidar, light-curtain
state, zone speed limits per ISO/TS 15066, machine interlocks, …). `get_contract(name)` / `CONTRACTS` is the registry
the validator + executors look up. ISO clauses are the per-action standards mapping (KB_17 §"Mapping to standards").
"""
from __future__ import annotations

from safety.contract import Invariant, Postcondition, Precondition, SafetyContract

# ISO/TS 15066 power-&-force-limiting: a conservative collaborative speed cap (m/s) when no zone limit is supplied.
_DEFAULT_COLLAB_SPEED_LIMIT_MPS = 0.25


def _within_zone_speed(ws: dict) -> bool:
    limit = ws.get("zone_speed_limit_mps", _DEFAULT_COLLAB_SPEED_LIMIT_MPS)
    speed = ws.get("planned_speed_mps", ws.get("max_speed_mps", 0.0))
    return float(speed) <= float(limit)


# 1. move_amr_to_charging_station — SIL 2
move_amr_to_charging_station = SafetyContract(
    name="move_amr_to_charging_station",
    sil=2,
    iso_clauses=["ISO 10218-2:2025 §5.4.2", "ISO/TS 15066 §5.5.5", "IEC 61508-1 §7.4"],
    preconditions=[
        Precondition(name="battery_sufficient", description="battery > 5% to reach the station",
                     check=lambda ws: float(ws.get("battery_pct", 0)) > 5.0),
        Precondition(name="path_clear", description="YOLO + lidar agree the path is clear",
                     check=lambda ws: bool(ws.get("path_clear_vision")) and bool(ws.get("path_clear_lidar"))),
        Precondition(name="not_zone_restricted", description="AMR is not in a zone-restricted operation",
                     check=lambda ws: not bool(ws.get("zone_restricted", False))),
    ],
    invariants=[Invariant(name="speed_within_zone_limit",
                          description="max speed ≤ ISO/TS 15066 limit for the current zone",
                          check=_within_zone_speed)],
    fail_safe_path="SS1",
)

# 2. start_conveyor_segment — SIL 2
start_conveyor_segment = SafetyContract(
    name="start_conveyor_segment",
    sil=2,
    iso_clauses=["ISO 13849-1:2023 §4 (PL d)", "IEC 62061:2021", "ISO 10218-2:2025 §5.10"],
    preconditions=[
        Precondition(name="light_curtain_intact", description="light curtain unbroken",
                     check=lambda ws: bool(ws.get("light_curtain_intact", False))),
        Precondition(name="no_person_in_vicinity", description="no person detected in the immediate vicinity",
                     check=lambda ws: not bool(ws.get("person_in_vicinity", True))),
    ],
    invariants=[Invariant(name="light_curtain_continuous", description="light curtain stays intact during run",
                          check=lambda ws: bool(ws.get("light_curtain_intact", False)))],
    fail_safe_path="STO",
)

# 3. expedite_supplier_order — SIL 0 (commercial, not safety-critical)
expedite_supplier_order = SafetyContract(
    name="expedite_supplier_order",
    sil=0,
    iso_clauses=[],
    preconditions=[Precondition(name="supplier_reachable", description="advisory: supplier API reachable",
                                check=lambda ws: bool(ws.get("supplier_reachable", True)))],
    fail_safe_path="no_action",
)

# 4. change_machine_state — SIL 2
change_machine_state = SafetyContract(
    name="change_machine_state",
    sil=2,
    iso_clauses=["IEC 61508-2 §7.4", "ISO 13849-1:2023 §4 (PL d)", "ISO 10218-2:2025 §5.7"],
    preconditions=[
        Precondition(name="interlocks_clear", description="all interlocks clear for the transition",
                     check=lambda ws: bool(ws.get("interlocks_clear", False))),
        Precondition(name="valid_transition", description="requested state transition is permitted",
                     check=lambda ws: ws.get("target_state") in (ws.get("allowed_transitions") or [])),
        Precondition(name="no_active_job", description="no job in progress that the change would corrupt",
                     check=lambda ws: not bool(ws.get("job_in_progress", False))),
    ],
    fail_safe_path="STO",
)

# 5. dispatch_amr_to_zone — SIL 2
dispatch_amr_to_zone = SafetyContract(
    name="dispatch_amr_to_zone",
    sil=2,
    iso_clauses=["ISO 10218-2:2025 §5.4", "ISO/TS 15066 §5.5", "IEC 61508-1 §7.4"],
    preconditions=[
        Precondition(name="zone_known", description="target zone exists in the layout",
                     check=lambda ws: bool(ws.get("zone_known", False))),
        Precondition(name="zone_not_full", description="zone is below its AMR capacity",
                     check=lambda ws: int(ws.get("zone_occupancy", 0)) < int(ws.get("zone_capacity", 0))),
        Precondition(name="amr_available", description="the AMR is idle/available to dispatch",
                     check=lambda ws: ws.get("amr_status", "busy") in ("idle", "available")),
    ],
    invariants=[Invariant(name="speed_within_zone_limit", description="max speed ≤ ISO/TS 15066 zone limit",
                          check=_within_zone_speed)],
    fail_safe_path="SS1",
)

CONTRACTS: dict[str, SafetyContract] = {
    c.name: c for c in (move_amr_to_charging_station, start_conveyor_segment, expedite_supplier_order,
                        change_machine_state, dispatch_amr_to_zone)
}


def get_contract(name: str) -> SafetyContract:
    if name not in CONTRACTS:
        raise KeyError(f"unknown safety contract {name!r}; known: {sorted(CONTRACTS)}")
    return CONTRACTS[name]


__all__ = ["CONTRACTS", "get_contract", "move_amr_to_charging_station", "start_conveyor_segment",
           "expedite_supplier_order", "change_machine_state", "dispatch_amr_to_zone"]
