"""
API Endpoint Tests
Tests all REST API endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert data["status"] in ["healthy", "degraded"]
    
    @pytest.mark.asyncio
    async def test_ready_endpoint(self, client: AsyncClient):
        """Test readiness endpoint."""
        response = await client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data


class TestSystemStateEndpoints:
    """Tests for system state endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_system_state(self, client: AsyncClient):
        """Test getting full system state."""
        response = await client.get("/api/system-state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "robots" in data
        assert "stages" in data
        assert "supply_chain" in data
        assert "metrics" in data
    
    @pytest.mark.asyncio
    async def test_get_system_state_filtered(self, client: AsyncClient):
        """Test getting filtered system state."""
        response = await client.get(
            "/api/system-state",
            params={
                "include_robots": True,
                "include_stages": False,
                "include_supply_chain": False,
                "include_metrics": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "robots" in data
        # Stages should still be present but may be empty list
    
    @pytest.mark.asyncio
    async def test_get_robot_state(self, client: AsyncClient):
        """Test getting specific robot state."""
        response = await client.get("/api/system-state/robots/1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == 1
        assert "position" in data
        assert "battery" in data
    
    @pytest.mark.asyncio
    async def test_get_robot_not_found(self, client: AsyncClient):
        """Test getting non-existent robot."""
        response = await client.get("/api/system-state/robots/9999")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_stage_state(self, client: AsyncClient):
        """Test getting specific stage state."""
        response = await client.get("/api/system-state/stages/1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == 1
        assert "queue_depth" in data
        assert "throughput" in data


class TestDecisionEndpoints:
    """Tests for AI decision endpoints."""
    
    @pytest.mark.asyncio
    async def test_trigger_decision(self, client: AsyncClient, sample_decision_request):
        """Test triggering AI decision."""
        response = await client.post("/api/decision", json=sample_decision_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "decision_id" in data
        assert "actions" in data
        assert "reasoning" in data
        assert "confidence" in data
        assert data["confidence"] >= 0 and data["confidence"] <= 1
    
    @pytest.mark.asyncio
    async def test_trigger_decision_with_constraints(self, client: AsyncClient):
        """Test decision with constraints."""
        request = {
            "priority": "energy",
            "constraints": ["avoid stage 4"],
            "force_decision": True
        }
        
        response = await client.post("/api/decision", json=request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify constraint is respected
        for action in data.get("actions", []):
            if action.get("target_type") == "stage":
                assert action.get("target_id") != 4
    
    @pytest.mark.asyncio
    async def test_get_decision_history(self, client: AsyncClient):
        """Test getting decision history."""
        response = await client.get("/api/decisions/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "decisions" in data
        assert "total" in data


class TestPredictionEndpoints:
    """Tests for prediction endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_prediction(self, client: AsyncClient):
        """Test getting predictions."""
        response = await client.get("/api/prediction", params={"horizon_minutes": 30})
        
        assert response.status_code == 200
        data = response.json()
        
        assert "predictions" in data
        assert "model_version" in data
        
        # Check prediction structure
        for pred in data.get("predictions", []):
            assert "timestamp" in pred
            assert "horizon_minutes" in pred
            assert "confidence" in pred
    
    @pytest.mark.asyncio
    async def test_prediction_with_uncertainty(self, client: AsyncClient):
        """Test prediction with uncertainty bounds."""
        response = await client.get(
            "/api/prediction",
            params={"horizon_minutes": 15, "include_uncertainty": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for pred in data.get("predictions", []):
            if pred.get("uncertainty_bounds"):
                assert "throughput_low" in pred["uncertainty_bounds"]
                assert "throughput_high" in pred["uncertainty_bounds"]
    
    @pytest.mark.asyncio
    async def test_prediction_invalid_horizon(self, client: AsyncClient):
        """Test prediction with invalid horizon."""
        response = await client.get("/api/prediction", params={"horizon_minutes": 100})
        
        assert response.status_code == 422  # Validation error


class TestExplainabilityEndpoints:
    """Tests for explainability endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_explainability(self, client: AsyncClient):
        """Test getting decision explanation."""
        # First create a decision
        decision_response = await client.post(
            "/api/decision",
            json={"priority": "balanced", "force_decision": True}
        )
        decision_id = decision_response.json()["decision_id"]
        
        # Then get explanation
        response = await client.get(f"/api/explainability/{decision_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "natural_language" in data
        assert "explanation_types" in data
    
    @pytest.mark.asyncio
    async def test_explainability_with_options(self, client: AsyncClient):
        """Test explainability with specific options."""
        # First create a decision
        decision_response = await client.post(
            "/api/decision",
            json={"priority": "energy"}
        )
        decision_id = decision_response.json()["decision_id"]
        
        # Get explanation with options
        response = await client.get(
            f"/api/explainability/{decision_id}",
            params={
                "include_shap": True,
                "include_attention": True,
                "include_counterfactual": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "feature_importance" in data
        assert "attention_weights" in data
        assert "counterfactuals" in data


class TestOverrideEndpoints:
    """Tests for human override endpoints."""
    
    @pytest.mark.asyncio
    async def test_apply_override(self, client: AsyncClient):
        """Test applying human override."""
        # First create a decision
        decision_response = await client.post(
            "/api/decision",
            json={"priority": "throughput"}
        )
        decision_id = decision_response.json()["decision_id"]
        
        # Apply override
        override_request = {
            "decision_id": decision_id,
            "action": "reject",
            "reason": "Safety constraint not met in this scenario"
        }
        
        response = await client.post("/api/override", json=override_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["decision_id"] == decision_id
        assert data["action"] == "reject"
        assert data["feedback_recorded"] == True
    
    @pytest.mark.asyncio
    async def test_override_with_modification(self, client: AsyncClient):
        """Test override with modified actions."""
        # First create a decision
        decision_response = await client.post("/api/decision", json={})
        decision_id = decision_response.json()["decision_id"]
        
        # Apply override with modifications
        override_request = {
            "decision_id": decision_id,
            "action": "modify",
            "reason": "Adjusting robot assignment based on operator knowledge",
            "modified_actions": [
                {"target_type": "robot", "target_id": 3, "action": "charge", "value": None}
            ]
        }
        
        response = await client.post("/api/override", json=override_request)
        
        assert response.status_code == 200


class TestOptimizationEndpoints:
    """Tests for optimization control endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_weights(self, client: AsyncClient):
        """Test getting optimization weights."""
        response = await client.get("/api/optimization/weights")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "throughput" in data
        assert "energy" in data
        assert "carbon" in data
        assert "quality" in data
    
    @pytest.mark.asyncio
    async def test_set_weights(self, client: AsyncClient):
        """Test setting optimization weights."""
        new_weights = {
            "throughput": 0.6,
            "energy": 0.2,
            "carbon": 0.1,
            "quality": 0.1
        }
        
        response = await client.post("/api/optimization/weights", json=new_weights)
        
        assert response.status_code == 200
        data = response.json()
        
        # Weights should be normalized
        total = data["throughput"] + data["energy"] + data["carbon"] + data["quality"]
        assert abs(total - 1.0) < 0.01
    
    @pytest.mark.asyncio
    async def test_set_mode(self, client: AsyncClient):
        """Test setting system mode."""
        response = await client.post("/api/optimization/mode/sustainability")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["mode"] == "sustainability"
        assert data["status"] == "applied"
    
    @pytest.mark.asyncio
    async def test_set_invalid_mode(self, client: AsyncClient):
        """Test setting invalid mode."""
        response = await client.post("/api/optimization/mode/invalid_mode")
        
        assert response.status_code == 400


class TestAlertEndpoints:
    """Tests for alert endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_alerts(self, client: AsyncClient):
        """Test getting alerts."""
        response = await client.get("/api/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_alerts_filtered(self, client: AsyncClient):
        """Test getting filtered alerts."""
        response = await client.get(
            "/api/alerts",
            params={"severity": "critical", "acknowledged": False}
        )
        
        assert response.status_code == 200
