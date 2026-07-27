"""
Embodied Agent - Unified Multi-Domain Coordinator
Uses LangGraph for orchestrating domain agents and resolving conflicts.

This is the SOLUTION that demonstrates how coordinated AI agents
outperform isolated domain agents.
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import structlog

from agents.base_agent import BaseAgent, AgentTool, AgentAction, ActionType, AgentStatus
from agents.robotics_agent import RoboticsAgent
from agents.manufacturing_agent import ManufacturingAgent
from agents.supply_chain_agent import SupplyChainAgent
from agents.llm_client import LLMClient, LLMMessage, get_llm_client
from knowledge_graph import get_neo4j_client

logger = structlog.get_logger(__name__)


class CoordinationMode(str, Enum):
    ISOLATED = "isolated"  # Problem mode: agents work independently
    COORDINATED = "coordinated"  # Solution mode: embodied agent coordinates


@dataclass
class ConflictResolution:
    """Result of conflict resolution between agents."""
    conflict_type: str
    agents_involved: List[str]
    resolution_action: str
    priority_agent: str
    resolved: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)


class EmbodiedAgent(BaseAgent):
    """
    Unified Embodied Agent that coordinates all domain agents.
    
    In ISOLATED mode: Agents work independently, showing coordination problems
    In COORDINATED mode: This agent orchestrates all domains optimally
    
    Key Capabilities:
    - Cross-domain conflict detection and resolution
    - Global optimization across robotics, manufacturing, supply chain
    - Resource allocation balancing
    - Predictive cross-domain planning
    """
    
    def __init__(self):
        super().__init__(
            domain="embodied",
            name="EmbodiedCoordinator",
            description="Unified AI agent coordinating robotics, manufacturing, and supply chain for global optimization"
        )
        
        self.mode = CoordinationMode.ISOLATED
        
        # Domain agents
        self.robotics_agent: Optional[RoboticsAgent] = None
        self.manufacturing_agent: Optional[ManufacturingAgent] = None
        self.supply_chain_agent: Optional[SupplyChainAgent] = None
        
        # Cross-domain state
        self.cross_domain_conflicts: List[Dict] = []
        self.resolutions: List[ConflictResolution] = []
        self.global_metrics: Dict = {}
        
        self._register_coordination_tools()
    
    def _register_coordination_tools(self):
        """Register cross-domain coordination tools."""
        tools = [
            ("coordinate_material_delivery", "Coordinate robot delivery for manufacturing", 
             {"stage_id": "integer", "material": "string", "priority": "string"}),
            ("balance_workload", "Balance workload across manufacturing and robotics",
             {"optimization_target": "string"}),
            ("resolve_conflict", "Resolve conflict between domain agents",
             {"conflict_id": "string", "resolution_strategy": "string"}),
            ("emergency_mode", "Activate emergency coordination mode",
             {"affected_domains": "array", "reason": "string"}),
        ]
        for name, desc, params in tools:
            self.register_tool(AgentTool(name=name, description=desc,
                parameters={"type": "object", "properties": {k: {"type": v} for k, v in params.items()}}))
    
    async def initialize(self) -> None:
        """Initialize the embodied agent and all domain agents."""
        await super().initialize()
        
        # Initialize domain agents
        self.robotics_agent = RoboticsAgent()
        self.manufacturing_agent = ManufacturingAgent()
        self.supply_chain_agent = SupplyChainAgent()
        
        await asyncio.gather(
            self.robotics_agent.initialize(),
            self.manufacturing_agent.initialize(),
            self.supply_chain_agent.initialize()
        )
        
        self.state.goals = [
            "Coordinate all domain agents for global optimization",
            "Detect and resolve cross-domain conflicts",
            "Maximize overall system efficiency",
            "Prevent cascading failures across domains"
        ]
        
        logger.info("Embodied agent initialized with all domain agents")
    
    def set_mode(self, mode: CoordinationMode) -> None:
        """Switch between isolated and coordinated modes."""
        self.mode = mode
        logger.info(f"Embodied agent mode set to {mode.value}")

    async def coordinate(self, incident: Dict[str, Any], *, sil_level: int = 0,
                         telemetry_window: Optional[List] = None,
                         hitl_resolution: Optional[str] = None) -> List[Dict[str, Any]]:
        """Stage 11 public contract: run one incident through the self-healing LangGraph runtime and return the
        coordinator's decisions. Thin wrapper — the deterministic, durable graph + the real Stage-4-10 (depth-
        hardened) models live in `agents.runtime`. Honest: the runtime degrades gracefully if a model is absent and
        the neuro-symbolic verifier genuinely gates execution; nothing is fabricated. The legacy `run_all_agents`
        coordination is retained alongside (full migration of that path is the Stage-11 continuation)."""
        from agents.runtime import run_incident
        out = run_incident(incident, sil_level=sil_level, telemetry_window=telemetry_window,
                           hitl_resolution=hitl_resolution)
        return out["decisions"]
    
    async def run_all_agents(self) -> Dict[str, List[AgentAction]]:
        """Run cycle for all domain agents."""
        if self.mode == CoordinationMode.ISOLATED:
            return await self._run_isolated()
        else:
            return await self._run_coordinated()
    
    async def _run_isolated(self) -> Dict[str, List[AgentAction]]:
        """Run agents independently (problem demonstration mode)."""
        results = {}
        
        # Run in parallel without coordination
        robotics_task = self.robotics_agent.run_cycle()
        manufacturing_task = self.manufacturing_agent.run_cycle()
        supply_chain_task = self.supply_chain_agent.run_cycle()
        
        (results["robotics"], results["manufacturing"], results["supply_chain"]) = await asyncio.gather(
            robotics_task, manufacturing_task, supply_chain_task
        )
        
        # Detect conflicts that emerge from isolation
        await self._detect_cross_domain_conflicts()
        
        return results
    
    async def _run_coordinated(self) -> Dict[str, List[AgentAction]]:
        """Run agents with coordination (solution demonstration mode)."""
        results = {"robotics": [], "manufacturing": [], "supply_chain": [], "coordinator": []}
        
        # 1. Observe all domains
        observations = {
            "robotics": await self.robotics_agent.observe(),
            "manufacturing": await self.manufacturing_agent.observe(),
            "supply_chain": await self.supply_chain_agent.observe()
        }
        
        # 2. Analyze all domains
        analyses = {
            "robotics": await self.robotics_agent.analyze(observations["robotics"]),
            "manufacturing": await self.manufacturing_agent.analyze(observations["manufacturing"]),
            "supply_chain": await self.supply_chain_agent.analyze(observations["supply_chain"])
        }
        
        # 3. Cross-domain analysis and conflict detection
        cross_analysis = await self._analyze_cross_domain(observations, analyses)
        
        # 4. Coordinated decision making
        all_problems = []
        for domain, analysis in analyses.items():
            for p in analysis.get("problems", []):
                p["domain"] = domain
                all_problems.append(p)
        
        # Prioritize problems globally
        prioritized = sorted(all_problems, key=lambda p: 
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(p.get("severity", "low"), 4))
        
        # 5. Resolve conflicts before execution
        for conflict in cross_analysis.get("conflicts", []):
            resolution = await self._resolve_conflict(conflict)
            results["coordinator"].append(AgentAction(
                action_type=ActionType.COORDINATE,
                action_name="resolve_conflict",
                result={"conflict": conflict, "resolution": resolution.resolution_action},
                success=resolution.resolved,
                reasoning=f"Resolved {conflict['type']} between {conflict['agents']}"
            ))
        
        # 6. Execute coordinated actions
        for problem in prioritized[:self.max_actions_per_cycle]:
            domain = problem["domain"]
            agent = getattr(self, f"{domain}_agent")
            
            decisions = await agent.decide(observations[domain], {"problems": [problem], "opportunities": []})
            for decision in decisions:
                action = await agent.execute_action(decision)
                results[domain].append(action)
        
        # 7. Cross-domain coordination actions
        for coordination in cross_analysis.get("coordinations", []):
            coord_action = await self._execute_coordination(coordination)
            results["coordinator"].append(coord_action)
        
        return results
    
    async def observe(self) -> dict:
        """Observe all domains."""
        return {
            "mode": self.mode.value,
            "robotics": await self.robotics_agent.observe() if self.robotics_agent else {},
            "manufacturing": await self.manufacturing_agent.observe() if self.manufacturing_agent else {},
            "supply_chain": await self.supply_chain_agent.observe() if self.supply_chain_agent else {},
            "conflicts": self.cross_domain_conflicts,
            "resolutions": len(self.resolutions),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def analyze(self, observation: dict) -> dict:
        """Analyze cross-domain issues."""
        problems = []
        
        # Analyze each domain
        for domain in ["robotics", "manufacturing", "supply_chain"]:
            agent = getattr(self, f"{domain}_agent")
            if agent and observation.get(domain):
                domain_analysis = await agent.analyze(observation[domain])
                for p in domain_analysis.get("problems", []):
                    p["domain"] = domain
                    problems.append(p)
        
        # Detect cross-domain conflicts
        await self._detect_cross_domain_conflicts()
        for conflict in self.cross_domain_conflicts:
            problems.append({
                "type": "cross_domain_conflict",
                "severity": "high",
                "domains": conflict["agents"],
                "description": conflict["description"]
            })
        
        return {"problems": problems, "problem_count": len(problems), "conflict_count": len(self.cross_domain_conflicts)}
    
    async def decide(self, observation: dict, analysis: dict) -> list[dict]:
        """Make coordinated decisions."""
        return []  # Decisions made in _run_coordinated
    
    async def execute_action(self, action: dict) -> AgentAction:
        """Execute coordination action."""
        return AgentAction(action_type=ActionType.COORDINATE, action_name=action.get("tool", "unknown"))
    
    async def _analyze_cross_domain(self, observations: Dict, analyses: Dict) -> Dict:
        """Analyze cross-domain dependencies and potential conflicts."""
        conflicts = []
        coordinations = []
        
        # 1. Manufacturing needs materials -> Robotics delivers -> Supply chain provides
        manufacturing_bottlenecks = [p for p in analyses["manufacturing"].get("problems", []) if "bottleneck" in p.get("type", "")]
        supply_shortages = [p for p in analyses["supply_chain"].get("problems", []) if "stock" in p.get("type", "")]
        robot_issues = [p for p in analyses["robotics"].get("problems", []) if p.get("severity") in ["critical", "high"]]
        
        # Conflict: Manufacturing needs materials but robots are busy/broken
        if manufacturing_bottlenecks and robot_issues:
            conflicts.append({
                "id": f"conflict_{datetime.utcnow().timestamp()}",
                "type": "resource_contention",
                "agents": ["manufacturing", "robotics"],
                "description": "Manufacturing bottleneck while robots have issues - material delivery impacted"
            })
        
        # Conflict: Supply shortage affecting manufacturing
        if supply_shortages and manufacturing_bottlenecks:
            conflicts.append({
                "id": f"conflict_{datetime.utcnow().timestamp()}",
                "type": "supply_production_mismatch",
                "agents": ["supply_chain", "manufacturing"],
                "description": "Supply shortage causing production delays"
            })
        
        # Coordination opportunity: Preemptive material staging
        if supply_shortages:
            coordinations.append({
                "type": "preemptive_staging",
                "domains": ["robotics", "supply_chain"],
                "action": "Stage robots near receiving dock for incoming shipments"
            })
        
        return {"conflicts": conflicts, "coordinations": coordinations}
    
    async def _detect_cross_domain_conflicts(self) -> None:
        """Detect conflicts between domain agents."""
        self.cross_domain_conflicts = []
        
        if not all([self.robotics_agent, self.manufacturing_agent, self.supply_chain_agent]):
            return
        
        # Check for resource conflicts
        robot_battery_issues = any(r.battery < 20 for r in self.robotics_agent.robots.values())
        manufacturing_bottlenecks = any(s.queue_depth > 20 for s in self.manufacturing_agent.stages.values())
        supply_critical = any(i.stock_level < i.reorder_point * 0.5 for i in self.supply_chain_agent.inventory.values())
        
        if robot_battery_issues and manufacturing_bottlenecks:
            self.cross_domain_conflicts.append({
                "type": "robot_manufacturing_conflict",
                "agents": ["robotics", "manufacturing"],
                "severity": "high",
                "description": "Robots low on battery while manufacturing has bottlenecks - cannot deliver materials"
            })
        
        if supply_critical and manufacturing_bottlenecks:
            self.cross_domain_conflicts.append({
                "type": "supply_manufacturing_conflict",
                "agents": ["supply_chain", "manufacturing"],
                "severity": "critical",
                "description": "Supply shortage causing production bottlenecks"
            })
    
    async def _resolve_conflict(self, conflict: Dict) -> ConflictResolution:
        """Resolve a cross-domain conflict using LLM reasoning."""
        llm = get_llm_client()
        
        context = f"""
Conflict detected in manufacturing system:
Type: {conflict['type']}
Agents involved: {conflict['agents']}
Description: {conflict['description']}

Available resolution strategies:
1. prioritize_production: Focus resources on manufacturing
2. prioritize_logistics: Focus on material movement
3. emergency_reorder: Expedite supply chain
4. load_balance: Redistribute workload evenly
"""
        
        response = await self.reason(context, "What is the best resolution strategy for this conflict?",
            ["prioritize_production", "prioritize_logistics", "emergency_reorder", "load_balance"])
        
        # Extract strategy from response
        strategy = "load_balance"  # Default
        for s in ["prioritize_production", "prioritize_logistics", "emergency_reorder", "load_balance"]:
            if s in response.lower():
                strategy = s
                break
        
        resolution = ConflictResolution(
            conflict_type=conflict["type"],
            agents_involved=conflict["agents"],
            resolution_action=strategy,
            priority_agent=conflict["agents"][0] if len(conflict["agents"]) > 0 else "embodied",
            resolved=True
        )
        
        self.resolutions.append(resolution)
        return resolution
    
    async def _execute_coordination(self, coordination: Dict) -> AgentAction:
        """Execute a cross-domain coordination action."""
        if coordination["type"] == "preemptive_staging":
            # Move robots near receiving dock
            actions = []
            for robot_id in list(self.robotics_agent.robots.keys())[:3]:
                await self.robotics_agent.execute_action({
                    "tool": "navigate_robot",
                    "parameters": {"robot_id": robot_id, "destination_x": 95, "destination_y": 30}
                })
        
        return AgentAction(
            action_type=ActionType.COORDINATE,
            action_name="coordinate",
            result={"coordination_type": coordination["type"], "domains": coordination["domains"]},
            success=True,
            reasoning=coordination.get("action", "Cross-domain coordination")
        )
    
    # ---- Stage 6 vertical slice: deterministic intervention decision --------

    @staticmethod
    def decide_intervention(diagnosis, *, queue_depth: Optional[int] = None,
                            capacity: Optional[int] = None):
        """Coordinator decision for a diagnosed machine (predict→diagnose→INTERVENE).

        Delegates to the shared deterministic v0 policy in
        ``services.intervention_policy`` — the same object the A/B harness uses,
        so the live coordinator path and the measured experiment cannot drift.
        Static on purpose: deciding requires no LLM, no Neo4j, and no initialized
        domain agents (free-cost, testable). Stage 7 swaps the policy for PPO;
        Stage 11 wraps it in the durable HITL workflow.
        """
        from services.intervention_policy import decide_intervention as _policy

        return _policy(diagnosis, queue_depth=queue_depth, capacity=capacity)

    def get_visualization_data(self) -> Dict:
        """Get unified visualization data from all domains."""
        return {
            "mode": self.mode.value,
            "robotics": self.robotics_agent.get_fleet_visualization_data() if self.robotics_agent else {},
            "manufacturing": self.manufacturing_agent.get_visualization_data() if self.manufacturing_agent else {},
            "supply_chain": self.supply_chain_agent.get_visualization_data() if self.supply_chain_agent else {},
            "conflicts": self.cross_domain_conflicts,
            "resolutions": [{"type": r.conflict_type, "action": r.resolution_action, "resolved": r.resolved} for r in self.resolutions[-5:]],
            "global_status": "coordinated" if self.mode == CoordinationMode.COORDINATED else "isolated"
        }
    
    def get_comparison_metrics(self) -> Dict:
        """Get metrics comparing isolated vs coordinated performance."""
        if not all([self.robotics_agent, self.manufacturing_agent, self.supply_chain_agent]):
            return {}
        
        robot_issues = sum(1 for r in self.robotics_agent.robots.values() if r.status in ["warning", "error"])
        manufacturing_bottlenecks = sum(1 for s in self.manufacturing_agent.stages.values() if s.queue_depth > 20)
        supply_critical = sum(1 for i in self.supply_chain_agent.inventory.values() if i.stock_level < i.reorder_point * 0.5)
        
        return {
            "mode": self.mode.value,
            "conflicts_detected": len(self.cross_domain_conflicts),
            "conflicts_resolved": len(self.resolutions),
            "robot_issues": robot_issues,
            "manufacturing_bottlenecks": manufacturing_bottlenecks,
            "supply_critical_items": supply_critical,
            "overall_health": "good" if (robot_issues + manufacturing_bottlenecks + supply_critical) < 5 else "degraded"
        }
