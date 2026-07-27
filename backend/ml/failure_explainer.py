"""Stage 10 — real explainability for the failure predictor (KB_25: explainable, auditable decisions).

Two genuine, dependency-light explanations for *why a machine is at-risk* and *what would make it safe*:

1. **Exact SHAP feature attributions** via XGBoost's native TreeSHAP (`pred_contribs`) — no `shap` library
   needed; the per-feature Shapley values are exact for the tree model and sum to the model's raw margin.
2. **A real counterfactual** — a guided minimal-change search over the ACTUAL model: how far must the
   actionable degradation features (tool wear, torque, rotational speed) move for the predictor to flip the
   machine from at-risk to not-at-risk. Real model queries, not a fabricated narrative.

Honest by design (mirrors `failure_predictor`/`world_model`): raises `ModelUnavailableError` when the brain/lib
is absent — NEVER fabricates an explanation. Proxy/sim caveat carries over from the predictor (G-035).
"""
from __future__ import annotations

from typing import Optional

from ml.failure_predictor import FailurePredictor, ModelUnavailableError, get_failure_predictor

# Features the counterfactual is allowed to move, and the safe direction (maintenance/relief reduces risk).
# tool wear ↓ (maintenance resets it), torque ↓ (lighter load), rotational speed ↑ (restore nominal).
_ACTIONABLE = {
    "Tool wear [min]": ("down", 0.0),
    "Torque [Nm]": ("down", 0.0),
    "Rotational speed [rpm]": ("up", None),
}


class FailureExplainer:
    """Exact-SHAP + counterfactual explanations for the XGBoost failure predictor."""

    def __init__(self, predictor: Optional[FailurePredictor] = None) -> None:
        self._predictor = predictor or get_failure_predictor()

    def is_available(self) -> bool:
        try:
            self._predictor._load()
            return self._predictor._kind == "xgb"
        except ModelUnavailableError:
            return False

    def explain(self, *, type_: str = "M", air_temp_k: float, process_temp_k: float,
                rot_speed_rpm: float, torque_nm: float, tool_wear_min: float,
                top_k: int = 5, counterfactual: bool = True, diverse_cf: bool = False) -> dict:
        """Return an exact-SHAP + counterfactual explanation for one machine sample.

        Raises ``ModelUnavailableError`` if the XGBoost brain/lib is absent (never fabricates).
        """
        kwargs = dict(type_=type_, air_temp_k=air_temp_k, process_temp_k=process_temp_k,
                      rot_speed_rpm=rot_speed_rpm, torque_nm=torque_nm, tool_wear_min=tool_wear_min)
        pred = self._predictor.predict_failure(**kwargs)
        names = self._predictor.feature_names()
        vec = self._predictor.raw_vector(**kwargs)
        contribs = self._predictor.shap_contribs(vec)          # len = n_features + 1 (bias)
        base = contribs[-1]
        feat_contribs = contribs[:-1]
        model_margin = float(sum(contribs))                     # == booster output_margin (TreeSHAP invariant)

        attributions = []
        for name, value, shap_v in zip(names, vec, feat_contribs):
            attributions.append({
                "feature": name,
                "value": round(float(value), 4),
                "shap_value": round(float(shap_v), 4),       # margin-space Shapley value (exact)
                "direction": "increases_risk" if shap_v > 0 else "decreases_risk",
            })
        ranked = sorted(attributions, key=lambda a: -abs(a["shap_value"]))

        out = {
            "p_fail": round(pred["p_fail"], 4),
            "at_risk": pred["at_risk"],
            "threshold": pred["threshold"],
            "base_value_margin": round(float(base), 4),
            "model_margin": round(model_margin, 4),
            "method": ("exact TreeSHAP (XGBoost native pred_contribs); the invariant "
                       "sum(shap_values)+base_value == model raw margin holds exactly. p_fail is the "
                       "predictor's calibrated probability (XGBoost applies a base_score offset, so "
                       "sigmoid(margin) approximates p_fail within ~0.02)."),
            "top_drivers": ranked[:top_k],
            "all_attributions": ranked,
        }
        if counterfactual:
            out["counterfactual"] = self._counterfactual(kwargs, pred)
        if diverse_cf:
            out["diverse_counterfactual"] = self._diverse_counterfactual(kwargs)
        return out

    def _diverse_counterfactual(self, kwargs: dict) -> dict:
        """DiCE diverse multi-feature counterfactuals (Stage 10 depth) — honest-unavailable if dice-ml absent."""
        try:
            from ml.dice_explainer import get_dice_explainer
            dx = get_dice_explainer()
            if not dx.is_available():
                return {"available": False, "note": "dice-ml not installed or non-XGBoost brain; "
                        "single-feature counterfactual above still applies"}
            return dx.diverse_counterfactuals(
                air_temp_k=kwargs["air_temp_k"], process_temp_k=kwargs["process_temp_k"],
                rot_speed_rpm=kwargs["rot_speed_rpm"], torque_nm=kwargs["torque_nm"],
                tool_wear_min=kwargs["tool_wear_min"])
        except Exception as e:  # never fabricate
            return {"available": False, "note": f"diverse counterfactual unavailable: {e}"}

    def global_importance(self, n: int = 400) -> dict:
        """Global SHAP feature importance over a reference sample (Stage 10 depth). Honest-unavailable."""
        from ml.dice_explainer import get_dice_explainer
        return get_dice_explainer().global_importance(n=n)

    def _counterfactual(self, kwargs: dict, pred: dict) -> dict:
        """Guided minimal-change search over actionable features to flip at_risk -> not-at-risk.

        Honest: every candidate is scored by the REAL model. If no change within the search bounds
        flips the verdict, that is reported (no fabricated "fix").
        """
        if not pred["at_risk"]:
            return {"needed": False, "note": "machine not at-risk; no counterfactual required"}

        threshold = pred["threshold"]
        # Map raw-vector feature names to predict_failure kwarg names for the actionable ones.
        kwarg_for = {"Tool wear [min]": "tool_wear_min", "Torque [Nm]": "torque_nm",
                     "Rotational speed [rpm]": "rot_speed_rpm"}
        changes = []
        # Try each actionable feature independently (single-feature minimal change), 40 steps to 0 / +50%.
        for feat, (direction, _floor) in _ACTIONABLE.items():
            kw = kwarg_for[feat]
            start = float(kwargs[kw])
            for step in range(1, 41):
                frac = step / 40.0
                if direction == "down":
                    cand = start * (1.0 - frac)            # toward 0
                else:
                    cand = start * (1.0 + 0.5 * frac)       # up to +50%
                trial = dict(kwargs); trial[kw] = cand
                p = self._predictor.predict_failure(**trial)["p_fail"]
                if p < threshold:
                    changes.append({
                        "feature": feat, "from": round(start, 2), "to": round(cand, 2),
                        "direction": direction, "p_fail_after": round(p, 4),
                        "rel_change_pct": round(100.0 * (cand - start) / (start or 1.0), 1),
                    })
                    break
        if not changes:
            return {"needed": True, "found": False,
                    "note": "no single actionable feature flipped the verdict within search bounds "
                            "(0..-100% wear/torque, 0..+50% rpm) — likely needs combined action / maintenance"}
        # Smallest relative change wins (the least-effort counterfactual).
        best = min(changes, key=lambda c: abs(c["rel_change_pct"]))
        return {"needed": True, "found": True, "minimal_change": best, "alternatives": changes,
                "note": "real counterfactual: each candidate scored by the actual predictor"}


_default: Optional[FailureExplainer] = None


def get_failure_explainer() -> FailureExplainer:
    global _default
    if _default is None:
        _default = FailureExplainer()
    return _default


__all__ = ["FailureExplainer", "get_failure_explainer", "ModelUnavailableError"]
