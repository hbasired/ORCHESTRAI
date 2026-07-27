"""MCP server: policy_query — recommend_action · explain_action.

`recommend_action(telemetry)` runs the REAL pipeline: failure prediction (Stage 4) -> learned-causal diagnosis
(Stage 8) -> intervention policy (Stage 7) and returns the recommended action. `explain_action(telemetry)` returns
the Stage-10 exact-SHAP top drivers + counterfactual for that sample. Honest-unavailable when a model can't load
(never a fabricated recommendation/explanation; Rule 1a).
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_servers._common import ok, run_server, unavailable

# Warm heavy imports on the MAIN thread at startup (see the other servers — avoids a worker-thread import-lock
# deadlock when a tool first imports xgboost/the ml+services modules in the stdio subprocess).
import numpy  # noqa: E402,F401
import xgboost  # noqa: E402,F401
import ml.failure_explainer  # noqa: E402,F401
import ml.failure_predictor  # noqa: E402,F401
import services.diagnosis  # noqa: E402,F401
import services.intervention_policy  # noqa: E402,F401

mcp = FastMCP("policy_query")

# Telemetry keys the AI4I-unit models consume.
_FEATURE_KEYS = ("air_temp_k", "process_temp_k", "rot_speed_rpm", "torque_nm", "tool_wear_min")


def _features(telemetry: dict) -> dict:
    missing = [k for k in _FEATURE_KEYS if k not in telemetry]
    if missing:
        raise KeyError(f"telemetry missing required keys: {missing}")
    return {k: float(telemetry[k]) for k in _FEATURE_KEYS} | {"type_": telemetry.get("type_", "M")}


@mcp.tool()
def recommend_action(telemetry: dict) -> dict:
    """Recommend an intervention for one machine sample.

    `telemetry`: must include {stage_id, air_temp_k, process_temp_k, rot_speed_rpm, torque_nm, tool_wear_min};
    optional {type_, queue_depth, capacity, recent_incidents}.
    Returns {available, stage_id, kind, rationale, diagnosis} or {available: false, reason}.
    """
    try:
        from ml.failure_predictor import get_failure_predictor
        from services.diagnosis import diagnose
        from services.intervention_policy import decide_intervention

        feats = _features(telemetry)
        if "stage_id" not in telemetry:
            return unavailable("telemetry missing 'stage_id'", input_error=True)
        prediction = get_failure_predictor().predict_failure(**feats)
        tele = dict(telemetry)
        tele.setdefault("stage_id", int(telemetry["stage_id"]))
        diag = diagnose(prediction, tele, recent_incidents=telemetry.get("recent_incidents", []))
        decision = decide_intervention(
            diag, queue_depth=telemetry.get("queue_depth"), capacity=telemetry.get("capacity"))
        result = decision.to_dict()
        # Stage 16: when fleet routing is appropriate (telemetry carries a `fleet` block: manufacturer/serial[/nodes]),
        # also return VDA 5050-shaped routing the master can dispatch (after its freshness + safety gates).
        fleet = telemetry.get("fleet")
        if isinstance(fleet, dict) and fleet.get("manufacturer") and fleet.get("serial_number"):
            from integrations.vda5050.actions import recommend_fleet_order
            result["vda5050_routing"] = recommend_fleet_order(result, fleet)
        return ok(result)
    except Exception as e:  # noqa: BLE001
        if type(e).__name__ == "ModelUnavailableError":
            return unavailable(str(e))
        if isinstance(e, (ValueError, KeyError)):
            return unavailable(f"bad input: {e}", input_error=True)
        raise


@mcp.tool()
def explain_action(telemetry: dict, top_k: int = 3) -> dict:
    """Explain the failure prediction driving the recommended action (Stage-10 exact TreeSHAP + counterfactual).

    `telemetry`: same feature keys as `recommend_action`.
    Returns {available, top_drivers, counterfactual, method} or {available: false, reason}.
    """
    try:
        from ml.failure_explainer import get_failure_explainer

        feats = _features(telemetry)
        ex = get_failure_explainer()
        if not ex.is_available():
            return unavailable("failure explainer unavailable (no XGBoost brain)")
        out = ex.explain(top_k=int(top_k), **feats)
        return ok({"top_drivers": out["top_drivers"], "counterfactual": out.get("counterfactual"),
                   "method": out.get("method")})
    except Exception as e:  # noqa: BLE001
        if type(e).__name__ == "ModelUnavailableError":
            return unavailable(str(e))
        if isinstance(e, (ValueError, KeyError)):
            return unavailable(f"bad input: {e}", input_error=True)
        raise


if __name__ == "__main__":
    run_server(mcp, "policy_query_server")
