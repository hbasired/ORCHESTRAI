"""
Pydantic Schemas for API Request/Response Models
Defines all data structures for the AI Embodied Agent API.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Enums
# ============================================================================

class RobotStatus(str, Enum):
    """Robot operational status."""
    IDLE = "idle"
    WORKING = "working"
    CHARGING = "charging"
    WARNING = "warning"
    ERROR = "error"


class StageStatus(str, Enum):
    """Manufacturing stage status."""
    NORMAL = "normal"
    WARNING = "warning"
    BOTTLENECK = "bottleneck"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


class SupplierStatus(str, Enum):
    """Supplier delivery status."""
    ON_TIME = "on_time"
    DELAYED = "delayed"
    AT_RISK = "at_risk"
    CONFIRMED = "confirmed"


class DecisionType(str, Enum):
    """Type of AI decision."""
    ROBOT_ROUTING = "robot_routing"
    STAGE_ADJUSTMENT = "stage_adjustment"
    SUPPLIER_ORDER = "supplier_order"
    SYSTEM_MODE = "system_mode"
    MULTI_ACTION = "multi_action"


class ActionType(str, Enum):
    """Specific action types."""
    NAVIGATE_TO = "navigate_to"
    SET_SPEED = "set_speed"
    CHARGE = "charge"
    REDUCE_THROUGHPUT = "reduce_throughput"
    INCREASE_THROUGHPUT = "increase_throughput"
    PAUSE_STAGE = "pause_stage"
    RESUME_STAGE = "resume_stage"
    ADVANCE_ORDER = "advance_order"
    DELAY_ORDER = "delay_order"
    EMERGENCY_PROCUREMENT = "emergency_procurement"
    SWITCH_MODE = "switch_mode"


class SystemMode(str, Enum):
    """Overall system operation mode."""
    NORMAL = "normal"
    EFFICIENCY = "efficiency"
    EMERGENCY = "emergency"
    SUSTAINABILITY = "sustainability"
    SIMULATION = "simulation"


class ExplanationType(str, Enum):
    """Type of decision explanation."""
    NATURAL_LANGUAGE = "natural_language"
    FEATURE_IMPORTANCE = "feature_importance"
    ATTENTION_HEATMAP = "attention_heatmap"
    COUNTERFACTUAL = "counterfactual"


# ============================================================================
# Robot Models
# ============================================================================

class Position(BaseModel):
    """2D position in warehouse."""
    x: float = Field(..., description="X coordinate in meters")
    y: float = Field(..., description="Y coordinate in meters")


class RobotState(BaseModel):
    """Current state of a single robot."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique robot identifier")
    position: Position = Field(..., description="Current position")
    battery: float = Field(..., ge=0, le=100, description="Battery percentage")
    speed: float = Field(default=0.0, ge=0, description="Current speed in m/s")
    task: Optional[str] = Field(default=None, description="Current task description")
    destination: Optional[Position] = Field(default=None, description="Target destination")
    status: RobotStatus = Field(default=RobotStatus.IDLE, description="Operational status")
    task_queue_length: int = Field(default=0, ge=0, description="Number of pending tasks")
    last_update: datetime = Field(default_factory=datetime.utcnow)


class RobotDetection(BaseModel):
    """Robot detection from vision model."""
    robot_id: int
    position: Position
    confidence: float = Field(..., ge=0, le=1)
    bounding_box: list[float] = Field(..., min_length=4, max_length=4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Stage Models
# ============================================================================

class StageState(BaseModel):
    """Current state of a manufacturing stage."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Stage identifier")
    name: str = Field(..., description="Stage name")
    queue_depth: int = Field(default=0, ge=0, description="Items in queue")
    throughput: float = Field(default=0.0, ge=0, description="Units per hour")
    target_throughput: float = Field(default=100.0, ge=0, description="Target throughput")
    cycle_time: float = Field(default=0.0, ge=0, description="Seconds per unit")
    defect_rate: float = Field(default=0.0, ge=0, le=100, description="Defect percentage")
    energy_consumption: float = Field(default=0.0, ge=0, description="kW current draw")
    status: StageStatus = Field(default=StageStatus.NORMAL)
    utilization: float = Field(default=0.0, ge=0, le=100, description="Capacity utilization %")
    idle_time: float = Field(default=0.0, ge=0, description="Idle time in seconds")
    last_update: datetime = Field(default_factory=datetime.utcnow)


class StageMetrics(BaseModel):
    """Aggregated metrics for a stage over time."""
    stage_id: int
    period_start: datetime
    period_end: datetime
    total_units: int
    avg_throughput: float
    avg_cycle_time: float
    total_energy_kwh: float
    total_defects: int
    uptime_percentage: float


# ============================================================================
# Supply Chain Models
# ============================================================================

class DemandForecast(BaseModel):
    """Demand forecast for a time period."""
    date: datetime
    predicted_demand: float
    lower_bound: float
    upper_bound: float
    confidence: float = Field(..., ge=0, le=1)


class SupplierState(BaseModel):
    """Current state of a supplier."""
    id: int
    name: str
    status: SupplierStatus
    lead_time_days: float
    reliability_score: float = Field(..., ge=0, le=1)
    pending_orders: int
    carbon_footprint_kg_per_unit: float


class InventoryState(BaseModel):
    """Current inventory levels."""
    material_id: int
    material_name: str
    current_stock: int
    min_stock: int
    max_stock: int
    days_of_supply: float
    reorder_point: int
    status: str  # "healthy", "low", "critical"


class SupplyChainState(BaseModel):
    """Complete supply chain state."""
    demand_forecast: list[DemandForecast] = Field(default_factory=list)
    suppliers: list[SupplierState] = Field(default_factory=list)
    inventory: list[InventoryState] = Field(default_factory=list)
    last_update: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# System State Models
# ============================================================================

class SystemMetrics(BaseModel):
    """Overall system KPIs."""
    overall_throughput: float = Field(default=0.0, description="Units per hour")
    overall_quality: float = Field(default=0.0, ge=0, le=100, description="Quality rate %")
    overall_energy: float = Field(default=0.0, description="Total kW consumption")
    carbon_footprint: float = Field(default=0.0, description="kg CO2 per hour")
    system_uptime: float = Field(default=100.0, ge=0, le=100, description="Uptime %")
    active_robots: int = Field(default=0, ge=0)
    active_stages: int = Field(default=0, ge=0)
    bottleneck_stage: Optional[int] = Field(default=None)
    efficiency_score: float = Field(default=0.0, ge=0, le=100)


class ExternalContext(BaseModel):
    """External context from APIs."""
    weather: Optional[dict] = Field(default=None)
    grid_carbon_intensity: Optional[float] = Field(default=None, description="gCO2/kWh")
    renewable_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    electricity_price: Optional[float] = Field(default=None, description="$/kWh")


class SystemStateResponse(BaseModel):
    """Complete system state response."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mode: SystemMode = Field(default=SystemMode.NORMAL)
    robots: list[RobotState] = Field(default_factory=list)
    stages: list[StageState] = Field(default_factory=list)
    supply_chain: SupplyChainState = Field(default_factory=SupplyChainState)
    metrics: SystemMetrics = Field(default_factory=SystemMetrics)
    external_context: ExternalContext = Field(default_factory=ExternalContext)
    alerts: list[dict] = Field(default_factory=list)


# ============================================================================
# Decision Models
# ============================================================================

class Action(BaseModel):
    """Single action in a decision."""
    target_type: str = Field(..., description="robot, stage, supplier, system")
    target_id: Optional[int] = Field(default=None)
    action: ActionType
    value: Optional[Any] = Field(default=None)
    destination: Optional[Position] = Field(default=None)


class DecisionRequest(BaseModel):
    """Request for AI decision."""
    priority: Optional[str] = Field(default="balanced", description="throughput, energy, carbon, balanced")
    constraints: list[str] = Field(default_factory=list, description="Constraints to apply")
    force_decision: bool = Field(default=False, description="Force decision even if not needed")
    custom_weights: Optional[dict[str, float]] = Field(default=None)


class ExpectedImpact(BaseModel):
    """Expected impact of a decision."""
    throughput_change: float = Field(default=0.0, description="Percentage change")
    energy_change: float = Field(default=0.0, description="Percentage change")
    carbon_change: float = Field(default=0.0, description="Percentage change")
    quality_change: float = Field(default=0.0, description="Percentage change")
    confidence: float = Field(default=0.0, ge=0, le=1)


class DecisionResponse(BaseModel):
    """AI decision response."""
    decision_id: str = Field(..., description="Unique decision identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    decision_type: DecisionType
    actions: list[Action] = Field(default_factory=list)
    reasoning: str = Field(..., description="Natural language explanation")
    confidence: float = Field(..., ge=0, le=1)
    expected_impact: ExpectedImpact = Field(default_factory=ExpectedImpact)
    requires_approval: bool = Field(default=False)
    alternative_actions: list[Action] = Field(default_factory=list)


# ============================================================================
# Prediction Models
# ============================================================================

class PredictionRequest(BaseModel):
    """Request for system state prediction."""
    horizon_minutes: int = Field(default=30, ge=5, le=60)
    include_uncertainty: bool = Field(default=True)


class PredictedState(BaseModel):
    """Predicted system state at a future time."""
    timestamp: datetime
    horizon_minutes: int
    robots: list[RobotState]
    stages: list[StageState]
    metrics: SystemMetrics
    confidence: float = Field(..., ge=0, le=1)
    uncertainty_bounds: Optional[dict] = Field(default=None)


class PredictionResponse(BaseModel):
    """Prediction response with multiple horizons."""
    request_timestamp: datetime = Field(default_factory=datetime.utcnow)
    predictions: list[PredictedState] = Field(default_factory=list)
    model_version: str = Field(default="lstm-v1")


# ============================================================================
# Explainability Models
# ============================================================================

class FeatureImportance(BaseModel):
    """SHAP-based feature importance."""
    feature_name: str
    feature_value: float
    importance_score: float
    contribution_direction: str  # "positive" or "negative"


class AttentionWeight(BaseModel):
    """Attention weight for a component."""
    component_type: str  # "robot", "stage", "supplier"
    component_id: int
    attention_score: float = Field(..., ge=0, le=1)


class CounterfactualScenario(BaseModel):
    """Counterfactual analysis scenario."""
    scenario_name: str
    changed_factors: dict[str, Any]
    predicted_outcome: dict
    outcome_difference: dict


class ExplainabilityResponse(BaseModel):
    """Complete explanation for a decision."""
    decision_id: str
    explanation_types: list[ExplanationType]
    natural_language: str = Field(..., description="Human-readable explanation")
    feature_importance: list[FeatureImportance] = Field(default_factory=list)
    attention_weights: list[AttentionWeight] = Field(default_factory=list)
    attention_heatmap_url: Optional[str] = Field(default=None)
    counterfactuals: list[CounterfactualScenario] = Field(default_factory=list)
    key_factors: list[str] = Field(default_factory=list)


# ============================================================================
# Override Models
# ============================================================================

class OverrideRequest(BaseModel):
    """Human override request."""
    decision_id: str = Field(..., description="ID of decision to override")
    action: str = Field(..., description="accept, reject, modify")
    reason: str = Field(..., min_length=10, description="Reason for override")
    modified_actions: Optional[list[Action]] = Field(default=None)
    operator_id: Optional[str] = Field(default=None)


class OverrideResponse(BaseModel):
    """Override response."""
    override_id: str
    decision_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str
    status: str  # "applied", "rejected", "pending"
    feedback_recorded: bool


# ============================================================================
# Optimization Weights
# ============================================================================

class OptimizationWeights(BaseModel):
    """Weights for multi-objective optimization."""
    throughput: float = Field(default=0.5, ge=0, le=1)
    energy: float = Field(default=0.2, ge=0, le=1)
    carbon: float = Field(default=0.2, ge=0, le=1)
    quality: float = Field(default=0.1, ge=0, le=1)
    
    def normalize(self) -> "OptimizationWeights":
        """Normalize weights to sum to 1."""
        total = self.throughput + self.energy + self.carbon + self.quality
        if total > 0:
            return OptimizationWeights(
                throughput=self.throughput / total,
                energy=self.energy / total,
                carbon=self.carbon / total,
                quality=self.quality / total
            )
        return self


# ============================================================================
# Alert Models
# ============================================================================

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(BaseModel):
    """System alert."""
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: AlertSeverity
    title: str
    message: str
    source: str  # "robot", "stage", "supply_chain", "system"
    source_id: Optional[int] = None
    recommended_actions: list[str] = Field(default_factory=list)
    acknowledged: bool = False
