"""
Base Agent Class for Domain Agents
Foundation for Robotics, Manufacturing, and Supply Chain agents.

As a GenAI Engineer specializing in agent systems:
- Defines the core agent interface
- Implements LangChain tool execution
- Provides state management and action logging
- Enables coordination through the knowledge graph
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

import structlog
from pydantic import BaseModel

from agents.llm_client import LLMClient, LLMMessage, LLMResponse, get_llm_client
from knowledge_graph import get_neo4j_client

logger = structlog.get_logger(__name__)


class AgentStatus(str, Enum):
    """Agent operational status."""
    IDLE = "idle"
    OBSERVING = "observing"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"


class ActionType(str, Enum):
    """Types of actions agents can take."""
    OBSERVE = "observe"
    ANALYZE = "analyze"
    DECIDE = "decide"
    EXECUTE = "execute"
    COMMUNICATE = "communicate"
    COORDINATE = "coordinate"


@dataclass
class AgentAction:
    """Represents an action taken by an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType = ActionType.OBSERVE
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    action_name: str = ""
    parameters: dict = field(default_factory=dict)
    result: Optional[Any] = None
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    reasoning: str = ""


@dataclass
class AgentState:
    """Current state of an agent."""
    domain: str
    status: AgentStatus = AgentStatus.IDLE
    current_observation: dict = field(default_factory=dict)
    recent_actions: list[AgentAction] = field(default_factory=list)
    pending_decisions: list[dict] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    performance_metrics: dict = field(default_factory=dict)
    last_update: datetime = field(default_factory=datetime.utcnow)


class AgentTool(BaseModel):
    """Definition of a tool available to an agent."""
    name: str
    description: str
    parameters: dict
    function: Optional[Callable] = None
    
    class Config:
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    """
    Abstract base class for all domain agents.
    
    Each domain agent (Robotics, Manufacturing, Supply Chain) extends this class
    and implements domain-specific perception, reasoning, and action.
    
    Key Responsibilities:
    1. Observe - Perceive the current state of the domain
    2. Analyze - Identify problems and opportunities
    3. Decide - Choose optimal actions using LLM reasoning
    4. Execute - Apply actions through domain-specific tools
    5. Report - Update knowledge graph with results
    """
    
    def __init__(
        self,
        domain: str,
        name: str = None,
        description: str = None
    ):
        self.domain = domain
        self.name = name or f"{domain.title()}Agent"
        self.description = description or f"AI agent for {domain} domain optimization"
        
        # State management
        self.state = AgentState(domain=domain)
        self.tools: dict[str, AgentTool] = {}
        
        # Dependencies
        self._llm: Optional[LLMClient] = None
        self._neo4j = None
        
        # Configuration
        self.max_actions_per_cycle = 5
        self.thinking_temperature = 0.7
        self.action_log: list[AgentAction] = []
        
        # Register default tools
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register tools available to all agents."""
        self.register_tool(AgentTool(
            name="observe_state",
            description="Observe the current state of the domain",
            parameters={"type": "object", "properties": {}}
        ))
        
        self.register_tool(AgentTool(
            name="report_problem",
            description="Report a detected problem to the knowledge graph",
            parameters={
                "type": "object",
                "properties": {
                    "problem_type": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "description": {"type": "string"},
                    "affected_entities": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["problem_type", "severity", "description"]
            }
        ))
        
        self.register_tool(AgentTool(
            name="request_coordination",
            description="Request coordination with another domain agent",
            parameters={
                "type": "object",
                "properties": {
                    "target_domain": {"type": "string", "enum": ["robotics", "manufacturing", "supply_chain"]},
                    "request_type": {"type": "string"},
                    "details": {"type": "object"}
                },
                "required": ["target_domain", "request_type"]
            }
        ))
    
    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool for this agent."""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}", agent=self.name)
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        self._llm = get_llm_client()
        self._neo4j = await get_neo4j_client()
        
        # Update knowledge graph
        await self._neo4j.upsert_agent({
            "domain": self.domain,
            "status": self.state.status.value,
            "current_action": "initializing"
        })
        
        self.state.status = AgentStatus.IDLE
        logger.info(f"Agent initialized: {self.name}")
    
    # =========================================================================
    # CORE AGENT LOOP
    # =========================================================================
    
    async def run_cycle(self) -> list[AgentAction]:
        """
        Execute one agent cycle: Observe → Analyze → Decide → Execute
        
        Returns:
            List of actions taken during this cycle
        """
        cycle_actions = []
        
        try:
            self.state.status = AgentStatus.OBSERVING
            
            # 1. OBSERVE - Get current domain state
            observation = await self.observe()
            self.state.current_observation = observation
            cycle_actions.append(AgentAction(
                action_type=ActionType.OBSERVE,
                action_name="observe_state",
                result={"entities_observed": len(observation)}
            ))
            
            # 2. ANALYZE - Identify problems and opportunities
            self.state.status = AgentStatus.PLANNING
            analysis = await self.analyze(observation)
            cycle_actions.append(AgentAction(
                action_type=ActionType.ANALYZE,
                action_name="analyze_state",
                result=analysis
            ))
            
            # 3. DECIDE - Choose optimal actions
            if analysis.get("problems") or analysis.get("opportunities"):
                decisions = await self.decide(observation, analysis)
                
                # 4. EXECUTE - Apply decisions
                self.state.status = AgentStatus.EXECUTING
                for decision in decisions[:self.max_actions_per_cycle]:
                    action_result = await self.execute_action(decision)
                    cycle_actions.append(action_result)
            
            # 5. REPORT - Update knowledge graph
            await self._update_knowledge_graph(cycle_actions)
            
            self.state.status = AgentStatus.IDLE
            self.state.recent_actions = cycle_actions
            self.action_log.extend(cycle_actions)
            
        except Exception as e:
            logger.error(f"Agent cycle error", agent=self.name, error=str(e))
            self.state.status = AgentStatus.ERROR
            cycle_actions.append(AgentAction(
                action_type=ActionType.OBSERVE,
                action_name="error",
                success=False,
                result={"error": str(e)}
            ))
        
        return cycle_actions
    
    # =========================================================================
    # ABSTRACT METHODS - Domain-specific implementation required
    # =========================================================================
    
    @abstractmethod
    async def observe(self) -> dict:
        """
        Observe the current state of the domain.
        
        Returns:
            Dictionary containing current domain state
        """
        pass
    
    @abstractmethod
    async def analyze(self, observation: dict) -> dict:
        """
        Analyze observations to identify problems and opportunities.
        
        Returns:
            Dictionary with 'problems' and 'opportunities' lists
        """
        pass
    
    @abstractmethod
    async def decide(self, observation: dict, analysis: dict) -> list[dict]:
        """
        Decide on actions to take based on analysis.
        
        Returns:
            List of action dictionaries to execute
        """
        pass
    
    @abstractmethod
    async def execute_action(self, action: dict) -> AgentAction:
        """
        Execute a specific action in the domain.
        
        Returns:
            AgentAction with results
        """
        pass
    
    # =========================================================================
    # LLM REASONING
    # =========================================================================
    
    async def reason(
        self,
        context: str,
        question: str,
        available_actions: list[str] = None
    ) -> str:
        """
        Use LLM to reason about a situation.
        
        Args:
            context: Current context/state description
            question: What to reason about
            available_actions: List of possible actions
        
        Returns:
            LLM reasoning response
        """
        system_prompt = f"""You are {self.name}, an AI agent specialized in {self.domain} optimization.

Your role: {self.description}

Current goals: {', '.join(self.state.goals) if self.state.goals else 'Optimize domain performance'}

Constraints: {', '.join(self.state.constraints) if self.state.constraints else 'None specified'}

Available actions: {', '.join(available_actions) if available_actions else 'Observe, Analyze, Report'}

Respond concisely and actionably. Focus on practical solutions."""

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=f"Context:\n{context}\n\nQuestion:\n{question}")
        ]
        
        response = await self._llm.generate(
            messages=messages,
            temperature=self.thinking_temperature,
            max_tokens=1024
        )
        
        return response.content
    
    async def plan_actions(
        self,
        observation: dict,
        problems: list[dict],
        opportunities: list[dict]
    ) -> list[dict]:
        """
        Use LLM to plan a sequence of actions.
        
        Returns:
            List of planned action dictionaries
        """
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        ])
        
        context = f"""
Current Observation:
{observation}

Problems Detected:
{problems}

Opportunities Identified:
{opportunities}

Available Tools:
{tool_descriptions}
"""
        
        question = """Based on the current situation, plan up to 3 actions to take.
For each action, specify:
1. tool_name: Which tool to use
2. parameters: Parameters for the tool
3. expected_outcome: What you expect to happen
4. priority: high/medium/low

Respond in JSON format as a list of action objects."""
        
        response = await self.reason(context, question, list(self.tools.keys()))
        
        # Parse actions from response
        try:
            import json
            # Try to extract JSON from response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end > start:
                actions = json.loads(response[start:end])
                return actions
        except Exception as e:
            logger.warning(f"Failed to parse actions", error=str(e))
        
        return []
    
    # =========================================================================
    # KNOWLEDGE GRAPH INTEGRATION
    # =========================================================================
    
    async def _update_knowledge_graph(self, actions: list[AgentAction]) -> None:
        """Update knowledge graph with agent actions and state."""
        if not self._neo4j:
            return
        
        # Update agent node
        await self._neo4j.upsert_agent({
            "domain": self.domain,
            "status": self.state.status.value,
            "current_action": actions[-1].action_name if actions else "idle"
        })
        
        # Record problems found
        for action in actions:
            if action.action_name == "report_problem" and action.result:
                # Would create Problem nodes in knowledge graph
                pass
    
    async def report_conflict(
        self,
        other_domain: str,
        conflict_type: str,
        description: str
    ) -> None:
        """Report a conflict with another agent to the knowledge graph."""
        if self._neo4j:
            await self._neo4j.record_agent_conflict(
                agent1_domain=self.domain,
                agent2_domain=other_domain,
                conflict_type=conflict_type,
                description=description
            )
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_state_summary(self) -> dict:
        """Get a summary of current agent state."""
        return {
            "domain": self.domain,
            "name": self.name,
            "status": self.state.status.value,
            "actions_taken": len(self.action_log),
            "last_update": self.state.last_update.isoformat(),
            "recent_actions": [
                {
                    "name": a.action_name,
                    "success": a.success,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in self.state.recent_actions[-5:]
            ]
        }
    
    def set_goals(self, goals: list[str]) -> None:
        """Set agent goals."""
        self.state.goals = goals
        logger.info(f"Goals updated", agent=self.name, goals=goals)
    
    def set_constraints(self, constraints: list[str]) -> None:
        """Set agent constraints."""
        self.state.constraints = constraints
        logger.info(f"Constraints updated", agent=self.name, constraints=constraints)
