"""
ML Metrics and Hyperparameter Tuning Module

Provides:
- Model metrics tracking (MAE, MSE, RMSE, R², Accuracy, F1)
- Hyperparameter tuning with Optuna
- Embodied Agent improvement metrics comparison
- Supabase integration for metrics persistence
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import asyncio

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# METRIC TYPES
# =============================================================================

class MetricType(Enum):
    """Types of ML metrics."""
    # Regression metrics
    MAE = "mae"           # Mean Absolute Error
    MSE = "mse"           # Mean Squared Error
    RMSE = "rmse"         # Root Mean Squared Error
    R2 = "r2"             # R-squared (coefficient of determination)
    MAPE = "mape"         # Mean Absolute Percentage Error
    
    # Classification metrics
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    
    # RL metrics
    REWARD = "reward"
    EPISODE_LENGTH = "episode_length"
    SUCCESS_RATE = "success_rate"


@dataclass
class ModelMetrics:
    """Metrics for a single model."""
    model_name: str
    model_type: str  # regression, classification, rl
    metrics: Dict[str, float] = field(default_factory=dict)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    training_samples: int = 0
    inference_time_ms: float = 0.0


@dataclass
class EmbodiedAgentMetrics:
    """Comparison metrics: Problem Mode vs Solution Mode."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Problem Mode (Isolated Agents)
    problem_conflicts: int = 0
    problem_robot_collisions: int = 0
    problem_bottlenecks: int = 0
    problem_stockouts: int = 0
    problem_throughput: float = 0.0
    problem_energy_kwh: float = 0.0
    problem_response_time_s: float = 0.0
    
    # Solution Mode (Coordinated Embodied Agent)
    solution_conflicts: int = 0
    solution_robot_collisions: int = 0
    solution_bottlenecks: int = 0
    solution_stockouts: int = 0
    solution_throughput: float = 0.0
    solution_energy_kwh: float = 0.0
    solution_response_time_s: float = 0.0
    
    # Improvement percentages
    @property
    def conflict_reduction(self) -> float:
        if self.problem_conflicts == 0:
            return 0.0
        return (self.problem_conflicts - self.solution_conflicts) / self.problem_conflicts * 100
    
    @property
    def collision_reduction(self) -> float:
        if self.problem_robot_collisions == 0:
            return 0.0
        return (self.problem_robot_collisions - self.solution_robot_collisions) / self.problem_robot_collisions * 100
    
    @property
    def bottleneck_reduction(self) -> float:
        if self.problem_bottlenecks == 0:
            return 0.0
        return (self.problem_bottlenecks - self.solution_bottlenecks) / self.problem_bottlenecks * 100
    
    @property
    def stockout_reduction(self) -> float:
        if self.problem_stockouts == 0:
            return 0.0
        return (self.problem_stockouts - self.solution_stockouts) / self.problem_stockouts * 100
    
    @property
    def throughput_improvement(self) -> float:
        if self.problem_throughput == 0:
            return 0.0
        return (self.solution_throughput - self.problem_throughput) / self.problem_throughput * 100
    
    @property
    def energy_savings(self) -> float:
        if self.problem_energy_kwh == 0:
            return 0.0
        return (self.problem_energy_kwh - self.solution_energy_kwh) / self.problem_energy_kwh * 100
    
    @property
    def response_time_improvement(self) -> float:
        if self.problem_response_time_s == 0:
            return 0.0
        return (self.problem_response_time_s - self.solution_response_time_s) / self.problem_response_time_s * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_mode": {
                "conflicts": self.problem_conflicts,
                "robot_collisions": self.problem_robot_collisions,
                "bottlenecks": self.problem_bottlenecks,
                "stockouts": self.problem_stockouts,
                "throughput": self.problem_throughput,
                "energy_kwh": self.problem_energy_kwh,
                "response_time_s": self.problem_response_time_s,
            },
            "solution_mode": {
                "conflicts": self.solution_conflicts,
                "robot_collisions": self.solution_robot_collisions,
                "bottlenecks": self.solution_bottlenecks,
                "stockouts": self.solution_stockouts,
                "throughput": self.solution_throughput,
                "energy_kwh": self.solution_energy_kwh,
                "response_time_s": self.solution_response_time_s,
            },
            "improvements": {
                "conflict_reduction_pct": round(self.conflict_reduction, 1),
                "collision_reduction_pct": round(self.collision_reduction, 1),
                "bottleneck_reduction_pct": round(self.bottleneck_reduction, 1),
                "stockout_reduction_pct": round(self.stockout_reduction, 1),
                "throughput_improvement_pct": round(self.throughput_improvement, 1),
                "energy_savings_pct": round(self.energy_savings, 1),
                "response_time_improvement_pct": round(self.response_time_improvement, 1),
            }
        }


# =============================================================================
# METRIC CALCULATORS
# =============================================================================

class RegressionMetrics:
    """Calculate regression metrics."""
    
    @staticmethod
    def calculate(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate all regression metrics."""
        y_true = np.array(y_true).flatten()
        y_pred = np.array(y_pred).flatten()
        
        n = len(y_true)
        if n == 0:
            return {"mae": 0, "mse": 0, "rmse": 0, "r2": 0, "mape": 0}
        
        # MAE
        mae = np.mean(np.abs(y_true - y_pred))
        
        # MSE
        mse = np.mean((y_true - y_pred) ** 2)
        
        # RMSE
        rmse = np.sqrt(mse)
        
        # R² (coefficient of determination)
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # MAPE (handle division by zero)
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.any() else 0
        
        return {
            "mae": round(float(mae), 4),
            "mse": round(float(mse), 4),
            "rmse": round(float(rmse), 4),
            "r2": round(float(r2), 4),
            "mape": round(float(mape), 2)
        }


class ClassificationMetrics:
    """Calculate classification metrics."""
    
    @staticmethod
    def calculate(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int = 2) -> Dict[str, float]:
        """Calculate all classification metrics."""
        y_true = np.array(y_true).flatten()
        y_pred = np.array(y_pred).flatten()
        
        n = len(y_true)
        if n == 0:
            return {"accuracy": 0, "precision": 0, "recall": 0, "f1": 0}
        
        # Accuracy
        accuracy = np.mean(y_true == y_pred)
        
        # For binary or multi-class, calculate macro-averaged metrics
        precisions = []
        recalls = []
        
        for cls in range(num_classes):
            tp = np.sum((y_pred == cls) & (y_true == cls))
            fp = np.sum((y_pred == cls) & (y_true != cls))
            fn = np.sum((y_pred != cls) & (y_true == cls))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            
            precisions.append(precision)
            recalls.append(recall)
        
        avg_precision = np.mean(precisions)
        avg_recall = np.mean(recalls)
        f1 = 2 * avg_precision * avg_recall / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
        
        return {
            "accuracy": round(float(accuracy), 4),
            "precision": round(float(avg_precision), 4),
            "recall": round(float(avg_recall), 4),
            "f1": round(float(f1), 4)
        }


class RLMetrics:
    """Calculate RL metrics."""
    
    @staticmethod
    def calculate(rewards: List[float], episode_lengths: List[int], successes: List[bool]) -> Dict[str, float]:
        """Calculate RL training metrics."""
        if not rewards:
            return {"avg_reward": 0, "avg_episode_length": 0, "success_rate": 0}
        
        return {
            "avg_reward": round(float(np.mean(rewards)), 2),
            "max_reward": round(float(np.max(rewards)), 2),
            "min_reward": round(float(np.min(rewards)), 2),
            "avg_episode_length": round(float(np.mean(episode_lengths)), 1),
            "success_rate": round(float(np.mean(successes)) * 100, 1)
        }


# =============================================================================
# HYPERPARAMETER TUNING
# =============================================================================

class HyperparameterTuner:
    """
    Hyperparameter tuning using Optuna.
    
    Supports tuning for:
    - ANN: learning_rate, hidden_dims, dropout, batch_size
    - CNN: learning_rate, conv_channels, kernel_size
    - LSTM: learning_rate, hidden_size, num_layers
    - RL: learning_rate, gamma, epsilon
    """
    
    def __init__(self, n_trials: int = 50):
        self.n_trials = n_trials
        self._study = None
    
    async def tune_ann(self, train_fn, val_fn) -> Dict[str, Any]:
        """Tune ANN hyperparameters."""
        try:
            import optuna
            
            def objective(trial):
                params = {
                    "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-2, log=True),
                    "hidden_dim_1": trial.suggest_int("hidden_dim_1", 32, 256),
                    "hidden_dim_2": trial.suggest_int("hidden_dim_2", 16, 128),
                    "dropout": trial.suggest_float("dropout", 0.1, 0.5),
                    "batch_size": trial.suggest_categorical("batch_size", [16, 32, 64, 128]),
                    "epochs": trial.suggest_int("epochs", 10, 100)
                }
                
                # Train with params and return validation loss
                return train_fn(params)
            
            self._study = optuna.create_study(direction="minimize")
            self._study.optimize(objective, n_trials=self.n_trials, show_progress_bar=True)
            
            best_params = self._study.best_params
            logger.info("ANN hyperparameter tuning complete", best_params=best_params)
            return best_params
            
        except ImportError:
            logger.warning("Optuna not available, using default hyperparameters")
            return self._default_ann_params()
    
    async def tune_cnn(self, train_fn, val_fn) -> Dict[str, Any]:
        """Tune CNN hyperparameters."""
        try:
            import optuna
            
            def objective(trial):
                params = {
                    "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-2, log=True),
                    "conv_channels_1": trial.suggest_categorical("conv_channels_1", [16, 32, 64]),
                    "conv_channels_2": trial.suggest_categorical("conv_channels_2", [32, 64, 128]),
                    "conv_channels_3": trial.suggest_categorical("conv_channels_3", [64, 128, 256]),
                    "kernel_size": trial.suggest_categorical("kernel_size", [3, 5]),
                    "dropout": trial.suggest_float("dropout", 0.3, 0.7),
                    "batch_size": trial.suggest_categorical("batch_size", [8, 16, 32]),
                }
                return train_fn(params)
            
            self._study = optuna.create_study(direction="minimize")
            self._study.optimize(objective, n_trials=self.n_trials)
            
            return self._study.best_params
            
        except ImportError:
            return self._default_cnn_params()
    
    async def tune_ppo(self, train_fn) -> Dict[str, Any]:
        """Tune PPO RL hyperparameters."""
        try:
            import optuna
            
            def objective(trial):
                params = {
                    "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
                    "gamma": trial.suggest_float("gamma", 0.9, 0.999),
                    "clip_epsilon": trial.suggest_float("clip_epsilon", 0.1, 0.3),
                    "gae_lambda": trial.suggest_float("gae_lambda", 0.9, 0.99),
                    "entropy_coef": trial.suggest_float("entropy_coef", 0.001, 0.1, log=True),
                    "n_steps": trial.suggest_categorical("n_steps", [128, 256, 512, 1024]),
                }
                return -train_fn(params)  # Negative because we want to maximize reward
            
            self._study = optuna.create_study(direction="maximize")
            self._study.optimize(objective, n_trials=self.n_trials)
            
            return self._study.best_params
            
        except ImportError:
            return self._default_ppo_params()
    
    def _default_ann_params(self) -> Dict[str, Any]:
        return {
            "learning_rate": 0.001,
            "hidden_dim_1": 64,
            "hidden_dim_2": 32,
            "dropout": 0.2,
            "batch_size": 32,
            "epochs": 50
        }
    
    def _default_cnn_params(self) -> Dict[str, Any]:
        return {
            "learning_rate": 0.001,
            "conv_channels_1": 32,
            "conv_channels_2": 64,
            "conv_channels_3": 128,
            "kernel_size": 3,
            "dropout": 0.5,
            "batch_size": 16
        }
    
    def _default_ppo_params(self) -> Dict[str, Any]:
        return {
            "learning_rate": 0.0003,
            "gamma": 0.99,
            "clip_epsilon": 0.2,
            "gae_lambda": 0.95,
            "entropy_coef": 0.01,
            "n_steps": 256
        }


# =============================================================================
# METRICS TRACKER (with Supabase persistence)
# =============================================================================

class MetricsTracker:
    """
    Track and persist metrics to Supabase.
    
    Tables required in Supabase:
    - model_metrics: id, model_name, model_type, metrics, hyperparameters, timestamp
    - embodied_metrics: id, problem_data, solution_data, improvements, timestamp
    """
    
    def __init__(self, supabase_client=None):
        self._supabase = supabase_client
        self._model_metrics: Dict[str, List[ModelMetrics]] = {}
        self._embodied_history: List[EmbodiedAgentMetrics] = []
    
    async def initialize(self):
        """Initialize Supabase connection if available."""
        from config import settings
        
        if settings.supabase_url and settings.supabase_key:
            try:
                from supabase import create_client
                self._supabase = create_client(settings.supabase_url, settings.supabase_key)
                logger.info("Supabase connected for metrics persistence")
            except Exception as e:
                logger.warning("Supabase connection failed", error=str(e))
    
    def record_model_metrics(self, metrics: ModelMetrics) -> None:
        """Record metrics for a model."""
        if metrics.model_name not in self._model_metrics:
            self._model_metrics[metrics.model_name] = []
        
        self._model_metrics[metrics.model_name].append(metrics)
        
        # Persist to Supabase
        if self._supabase:
            try:
                self._supabase.table("model_metrics").insert({
                    "model_name": metrics.model_name,
                    "model_type": metrics.model_type,
                    "metrics": json.dumps(metrics.metrics),
                    "hyperparameters": json.dumps(metrics.hyperparameters),
                    "training_samples": metrics.training_samples,
                    "inference_time_ms": metrics.inference_time_ms,
                    "timestamp": metrics.timestamp.isoformat()
                }).execute()
            except Exception as e:
                logger.warning("Failed to persist metrics", error=str(e))
    
    def record_embodied_metrics(self, metrics: EmbodiedAgentMetrics) -> None:
        """Record embodied agent comparison metrics."""
        self._embodied_history.append(metrics)
        
        if self._supabase:
            try:
                data = metrics.to_dict()
                self._supabase.table("embodied_metrics").insert({
                    "problem_data": json.dumps(data["problem_mode"]),
                    "solution_data": json.dumps(data["solution_mode"]),
                    "improvements": json.dumps(data["improvements"]),
                    "timestamp": metrics.timestamp.isoformat()
                }).execute()
            except Exception as e:
                logger.warning("Failed to persist embodied metrics", error=str(e))
    
    def get_model_metrics(self, model_name: str) -> List[ModelMetrics]:
        """Get metrics history for a model."""
        return self._model_metrics.get(model_name, [])
    
    def get_latest_model_metrics(self, model_name: str) -> Optional[ModelMetrics]:
        """Get latest metrics for a model."""
        history = self._model_metrics.get(model_name, [])
        return history[-1] if history else None
    
    def get_all_model_summaries(self) -> Dict[str, Dict]:
        """Get summary of all model metrics for frontend display."""
        summaries = {}
        
        for model_name, history in self._model_metrics.items():
            if not history:
                continue
            
            latest = history[-1]
            summaries[model_name] = {
                "model_type": latest.model_type,
                "latest_metrics": latest.metrics,
                "hyperparameters": latest.hyperparameters,
                "training_samples": latest.training_samples,
                "inference_time_ms": latest.inference_time_ms,
                "history_count": len(history)
            }
        
        return summaries
    
    def get_embodied_summary(self) -> Optional[Dict]:
        """Get latest embodied agent comparison for frontend."""
        if not self._embodied_history:
            return None
        return self._embodied_history[-1].to_dict()


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_metrics_tracker: Optional[MetricsTracker] = None


async def get_metrics_tracker() -> MetricsTracker:
    """Get or create global metrics tracker."""
    global _metrics_tracker
    if _metrics_tracker is None:
        _metrics_tracker = MetricsTracker()
        await _metrics_tracker.initialize()
    return _metrics_tracker
