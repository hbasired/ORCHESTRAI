"""
Explainability (Stage 10) — honest SHAP + counterfactual + natural-language.

De-mocked 2026-06-13: the previous module fabricated SHAP importances, attention weights, counterfactuals and
heatmap scatter with fabricated RNG values. All fabrication is removed. Now:

- When a decision carries **failure-prediction features** (`decision["failure_features"]` = the telemetry kwargs
  the predictor consumes), `compute_shap` / `generate_counterfactuals` delegate to the REAL
  `ml.failure_explainer` (exact XGBoost TreeSHAP + a real counterfactual search over the actual model).
- Otherwise (generic decisions with no model wired behind them — the off-slice decision-engine pipeline) the
  methods return **honest empty** results: no fabricated numbers. `generate_natural_language` builds text only
  from whatever real fields are present.

This is the project's "explainable, auditable decisions" capability (KB_25): for the self-healing spine the
explanation is exact and real; for unmodelled generic decisions it is honestly empty rather than theatrical.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(__name__)


class Explainer:
    """Decision explainer. Real SHAP/counterfactual for failure predictions; honest-empty otherwise."""

    def __init__(self) -> None:
        self.is_initialized = False

    async def initialize(self) -> None:
        self.is_initialized = True
        logger.info("Explainer initialized (honest: real SHAP for failure features, empty otherwise)")

    # ---- helpers -----------------------------------------------------------

    @staticmethod
    def _failure_features(decision: dict) -> dict | None:
        """Extract the telemetry kwargs for the failure predictor, if the decision carries them."""
        f = decision.get("failure_features") if isinstance(decision, dict) else None
        if not f:
            return None
        required = {"air_temp_k", "process_temp_k", "rot_speed_rpm", "torque_nm", "tool_wear_min"}
        return f if required <= set(f) else None

    # ---- SHAP --------------------------------------------------------------

    async def compute_shap(self, decision: dict, num_features: int = 10) -> list[dict]:
        """Exact SHAP feature importance for a FAILURE-prediction decision (via `failure_explainer`).

        Returns `[]` honestly for generic decisions with no model behind them — never fabricates.
        """
        feats = self._failure_features(decision)
        if feats is None:
            return []
        try:
            from ml.failure_explainer import get_failure_explainer, ModelUnavailableError
            try:
                exp = get_failure_explainer().explain(counterfactual=False, top_k=num_features, **feats)
            except ModelUnavailableError as e:
                logger.warning("compute_shap: model unavailable, returning empty (no fabrication)", error=str(e))
                return []
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("compute_shap failed, returning empty (no fabrication)", error=str(e))
            return []
        return [
            {
                "feature_name": a["feature"],
                "feature_value": a["value"],
                "importance_score": abs(a["shap_value"]),     # |exact Shapley value| (margin space)
                "shap_value": a["shap_value"],
                "contribution_direction": "positive" if a["shap_value"] > 0 else "negative",
            }
            for a in exp["top_drivers"]
        ]

    async def compute_attention(self, decision: dict) -> list[dict]:
        """Honest: returns `[]`. There is no trained attention model in the system; attention
        visualisation is not fabricated. (RNG scatter removed Stage 10.)"""
        return []

    # ---- natural language (honest; text from real fields only) -------------

    async def generate_natural_language(self, decision: dict, feature_importance: list[dict] = None,
                                        attention_weights: list[dict] = None) -> str:
        parts = []
        actions = decision.get("actions", []) if isinstance(decision, dict) else []
        confidence = decision.get("confidence", 0) if isinstance(decision, dict) else 0

        if confidence > 0.8:
            parts.append("With high confidence,")
        elif confidence > 0.5:
            parts.append("With moderate confidence,")
        elif confidence > 0:
            parts.append("With some uncertainty,")

        action_summaries = []
        for action in actions[:3]:
            target = action.get("target_type"); target_id = action.get("target_id")
            action_type = action.get("action", "").replace("_", " "); value = action.get("value")
            if target == "robot":
                action_summaries.append(f"sending Robot {target_id} to charge" if "charge" in action_type
                                        else f"adjusting Robot {target_id} to {action_type}")
            elif target == "stage":
                action_summaries.append(f"setting Stage {target_id} to {value}% throughput")
            elif target == "supplier":
                action_summaries.append(f"modifying Supplier {target_id} order")
            elif target == "system":
                action_summaries.append(f"switching system to {value} mode")
        if action_summaries:
            parts.append("the recommended actions are: " + ", ".join(action_summaries) + ".")

        if feature_importance:
            reasons = [f"{f['feature_name'].replace('_', ' ')} ({f['contribution_direction']} impact)"
                       for f in feature_importance[:3]]
            parts.append(f"This decision was primarily influenced by: {', '.join(reasons)}.")

        impact = decision.get("expected_impact", {}) if isinstance(decision, dict) else {}
        impacts = []
        for key, label in (("throughput_change", "throughput"), ("energy_change", "energy"),
                           ("carbon_change", "carbon")):
            if impact.get(key, 0):
                sign = "+" if impact[key] > 0 else ""
                impacts.append(f"{sign}{impact[key]}% {label}")
        if impacts:
            parts.append(f"Expected impact: {', '.join(impacts)}.")

        return " ".join(parts) if parts else "No explanation available (no modelled factors for this decision)."

    # ---- counterfactuals ---------------------------------------------------

    async def generate_counterfactuals(self, decision: dict, num_counterfactuals: int = 3) -> list[dict]:
        """Real counterfactual for a FAILURE-prediction decision (via `failure_explainer` — a guided
        minimal-change search over the actual model). Returns `[]` honestly otherwise — never fabricates."""
        feats = self._failure_features(decision)
        if feats is None:
            return []
        try:
            from ml.failure_explainer import get_failure_explainer, ModelUnavailableError
            try:
                exp = get_failure_explainer().explain(counterfactual=True, **feats)
            except ModelUnavailableError:
                return []
        except Exception:  # pragma: no cover - defensive
            return []
        cf = exp.get("counterfactual", {})
        if not cf.get("found"):
            return []
        out = []
        for alt in cf.get("alternatives", [])[:num_counterfactuals]:
            out.append({
                "type": "minimal_feature_change",
                "feature": alt["feature"], "from": alt["from"], "to": alt["to"],
                "direction": alt["direction"], "p_fail_after": alt["p_fail_after"],
                "rel_change_pct": alt["rel_change_pct"],
                "note": "scored by the actual failure predictor (no fabrication)",
            })
        return out

    async def generate_heatmap_data(self, attention_weights: list[dict]) -> dict:
        """Honest: derives a structured map ONLY from real attention weights. With no attention model
        (compute_attention returns []), this is an empty map — no random scatter (removed Stage 10)."""
        return {
            "points": [
                {"component_type": w.get("component_type"), "component_id": w.get("component_id"),
                 "intensity": w.get("attention_score")}
                for w in (attention_weights or [])
            ],
            "note": "empty unless a real attention model is wired (none today)",
        }

    # ---- orchestration -----------------------------------------------------

    async def explain(self, decision: dict, include_shap: bool = True, include_attention: bool = True,
                      include_counterfactual: bool = False) -> dict:
        explanation = {
            "decision_id": decision.get("decision_id") if isinstance(decision, dict) else None,
            "explanation_types": ["natural_language"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        feature_importance = []
        attention_weights = []
        if include_shap:
            feature_importance = await self.compute_shap(decision)
            explanation["feature_importance"] = feature_importance
            if feature_importance:
                explanation["explanation_types"].append("feature_importance")
        if include_attention:
            attention_weights = await self.compute_attention(decision)
            explanation["attention_weights"] = attention_weights
            explanation["attention_heatmap_data"] = await self.generate_heatmap_data(attention_weights)
        explanation["natural_language"] = await self.generate_natural_language(
            decision, feature_importance, attention_weights)
        if include_counterfactual:
            cfs = await self.generate_counterfactuals(decision)
            explanation["counterfactuals"] = cfs
            if cfs:
                explanation["explanation_types"].append("counterfactual")
        explanation["key_factors"] = [
            f["feature_name"].replace("_", " ").title() for f in feature_importance[:5]
        ]
        return explanation

    async def explain_failure(self, *, top_k: int = 5, counterfactual: bool = True, **telemetry) -> dict:
        """Direct spine entry point: exact SHAP + real counterfactual for a failure-prediction sample.
        Delegates to `ml.failure_explainer`. Raises `ModelUnavailableError` if the brain is absent."""
        from ml.failure_explainer import get_failure_explainer
        return get_failure_explainer().explain(top_k=top_k, counterfactual=counterfactual, **telemetry)


_default: "Explainer | None" = None


def get_explainer() -> "Explainer":
    global _default
    if _default is None:
        _default = Explainer()
    return _default


__all__ = ["Explainer", "get_explainer"]
