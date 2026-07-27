"""
State Manager for AI Embodied Agent
Manages real-time system state including robots, stages, and supply chain.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional
from collections import deque

import structlog
from cachetools import TTLCache

from config import settings
from api.schemas import (
    RobotState, StageState, SupplyChainState,
    Position, RobotStatus, StageStatus, SupplierStatus,
    DemandForecast, SupplierState, InventoryState,
    SystemMetrics, ExternalContext, AlertSeverity
)

logger = structlog.get_logger(__name__)


class StateManager:
    """
    Manages the real-time state of the manufacturing system.
    
    In simulation mode, generates realistic mock data.
    In production mode, aggregates data from MQTT, video, and API sources.
    """
    
    def __init__(self):
        self.is_initialized = False
        self._robots: dict[int, dict] = {}
        self._stages: dict[int, dict] = {}
        self._supply_chain: dict = {}
        self._metrics: dict = {}
        self._external_context: dict = {}
        self._alerts: list[dict] = []
        self._mode: str = "normal"
        
        # State history for LSTM predictions (last 10 minutes at 1Hz)
        self._state_history: deque = deque(maxlen=600)
        
        # Cache for performance
        self._state_cache = TTLCache(maxsize=100, ttl=0.5)  # 500ms TTL
        
        # Simulation task
        self._simulation_task: Optional[asyncio.Task] = None
        
        # Warehouse dimensions (meters)
        self.warehouse_width = 100.0
        self.warehouse_height = 60.0
        
    async def initialize(self) -> None:
        """Initialize the state manager."""
        logger.info("Initializing state manager")
        
        # Initialize robots
        for i in range(1, settings.mock_robot_count + 1):
            self._robots[i] = self._create_initial_robot(i)
        
        # Initialize stages
        stage_names = [
            "Receiving", "Inspection", "Sorting", "Assembly Line A",
            "Assembly Line B", "Quality Check", "Packaging", 
            "Labeling", "Dispatch Prep", "Shipping"
        ]
        for i in range(1, min(settings.mock_stage_count + 1, len(stage_names) + 1)):
            self._stages[i] = self._create_initial_stage(i, stage_names[i-1])
        
        # Initialize supply chain
        self._supply_chain = self._create_initial_supply_chain()
        
        # Initialize metrics
        self._metrics = self._calculate_metrics()
        
        # Initialize external context
        self._external_context = {
            "weather": {"temperature": 22, "humidity": 45, "conditions": "clear"},
            "grid_carbon_intensity": 320,  # gCO2/kWh
            "renewable_percentage": 35,
            "electricity_price": 0.12
        }
        
        self.is_initialized = True
        logger.info("State manager initialized", 
                   robots=len(self._robots), 
                   stages=len(self._stages))
    
    def _create_initial_robot(self, robot_id: int) -> dict:
        """Create initial state for a robot."""
        # Stage 28 de-mock (G-082): DETERMINISTIC id-derived initial state (reproducible; no RNG). This is an
        # explicitly-labelled simulation demo layer; the real live state is the SimWorld runtime + /api/simulation.
        _tasks = ["Transporting to Stage 3", "Picking items", "Returning to base", "Charging", "Waiting for task", None]
        _statuses = [st.value for st in RobotStatus]
        return {
            "id": robot_id,
            "position": {
                "x": 5.0 + (robot_id * 7) % max(1, int(self.warehouse_width - 10)),
                "y": 5.0 + (robot_id * 11) % max(1, int(self.warehouse_height - 10))
            },
            "battery": 30.0 + (robot_id * 13) % 70,
            "speed": (robot_id % 3) * 0.5,
            "task": _tasks[robot_id % len(_tasks)],
            "destination": None,
            "status": _statuses[robot_id % len(_statuses)],
            "task_queue_length": robot_id % 6,
            "last_update": datetime.utcnow().isoformat()
        }
    
    def _create_initial_stage(self, stage_id: int, name: str) -> dict:
        """Create initial state for a manufacturing stage."""
        # Stage 28 de-mock (G-082): DETERMINISTIC id-derived initial stage state (no RNG).
        _statuses = [st.value for st in StageStatus]
        return {
            "id": stage_id,
            "name": name,
            "queue_depth": (stage_id * 5) % 26,
            "throughput": 50.0 + (stage_id * 17) % 100,
            "target_throughput": 100.0,
            "cycle_time": 30.0 + (stage_id * 13) % 90,
            "defect_rate": (stage_id % 5),
            "energy_consumption": 5.0 + (stage_id * 3) % 20,
            "status": _statuses[stage_id % len(_statuses)],
            "utilization": 50.0 + (stage_id * 9) % 45,
            "idle_time": (stage_id * 30) % 300,
            "last_update": datetime.utcnow().isoformat()
        }
    
    def _create_initial_supply_chain(self) -> dict:
        """Create initial supply chain state."""
        # G-036 (Stage 30): the 7-day forecast is now SERVED by the real demand-forecast service — it serves the
        # trained LSTM / empirical stats when a real history flows, and returns an HONESTLY LABELLED planning baseline
        # (no fabricated per-day confidence) at build time. Real hourly-demand re-fit = G-035 (buyer-blocked).
        from services.demand_forecast_service import seven_day_forecast
        forecast_result = seven_day_forecast()      # no live feed at init -> honest labelled baseline
        demand_forecast = forecast_result["forecast"]

        # Suppliers
        suppliers = [
            {
                "id": 1,
                "name": "Alpha Components",
                "status": SupplierStatus.ON_TIME.value,
                "lead_time_days": 3.5,
                "reliability_score": 0.92,
                "pending_orders": 5,
                "carbon_footprint_kg_per_unit": 0.8
            },
            {
                "id": 2,
                "name": "Beta Materials",
                "status": SupplierStatus.DELAYED.value,
                "lead_time_days": 5.0,
                "reliability_score": 0.78,
                "pending_orders": 3,
                "carbon_footprint_kg_per_unit": 1.2
            },
            {
                "id": 3,
                "name": "Gamma Electronics",
                "status": SupplierStatus.ON_TIME.value,
                "lead_time_days": 2.0,
                "reliability_score": 0.95,
                "pending_orders": 8,
                "carbon_footprint_kg_per_unit": 0.5
            }
        ]
        
        # Inventory
        inventory = [
            {
                "material_id": 1,
                "material_name": "Circuit Boards",
                "current_stock": 1500,
                "min_stock": 500,
                "max_stock": 3000,
                "days_of_supply": 5.2,
                "reorder_point": 800,
                "status": "healthy"
            },
            {
                "material_id": 2,
                "material_name": "Enclosures",
                "current_stock": 320,
                "min_stock": 400,
                "max_stock": 2000,
                "days_of_supply": 1.8,
                "reorder_point": 600,
                "status": "low"
            },
            {
                "material_id": 3,
                "material_name": "Connectors",
                "current_stock": 8500,
                "min_stock": 2000,
                "max_stock": 15000,
                "days_of_supply": 12.0,
                "reorder_point": 4000,
                "status": "healthy"
            }
        ]
        
        return {
            "demand_forecast": demand_forecast,
            "demand_forecast_source": forecast_result["source"],   # G-036: honest provenance of the forecast
            "demand_forecast_served": forecast_result["served"],
            "demand_forecast_note": forecast_result.get("note"),
            "suppliers": suppliers,
            "inventory": inventory,
            "last_update": datetime.utcnow().isoformat()
        }
    
    def _calculate_metrics(self) -> dict:
        """Calculate system-wide metrics."""
        active_robots = sum(1 for r in self._robots.values() 
                          if r["status"] != RobotStatus.ERROR.value)
        active_stages = sum(1 for s in self._stages.values() 
                          if s["status"] != StageStatus.OFFLINE.value)
        
        total_throughput = sum(s["throughput"] for s in self._stages.values())
        total_energy = sum(s["energy_consumption"] for s in self._stages.values())
        avg_quality = 100 - (sum(s["defect_rate"] for s in self._stages.values()) / 
                            max(len(self._stages), 1))
        
        # Find bottleneck (highest queue depth)
        bottleneck = max(self._stages.values(), key=lambda s: s["queue_depth"], default=None)
        
        return {
            "overall_throughput": total_throughput,
            "overall_quality": avg_quality,
            "overall_energy": total_energy,
            "carbon_footprint": total_energy * 0.32,  # kg CO2/kWh
            "system_uptime": 99.5,
            "active_robots": active_robots,
            "active_stages": active_stages,
            "bottleneck_stage": bottleneck["id"] if bottleneck else None,
            "efficiency_score": min(100, (total_throughput / 1000) * 100)
        }
    
    async def start_simulation(self) -> None:
        """Start the simulation data generation loop."""
        logger.info("Starting simulation mode")
        self._simulation_task = asyncio.create_task(self._simulation_loop())
    
    async def _simulation_loop(self) -> None:
        """Background task to update simulated data."""
        while True:
            try:
                await self._update_simulated_state()
                await asyncio.sleep(1.0)  # Update every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Simulation error", error=str(e))
                await asyncio.sleep(1.0)
    
    async def _update_simulated_state(self) -> None:
        """Update simulated state with realistic changes."""
        now = datetime.utcnow()
        
        # Stage 28 de-mock (G-082): DETERMINISTIC step-based drift (no RNG). `_step` advances each tick.
        self._step = getattr(self, "_step", 0) + 1
        for robot_id, robot in self._robots.items():
            import math as _m
            robot["position"]["x"] += 0.4 * _m.sin((self._step + robot_id) * 0.3)
            robot["position"]["y"] += 0.4 * _m.cos((self._step + robot_id) * 0.3)
            
            # Keep within bounds
            robot["position"]["x"] = max(0, min(self.warehouse_width, robot["position"]["x"]))
            robot["position"]["y"] = max(0, min(self.warehouse_height, robot["position"]["y"]))
            
            # Update battery (drain or charge)
            if robot["status"] == RobotStatus.CHARGING.value:
                robot["battery"] = min(100, robot["battery"] + 0.5)
            else:
                robot["battery"] = max(0, robot["battery"] - 0.1)
            
            # Check battery warnings
            if robot["battery"] < 15:
                robot["status"] = RobotStatus.WARNING.value
            elif robot["battery"] < 5:
                robot["status"] = RobotStatus.ERROR.value
            elif robot["status"] in [RobotStatus.WARNING.value, RobotStatus.ERROR.value] and robot["battery"] > 20:
                robot["status"] = RobotStatus.IDLE.value
            
            robot["speed"] = (0.5 + (robot_id % 3) * 0.5) if robot["status"] == RobotStatus.WORKING.value else 0
            robot["last_update"] = now.isoformat()
        
        # Stage 28 de-mock (G-082): DETERMINISTIC step-based fluctuation (no RNG).
        for stage_id, stage in self._stages.items():
            import math as _m
            _o = _m.sin((self._step + stage_id) * 0.25)
            stage["queue_depth"] = max(0, stage["queue_depth"] + (1 if _o > 0.5 else (-1 if _o < -0.5 else 0)))
            stage["throughput"] = max(0, stage["throughput"] + 4 * _o)
            stage["energy_consumption"] = max(1, stage["energy_consumption"] + _o)
            
            # Update status based on queue
            if stage["queue_depth"] > 20:
                stage["status"] = StageStatus.BOTTLENECK.value
            elif stage["queue_depth"] > 15:
                stage["status"] = StageStatus.WARNING.value
            else:
                stage["status"] = StageStatus.NORMAL.value
            
            stage["last_update"] = now.isoformat()
        
        # Update metrics
        self._metrics = self._calculate_metrics()
        
        # Stage 28 de-mock (G-082): DETERMINISTIC periodic alert (every 20 steps) — no RNG probability.
        if self._step % 20 == 0:
            await self._generate_random_alert()
        
        # Store in history
        self._state_history.append({
            "timestamp": now.isoformat(),
            "robots": {k: v.copy() for k, v in self._robots.items()},
            "stages": {k: v.copy() for k, v in self._stages.items()},
            "metrics": self._metrics.copy()
        })
        
        # Clear cache to force fresh data
        self._state_cache.clear()
    
    async def _generate_random_alert(self) -> None:
        """Generate a random alert for simulation."""
        alert_types = [
            {
                "severity": AlertSeverity.INFO.value,
                "title": "Optimization Complete",
                "message": "Route optimization saved 3% energy",
                "source": "system"
            },
            {
                "severity": AlertSeverity.WARNING.value,
                "title": "High Queue Depth",
                "message": "Stage 4 queue exceeding threshold",
                "source": "stage"
            },
            {
                "severity": AlertSeverity.WARNING.value,
                "title": "Low Battery",
                "message": "Robot 5 battery below 20%",
                "source": "robot"
            },
            {
                "severity": AlertSeverity.CRITICAL.value,
                "title": "Supplier Delay",
                "message": "Beta Materials shipment delayed 2 days",
                "source": "supply_chain"
            }
        ]
        
        alert = dict(alert_types[(getattr(self, "_step", 0) // 20) % len(alert_types)])  # deterministic rotation
        alert["id"] = str(uuid.uuid4())
        alert["timestamp"] = datetime.utcnow().isoformat()
        alert["recommended_actions"] = ["Review system status", "Check related components"]
        alert["acknowledged"] = False
        
        self._alerts.insert(0, alert)
        
        # Keep only last 100 alerts
        if len(self._alerts) > 100:
            self._alerts = self._alerts[:100]
    
    async def get_current_state(
        self,
        include_robots: bool = True,
        include_stages: bool = True,
        include_supply_chain: bool = True,
        include_metrics: bool = True
    ) -> dict:
        """Get the current system state."""
        cache_key = f"{include_robots}:{include_stages}:{include_supply_chain}:{include_metrics}"
        
        if cache_key in self._state_cache:
            return self._state_cache[cache_key]
        
        state = {
            "timestamp": datetime.utcnow().isoformat(),
            "mode": self._mode
        }
        
        if include_robots:
            state["robots"] = list(self._robots.values())
        
        if include_stages:
            state["stages"] = list(self._stages.values())
        
        if include_supply_chain:
            state["supply_chain"] = self._supply_chain
        
        if include_metrics:
            state["metrics"] = self._metrics
            state["external_context"] = self._external_context
        
        state["alerts"] = [a for a in self._alerts if not a.get("acknowledged", False)][:10]
        
        self._state_cache[cache_key] = state
        return state
    
    async def get_robot_state(self, robot_id: int) -> Optional[dict]:
        """Get state of a specific robot."""
        return self._robots.get(robot_id)
    
    async def get_stage_state(self, stage_id: int) -> Optional[dict]:
        """Get state of a specific stage."""
        return self._stages.get(stage_id)
    
    async def get_state_history(self, minutes: int = 10) -> list[dict]:
        """Get state history for the last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        history = []
        
        for state in self._state_history:
            try:
                ts = datetime.fromisoformat(state["timestamp"].replace("Z", "+00:00"))
                if ts >= cutoff:
                    history.append(state)
            except Exception:
                continue
        
        return history
    
    async def update_robot_state(self, robot_id: int, updates: dict) -> bool:
        """Update state of a specific robot."""
        if robot_id not in self._robots:
            return False
        
        self._robots[robot_id].update(updates)
        self._robots[robot_id]["last_update"] = datetime.utcnow().isoformat()
        self._state_cache.clear()
        return True
    
    async def update_stage_state(self, stage_id: int, updates: dict) -> bool:
        """Update state of a specific stage."""
        if stage_id not in self._stages:
            return False
        
        self._stages[stage_id].update(updates)
        self._stages[stage_id]["last_update"] = datetime.utcnow().isoformat()
        self._state_cache.clear()
        return True
    
    async def get_alerts(
        self,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 50
    ) -> list[dict]:
        """Get system alerts with optional filtering."""
        alerts = self._alerts
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.get("acknowledged", False) == acknowledged]
        
        return alerts[:limit]
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert by ID."""
        for alert in self._alerts:
            if alert.get("id") == alert_id:
                alert["acknowledged"] = True
                return True
        return False
    
    async def set_mode(self, mode: str) -> None:
        """Set the system operation mode."""
        self._mode = mode
        logger.info("System mode changed", mode=mode)
    
    async def shutdown(self) -> None:
        """Shutdown the state manager."""
        if self._simulation_task:
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("State manager shutdown complete")
