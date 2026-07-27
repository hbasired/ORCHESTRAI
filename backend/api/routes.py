"""
API Routes for AI Embodied Agent
Implements all REST endpoints for system state, decisions, predictions, and overrides.
"""

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Depends
from prometheus_client import Counter, Histogram

from api.schemas import (
    SystemStateResponse,
    DecisionRequest,
    DecisionResponse,
    PredictionRequest,
    PredictionResponse,
    ExplainabilityResponse,
    OverrideRequest,
    OverrideResponse,
    OptimizationWeights,
    Alert,
    AlertSeverity,
)

logger = structlog.get_logger(__name__)

# Prometheus metrics
API_REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total API requests by endpoint",
    ["endpoint", "method", "status"]
)
API_LATENCY = Histogram(
    "api_request_duration_seconds",
    "API request latency",
    ["endpoint"]
)

router = APIRouter(tags=["AI Agent"])


# Dependency to get services
async def get_state_manager():
    """Get the state manager instance."""
    from main import state_manager
    if state_manager is None:
        raise HTTPException(status_code=503, detail="State manager not initialized")
    return state_manager


async def get_decision_engine():
    """Get the decision engine instance."""
    from main import decision_engine
    if decision_engine is None:
        raise HTTPException(status_code=503, detail="Decision engine not initialized")
    return decision_engine


# ============================================================================
# System State Endpoints
# ============================================================================

@router.get(
    "/system-state",
    response_model=SystemStateResponse,
    summary="Get current system state",
    description="Returns the current state of all robots, stages, and supply chain"
)
async def get_system_state(
    include_robots: bool = Query(True, description="Include robot states"),
    include_stages: bool = Query(True, description="Include stage states"),
    include_supply_chain: bool = Query(True, description="Include supply chain"),
    include_metrics: bool = Query(True, description="Include system metrics"),
    state_manager=Depends(get_state_manager)
) -> SystemStateResponse:
    """
    Get the current system state.
    
    Returns a comprehensive view of:
    - Robot positions, battery levels, and tasks
    - Manufacturing stage queues and throughput
    - Supply chain demand forecast and inventory
    - Overall system metrics and KPIs
    """
    try:
        with API_LATENCY.labels(endpoint="system-state").time():
            state = await state_manager.get_current_state(
                include_robots=include_robots,
                include_stages=include_stages,
                include_supply_chain=include_supply_chain,
                include_metrics=include_metrics
            )
            
            API_REQUEST_COUNT.labels(
                endpoint="system-state",
                method="GET",
                status="success"
            ).inc()
            
            return SystemStateResponse(**state)
            
    except Exception as e:
        logger.error("Error getting system state", error=str(e))
        API_REQUEST_COUNT.labels(
            endpoint="system-state",
            method="GET",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/system-state/robots/{robot_id}",
    summary="Get specific robot state",
    description="Returns detailed state for a specific robot"
)
async def get_robot_state(
    robot_id: int,
    state_manager=Depends(get_state_manager)
) -> dict:
    """Get state of a specific robot by ID."""
    try:
        robot = await state_manager.get_robot_state(robot_id)
        if robot is None:
            raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")
        return robot
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting robot state", robot_id=robot_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/system-state/stages/{stage_id}",
    summary="Get specific stage state",
    description="Returns detailed state for a specific manufacturing stage"
)
async def get_stage_state(
    stage_id: int,
    state_manager=Depends(get_state_manager)
) -> dict:
    """Get state of a specific stage by ID."""
    try:
        stage = await state_manager.get_stage_state(stage_id)
        if stage is None:
            raise HTTPException(status_code=404, detail=f"Stage {stage_id} not found")
        return stage
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting stage state", stage_id=stage_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Decision Endpoints
# ============================================================================

@router.post(
    "/decision",
    response_model=DecisionResponse,
    summary="Trigger AI decision",
    description="Requests the AI agent to compute an optimal decision"
)
async def trigger_decision(
    request: DecisionRequest,
    state_manager=Depends(get_state_manager),
    decision_engine=Depends(get_decision_engine)
) -> DecisionResponse:
    """
    Trigger the AI agent to make a decision.
    
    The agent will:
    1. Analyze current system state
    2. Run the RL policy to determine optimal actions
    3. Generate explanations for the decision
    4. Return actions with confidence scores
    """
    try:
        with API_LATENCY.labels(endpoint="decision").time():
            # Get current state
            state = await state_manager.get_current_state()
            
            # Apply custom weights if provided
            if request.custom_weights:
                weights = OptimizationWeights(**request.custom_weights).normalize()
                await decision_engine.set_optimization_weights(weights.model_dump())
            
            # Make decision
            decision = await decision_engine.make_decision(
                state=state,
                priority=request.priority,
                constraints=request.constraints,
                force=request.force_decision
            )
            
            API_REQUEST_COUNT.labels(
                endpoint="decision",
                method="POST",
                status="success"
            ).inc()
            
            return DecisionResponse(**decision)
            
    except Exception as e:
        logger.error("Error making decision", error=str(e))
        API_REQUEST_COUNT.labels(
            endpoint="decision",
            method="POST",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/decision/{decision_id}",
    response_model=DecisionResponse,
    summary="Get specific decision",
    description="Retrieves details of a previously made decision"
)
async def get_decision(
    decision_id: str,
    decision_engine=Depends(get_decision_engine)
) -> DecisionResponse:
    """Get details of a specific decision by ID."""
    try:
        decision = await decision_engine.get_decision(decision_id)
        if decision is None:
            raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")
        return DecisionResponse(**decision)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting decision", decision_id=decision_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/decisions/history",
    summary="Get decision history",
    description="Returns recent AI decisions"
)
async def get_decision_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    decision_engine=Depends(get_decision_engine)
) -> dict:
    """Get history of recent decisions."""
    try:
        history = await decision_engine.get_decision_history(limit=limit, offset=offset)
        return {
            "total": len(history),
            "limit": limit,
            "offset": offset,
            "decisions": history
        }
    except Exception as e:
        logger.error("Error getting decision history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Prediction Endpoints
# ============================================================================

@router.get(
    "/prediction",
    response_model=PredictionResponse,
    summary="Get system state prediction",
    description="Predicts future system state using the LSTM world model"
)
async def get_prediction(
    horizon_minutes: int = Query(30, ge=5, le=60, description="Prediction horizon in minutes"),
    include_uncertainty: bool = Query(True, description="Include uncertainty bounds"),
    state_manager=Depends(get_state_manager),
    decision_engine=Depends(get_decision_engine)
) -> PredictionResponse:
    """
    Get prediction of future system state.
    
    Uses the LSTM world model to forecast:
    - Robot positions and battery levels
    - Stage queue depths and throughput
    - Overall system metrics
    
    Predictions include confidence intervals when include_uncertainty=True.
    """
    try:
        with API_LATENCY.labels(endpoint="prediction").time():
            # Get current state for prediction input
            state = await state_manager.get_current_state()
            state_history = await state_manager.get_state_history(
                minutes=10  # Get 10 minutes of history for LSTM
            )
            
            # Make prediction
            prediction = await decision_engine.predict_future_state(
                current_state=state,
                state_history=state_history,
                horizon_minutes=horizon_minutes,
                include_uncertainty=include_uncertainty
            )
            
            API_REQUEST_COUNT.labels(
                endpoint="prediction",
                method="GET",
                status="success"
            ).inc()
            
            return PredictionResponse(**prediction)
            
    except Exception as e:
        logger.error("Error making prediction", error=str(e))
        API_REQUEST_COUNT.labels(
            endpoint="prediction",
            method="GET",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Explainability Endpoints
# ============================================================================

@router.get(
    "/explainability/{decision_id}",
    response_model=ExplainabilityResponse,
    summary="Get decision explanation",
    description="Returns detailed explanation for a decision"
)
async def get_explainability(
    decision_id: str,
    include_shap: bool = Query(True, description="Include SHAP feature importance"),
    include_attention: bool = Query(True, description="Include attention weights"),
    include_counterfactual: bool = Query(False, description="Include counterfactual analysis"),
    decision_engine=Depends(get_decision_engine)
) -> ExplainabilityResponse:
    """
    Get detailed explanation for a specific decision.
    
    Returns:
    - Natural language explanation
    - SHAP feature importance values
    - Attention heatmap (which factors influenced the decision)
    - Counterfactual scenarios (optional)
    """
    try:
        with API_LATENCY.labels(endpoint="explainability").time():
            explanation = await decision_engine.explain_decision(
                decision_id=decision_id,
                include_shap=include_shap,
                include_attention=include_attention,
                include_counterfactual=include_counterfactual
            )
            
            if explanation is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Decision {decision_id} not found or explanation unavailable"
                )
            
            API_REQUEST_COUNT.labels(
                endpoint="explainability",
                method="GET",
                status="success"
            ).inc()
            
            return ExplainabilityResponse(**explanation)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting explanation", decision_id=decision_id, error=str(e))
        API_REQUEST_COUNT.labels(
            endpoint="explainability",
            method="GET",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Override Endpoints
# ============================================================================

@router.post(
    "/override",
    response_model=OverrideResponse,
    summary="Human override",
    description="Allows human operator to override an AI decision"
)
async def apply_override(
    request: OverrideRequest,
    decision_engine=Depends(get_decision_engine)
) -> OverrideResponse:
    """
    Apply human override to a decision.
    
    Operators can:
    - Accept: Approve and execute the decision
    - Reject: Cancel the decision with reason
    - Modify: Change the actions before execution
    
    All overrides are logged for continuous learning.
    """
    try:
        with API_LATENCY.labels(endpoint="override").time():
            result = await decision_engine.apply_override(
                decision_id=request.decision_id,
                action=request.action,
                reason=request.reason,
                modified_actions=request.modified_actions,
                operator_id=request.operator_id
            )
            
            API_REQUEST_COUNT.labels(
                endpoint="override",
                method="POST",
                status="success"
            ).inc()
            
            return OverrideResponse(
                override_id=str(uuid.uuid4()),
                decision_id=request.decision_id,
                timestamp=datetime.utcnow(),
                action=request.action,
                status=result.get("status", "applied"),
                feedback_recorded=True
            )
            
    except Exception as e:
        logger.error("Error applying override", error=str(e))
        API_REQUEST_COUNT.labels(
            endpoint="override",
            method="POST",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Optimization Control Endpoints
# ============================================================================

@router.get(
    "/optimization/weights",
    response_model=OptimizationWeights,
    summary="Get optimization weights",
    description="Returns current optimization priority weights"
)
async def get_optimization_weights(
    decision_engine=Depends(get_decision_engine)
) -> OptimizationWeights:
    """Get current optimization weights."""
    try:
        weights = await decision_engine.get_optimization_weights()
        return OptimizationWeights(**weights)
    except Exception as e:
        logger.error("Error getting weights", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/optimization/weights",
    response_model=OptimizationWeights,
    summary="Set optimization weights",
    description="Updates optimization priority weights"
)
async def set_optimization_weights(
    weights: OptimizationWeights,
    decision_engine=Depends(get_decision_engine)
) -> OptimizationWeights:
    """Set new optimization weights."""
    try:
        normalized = weights.normalize()
        await decision_engine.set_optimization_weights(normalized.model_dump())
        return normalized
    except Exception as e:
        logger.error("Error setting weights", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/optimization/mode/{mode}",
    summary="Set system mode",
    description="Switch system operation mode"
)
async def set_system_mode(
    mode: str,
    decision_engine=Depends(get_decision_engine)
) -> dict:
    """
    Set system operation mode.
    
    Available modes:
    - normal: Balanced operation
    - efficiency: Prioritize throughput
    - emergency: Maximum speed, ignore carbon
    - sustainability: Prioritize carbon reduction
    - simulation: Test mode without real actions
    """
    valid_modes = ["normal", "efficiency", "emergency", "sustainability", "simulation"]
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {valid_modes}"
        )
    
    try:
        await decision_engine.set_mode(mode)
        return {"mode": mode, "status": "applied", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error("Error setting mode", mode=mode, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Alerts Endpoints
# ============================================================================

@router.get(
    "/alerts",
    response_model=list[Alert],
    summary="Get active alerts",
    description="Returns current system alerts"
)
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    limit: int = Query(50, ge=1, le=200),
    state_manager=Depends(get_state_manager)
) -> list[Alert]:
    """Get active system alerts."""
    try:
        alerts = await state_manager.get_alerts(
            severity=severity,
            acknowledged=acknowledged,
            limit=limit
        )
        return [Alert(**a) for a in alerts]
    except Exception as e:
        logger.error("Error getting alerts", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alerts/{alert_id}/acknowledge",
    summary="Acknowledge alert",
    description="Mark an alert as acknowledged"
)
async def acknowledge_alert(
    alert_id: str,
    state_manager=Depends(get_state_manager)
) -> dict:
    """Acknowledge an alert by ID."""
    try:
        result = await state_manager.acknowledge_alert(alert_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return {"alert_id": alert_id, "acknowledged": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error acknowledging alert", alert_id=alert_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
