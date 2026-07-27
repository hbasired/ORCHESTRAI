"""Stage 10 — real explainability tests (exact TreeSHAP + real counterfactual + honest-empty).

Exactness/counterfactual tests use the real XGBoost failure predictor and skip honestly when absent.
The honest-empty / honest-unavailable tests need no model.
"""
from __future__ import annotations

import asyncio

import pytest

from ml.failure_predictor import ModelUnavailableError


def _explainer_available() -> bool:
    from ml.failure_explainer import get_failure_explainer
    return get_failure_explainer().is_available()


needs_model = pytest.mark.skipif(not _explainer_available(),
                                 reason="XGBoost failure predictor unavailable (honest skip)")

# A worn, overstrained machine — expected at-risk with tool-wear the dominant driver.
WORN = dict(type_="M", air_temp_k=300.0, process_temp_k=312.0, rot_speed_rpm=1380.0,
            torque_nm=60.0, tool_wear_min=215.0)
# A healthy machine — expected not at-risk.
HEALTHY = dict(type_="M", air_temp_k=300.0, process_temp_k=309.0, rot_speed_rpm=1550.0,
               torque_nm=38.0, tool_wear_min=20.0)


# ---- exact TreeSHAP (the core invariant) ------------------------------------

@needs_model
def test_shap_is_exact_sum_equals_margin():
    """The defining TreeSHAP invariant: sum(shap_values) + base_value == model raw margin (exact)."""
    from ml.failure_explainer import get_failure_explainer
    e = get_failure_explainer().explain(**WORN)
    s = sum(a["shap_value"] for a in e["all_attributions"]) + e["base_value_margin"]
    assert abs(s - e["model_margin"]) < 1e-3, f"sum(shap)+base {s} != margin {e['model_margin']}"


@needs_model
def test_shap_top_driver_is_tool_wear_for_worn_machine():
    from ml.failure_explainer import get_failure_explainer
    e = get_failure_explainer().explain(**WORN)
    assert e["at_risk"] is True
    top = e["top_drivers"][0]
    assert top["feature"] == "Tool wear [min]"
    assert top["direction"] == "increases_risk"
    assert top["shap_value"] > 0


@needs_model
def test_shap_attribution_count_matches_features():
    from ml.failure_explainer import get_failure_explainer
    from ml.failure_predictor import get_failure_predictor
    e = get_failure_explainer().explain(**WORN)
    assert len(e["all_attributions"]) == len(get_failure_predictor().feature_names())


# ---- real counterfactual ----------------------------------------------------

@needs_model
def test_counterfactual_not_needed_when_healthy():
    from ml.failure_explainer import get_failure_explainer
    e = get_failure_explainer().explain(**HEALTHY)
    assert e["at_risk"] is False
    assert e["counterfactual"]["needed"] is False


@needs_model
def test_counterfactual_flip_is_scored_by_real_model():
    """If a counterfactual is found, applying it to the real predictor must actually drop p_fail
    below threshold — i.e. it is a genuine model-verified flip, not a narrative."""
    from ml.failure_explainer import get_failure_explainer
    from ml.failure_predictor import get_failure_predictor
    e = get_failure_explainer().explain(**WORN)
    cf = e["counterfactual"]
    assert cf["needed"] is True
    if cf.get("found"):
        mc = cf["minimal_change"]
        kw = {"Tool wear [min]": "tool_wear_min", "Torque [Nm]": "torque_nm",
              "Rotational speed [rpm]": "rot_speed_rpm"}[mc["feature"]]
        trial = dict(WORN); trial[kw] = mc["to"]
        p = get_failure_predictor().predict_failure(**trial)["p_fail"]
        assert p < e["threshold"], f"counterfactual must drop p_fail below {e['threshold']}, got {p}"


# ---- honest unavailability + honest-empty -----------------------------------

def test_explainer_honest_unavailable_when_no_model(tmp_path):
    """A predictor pointed at a missing model dir → explainer raises, never fabricates."""
    from ml.failure_predictor import FailurePredictor
    from ml.failure_explainer import FailureExplainer
    fx = FailureExplainer(predictor=FailurePredictor(models_dir=tmp_path))
    assert fx.is_available() is False
    with pytest.raises(ModelUnavailableError):
        fx.explain(**WORN)


def test_explainability_module_real_shap_via_failure_features():
    """The Explainer delegates to real SHAP when given failure_features."""
    from ml.explainability import get_explainer
    if not _explainer_available():
        pytest.skip("model unavailable")
    ex = get_explainer()
    shap_values = asyncio.new_event_loop().run_until_complete(
        ex.compute_shap({"failure_features": {k: v for k, v in WORN.items() if k != "type_"}}))
    assert len(shap_values) > 0
    assert all("shap_value" in s and "feature_name" in s for s in shap_values)


def test_explainability_module_honest_empty_for_generic():
    from ml.explainability import get_explainer
    ex = get_explainer()
    loop = asyncio.new_event_loop()
    assert loop.run_until_complete(ex.compute_shap({"actions": [{"target_type": "robot"}]})) == []
    assert loop.run_until_complete(ex.compute_attention({})) == []
    assert loop.run_until_complete(ex.generate_counterfactuals({"actions": []})) == []
