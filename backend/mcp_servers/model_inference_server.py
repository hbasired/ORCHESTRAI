"""MCP server: model_inference — predict_demand · predict_failure · classify_defect.

Wraps the REAL Stage-4/5/9 model singletons (`DemandForecaster`, `FailurePredictor`, `DefectClassifier`). Honest:
a model that can't load returns ``{"available": false, "reason": ...}`` (the model's own ModelUnavailableError text),
never a fabricated prediction (Rule 1a).
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_servers._common import ok, run_server, unavailable

# Warm heavy imports on the MAIN thread at server startup. FastMCP runs sync tools in an anyio worker thread;
# importing torch/xgboost/torchvision/PIL there for the FIRST time (in a subprocess) deadlocks on the CPython
# import lock. Importing here makes the models' lazy in-tool imports cached no-ops.
import numpy  # noqa: E402,F401
import torch  # noqa: E402,F401
import torchvision  # noqa: E402,F401
import xgboost  # noqa: E402,F401
from PIL import Image  # noqa: E402,F401

mcp = FastMCP("model_inference")


def _guard(fn):
    """Run `fn`; convert any model's ModelUnavailableError into an honest unavailable result."""
    try:
        return ok(fn())
    except Exception as e:  # noqa: BLE001 - we classify, then re-raise the unexpected
        if type(e).__name__ == "ModelUnavailableError":
            return unavailable(str(e))
        if isinstance(e, (ValueError, KeyError)):
            return unavailable(f"bad input: {e}", input_error=True)
        raise


@mcp.tool()
def predict_demand(history: list[dict], ) -> dict:
    """Forecast next-step demand from recent hourly readings (Stage-5 LSTM, Bike-Sharing proxy).

    `history`: list of hourly dicts with keys cnt, temp, atemp, hum, windspeed, hr, weekday, mnth/month,
    workingday, holiday, weathersit, season (>= the model's window length).
    Returns {available, forecast, window, model} or {available: false, reason}.
    """
    from ml.demand_forecaster import get_demand_forecaster
    return _guard(lambda: get_demand_forecaster().forecast(history))


@mcp.tool()
def predict_failure(air_temp_k: float, process_temp_k: float, rot_speed_rpm: float,
                    torque_nm: float, tool_wear_min: float, type_: str = "M") -> dict:
    """Predict machine-failure probability for one AI4I-unit sample (Stage-4 XGBoost/MLP).

    Returns {available, p_fail, at_risk, threshold, arch, dataset} or {available: false, reason}.
    """
    from ml.failure_predictor import get_failure_predictor
    return _guard(lambda: get_failure_predictor().predict_failure(
        type_=type_, air_temp_k=air_temp_k, process_temp_k=process_temp_k,
        rot_speed_rpm=rot_speed_rpm, torque_nm=torque_nm, tool_wear_min=tool_wear_min))


@mcp.tool()
def classify_defect(image_path: str) -> dict:
    """Classify a surface-defect image (Stage-9 ResNet18 transfer-learned on NEU-CLS).

    `image_path`: a local filesystem path to an image (any size; loaded + resized internally).
    Returns {available, label, label_index, confidence, probabilities} or {available: false, reason}.
    """
    import os

    from ml.defect_classifier import get_defect_classifier

    if not image_path or not os.path.isfile(image_path):
        return unavailable(f"image not found: {image_path!r}", input_error=True)

    def _run() -> dict:
        from PIL import Image
        img = Image.open(image_path)
        return get_defect_classifier().classify(img)

    return _guard(_run)


if __name__ == "__main__":
    run_server(mcp, "model_inference_server")
