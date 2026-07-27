"""
Metrics API Routes

Provides endpoints for:
- Model performance metrics (ANN, CNN, LSTM, PPO)
- Embodied Agent improvement comparison
- Hyperparameter configuration

Stage 1 (2026-05-11): the demo-metrics fallback helpers were deleted. Both
GET endpoints now raise HTTP 503 when no real metrics have been recorded,
instead of returning fabricated MAE/R²/accuracy values. Real metrics will
arrive in Stage 4 once model training notebooks land. See
knowledge-base/KB_02_Models_Inventory.md for the per-model rollout schedule.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

import structlog

from ml.metrics import (
    get_metrics_tracker,
    ModelMetrics,
    EmbodiedAgentMetrics,
    RegressionMetrics,
    ClassificationMetrics,
    HyperparameterTuner
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# Single source of truth for the "metrics not yet real" failure mode; keep
# the wording stable so frontend can surface it verbatim.
METRICS_UNAVAILABLE_DETAIL = (
    "Real model metrics not yet available. "
    "See KB_02_Models_Inventory.md for the per-model training status."
)


class RecordMetricsRequest(BaseModel):
    model_name: str
    model_type: str  # regression, classification, rl
    metrics: Dict[str, float]
    hyperparameters: Dict[str, Any] = {}
    training_samples: int = 0
    inference_time_ms: float = 0.0


class EmbodiedMetricsRequest(BaseModel):
    problem_conflicts: int = 0
    problem_robot_collisions: int = 0
    problem_bottlenecks: int = 0
    problem_stockouts: int = 0
    problem_throughput: float = 0.0
    problem_energy_kwh: float = 0.0
    problem_response_time_s: float = 0.0

    solution_conflicts: int = 0
    solution_robot_collisions: int = 0
    solution_bottlenecks: int = 0
    solution_stockouts: int = 0
    solution_throughput: float = 0.0
    solution_energy_kwh: float = 0.0
    solution_response_time_s: float = 0.0


@router.get("/models")
async def get_all_model_metrics():
    """Get performance metrics for all ML models. 503 until Stage 4 ships real ones."""
    tracker = await get_metrics_tracker()
    summaries = tracker.get_all_model_summaries()

    if not summaries:
        raise HTTPException(status_code=503, detail=METRICS_UNAVAILABLE_DETAIL)

    return {"models": summaries}


@router.get("/models/{model_name}")
async def get_model_metrics(model_name: str):
    """Get metrics history for a specific model."""
    tracker = await get_metrics_tracker()
    history = tracker.get_model_metrics(model_name)

    if not history:
        return {"model_name": model_name, "history": [], "message": "No metrics recorded yet"}

    return {
        "model_name": model_name,
        "latest": history[-1].metrics,
        "hyperparameters": history[-1].hyperparameters,
        "history_count": len(history)
    }


@router.post("/models")
async def record_model_metrics(request: RecordMetricsRequest):
    """Record new metrics for a model."""
    tracker = await get_metrics_tracker()

    metrics = ModelMetrics(
        model_name=request.model_name,
        model_type=request.model_type,
        metrics=request.metrics,
        hyperparameters=request.hyperparameters,
        training_samples=request.training_samples,
        inference_time_ms=request.inference_time_ms
    )

    tracker.record_model_metrics(metrics)

    return {"status": "recorded", "model_name": request.model_name}


@router.get("/embodied")
async def get_embodied_comparison():
    """Get Embodied Agent improvement metrics. 503 until real comparisons run."""
    tracker = await get_metrics_tracker()
    summary = tracker.get_embodied_summary()

    if not summary:
        raise HTTPException(status_code=503, detail=METRICS_UNAVAILABLE_DETAIL)

    return summary


@router.post("/embodied")
async def record_embodied_metrics(request: EmbodiedMetricsRequest):
    """Record new embodied agent comparison metrics."""
    tracker = await get_metrics_tracker()

    metrics = EmbodiedAgentMetrics(
        problem_conflicts=request.problem_conflicts,
        problem_robot_collisions=request.problem_robot_collisions,
        problem_bottlenecks=request.problem_bottlenecks,
        problem_stockouts=request.problem_stockouts,
        problem_throughput=request.problem_throughput,
        problem_energy_kwh=request.problem_energy_kwh,
        problem_response_time_s=request.problem_response_time_s,
        solution_conflicts=request.solution_conflicts,
        solution_robot_collisions=request.solution_robot_collisions,
        solution_bottlenecks=request.solution_bottlenecks,
        solution_stockouts=request.solution_stockouts,
        solution_throughput=request.solution_throughput,
        solution_energy_kwh=request.solution_energy_kwh,
        solution_response_time_s=request.solution_response_time_s
    )

    tracker.record_embodied_metrics(metrics)

    return {"status": "recorded", "improvements": metrics.to_dict()["improvements"]}


@router.get("/hyperparameters/{model_name}")
async def get_hyperparameters(model_name: str):
    """Get current hyperparameters for a model."""
    tracker = await get_metrics_tracker()
    latest = tracker.get_latest_model_metrics(model_name)

    if latest:
        return {"model_name": model_name, "hyperparameters": latest.hyperparameters}

    tuner = HyperparameterTuner()
    defaults = {
        "ann_demand": tuner._default_ann_params(),
        "ann_energy": tuner._default_ann_params(),
        "cnn_defect": tuner._default_cnn_params(),
        "cnn_obstacle": tuner._default_cnn_params(),
        "ppo_navigation": tuner._default_ppo_params(),
    }

    return {"model_name": model_name, "hyperparameters": defaults.get(model_name, {})}
