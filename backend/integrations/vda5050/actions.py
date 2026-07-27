"""Stage 16 — map an intervention decision + fleet context to VDA 5050-shaped routing (KB_25 → fleet actuation).

When an intervention implies moving material/an AGV (fleet routing), an agent decision is expressed as a VDA 5050
**order graph** (the standard's routing primitive: nodes with actions, edges between them). `recommend_fleet_order`
returns the `nodes`/`edges` (schema-valid) that `Vda5050Master.build_order` turns into a dispatchable order — the
master still verifies connection freshness + the safety gate before it goes out (KB_17). This is the
`policy_query.recommend_action` → VDA-5050 bridge (Stage-16 AC).
"""
from __future__ import annotations

import uuid
from typing import Any

# VDA 5050 blockingType enum
NONE, SOFT, HARD = "NONE", "SOFT", "HARD"


def _action(action_type: str, description: str, blocking: str = SOFT,
            params: dict[str, Any] | None = None) -> dict:
    """A VDA 5050 `Action` object (actionType/actionId/blockingType required)."""
    a: dict[str, Any] = {"actionType": action_type, "actionId": f"act-{uuid.uuid4().hex[:8]}",
                         "actionDescription": description, "blockingType": blocking}
    if params:
        a["actionParameters"] = [{"key": k, "value": v} for k, v in params.items()]
    return a


def recommend_fleet_order(decision: dict, fleet: dict) -> dict:
    """Build VDA 5050 node/edge routing (pickup → dropoff) from an intervention decision + fleet context.

    `fleet`: {manufacturer, serial_number, pickup_node?, dropoff_node?}. Returns {nodes, edges, action_type,
    manufacturer, serial_number} — feed nodes/edges to `Vda5050Master.build_order`. The two node actions (pick/drop)
    carry the decision rationale + stage so the AGV + the audit trail record WHY the move was ordered.
    """
    pickup = str(fleet.get("pickup_node", "P1"))
    dropoff = str(fleet.get("dropoff_node", "D1"))
    rationale = decision.get("rationale", "")
    stage_id = decision.get("stage_id")
    nodes = [
        {"nodeId": pickup, "sequenceId": 0, "released": True,
         "actions": [_action("pick", f"pick at {pickup}", HARD,
                             {"reason": decision.get("kind", "transport"), "stage_id": stage_id})]},
        {"nodeId": dropoff, "sequenceId": 2, "released": True,
         "actions": [_action("drop", f"drop at {dropoff} ({rationale})"[:200], HARD,
                             {"stage_id": stage_id})]},
    ]
    edges = [{"edgeId": f"{pickup}-{dropoff}", "sequenceId": 1, "released": True,
              "startNodeId": pickup, "endNodeId": dropoff, "actions": []}]
    return {"nodes": nodes, "edges": edges, "action_type": "transport",
            "manufacturer": fleet.get("manufacturer"), "serial_number": fleet.get("serial_number")}


__all__ = ["recommend_fleet_order", "NONE", "SOFT", "HARD"]
