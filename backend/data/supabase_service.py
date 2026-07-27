"""
Supabase Integration Service

Comprehensive database integration for:
- Robot states and history
- Production stage metrics
- Inventory levels
- Agent decisions and actions
- Simulation events
- Performance comparisons
- User sessions and preferences

Provides real-time subscriptions and history queries.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import structlog

from config import settings

logger = structlog.get_logger(__name__)


class SupabaseService:
    """
    Comprehensive Supabase integration.
    
    Tables:
    - robots: Current robot states
    - robot_history: Historical robot telemetry
    - production_stages: Current stage states
    - production_history: Historical stage metrics
    - inventory: Current inventory levels
    - inventory_history: Stock level history
    - agent_decisions: All agent decisions with reasoning
    - simulation_events: Events during simulation
    - embodied_comparisons: Problem vs Solution metrics
    - model_metrics: ML model performance
    - sessions: User sessions
    """
    
    def __init__(self):
        self._client = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Supabase connection."""
        if not settings.supabase_url or not settings.supabase_key:
            logger.warning("Supabase credentials not configured")
            return False
        
        try:
            from supabase import create_client
            
            self._client = create_client(settings.supabase_url, settings.supabase_key)
            self._initialized = True
            logger.info("Supabase connected")
            
            # Ensure tables exist
            await self._ensure_schema()
            
            return True
            
        except Exception as e:
            logger.error("Supabase initialization failed", error=str(e))
            return False
    
    async def _ensure_schema(self) -> None:
        # Schema is owned by Alembic: backend/alembic/versions/0001_init.py
        # is the single source of truth. This method is a no-op kept as a
        # hook in case a future stage needs Supabase-cloud-specific RLS
        # policies that don't belong in the Alembic migration set.
        return None

    # =========================================================================
    # INCIDENT OPERATIONS (Stage 2 — KB_04 §incidents)
    # =========================================================================

    async def insert_incident(self, payload: Dict[str, Any]) -> Optional[str]:
        """Insert a row into the `incidents` table.

        Called from the SimPy persistence layer
        (backend/simulation/persistence.py) whenever an inject is processed.
        Raises on persistence failure so the caller can route the payload to
        the Redis retry queue.

        Schema (from backend/alembic/versions/0001_init.py):
          incident_id UUID PK, started_at TIMESTAMPTZ, ended_at TIMESTAMPTZ NULL,
          type VARCHAR(50) CHECK IN (six allowed values), target_id INT NULL,
          details JSONB DEFAULT {}, severity VARCHAR(20) CHECK IN (info|warning|critical).
        """
        if not self._initialized or self._client is None:
            raise RuntimeError("Supabase client not initialized; cannot insert incident")
        row = {
            "incident_id": payload["incident_id"],
            "started_at": payload.get("started_at"),
            "ended_at": payload.get("ended_at"),
            "type": payload["type"],
            "target_id": payload.get("target_id"),
            "details": payload.get("details", {}),
            "severity": payload.get("severity", "warning"),
        }
        # supabase-py is sync; run in a worker thread to keep the FastAPI loop free.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.table("incidents").insert(row).execute(),
        )
        return row["incident_id"]
    
    # =========================================================================
    # ROBOT OPERATIONS
    # =========================================================================
    
    async def upsert_robot(self, robot_data: Dict) -> bool:
        """Insert or update robot state."""
        if not self._initialized:
            return False
        
        try:
            self._client.table("robots").upsert({
                "robot_id": robot_data["robot_id"],
                "position_x": robot_data["position_x"],
                "position_y": robot_data["position_y"],
                "battery": robot_data["battery"],
                "status": robot_data["status"],
                "current_task": robot_data.get("current_task"),
                "velocity": robot_data.get("velocity", 0),
                "last_updated": datetime.utcnow().isoformat()
            }).execute()
            return True
        except Exception as e:
            logger.error("Failed to upsert robot", error=str(e))
            return False
    
    async def upsert_robots_batch(self, robots: List[Dict]) -> bool:
        """Batch upsert robot states."""
        if not self._initialized:
            return False
        
        try:
            records = [{
                "robot_id": r["robot_id"],
                "position_x": r["position_x"],
                "position_y": r["position_y"],
                "battery": r["battery"],
                "status": r["status"],
                "current_task": r.get("current_task"),
                "velocity": r.get("velocity", 0),
                "last_updated": datetime.utcnow().isoformat()
            } for r in robots]
            
            self._client.table("robots").upsert(records).execute()
            return True
        except Exception as e:
            logger.error("Failed to batch upsert robots", error=str(e))
            return False
    
    async def record_robot_history(self, robot_data: Dict) -> bool:
        """Record robot state to history."""
        if not self._initialized:
            return False
        
        try:
            self._client.table("robot_history").insert({
                "robot_id": robot_data["robot_id"],
                "position_x": robot_data["position_x"],
                "position_y": robot_data["position_y"],
                "battery": robot_data["battery"],
                "status": robot_data["status"]
            }).execute()
            return True
        except Exception as e:
            logger.error("Failed to record robot history", error=str(e))
            return False
    
    async def get_robots(self) -> List[Dict]:
        """Get current robot states."""
        if not self._initialized:
            return []
        
        try:
            response = self._client.table("robots").select("*").execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get robots", error=str(e))
            return []
    
    async def get_robot_history(self, robot_id: int, hours: int = 24) -> List[Dict]:
        """Get robot history for the past N hours."""
        if not self._initialized:
            return []
        
        try:
            since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            response = self._client.table("robot_history")\
                .select("*")\
                .eq("robot_id", robot_id)\
                .gte("recorded_at", since)\
                .order("recorded_at")\
                .execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get robot history", error=str(e))
            return []
    
    # =========================================================================
    # PRODUCTION OPERATIONS
    # =========================================================================
    
    async def upsert_stage(self, stage_data: Dict) -> bool:
        """Insert or update production stage."""
        if not self._initialized:
            return False
        
        try:
            self._client.table("production_stages").upsert({
                "stage_id": stage_data["stage_id"],
                "name": stage_data["name"],
                "queue_depth": stage_data["queue_depth"],
                "throughput": stage_data["throughput"],
                "temperature": stage_data.get("temperature"),
                "power_consumption": stage_data.get("power_consumption"),
                "defect_count": stage_data.get("defect_count", 0),
                "status": stage_data["status"],
                "last_updated": datetime.utcnow().isoformat()
            }).execute()
            return True
        except Exception as e:
            logger.error("Failed to upsert stage", error=str(e))
            return False
    
    async def upsert_stages_batch(self, stages: List[Dict]) -> bool:
        """Batch upsert production stages."""
        if not self._initialized:
            return False
        
        try:
            records = [{
                "stage_id": s["stage_id"],
                "name": s["name"],
                "queue_depth": s["queue_depth"],
                "throughput": s["throughput"],
                "temperature": s.get("temperature"),
                "power_consumption": s.get("power_consumption"),
                "defect_count": s.get("defect_count", 0),
                "status": s["status"],
                "last_updated": datetime.utcnow().isoformat()
            } for s in stages]
            
            self._client.table("production_stages").upsert(records).execute()
            return True
        except Exception as e:
            logger.error("Failed to batch upsert stages", error=str(e))
            return False
    
    async def get_stages(self) -> List[Dict]:
        """Get current production stages."""
        if not self._initialized:
            return []
        
        try:
            response = self._client.table("production_stages").select("*").order("stage_id").execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get stages", error=str(e))
            return []
    
    # =========================================================================
    # INVENTORY OPERATIONS
    # =========================================================================
    
    async def upsert_inventory(self, item_data: Dict) -> bool:
        """Insert or update inventory item."""
        if not self._initialized:
            return False
        
        try:
            self._client.table("inventory").upsert({
                "item_id": item_data["item_id"],
                "name": item_data["name"],
                "stock_level": item_data["stock_level"],
                "min_threshold": item_data.get("min_threshold", 50),
                "max_capacity": item_data.get("max_capacity", 1000),
                "reorder_point": item_data.get("reorder_point", 100),
                "supplier_id": item_data.get("supplier_id"),
                "consumption_rate": item_data.get("consumption_rate", 0),
                "last_updated": datetime.utcnow().isoformat()
            }).execute()
            return True
        except Exception as e:
            logger.error("Failed to upsert inventory", error=str(e))
            return False
    
    async def upsert_inventory_batch(self, items: List[Dict]) -> bool:
        """Batch upsert inventory items."""
        if not self._initialized:
            return False
        
        try:
            records = [{
                "item_id": i["item_id"],
                "name": i["name"],
                "stock_level": i["stock_level"],
                "min_threshold": i.get("min_threshold", 50),
                "consumption_rate": i.get("consumption_rate", 0),
                "last_updated": datetime.utcnow().isoformat()
            } for i in items]
            
            self._client.table("inventory").upsert(records).execute()
            return True
        except Exception as e:
            logger.error("Failed to batch upsert inventory", error=str(e))
            return False
    
    async def get_inventory(self) -> List[Dict]:
        """Get current inventory levels."""
        if not self._initialized:
            return []
        
        try:
            response = self._client.table("inventory").select("*").execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get inventory", error=str(e))
            return []
    
    async def get_critical_inventory(self) -> List[Dict]:
        """Get items below reorder point."""
        if not self._initialized:
            return []
        
        try:
            # Items where stock_level < min_threshold
            response = self._client.table("inventory")\
                .select("*")\
                .lt("stock_level", 50)\
                .execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get critical inventory", error=str(e))
            return []
    
    # =========================================================================
    # AGENT DECISIONS
    # =========================================================================
    
    async def record_decision(self, agent_type: str, decision_type: str, action: str,
                             reasoning: str = None, confidence: float = None,
                             affected_entities: List[str] = None, mode: str = "isolated") -> bool:
        """Record an agent decision."""
        if not self._initialized:
            return False
        
        try:
            self._client.table("agent_decisions").insert({
                "agent_type": agent_type,
                "decision_type": decision_type,
                "action": action,
                "reasoning": reasoning,
                "confidence": confidence,
                "affected_entities": json.dumps(affected_entities) if affected_entities else None,
                "mode": mode
            }).execute()
            return True
        except Exception as e:
            logger.error("Failed to record decision", error=str(e))
            return False
    
    async def get_decisions(self, agent_type: str = None, limit: int = 100) -> List[Dict]:
        """Get recent agent decisions."""
        if not self._initialized:
            return []
        
        try:
            query = self._client.table("agent_decisions").select("*")
            if agent_type:
                query = query.eq("agent_type", agent_type)
            response = query.order("created_at", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get decisions", error=str(e))
            return []
    
    # =========================================================================
    # SIMULATION EVENTS
    # =========================================================================
    
    async def record_event(self, event_type: str, domain: str, severity: str,
                          description: str, data: Dict = None, mode: str = "isolated") -> bool:
        """Record a simulation event."""
        if not self._initialized:
            return False
        
        try:
            self._client.table("simulation_events").insert({
                "event_type": event_type,
                "domain": domain,
                "severity": severity,
                "description": description,
                "data": json.dumps(data) if data else None,
                "mode": mode
            }).execute()
            return True
        except Exception as e:
            logger.error("Failed to record event", error=str(e))
            return False
    
    async def get_events(self, domain: str = None, severity: str = None, limit: int = 100) -> List[Dict]:
        """Get simulation events."""
        if not self._initialized:
            return []
        
        try:
            query = self._client.table("simulation_events").select("*")
            if domain:
                query = query.eq("domain", domain)
            if severity:
                query = query.eq("severity", severity)
            response = query.order("created_at", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get events", error=str(e))
            return []
    
    # =========================================================================
    # EMBODIED COMPARISONS
    # =========================================================================
    
    async def record_comparison(self, problem_data: Dict, solution_data: Dict, duration_s: int) -> bool:
        """Record problem vs solution comparison."""
        if not self._initialized:
            return False
        
        try:
            self._client.table("embodied_comparisons").insert({
                "problem_conflicts": problem_data.get("conflicts", 0),
                "problem_collisions": problem_data.get("robot_collisions", 0),
                "problem_bottlenecks": problem_data.get("bottlenecks", 0),
                "problem_stockouts": problem_data.get("stockouts", 0),
                "problem_throughput": problem_data.get("throughput", 0),
                "problem_energy": problem_data.get("energy_kwh", 0),
                "problem_response_time": problem_data.get("response_time_s", 0),
                "solution_conflicts": solution_data.get("conflicts", 0),
                "solution_collisions": solution_data.get("robot_collisions", 0),
                "solution_bottlenecks": solution_data.get("bottlenecks", 0),
                "solution_stockouts": solution_data.get("stockouts", 0),
                "solution_throughput": solution_data.get("throughput", 0),
                "solution_energy": solution_data.get("energy_kwh", 0),
                "solution_response_time": solution_data.get("response_time_s", 0),
                "simulation_duration_s": duration_s
            }).execute()
            return True
        except Exception as e:
            logger.error("Failed to record comparison", error=str(e))
            return False
    
    async def get_comparisons(self, limit: int = 10) -> List[Dict]:
        """Get recent comparisons."""
        if not self._initialized:
            return []
        
        try:
            response = self._client.table("embodied_comparisons")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data
        except Exception as e:
            logger.error("Failed to get comparisons", error=str(e))
            return []
    
    # =========================================================================
    # SYNC OPERATIONS
    # =========================================================================
    
    async def sync_full_state(self, robots: List[Dict], stages: List[Dict], inventory: List[Dict]) -> bool:
        """Sync complete system state to Supabase."""
        if not self._initialized:
            return False
        
        results = await asyncio.gather(
            self.upsert_robots_batch(robots),
            self.upsert_stages_batch(stages),
            self.upsert_inventory_batch(inventory),
            return_exceptions=True
        )
        
        return all(r == True for r in results if not isinstance(r, Exception))


# Global instance
_supabase_service: Optional[SupabaseService] = None


async def get_supabase_service() -> SupabaseService:
    """Get or create global Supabase service."""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
        await _supabase_service.initialize()
    return _supabase_service
