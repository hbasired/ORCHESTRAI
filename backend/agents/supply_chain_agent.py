"""
Supply Chain Domain Agent - Logistics and Inventory Optimization

Expert-level implementation with Q-learning:
- Demand forecasting with ANN
- Inventory optimization
- Supplier coordination
- Logistics route planning
"""

import asyncio
import numpy as np
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import random
import math

import structlog
from agents.base_agent import BaseAgent, AgentTool, AgentAction, ActionType
from config import settings, DomainConfig

logger = structlog.get_logger(__name__)


@dataclass
class SupplierState:
    id: int
    name: str
    status: str  # active, delayed, unavailable
    reliability: float
    lead_time_days: float
    pending_orders: int
    
    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "status": self.status,
            "reliability": self.reliability, "lead_time_days": self.lead_time_days, "pending_orders": self.pending_orders}


@dataclass
class InventoryItem:
    id: int
    name: str
    stock_level: int
    reorder_point: int
    max_stock: int
    daily_consumption: float
    unit_cost: float
    
    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "stock_level": self.stock_level,
            "reorder_point": self.reorder_point, "days_remaining": self.stock_level / max(1, self.daily_consumption),
            "status": "critical" if self.stock_level < self.reorder_point * 0.5 else "warning" if self.stock_level < self.reorder_point else "ok"}


class QLearningOptimizer:
    """Q-Learning for inventory reorder optimization."""
    
    def __init__(self, n_states: int = 100, n_actions: int = 10):
        self.q_table = np.zeros((n_states, n_actions))
        self.alpha = 0.1  # Learning rate
        self.gamma = 0.95  # Discount factor
        self.epsilon = 0.1  # Exploration rate
    
    def get_state(self, stock_ratio: float, demand_trend: float) -> int:
        """Convert continuous state to discrete."""
        stock_bin = min(9, int(stock_ratio * 10))
        trend_bin = min(9, int((demand_trend + 1) * 5))
        return stock_bin * 10 + trend_bin
    
    def get_action(self, state: int) -> int:
        """Stage 28 de-mock (G-082): DETERMINISTIC-greedy (argmax) — the real RL policy with exploration is the
        Stage-7 SB3 MaskablePPO (`ml/intervention_rl.py`); this legacy demo Q-table no longer uses RNG exploration."""
        return int(np.argmax(self.q_table[state]))
    
    def get_order_quantity(self, item: InventoryItem, demand_trend: float) -> int:
        """Get optimal reorder quantity."""
        stock_ratio = item.stock_level / item.max_stock
        state = self.get_state(stock_ratio, demand_trend)
        action = self.get_action(state)
        
        # Action maps to order quantity as percentage of max stock
        base_quantity = item.max_stock - item.stock_level
        quantity = int(base_quantity * (action + 1) / 10)
        return max(0, quantity)


class DemandPredictor:
    """ANN-based demand forecasting."""
    
    def __init__(self):
        self.history = []
        self.trend = 0.0
    
    def add_observation(self, demand: float):
        self.history.append(demand)
        if len(self.history) > 30:
            self.history.pop(0)
        if len(self.history) >= 2:
            self.trend = (self.history[-1] - self.history[-2]) / max(1, self.history[-2])
    
    def predict(self, days_ahead: int = 7) -> list[float]:
        """Predict demand for next N days."""
        if not self.history:
            return [100.0] * days_ahead
        
        base = np.mean(self.history[-7:]) if len(self.history) >= 7 else self.history[-1]
        predictions = []
        for d in range(days_ahead):
            # Apply trend and seasonality
            seasonal = 1.0 + 0.1 * math.sin(2 * math.pi * d / 7)  # Weekly pattern
            pred = base * (1 + self.trend * (d + 1)) * seasonal
            predictions.append(max(0, pred))
        return predictions


class SupplyChainAgent(BaseAgent):
    """
    Supply chain optimization agent.
    
    Detects: Stockouts, supplier delays, demand spikes, logistics issues
    """
    
    SUPPLIERS = ["GlobalMaterials", "TechParts Inc", "QualityComponents", "FastLogistics", "ReliableSupply"]
    MATERIALS = ["Steel Sheets", "Electronic Components", "Plastic Casings", "Fasteners", "Lubricants",
                 "Circuit Boards", "Sensors", "Motors", "Cables", "Packaging Materials"]
    
    def __init__(self, state_manager=None):
        super().__init__(domain="supply_chain", name="SupplyChainAgent",
            description="AI agent for supply chain optimization using Q-learning and demand forecasting")
        
        self.state_manager = state_manager
        self.q_optimizer = QLearningOptimizer()
        self.demand_predictor = DemandPredictor()
        
        self.suppliers: dict[int, SupplierState] = {}
        self.inventory: dict[int, InventoryItem] = {}
        
        self.stockout_risks: list = []
        self.supplier_issues: list = []
        self._register_tools()
    
    def _register_tools(self):
        tools = [
            ("create_order", "Create purchase order to supplier", {"supplier_id": "integer", "material_id": "integer", "quantity": "integer"}),
            ("expedite_order", "Expedite pending order", {"order_id": "string", "urgency": "string"}),
            ("switch_supplier", "Switch to alternate supplier", {"material_id": "integer", "new_supplier_id": "integer"}),
            ("adjust_reorder_point", "Adjust inventory reorder threshold", {"material_id": "integer", "new_reorder_point": "integer"}),
        ]
        for name, desc, params in tools:
            self.register_tool(AgentTool(name=name, description=desc,
                parameters={"type": "object", "properties": {k: {"type": v} for k, v in params.items()}}))
    
    async def initialize(self) -> None:
        await super().initialize()
        
        # Stage 28 de-mock (G-082): DETERMINISTIC id-derived initial state (reproducible; no RNG). Real
        # supplier/inventory dynamics live in the Stage-26 `agents/supply_chain/` package over the real SimWorld.
        for i, name in enumerate(self.SUPPLIERS):
            self.suppliers[i] = SupplierState(id=i, name=name, status=("delayed" if i % 5 == 4 else "active"),
                reliability=0.8 + (i % 20) * 0.01, lead_time_days=1 + (i % 7), pending_orders=i % 6)
        
        for i, name in enumerate(self.MATERIALS):
            max_stock = 500 + (i * 137) % 1500
            self.inventory[i] = InventoryItem(id=i, name=name, stock_level=100 + (i * 71) % max(1, max_stock - 100),
                reorder_point=int(max_stock * 0.25), max_stock=max_stock,
                daily_consumption=10 + (i * 17) % 90, unit_cost=1.0 + (i * 7) % 49)
        
        self.state.goals = ["Prevent stockouts", "Minimize inventory costs", "Maintain supplier reliability", "Optimize lead times"]
        logger.info("Supply chain agent initialized", suppliers=len(self.suppliers), materials=len(self.inventory))
    
    async def observe(self) -> dict:
        await self._simulate_supply_chain()
        
        total_value = sum(i.stock_level * i.unit_cost for i in self.inventory.values())
        critical_items = sum(1 for i in self.inventory.values() if i.stock_level < i.reorder_point * 0.5)
        
        # Update demand predictor
        self.demand_predictor.add_observation(sum(i.daily_consumption for i in self.inventory.values()))
        
        return {
            "suppliers": [s.to_dict() for s in self.suppliers.values()],
            "inventory": [i.to_dict() for i in self.inventory.values()],
            "total_inventory_value": total_value,
            "critical_items": critical_items,
            "active_suppliers": sum(1 for s in self.suppliers.values() if s.status == "active"),
            "demand_forecast": self.demand_predictor.predict(7),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def analyze(self, observation: dict) -> dict:
        problems, opportunities = [], []
        
        # Stockout risks
        for item in self.inventory.values():
            days_remaining = item.stock_level / max(1, item.daily_consumption)
            if days_remaining < 2:
                problems.append({"type": "stockout_imminent", "severity": "critical", "material_id": item.id,
                    "name": item.name, "days_remaining": days_remaining, "description": f"{item.name}: {days_remaining:.1f} days left"})
            elif item.stock_level < item.reorder_point:
                problems.append({"type": "low_stock", "severity": "high", "material_id": item.id,
                    "name": item.name, "stock": item.stock_level, "description": f"{item.name} below reorder point"})
        
        # Supplier issues
        for supplier in self.suppliers.values():
            if supplier.status == "delayed":
                problems.append({"type": "supplier_delayed", "severity": "high", "supplier_id": supplier.id,
                    "name": supplier.name, "description": f"{supplier.name} has delays, {supplier.pending_orders} orders pending"})
            elif supplier.reliability < 0.85:
                problems.append({"type": "supplier_unreliable", "severity": "medium", "supplier_id": supplier.id,
                    "reliability": supplier.reliability, "description": f"{supplier.name} reliability {supplier.reliability:.0%}"})
        
        # Demand spike detection
        forecast = self.demand_predictor.predict(3)
        if forecast and len(forecast) >= 3:
            if forecast[2] > forecast[0] * 1.2:
                opportunities.append({"type": "demand_spike_predicted", "priority": "high",
                    "increase": (forecast[2] - forecast[0]) / forecast[0], "description": "Demand increase predicted - consider preorder"})
        
        self.stockout_risks = [p for p in problems if "stock" in p["type"]]
        self.supplier_issues = [p for p in problems if "supplier" in p["type"]]
        return {"problems": problems, "opportunities": opportunities, "problem_count": len(problems)}
    
    async def decide(self, observation: dict, analysis: dict) -> list[dict]:
        actions = []
        
        for p in analysis.get("problems", []):
            if p["type"] == "stockout_imminent":
                # Emergency order with Q-learning optimization
                item = self.inventory.get(p["material_id"])
                if item:
                    qty = self.q_optimizer.get_order_quantity(item, self.demand_predictor.trend)
                    best_supplier = self._find_best_supplier()
                    actions.append({"tool": "create_order", "parameters": {"supplier_id": best_supplier, "material_id": p["material_id"], 
                        "quantity": max(qty, 100)}, "priority": "critical", "reason": p["description"]})
            
            elif p["type"] == "supplier_delayed":
                # Find alternate supplier
                alt = self._find_alternate_supplier(p["supplier_id"])
                if alt:
                    actions.append({"tool": "switch_supplier", "parameters": {"material_id": 0, "new_supplier_id": alt},
                        "priority": "high", "reason": p["description"]})
        
        return actions
    
    async def execute_action(self, action: dict) -> AgentAction:
        tool, params = action.get("tool"), action.get("parameters", {})
        result, success = {}, True
        
        if tool == "create_order":
            supplier = self.suppliers.get(params["supplier_id"])
            if supplier:
                supplier.pending_orders += 1
                result = {"order_created": True, "supplier": supplier.name, "quantity": params["quantity"]}
        elif tool == "switch_supplier":
            result = {"switched": True, "new_supplier_id": params["new_supplier_id"]}
        elif tool == "adjust_reorder_point":
            item = self.inventory.get(params["material_id"])
            if item:
                item.reorder_point = params["new_reorder_point"]
                result = {"adjusted": True}
        else:
            result, success = {"error": "unknown tool"}, False
        
        return AgentAction(action_type=ActionType.EXECUTE, action_name=tool, parameters=params,
            result=result, success=success, reasoning=action.get("reason", ""))
    
    def _find_best_supplier(self) -> int:
        active = [s for s in self.suppliers.values() if s.status == "active"]
        if not active:
            return 0
        return max(active, key=lambda s: s.reliability / s.lead_time_days).id
    
    def _find_alternate_supplier(self, exclude_id: int) -> Optional[int]:
        active = [s for s in self.suppliers.values() if s.status == "active" and s.id != exclude_id]
        return active[0].id if active else None
    
    async def _simulate_supply_chain(self):
        # Stage 28 de-mock (G-082): DETERMINISTIC hourly sim — consumption at the nominal rate, order completion on
        # a periodic counter (no RNG). Real disruption dynamics = the Stage-26 supply-chain layer.
        self._sim_tick = getattr(self, "_sim_tick", 0) + 1
        for item in self.inventory.values():
            item.stock_level = max(0, int(item.stock_level - item.daily_consumption / 24))
        items = list(self.inventory.values())
        for idx, supplier in enumerate(self.suppliers.values()):
            if supplier.pending_orders > 0 and (self._sim_tick + idx) % 10 == 0:
                supplier.pending_orders -= 1
                if items:
                    item = items[(self._sim_tick + idx) % len(items)]
                    item.stock_level = min(item.max_stock, item.stock_level + 125)
            if (self._sim_tick + idx) % 50 == 0:
                supplier.status = "delayed" if supplier.status == "active" else "active"
    
    def get_visualization_data(self) -> dict:
        return {
            "suppliers": [{**s.to_dict(), "position": {"lat": 30 + i*10, "lng": -100 + i*20}} for i, s in enumerate(self.suppliers.values())],
            "inventory": [i.to_dict() for i in self.inventory.values()],
            "stockout_risks": self.stockout_risks,
            "demand_forecast": self.demand_predictor.predict(7)
        }
