"""
Unit Tests for ML Models
Tests vision, world model, RL policy, and explainability modules.
"""

import pytest
import numpy as np


class TestVisionModel:
    """Tests for the YOLOv8 vision model."""
    
    # Updated 2026-06-13 (Stage 9): the vision model is now honest — it no longer fabricates
    # detections. `_generate_mock_detections` is removed; `detect()` raises ModelUnavailableError
    # when ultralytics/weights are absent and runs REAL YOLOv8n otherwise. Deep tests live in
    # tests/test_vision_defect.py.

    def test_is_available_is_bool(self):
        from ml.vision_model import VisionModel
        assert isinstance(VisionModel().is_available(), bool)

    def test_no_mock_fabrication_method(self):
        """The theatrical random-detection fallback must be gone."""
        from ml.vision_model import VisionModel
        assert not hasattr(VisionModel, "_generate_mock_detections")

    @pytest.mark.asyncio
    async def test_detection_output_format_or_honest_unavailable(self):
        """detect() returns a real-detection list when YOLO is available, else raises
        ModelUnavailableError — never fabricates."""
        from ml.vision_model import VisionModel, ModelUnavailableError
        model = VisionModel()
        frame = (np.random.rand(640, 640, 3) * 255).astype(np.uint8)
        if model.is_available():
            detections = await model.detect(frame)
            assert isinstance(detections, list)
            for det in detections:
                assert "position" in det and "x" in det["position"] and "y" in det["position"]
        else:
            with pytest.raises(ModelUnavailableError):
                await model.detect(frame)

    def test_confidence_threshold_setting(self):
        """Test confidence threshold adjustment."""
        from ml.vision_model import VisionModel
        
        model = VisionModel()
        model.set_confidence_threshold(0.7)
        
        assert model.confidence_threshold == 0.7
        
        # Test bounds
        model.set_confidence_threshold(0.05)
        assert model.confidence_threshold == 0.1
        
        model.set_confidence_threshold(1.5)
        assert model.confidence_threshold == 0.99


class TestWorldModel:
    """Tests for the Stage-8 world model (TTF forecaster). Updated 2026-06-13 to the honest
    contract: the model is a real time-to-failure forecaster that raises ModelUnavailableError
    when its trained weights/torch are absent — it no longer initialises random weights or
    fabricates sequences. Deep TTF/causal tests live in tests/test_world_model.py."""

    def test_is_available_is_bool(self):
        from ml.world_model import WorldModel
        assert isinstance(WorldModel().is_available(), bool)

    def test_honest_unavailable_on_missing_weights(self, tmp_path):
        from ml.world_model import WorldModel, ModelUnavailableError, FEATURES
        model = WorldModel(weights_path=tmp_path / "missing.pt")
        assert model.is_available() is False
        with pytest.raises(ModelUnavailableError):
            model.predict_ttf(np.zeros((6, len(FEATURES)), dtype=np.float32))

    def test_model_info_shape(self):
        from ml.world_model import WorldModel
        info = WorldModel().model_info
        assert info["task"].startswith("time-to-failure")
        assert "available" in info

    @pytest.mark.asyncio
    async def test_async_load_does_not_raise(self):
        """decision_engine calls await load(); it must not raise even when weights are absent
        (predict() is the honest gate, wrapped in decision_engine's try/except)."""
        from ml.world_model import WorldModel
        await WorldModel(weights_path="definitely_missing.pt").load()  # no exception


class TestRLPolicy:
    """Tests for the PPO RL policy."""
    
    @pytest.mark.asyncio
    async def test_policy_load(self):
        """Test RL policy initialization."""
        from ml.rl_policy import RLPolicy
        
        policy = RLPolicy()
        await policy.load()
        
        assert policy.is_loaded
        assert policy.action_dim == 50
    
    @pytest.mark.asyncio
    async def test_action_generation(self, sample_features):
        """Test action generation."""
        from ml.rl_policy import RLPolicy
        
        policy = RLPolicy()
        await policy.load()
        
        actions, confidence = await policy.get_action(
            sample_features,
            weights={"throughput": 0.5, "energy": 0.2, "carbon": 0.2, "quality": 0.1}
        )
        
        assert isinstance(actions, list)
        assert isinstance(confidence, float)
        assert confidence >= 0 and confidence <= 1
        
        for action in actions:
            assert "target_type" in action
            assert "action" in action
    
    @pytest.mark.asyncio
    async def test_action_with_constraints(self, sample_features):
        """Test action generation with constraints."""
        from ml.rl_policy import RLPolicy
        
        policy = RLPolicy()
        await policy.load()
        
        actions, _ = await policy.get_action(
            sample_features,
            constraints=["avoid stage 1", "avoid stage 2"]
        )
        
        # Verify constraints are respected
        for action in actions:
            if action.get("target_type") == "stage":
                assert action.get("target_id") not in [1, 2]
    
    @pytest.mark.asyncio
    async def test_value_estimation(self, sample_features):
        """Test value estimation."""
        from ml.rl_policy import RLPolicy
        
        policy = RLPolicy()
        await policy.load()
        
        value = await policy.get_value(sample_features)
        
        assert isinstance(value, float)


class TestExplainability:
    """Tests for the explainability module (HONEST contract, updated 2026-06-13 Stage 10).

    The module no longer fabricates SHAP/attention/counterfactuals with random.*. For a decision that
    carries `failure_features` it computes REAL exact TreeSHAP; for generic decisions with no model behind
    them it returns honest-empty. Deep real-SHAP/counterfactual tests live in tests/test_explainability.py."""

    @pytest.mark.asyncio
    async def test_explainer_init(self):
        from ml.explainability import Explainer
        explainer = Explainer()
        await explainer.initialize()
        assert explainer.is_initialized

    @pytest.mark.asyncio
    async def test_shap_empty_for_generic_decision(self):
        """No model behind a generic decision → honest empty, never fabricated importances."""
        from ml.explainability import Explainer
        explainer = Explainer()
        await explainer.initialize()
        decision = {"decision_id": "t", "actions": [{"target_type": "robot", "target_id": 1}],
                    "state_snapshot": {"bottleneck_stage": 4}}
        shap_values = await explainer.compute_shap(decision, num_features=5)
        assert shap_values == []

    @pytest.mark.asyncio
    async def test_attention_honest_empty(self):
        """No trained attention model → honest empty (was random.*)."""
        from ml.explainability import Explainer
        explainer = Explainer()
        await explainer.initialize()
        assert await explainer.compute_attention({"actions": []}) == []

    @pytest.mark.asyncio
    async def test_natural_language_generation(self):
        from ml.explainability import Explainer
        explainer = Explainer()
        await explainer.initialize()
        decision = {"confidence": 0.85,
                    "actions": [{"target_type": "robot", "target_id": 5, "action": "charge"}],
                    "expected_impact": {"throughput_change": 2.5, "energy_change": -1.0}}
        fi = [{"feature_name": "robot_5_battery", "contribution_direction": "positive"}]
        text = await explainer.generate_natural_language(decision, fi)
        assert isinstance(text, str) and len(text) > 0

    @pytest.mark.asyncio
    async def test_counterfactual_empty_for_generic(self):
        """Generic decision → honest empty counterfactuals (was exactly-2 fabricated)."""
        from ml.explainability import Explainer
        explainer = Explainer()
        await explainer.initialize()
        cfs = await explainer.generate_counterfactuals({"actions": []}, num_counterfactuals=2)
        assert cfs == []

    @pytest.mark.asyncio
    async def test_complete_explanation_shape(self):
        from ml.explainability import Explainer
        explainer = Explainer()
        await explainer.initialize()
        decision = {"decision_id": "test_002", "confidence": 0.75,
                    "actions": [{"target_type": "stage", "target_id": 4, "action": "reduce_throughput", "value": 80}],
                    "expected_impact": {"throughput_change": -1.0, "energy_change": -2.0}}
        explanation = await explainer.explain(decision, include_shap=True, include_attention=True,
                                              include_counterfactual=True)
        assert explanation["decision_id"] == "test_002"
        assert "natural_language" in explanation
        assert "feature_importance" in explanation       # present (honest [] for a generic decision)
        assert "attention_weights" in explanation
        assert "counterfactuals" in explanation
        assert "natural_language" in explanation["explanation_types"]


class TestModelIntegration:
    """Integration tests for ML models working together."""
    
    @pytest.mark.asyncio
    async def test_full_decision_pipeline(self, sample_features):
        """Test complete decision pipeline."""
        from ml.world_model import WorldModel
        from ml.rl_policy import RLPolicy
        from ml.explainability import Explainer
        
        # Initialize models
        world_model = WorldModel()
        await world_model.load()
        
        policy = RLPolicy()
        await policy.load()
        
        explainer = Explainer()
        await explainer.initialize()
        
        # World model (Stage-8 honest contract): it forecasts time-to-failure from a (window, 5)
        # telemetry window and raises ModelUnavailableError on the legacy flat feature vector —
        # it no longer fabricates a horizon dict. decision_engine wraps this in try/except and
        # falls back, so the pipeline degrades gracefully rather than on fake predictions.
        from ml.world_model import ModelUnavailableError
        with pytest.raises(ModelUnavailableError):
            await world_model.predict(sample_features, horizons=[5, 15])

        # Get actions
        actions, confidence = await policy.get_action(sample_features)
        assert len(actions) > 0
        
        # Generate explanation
        decision = {
            "decision_id": "integration_test",
            "actions": actions,
            "confidence": confidence,
            "expected_impact": {},
            "state_snapshot": {}
        }
        
        explanation = await explainer.explain(decision)
        assert "natural_language" in explanation
