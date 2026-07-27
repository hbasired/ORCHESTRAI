"""
Decision Engine for AI Embodied Agent
Orchestrates AI decision-making using RL policy, world model predictions, and explainability.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any
from collections import deque

import structlog
import numpy as np

from config import settings
from services.state_manager import StateManager

logger = structlog.get_logger(__name__)


class DecisionEngine:
    """
    Orchestrates AI decision-making for manufacturing optimization.
    
    Combines:
    - World Model (LSTM): Predicts future states
    - RL Policy (PPO): Determines optimal actions
    - Explainability (SHAP): Explains decisions
    """
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.is_initialized = False
        
        # Decision history
        self._decisions: dict[str, dict] = {}
        self._decision_order: deque = deque(maxlen=1000)
        
        # Optimization weights
        self._weights = {
            "throughput": settings.default_throughput_weight,
            "energy": settings.default_energy_weight,
            "carbon": settings.default_carbon_weight,
            "quality": settings.default_quality_weight
        }
        
        # Current mode
        self._mode = "normal"
        
        # ML models (lazy loaded)
        self._vision_model = None
        self._world_model = None
        self._rl_policy = None
        self._explainer = None
    
    async def initialize(self) -> None:
        """Initialize the decision engine and load ML models."""
        logger.info("Initializing decision engine")
        
        try:
            # Lazy import ML modules
            from ml.vision_model import VisionModel
            from ml.world_model import WorldModel
            from ml.rl_policy import RLPolicy
            from ml.explainability import Explainer
            
            # Initialize models (lightweight versions for demo)
            self._vision_model = VisionModel()
            await self._vision_model.load()
            
            self._world_model = WorldModel()
            await self._world_model.load()
            
            self._rl_policy = RLPolicy()
            await self._rl_policy.load()
            
            self._explainer = Explainer()
            await self._explainer.initialize()
            
            self.is_initialized = True
            logger.info("Decision engine initialized successfully")
            
        except Exception as e:
            logger.warning("ML models not fully loaded, using fallback", error=str(e))
            self.is_initialized = True  # Allow operation with fallback
    
    async def make_decision(
        self,
        state: dict,
        priority: str = "balanced",
        constraints: list[str] = None,
        force: bool = False
    ) -> dict:
        """
        Make an AI decision based on current state.
        
        Args:
            state: Current system state
            priority: Optimization priority (throughput, energy, carbon, balanced)
            constraints: List of constraints to apply
            force: Force decision even if not needed
            
        Returns:
            Decision with actions, reasoning, and confidence
        """
        decision_id = f"dec_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow()
        
        logger.info("Making decision", decision_id=decision_id, priority=priority)
        
        # Adjust weights based on priority
        weight_overrides = self._get_priority_weights(priority)
        effective_weights = {**self._weights, **weight_overrides}
        
        # Analyze state and generate actions
        try:
            # Extract state features
            features = self._extract_features(state)
            
            # Get predictions from world model
            predictions = await self._get_predictions(state, features)
            
            # Run RL policy to get actions
            actions, confidence = await self._run_policy(features, effective_weights, constraints)
            
            # Calculate expected impact
            expected_impact = self._calculate_expected_impact(state, actions, predictions)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(state, actions, predictions, effective_weights)
            
            # Determine decision type
            decision_type = self._classify_decision_type(actions)
            
            # Check if approval is needed
            requires_approval = confidence < 0.7 or any(
                a.get("action") in ["emergency_procurement", "pause_stage"] 
                for a in actions
            )
            
            decision = {
                "decision_id": decision_id,
                "timestamp": timestamp.isoformat(),
                "decision_type": decision_type,
                "actions": actions,
                "reasoning": reasoning,
                "confidence": confidence,
                "expected_impact": expected_impact,
                "requires_approval": requires_approval,
                "alternative_actions": [],
                "state_snapshot": {
                    "bottleneck_stage": state.get("metrics", {}).get("bottleneck_stage"),
                    "active_robots": state.get("metrics", {}).get("active_robots"),
                    "overall_throughput": state.get("metrics", {}).get("overall_throughput")
                },
                "weights_used": effective_weights,
                "priority": priority,
                "constraints": constraints or []
            }
            
            # Store decision
            self._decisions[decision_id] = decision
            self._decision_order.append(decision_id)
            
            logger.info("Decision made", 
                       decision_id=decision_id, 
                       actions=len(actions),
                       confidence=confidence)
            
            return decision
            
        except Exception as e:
            logger.error("Decision error", decision_id=decision_id, error=str(e))
            
            # Return fallback decision
            return {
                "decision_id": decision_id,
                "timestamp": timestamp.isoformat(),
                "decision_type": "system_mode",
                "actions": [],
                "reasoning": f"Decision engine error: {str(e)}. Maintaining current state.",
                "confidence": 0.0,
                "expected_impact": {
                    "throughput_change": 0.0,
                    "energy_change": 0.0,
                    "carbon_change": 0.0,
                    "quality_change": 0.0,
                    "confidence": 0.0
                },
                "requires_approval": True,
                "alternative_actions": []
            }
    
    def _get_priority_weights(self, priority: str) -> dict:
        """Get weight overrides based on priority."""
        priorities = {
            "throughput": {"throughput": 0.7, "energy": 0.1, "carbon": 0.1, "quality": 0.1},
            "energy": {"throughput": 0.2, "energy": 0.5, "carbon": 0.2, "quality": 0.1},
            "carbon": {"throughput": 0.2, "energy": 0.2, "carbon": 0.5, "quality": 0.1},
            "quality": {"throughput": 0.2, "energy": 0.1, "carbon": 0.1, "quality": 0.6},
            "balanced": {}
        }
        return priorities.get(priority, {})
    
    def _extract_features(self, state: dict) -> np.ndarray:
        """Extract feature vector from state."""
        features = []
        
        # Robot features
        for robot in state.get("robots", []):
            features.extend([
                robot.get("position", {}).get("x", 0) / 100,  # Normalized
                robot.get("position", {}).get("y", 0) / 60,
                robot.get("battery", 0) / 100,
                1 if robot.get("status") == "working" else 0,
                robot.get("task_queue_length", 0) / 10
            ])
        
        # Pad if fewer robots
        while len(features) < 100:  # 20 robots * 5 features
            features.extend([0, 0, 0, 0, 0])
        
        # Stage features
        for stage in state.get("stages", []):
            features.extend([
                stage.get("queue_depth", 0) / 30,
                stage.get("throughput", 0) / 200,
                stage.get("energy_consumption", 0) / 50,
                1 if stage.get("status") == "bottleneck" else 0,
                stage.get("utilization", 0) / 100
            ])
        
        # Pad if fewer stages
        while len(features) < 150:  # 10 stages * 5 features + robot features
            features.extend([0, 0, 0, 0, 0])
        
        # System metrics
        metrics = state.get("metrics", {})
        features.extend([
            metrics.get("overall_throughput", 0) / 1000,
            metrics.get("overall_energy", 0) / 200,
            metrics.get("efficiency_score", 0) / 100
        ])
        
        return np.array(features, dtype=np.float32)
    
    async def _get_predictions(self, state: dict, features: np.ndarray) -> dict:
        """Get predictions from world model."""
        if self._world_model:
            try:
                return await self._world_model.predict(features, horizons=[5, 15, 30])
            except Exception as e:
                logger.warning("World model prediction failed", error=str(e))
        
        # Honest naive-persistence baseline (G-052 de-mock): NO fabricated growth (the old ×1.02/×1.01
        # multipliers invented an optimistic trend with no model behind it). Persistence = "throughput stays at
        # the current value" is a legitimate, labelled baseline — not a prediction dressed up as a model output.
        cur = float(state.get("metrics", {}).get("overall_throughput", 0) or 0)
        return {
            "5min": {"throughput": cur}, "15min": {"throughput": cur}, "30min": {"throughput": cur},
            "source": "naive_persistence_no_world_model",
        }
    
    async def _run_policy(
        self, 
        features: np.ndarray, 
        weights: dict,
        constraints: list[str] = None
    ) -> tuple[list[dict], float]:
        """Run RL policy to get actions."""
        if self._rl_policy:
            try:
                return await self._rl_policy.get_action(features, weights, constraints)
            except Exception as e:
                logger.warning("RL policy failed", error=str(e))
        
        # Fallback: Generate heuristic actions
        actions = []
        
        # Simple heuristic based on features
        if features[7] < 0.15:  # Low battery robot
            actions.append({
                "target_type": "robot",
                "target_id": 1,
                "action": "charge",
                "value": None
            })
        
        # Check for bottleneck stages
        for i in range(10):
            if features[100 + i * 5 + 3] > 0.5:  # Bottleneck flag
                actions.append({
                    "target_type": "stage",
                    "target_id": i + 1,
                    "action": "reduce_throughput",
                    "value": 80
                })
        
        # Default action if none generated
        if not actions:
            actions.append({
                "target_type": "system",
                "target_id": None,
                "action": "switch_mode",
                "value": "normal"
            })
        
        return actions, 0.75
    
    def _calculate_expected_impact(
        self, 
        state: dict, 
        actions: list[dict],
        predictions: dict
    ) -> dict:
        """Calculate expected impact of actions."""
        # Simple estimation based on action types
        throughput_change = 0.0
        energy_change = 0.0
        carbon_change = 0.0
        quality_change = 0.0
        
        for action in actions:
            action_type = action.get("action", "")
            
            if action_type in ["increase_throughput", "navigate_to"]:
                throughput_change += 2.0
                energy_change += 1.5
            elif action_type in ["reduce_throughput", "pause_stage"]:
                throughput_change -= 1.0
                energy_change -= 2.0
                carbon_change -= 1.5
            elif action_type == "charge":
                energy_change += 0.5
            elif action_type == "switch_mode":
                if action.get("value") == "sustainability":
                    carbon_change -= 3.0
                    energy_change -= 2.0
        
        return {
            "throughput_change": round(throughput_change, 2),
            "energy_change": round(energy_change, 2),
            "carbon_change": round(carbon_change, 2),
            "quality_change": round(quality_change, 2),
            "confidence": 0.8
        }
    
    def _generate_reasoning(
        self,
        state: dict,
        actions: list[dict],
        predictions: dict,
        weights: dict
    ) -> str:
        """Generate natural language reasoning for the decision."""
        reasons = []
        
        # Analyze state
        metrics = state.get("metrics", {})
        bottleneck = metrics.get("bottleneck_stage")
        
        if bottleneck:
            reasons.append(f"Stage {bottleneck} identified as bottleneck with high queue depth")
        
        # Check for low battery robots
        low_battery = [r for r in state.get("robots", []) if r.get("battery", 100) < 20]
        if low_battery:
            reasons.append(f"{len(low_battery)} robot(s) have low battery requiring attention")
        
        # Check throughput trend
        current_throughput = metrics.get("overall_throughput", 0)
        if current_throughput < 500:
            reasons.append("Overall throughput below target, optimization needed")
        
        # Weight explanation
        priority_name = max(weights, key=weights.get)
        reasons.append(f"Optimizing primarily for {priority_name} based on current weights")
        
        # Action summary
        action_summary = []
        for action in actions[:3]:  # First 3 actions
            if action.get("target_type") == "robot":
                action_summary.append(f"Robot {action.get('target_id')}: {action.get('action')}")
            elif action.get("target_type") == "stage":
                action_summary.append(f"Stage {action.get('target_id')}: {action.get('action')}")
        
        if action_summary:
            reasons.append(f"Recommended actions: {', '.join(action_summary)}")
        
        return ". ".join(reasons) + "."
    
    def _classify_decision_type(self, actions: list[dict]) -> str:
        """Classify the overall decision type."""
        if not actions:
            return "system_mode"
        
        target_types = [a.get("target_type") for a in actions]
        
        if len(set(target_types)) > 1:
            return "multi_action"
        elif "robot" in target_types:
            return "robot_routing"
        elif "stage" in target_types:
            return "stage_adjustment"
        elif "supplier" in target_types:
            return "supplier_order"
        else:
            return "system_mode"
    
    async def get_decision(self, decision_id: str) -> Optional[dict]:
        """Get a specific decision by ID."""
        return self._decisions.get(decision_id)
    
    async def get_decision_history(
        self, 
        limit: int = 20, 
        offset: int = 0
    ) -> list[dict]:
        """Get recent decisions."""
        decision_ids = list(self._decision_order)
        decision_ids.reverse()
        
        selected_ids = decision_ids[offset:offset + limit]
        return [self._decisions[did] for did in selected_ids if did in self._decisions]
    
    async def predict_future_state(
        self,
        current_state: dict,
        state_history: list[dict],
        horizon_minutes: int = 30,
        include_uncertainty: bool = True
    ) -> dict:
        """Predict future system state."""
        timestamp = datetime.utcnow()
        
        # Extract features from history
        features = self._extract_features(current_state)
        
        # Make predictions
        predictions = await self._get_predictions(current_state, features)
        # G-052 de-mock: report HONESTLY whether a real world model produced these or it's the naive baseline.
        is_naive = predictions.get("source", "").startswith("naive_persistence")
        model_version = "naive-persistence (no world model loaded)" if is_naive \
            else getattr(self._world_model, "version", "world-model")

        predicted_states = []
        horizons = [5, 15, 30] if horizon_minutes >= 30 else [5, horizon_minutes]

        for h in horizons:
            if h > horizon_minutes:
                continue
            pred_time = timestamp + timedelta(minutes=h)
            phorizon = predictions.get(f"{h}min", {})
            thr = phorizon.get("throughput", current_state.get("metrics", {}).get("overall_throughput", 0))
            # Honest uncertainty: ONLY emit bounds the model actually produced; the naive baseline has none
            # (the old ±10% bounds were fabricated). Likewise confidence is reported only when model-derived.
            real_low, real_high = phorizon.get("throughput_low"), phorizon.get("throughput_high")
            bounds = None
            if include_uncertainty and real_low is not None and real_high is not None:
                bounds = {"throughput_low": real_low, "throughput_high": real_high}
            predicted_states.append({
                "timestamp": pred_time.isoformat(),
                "horizon_minutes": h,
                "robots": current_state.get("robots", []),  # carried forward, not predicted
                "stages": current_state.get("stages", []),
                "metrics": {**current_state.get("metrics", {}), "overall_throughput": thr},
                # Honest confidence: a real model reports its own; the naive carry-forward reports a LOW, fixed,
                # clearly-labelled value (0.25) — NOT the old fabricated decreasing 0.9-h*0.01 that pretended to be
                # a model output. Low+labelled = honest "no model behind this"; not a plausible fake.
                "confidence": float(phorizon.get("confidence")) if (not is_naive and phorizon.get("confidence") is not None) else 0.25,
                "confidence_basis": "model" if not is_naive else "naive_persistence_no_model",
                "uncertainty_bounds": bounds,
            })

        return {
            "request_timestamp": timestamp.isoformat(),
            "predictions": predicted_states,
            "model_version": model_version,
            "is_naive_baseline": is_naive,
        }
    
    async def explain_decision(
        self,
        decision_id: str,
        include_shap: bool = True,
        include_attention: bool = True,
        include_counterfactual: bool = False
    ) -> Optional[dict]:
        """Generate detailed explanation for a decision."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return None
        
        explanation = {
            "decision_id": decision_id,
            "explanation_types": [],
            "natural_language": decision.get("reasoning", ""),
            "feature_importance": [],
            "attention_weights": [],
            "attention_heatmap_url": None,
            "counterfactuals": [],
            "key_factors": []
        }
        
        explanation["explanation_types"].append("natural_language")
        
        if include_shap and self._explainer:
            try:
                shap_values = await self._explainer.compute_shap(decision)
                explanation["feature_importance"] = shap_values
                explanation["explanation_types"].append("feature_importance")
            except Exception as e:
                logger.warning("SHAP computation failed", error=str(e))
                # Honest: NO fabricated SHAP (Stage 10 de-mock). The real explainer returns exact
                # TreeSHAP for failure decisions and honest-empty for generic decisions with no model.
                explanation["feature_importance"] = []
        
        if include_attention and self._explainer:
            try:
                explanation["attention_weights"] = await self._explainer.compute_attention(decision)
                if explanation["attention_weights"]:
                    explanation["explanation_types"].append("attention_heatmap")
            except Exception as e:
                logger.warning("attention computation failed", error=str(e))
                explanation["attention_weights"] = []  # honest: no trained attention model (Stage 10 de-mock; no fabrication)
        
        if include_counterfactual and self._explainer:
            try:
                explanation["counterfactuals"] = await self._explainer.generate_counterfactuals(decision)
                if explanation["counterfactuals"]:
                    explanation["explanation_types"].append("counterfactual")
            except Exception as e:
                logger.warning("counterfactual computation failed", error=str(e))
                explanation["counterfactuals"] = []  # honest: real explainer or empty (Stage 10 de-mock; no fabrication)

        # Key factors derived HONESTLY from the real decision reasoning (no fabricated list; Stage 10 de-mock).
        reasoning = (decision.get("reasoning") or "").strip()
        explanation["key_factors"] = [s.strip() for s in reasoning.replace(";", ".").split(".") if s.strip()][:5]

        return explanation
    
    async def apply_override(
        self,
        decision_id: str,
        action: str,
        reason: str,
        modified_actions: list[dict] = None,
        operator_id: str = None
    ) -> dict:
        """Apply human override to a decision."""
        decision = self._decisions.get(decision_id)
        
        if not decision:
            return {"status": "error", "message": f"Decision {decision_id} not found"}
        
        # Record override
        decision["override"] = {
            "action": action,
            "reason": reason,
            "modified_actions": modified_actions,
            "operator_id": operator_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if action == "accept":
            decision["status"] = "accepted"
            # In production, would execute the actions here
            logger.info("Decision accepted", decision_id=decision_id)
            
        elif action == "reject":
            decision["status"] = "rejected"
            logger.info("Decision rejected", decision_id=decision_id, reason=reason)
            
        elif action == "modify":
            decision["status"] = "modified"
            decision["actions"] = modified_actions or decision["actions"]
            logger.info("Decision modified", decision_id=decision_id)
        
        return {"status": "applied", "decision_id": decision_id}
    
    async def get_optimization_weights(self) -> dict:
        """Get current optimization weights."""
        return self._weights.copy()
    
    async def set_optimization_weights(self, weights: dict) -> None:
        """Set new optimization weights."""
        self._weights.update(weights)
        logger.info("Optimization weights updated", weights=self._weights)
    
    async def set_mode(self, mode: str) -> None:
        """Set the operation mode."""
        self._mode = mode
        
        # Adjust weights based on mode
        mode_weights = {
            "normal": {"throughput": 0.4, "energy": 0.2, "carbon": 0.2, "quality": 0.2},
            "efficiency": {"throughput": 0.7, "energy": 0.1, "carbon": 0.1, "quality": 0.1},
            "emergency": {"throughput": 0.9, "energy": 0.05, "carbon": 0.0, "quality": 0.05},
            "sustainability": {"throughput": 0.2, "energy": 0.3, "carbon": 0.4, "quality": 0.1},
            "simulation": {"throughput": 0.4, "energy": 0.2, "carbon": 0.2, "quality": 0.2}
        }
        
        if mode in mode_weights:
            self._weights = mode_weights[mode]
        
        if self.state_manager:
            await self.state_manager.set_mode(mode)
        
        logger.info("Mode changed", mode=mode, weights=self._weights)
