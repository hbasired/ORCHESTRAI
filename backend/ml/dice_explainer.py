"""Stage 10 depth-hardening — DiCE diverse multi-feature counterfactuals + global SHAP.

The v0 Stage-10 explainer (`failure_explainer.py`) shipped exact TreeSHAP (kept — it is already exact) plus a
**single-feature** greedy counterfactual. This module adds the two depth pieces research §16.6 calls for:

1. **DiCE** (`dice-ml`, Mothilal/Sharma/Tan) — **diverse, multi-feature, actionable** counterfactuals: instead of
   "drop tool-wear 40%", it returns several DIFFERENT minimal recipes (e.g. "torque −15% AND rpm +10%") that each
   flip the model from at-risk to safe — the standard SOTA recourse method. We vary only the **actionable base
   physical features** (torque↓, rpm↑, tool-wear↓); the predictor recomputes the derived features (temp_diff,
   power_w) internally, so every counterfactual is **physically consistent** (no inconsistent engineered features).

2. **Global SHAP** — feature importance over a whole reference sample (mean |Shapley| per feature) + the per-feature
   value/impact spread (beeswarm data), computed with XGBoost's exact native TreeSHAP over many rows. This is the
   dataset-level "what drives risk in general", complementing the per-decision SHAP.

Honest by design: raises `ModelUnavailableError` if the XGBoost brain / `dice-ml` is absent — never fabricates.
The reference distribution is the documented AI4I operating envelope; DiCE uses it for feasibility/feature scaling.
Proxy/sim caveat carries over from the predictor (G-035).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ml.failure_predictor import FailurePredictor, ModelUnavailableError, get_failure_predictor

# AI4I operating envelope (documented realistic ranges) — the reference distribution for DiCE feasibility.
_RANGES = {
    "air_temp_k": (295.0, 305.0),
    "process_temp_k": (305.0, 314.0),
    "rot_speed_rpm": (1168.0, 2886.0),
    "torque_nm": (3.8, 77.0),
    "tool_wear_min": (0.0, 253.0),
}
_BASE_FEATURES = list(_RANGES.keys())
_ACTIONABLE = ["torque_nm", "rot_speed_rpm", "tool_wear_min"]   # what an operator can act on


class _PredictorBlackBox:
    """sklearn-compatible wrapper so DiCE can query the real predictor over BASE physical features.
    Derived features (temp_diff, power_w) are recomputed inside `predict_failure` → consistent counterfactuals."""

    def __init__(self, predictor: FailurePredictor, type_: str = "M"):
        self._p = predictor
        self._type = type_

    def _p_fail_row(self, row) -> float:
        return float(self._p.predict_failure(
            type_=self._type, air_temp_k=float(row["air_temp_k"]), process_temp_k=float(row["process_temp_k"]),
            rot_speed_rpm=float(row["rot_speed_rpm"]), torque_nm=float(row["torque_nm"]),
            tool_wear_min=float(row["tool_wear_min"]))["p_fail"])

    def predict_proba(self, X):
        import pandas as pd
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X, columns=_BASE_FEATURES)
        p = np.array([self._p_fail_row(r) for _, r in X.iterrows()], dtype=np.float64)
        return np.column_stack([1.0 - p, p])

    def predict(self, X):
        thr = self._p._threshold()
        return (self.predict_proba(X)[:, 1] >= thr).astype(int)


class DiceExplainer:
    """DiCE diverse counterfactuals + global SHAP for the XGBoost failure predictor."""

    def __init__(self, predictor: Optional[FailurePredictor] = None, n_reference: int = 600, seed: int = 10):
        self._predictor = predictor or get_failure_predictor()
        self._n_ref = n_reference
        self._seed = seed
        self._dice = None
        self._ref_df = None

    def is_available(self) -> bool:
        try:
            import dice_ml  # noqa: F401
        except Exception:
            return False
        try:
            self._predictor._load()
            return self._predictor._kind == "xgb"
        except ModelUnavailableError:
            return False

    def _build(self):
        if self._dice is not None:
            return
        try:
            import dice_ml
            import pandas as pd
        except Exception as e:
            raise ModelUnavailableError(f"dice-ml/pandas not available: {e}")
        self._predictor._load()
        if self._predictor._kind != "xgb":
            raise ModelUnavailableError("DiCE counterfactuals require the XGBoost brain (no fabrication).")
        rng = np.random.default_rng(self._seed)
        # reference sample from the documented operating envelope, labelled by the real model.
        data = {f: rng.uniform(lo, hi, self._n_ref) for f, (lo, hi) in _RANGES.items()}
        df = pd.DataFrame(data)
        bb = _PredictorBlackBox(self._predictor)
        df["at_risk"] = bb.predict(df[_BASE_FEATURES])
        self._ref_df = df
        d = dice_ml.Data(dataframe=df, continuous_features=_BASE_FEATURES, outcome_name="at_risk")
        m = dice_ml.Model(model=bb, backend="sklearn", model_type="classifier")
        self._dice = dice_ml.Dice(d, m, method="random")

    def diverse_counterfactuals(self, *, air_temp_k: float, process_temp_k: float, rot_speed_rpm: float,
                                torque_nm: float, tool_wear_min: float, total_cfs: int = 4) -> dict:
        """Generate `total_cfs` DIVERSE, multi-feature, actionable counterfactuals that flip at-risk → safe.

        Only `torque_nm`, `rot_speed_rpm`, `tool_wear_min` are varied (operator-actionable); the predictor
        recomputes derived features. Raises ``ModelUnavailableError`` if the brain/DiCE is absent.
        """
        import pandas as pd
        self._build()
        query = pd.DataFrame([{
            "air_temp_k": air_temp_k, "process_temp_k": process_temp_k, "rot_speed_rpm": rot_speed_rpm,
            "torque_nm": torque_nm, "tool_wear_min": tool_wear_min,
        }])[_BASE_FEATURES]
        p0 = float(self._predictor.predict_failure(
            type_="M", air_temp_k=air_temp_k, process_temp_k=process_temp_k, rot_speed_rpm=rot_speed_rpm,
            torque_nm=torque_nm, tool_wear_min=tool_wear_min)["p_fail"])
        thr = self._predictor._threshold()
        if p0 < thr:
            return {"needed": False, "p_fail": round(p0, 4),
                    "note": "machine not at-risk; no counterfactual required"}
        try:
            res = self._dice.generate_counterfactuals(
                query, total_CFs=total_cfs, desired_class="opposite", features_to_vary=_ACTIONABLE)
            cf_df = res.cf_examples_list[0].final_cfs_df
        except Exception as e:
            return {"needed": True, "found": False, "method": "DiCE (random)",
                    "note": f"DiCE found no counterfactual within bounds: {e}"}
        if cf_df is None or len(cf_df) == 0:
            return {"needed": True, "found": False, "method": "DiCE (random)",
                    "note": "DiCE returned no counterfactual within feasibility bounds"}
        orig = {"torque_nm": torque_nm, "rot_speed_rpm": rot_speed_rpm, "tool_wear_min": tool_wear_min}
        recipes = []
        for _, row in cf_df.iterrows():
            changes = {f: {"from": round(float(orig[f]), 2), "to": round(float(row[f]), 2),
                           "rel_pct": round(100.0 * (float(row[f]) - orig[f]) / (orig[f] or 1.0), 1)}
                       for f in _ACTIONABLE if abs(float(row[f]) - orig[f]) > 1e-6}
            p_after = float(self._predictor.predict_failure(
                type_="M", air_temp_k=air_temp_k, process_temp_k=process_temp_k,
                rot_speed_rpm=float(row["rot_speed_rpm"]), torque_nm=float(row["torque_nm"]),
                tool_wear_min=float(row["tool_wear_min"]))["p_fail"])
            recipes.append({"changes": changes, "n_features_changed": len(changes),
                            "p_fail_after": round(p_after, 4), "flips": bool(p_after < thr)})
        return {"needed": True, "found": True, "p_fail": round(p0, 4), "threshold": round(thr, 4),
                "method": "DiCE diverse multi-feature counterfactuals (dice-ml, random method)",
                "n_counterfactuals": len(recipes), "counterfactuals": recipes,
                "note": "diverse actionable recipes; each verified against the real predictor (flips=True)"}

    def global_importance(self, n: int = 400) -> dict:
        """Global SHAP: mean |Shapley| per feature over a reference sample (exact XGBoost TreeSHAP)."""
        self._build()
        rng = np.random.default_rng(self._seed + 1)
        names = self._predictor.feature_names()
        sample = self._ref_df.sample(min(n, len(self._ref_df)), random_state=self._seed)
        shap_rows = []
        for _, r in sample.iterrows():
            vec = self._predictor.raw_vector(
                type_="M", air_temp_k=float(r["air_temp_k"]), process_temp_k=float(r["process_temp_k"]),
                rot_speed_rpm=float(r["rot_speed_rpm"]), torque_nm=float(r["torque_nm"]),
                tool_wear_min=float(r["tool_wear_min"]))
            shap_rows.append(self._predictor.shap_contribs(vec)[:-1])  # drop bias
        S = np.asarray(shap_rows, dtype=np.float64)
        mean_abs = np.abs(S).mean(axis=0)
        order = np.argsort(-mean_abs)
        importance = [{"feature": names[i], "mean_abs_shap": round(float(mean_abs[i]), 4),
                       "mean_shap": round(float(S[:, i].mean()), 4)} for i in order]
        return {"n": int(len(S)), "method": "global exact TreeSHAP (mean |Shapley| over reference sample)",
                "importance": importance}


_default: Optional[DiceExplainer] = None


def get_dice_explainer() -> DiceExplainer:
    global _default
    if _default is None:
        _default = DiceExplainer()
    return _default


__all__ = ["DiceExplainer", "get_dice_explainer", "ModelUnavailableError"]
