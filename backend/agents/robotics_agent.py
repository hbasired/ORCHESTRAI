"""
Robotics Domain Agent
AI agent for autonomous mobile robot (AMR) fleet optimization.

As a Robotics AI Engineer with 30+ years experience:
- PPO-based Reinforcement Learning for robot navigation
- Real-time collision avoidance and path optimization
- Battery management and charging scheduling
- Multi-robot coordination and task allocation
- Integration with knowledge graph for fleet visibility
"""

import asyncio
import numpy as np
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime
import math
import random

import structlog

from agents.base_agent import BaseAgent, AgentTool, AgentAction, ActionType, AgentStatus
from agents.llm_client import LLMMessage
from config import settings, DomainConfig

logger = structlog.get_logger(__name__)


@dataclass
class RobotState:
    """State of a single robot."""
    id: int
    position_x: float
    position_y: float
    battery: float
    speed: float
    status: str  # idle, working, charging, warning, error
    task: Optional[str] = None
    destination: Optional[tuple[float, float]] = None
    path: list[tuple[float, float]] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": {"x": self.position_x, "y": self.position_y},
            "battery": self.battery,
            "speed": self.speed,
            "status": self.status,
            "task": self.task,
            "destination": self.destination
        }


class PPONavigator:
    """
    PPO-based navigation policy for robot path planning.
    
    State Space:
    - Robot position (x, y)
    - Destination (x, y)
    - Battery level
    - Nearby obstacles (8 directions)
    - Other robots' positions
    
    Action Space:
    - Movement direction (continuous: 0-360 degrees)
    - Speed (continuous: 0-1)
    """
    
    def __init__(self, state_dim: int = 20, action_dim: int = 2):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = 0.99
        self.epsilon = 0.2
        
        # Initialize neural network (simplified for demo)
        self._actor = None
        self._critic = None
        self._initialized = False
    
    async def load_model(self, path: str = None) -> None:
        """Load trained PPO model."""
        try:
            import torch
            import torch.nn as nn
            
            class ActorCritic(nn.Module):
                def __init__(self, state_dim, action_dim):
                    super().__init__()
                    self.shared = nn.Sequential(
                        nn.Linear(state_dim, 128),
                        nn.ReLU(),
                        nn.Linear(128, 64),
                        nn.ReLU()
                    )
                    self.actor = nn.Sequential(
                        nn.Linear(64, action_dim),
                        nn.Tanh()  # Actions in [-1, 1]
                    )
                    self.critic = nn.Linear(64, 1)
                
                def forward(self, x):
                    shared = self.shared(x)
                    return self.actor(shared), self.critic(shared)
            
            self._model = ActorCritic(self.state_dim, self.action_dim)
            
            if path:
                self._model.load_state_dict(torch.load(path))
            
            self._initialized = True
            logger.info("PPO Navigator initialized")
            
        except Exception as e:
            logger.warning("PyTorch not available, using heuristic navigation", error=str(e))
            self._initialized = False
    
    def get_state_vector(
        self,
        robot: RobotState,
        destination: tuple[float, float],
        obstacles: list[tuple[float, float]],
        other_robots: list[RobotState]
    ) -> np.ndarray:
        """Convert robot state to feature vector for PPO."""
        features = []
        
        # Robot state (normalized)
        features.extend([
            robot.position_x / 100.0,
            robot.position_y / 60.0,
            robot.battery / 100.0,
            robot.speed / DomainConfig.Robotics.MAX_SPEED
        ])
        
        # Destination (normalized)
        features.extend([
            destination[0] / 100.0 if destination else 0,
            destination[1] / 60.0 if destination else 0
        ])
        
        # Distance and angle to destination
        if destination:
            dx = destination[0] - robot.position_x
            dy = destination[1] - robot.position_y
            distance = math.sqrt(dx*dx + dy*dy)
            angle = math.atan2(dy, dx)
            features.extend([distance / 100.0, angle / math.pi])
        else:
            features.extend([0, 0])
        
        # Nearby obstacle distances (8 directions)
        for direction in range(0, 360, 45):
            rad = math.radians(direction)
            min_dist = 10.0  # Max detection range
            
            # Check each obstacle
            for ox, oy in obstacles:
                dx = ox - robot.position_x
                dy = oy - robot.position_y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < min_dist:
                    obs_angle = math.atan2(dy, dx)
                    if abs(obs_angle - rad) < 0.5:  # Within 30 degrees
                        min_dist = dist
            
            features.append(min_dist / 10.0)
        
        # Nearby robots (closest 4)
        robot_distances = []
        for other in other_robots:
            if other.id != robot.id:
                dx = other.position_x - robot.position_x
                dy = other.position_y - robot.position_y
                dist = math.sqrt(dx*dx + dy*dy)
                robot_distances.append(dist)
        
        robot_distances.sort()
        for i in range(4):
            if i < len(robot_distances):
                features.append(robot_distances[i] / 20.0)
            else:
                features.append(1.0)  # Far away
        
        return np.array(features, dtype=np.float32)
    
    def get_action(
        self,
        robot: RobotState,
        destination: tuple[float, float],
        obstacles: list[tuple[float, float]],
        other_robots: list[RobotState]
    ) -> tuple[float, float]:
        """
        Get navigation action from PPO policy.
        
        Returns:
            (direction_degrees, speed_factor)
        """
        if self._initialized:
            import torch
            
            state = self.get_state_vector(robot, destination, obstacles, other_robots)
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            
            with torch.no_grad():
                action, _ = self._model(state_tensor)
                action = action.squeeze().numpy()
            
            # Convert action to direction and speed
            direction = (action[0] + 1) * 180  # [-1,1] -> [0, 360]
            speed = (action[1] + 1) / 2  # [-1,1] -> [0, 1]
            
            return direction, speed
        else:
            # Heuristic fallback: direct path with collision avoidance
            return self._heuristic_action(robot, destination, obstacles, other_robots)
    
    def _heuristic_action(
        self,
        robot: RobotState,
        destination: tuple[float, float],
        obstacles: list[tuple[float, float]],
        other_robots: list[RobotState]
    ) -> tuple[float, float]:
        """Fallback heuristic navigation."""
        if not destination:
            return 0, 0
        
        # Direction to destination
        dx = destination[0] - robot.position_x
        dy = destination[1] - robot.position_y
        target_direction = math.degrees(math.atan2(dy, dx)) % 360
        
        # Check for nearby robots and adjust
        for other in other_robots:
            if other.id != robot.id:
                ox = other.position_x - robot.position_x
                oy = other.position_y - robot.position_y
                dist = math.sqrt(ox*ox + oy*oy)
                
                if dist < DomainConfig.Robotics.COLLISION_RADIUS * 2:
                    # Collision imminent - turn away
                    collision_angle = math.degrees(math.atan2(oy, ox))
                    target_direction = (target_direction + 90) % 360
        
        # Speed based on distance
        distance = math.sqrt(dx*dx + dy*dy)
        speed = min(distance / 10.0, 1.0)
        
        # Slow down if battery is low
        if robot.battery < 20:
            speed *= 0.5
        
        return target_direction, speed


class RoboticsAgent(BaseAgent):
    """
    Domain agent for robotics fleet optimization.
    
    Capabilities:
    - Monitor fleet of 20+ autonomous mobile robots
    - Detect collision risks and path conflicts
    - Optimize task allocation and routing
    - Manage battery and charging schedules
    - Identify inefficiencies and bottlenecks
    
    Problems This Agent Will Detect:
    - Robot collisions and near-misses
    - Suboptimal paths causing delays
    - Battery emergencies
    - Task allocation inefficiencies
    - Charging station congestion
    """
    
    def __init__(self, state_manager=None):
        super().__init__(
            domain="robotics",
            name="RoboticsFleetAgent",
            description="AI agent for autonomous mobile robot fleet optimization using reinforcement learning"
        )
        
        self.state_manager = state_manager
        self.navigator = PPONavigator()
        
        # Fleet state
        self.robots: dict[int, RobotState] = {}
        self.warehouse_bounds = (100.0, 60.0)  # width, height
        self.charging_stations = [
            (10, 10), (10, 50), (90, 10), (90, 50)
        ]
        self.obstacles: list[tuple[float, float]] = []
        
        # Problem tracking
        self.detected_collisions: list[dict] = []
        self.path_inefficiencies: list[dict] = []
        self.battery_alerts: list[dict] = []
        
        # Register domain-specific tools
        self._register_robotics_tools()
    
    def _register_robotics_tools(self) -> None:
        """Register robotics-specific tools."""
        self.register_tool(AgentTool(
            name="navigate_robot",
            description="Send a robot to a destination using RL navigation",
            parameters={
                "type": "object",
                "properties": {
                    "robot_id": {"type": "integer"},
                    "destination_x": {"type": "number"},
                    "destination_y": {"type": "number"}
                },
                "required": ["robot_id", "destination_x", "destination_y"]
            }
        ))
        
        self.register_tool(AgentTool(
            name="send_to_charging",
            description="Send a robot to the nearest charging station",
            parameters={
                "type": "object",
                "properties": {
                    "robot_id": {"type": "integer"}
                },
                "required": ["robot_id"]
            }
        ))
        
        self.register_tool(AgentTool(
            name="adjust_speed",
            description="Adjust robot speed for safety or efficiency",
            parameters={
                "type": "object",
                "properties": {
                    "robot_id": {"type": "integer"},
                    "speed_factor": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["robot_id", "speed_factor"]
            }
        ))
        
        self.register_tool(AgentTool(
            name="reroute_robot",
            description="Calculate new route to avoid collision or obstacle",
            parameters={
                "type": "object",
                "properties": {
                    "robot_id": {"type": "integer"},
                    "avoid_zone": {"type": "object"}
                },
                "required": ["robot_id"]
            }
        ))
    
    async def initialize(self) -> None:
        """Initialize the robotics agent."""
        await super().initialize()
        await self.navigator.load_model(settings.rl_policy_path)
        
        # Initialize robot fleet
        for i in range(1, settings.mock_robot_count + 1):
            # Stage 28 de-mock (G-082): DETERMINISTIC id-derived initial fleet (reproducible; no RNG).
            _tasks = [None, "Transport to Stage 3", "Pick items", "Delivery"]
            _statuses = ["idle", "working", "charging"]
            self.robots[i] = RobotState(
                id=i,
                position_x=5 + (i * 7) % max(1, int(self.warehouse_bounds[0] - 10)),
                position_y=5 + (i * 11) % max(1, int(self.warehouse_bounds[1] - 10)),
                battery=30 + (i * 13) % 70,
                speed=(i % 3) * 0.5,
                status=_statuses[i % 3],
                task=_tasks[i % 4]
            )
        
        self.state.goals = [
            "Maximize fleet utilization",
            "Minimize collision risks",
            "Optimize battery management",
            "Reduce path lengths"
        ]
        
        logger.info("Robotics agent initialized", robot_count=len(self.robots))
    
    # =========================================================================
    # CORE AGENT METHODS
    # =========================================================================
    
    async def observe(self) -> dict:
        """Observe current state of the robot fleet."""
        # In production, this would read from sensors/state manager
        
        # Simulate robot movement
        await self._simulate_robot_movement()
        
        return {
            "robots": [r.to_dict() for r in self.robots.values()],
            "total_robots": len(self.robots),
            "active_robots": sum(1 for r in self.robots.values() if r.status == "working"),
            "charging_robots": sum(1 for r in self.robots.values() if r.status == "charging"),
            "idle_robots": sum(1 for r in self.robots.values() if r.status == "idle"),
            "warning_robots": sum(1 for r in self.robots.values() if r.status == "warning"),
            "average_battery": sum(r.battery for r in self.robots.values()) / len(self.robots),
            "charging_stations": self.charging_stations,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def analyze(self, observation: dict) -> dict:
        """Analyze fleet state for problems and opportunities."""
        problems = []
        opportunities = []
        
        # 1. Detect collision risks
        collisions = await self._detect_collision_risks()
        for collision in collisions:
            problems.append({
                "type": "collision_risk",
                "severity": "high",
                "robots": collision["robots"],
                "distance": collision["distance"],
                "description": f"Robots {collision['robots']} are {collision['distance']:.2f}m apart - collision risk!"
            })
        
        # 2. Detect low battery
        for robot in self.robots.values():
            if robot.battery < DomainConfig.Robotics.BATTERY_CRITICAL:
                problems.append({
                    "type": "battery_critical",
                    "severity": "critical",
                    "robot_id": robot.id,
                    "battery": robot.battery,
                    "description": f"Robot {robot.id} has critical battery ({robot.battery:.1f}%)"
                })
            elif robot.battery < DomainConfig.Robotics.BATTERY_WARNING:
                problems.append({
                    "type": "battery_warning",
                    "severity": "medium",
                    "robot_id": robot.id,
                    "battery": robot.battery,
                    "description": f"Robot {robot.id} has low battery ({robot.battery:.1f}%)"
                })
        
        # 3. Detect idle robots with work available
        idle_count = observation["idle_robots"]
        if idle_count > 5:  # Too many idle
            opportunities.append({
                "type": "idle_capacity",
                "priority": "medium",
                "idle_count": idle_count,
                "description": f"{idle_count} robots idle - opportunity for better task allocation"
            })
        
        # 4. Detect path inefficiencies
        inefficiencies = await self._detect_path_inefficiencies()
        for ineff in inefficiencies:
            problems.append({
                "type": "path_inefficiency",
                "severity": "low",
                **ineff
            })
        
        # 5. Detect charging station congestion
        station_usage = {}
        for robot in self.robots.values():
            if robot.status == "charging":
                station = self._nearest_charging_station(robot.position_x, robot.position_y)
                station_usage[station] = station_usage.get(station, 0) + 1
        
        for station, count in station_usage.items():
            if count > 2:  # More than 2 robots at one station
                problems.append({
                    "type": "charging_congestion",
                    "severity": "medium",
                    "station": station,
                    "robot_count": count,
                    "description": f"Charging station at {station} has {count} robots waiting"
                })
        
        # Store for reporting
        self.detected_collisions = [p for p in problems if p["type"] == "collision_risk"]
        self.battery_alerts = [p for p in problems if "battery" in p["type"]]
        
        return {
            "problems": problems,
            "opportunities": opportunities,
            "problem_count": len(problems),
            "critical_count": sum(1 for p in problems if p.get("severity") == "critical")
        }
    
    async def decide(self, observation: dict, analysis: dict) -> list[dict]:
        """Decide on actions to address problems."""
        actions = []
        
        # Priority 1: Handle critical battery
        for problem in analysis.get("problems", []):
            if problem.get("type") == "battery_critical":
                actions.append({
                    "tool": "send_to_charging",
                    "parameters": {"robot_id": problem["robot_id"]},
                    "priority": "critical",
                    "reason": problem["description"]
                })
        
        # Priority 2: Collision avoidance
        for problem in analysis.get("problems", []):
            if problem.get("type") == "collision_risk":
                robot1, robot2 = problem["robots"]
                # Slow down the faster robot or reroute
                actions.append({
                    "tool": "adjust_speed",
                    "parameters": {"robot_id": robot1, "speed_factor": 0.3},
                    "priority": "high",
                    "reason": f"Slow down robot {robot1} to avoid collision"
                })
        
        # Priority 3: Battery warnings
        for problem in analysis.get("problems", []):
            if problem.get("type") == "battery_warning":
                robot = self.robots.get(problem["robot_id"])
                if robot and robot.status != "charging":
                    actions.append({
                        "tool": "send_to_charging",
                        "parameters": {"robot_id": problem["robot_id"]},
                        "priority": "medium",
                        "reason": problem["description"]
                    })
        
        # Use LLM for complex decisions if needed
        if len(actions) < 2 and analysis.get("opportunities"):
            llm_actions = await self.plan_actions(
                observation,
                analysis.get("problems", []),
                analysis.get("opportunities", [])
            )
            actions.extend(llm_actions)
        
        return actions
    
    async def execute_action(self, action: dict) -> AgentAction:
        """Execute a robotics action."""
        start_time = datetime.utcnow()
        tool_name = action.get("tool", "unknown")
        params = action.get("parameters", {})
        
        result = None
        success = True
        
        try:
            if tool_name == "navigate_robot":
                result = await self._execute_navigate(params)
            elif tool_name == "send_to_charging":
                result = await self._execute_send_to_charging(params)
            elif tool_name == "adjust_speed":
                result = await self._execute_adjust_speed(params)
            elif tool_name == "reroute_robot":
                result = await self._execute_reroute(params)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
                success = False
                
        except Exception as e:
            result = {"error": str(e)}
            success = False
            logger.error(f"Action execution failed", tool=tool_name, error=str(e))
        
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return AgentAction(
            action_type=ActionType.EXECUTE,
            target_type="robot",
            target_id=params.get("robot_id"),
            action_name=tool_name,
            parameters=params,
            result=result,
            success=success,
            duration_ms=duration,
            reasoning=action.get("reason", "")
        )
    
    # =========================================================================
    # TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _execute_navigate(self, params: dict) -> dict:
        """Navigate robot to destination using RL policy."""
        robot_id = params["robot_id"]
        dest = (params["destination_x"], params["destination_y"])
        
        robot = self.robots.get(robot_id)
        if not robot:
            return {"error": f"Robot {robot_id} not found"}
        
        # Get RL action
        direction, speed = self.navigator.get_action(
            robot,
            dest,
            self.obstacles,
            list(self.robots.values())
        )
        
        # Update robot state
        robot.destination = dest
        robot.status = "working"
        robot.task = f"Navigating to ({dest[0]:.1f}, {dest[1]:.1f})"
        robot.speed = speed * DomainConfig.Robotics.MAX_SPEED
        
        return {
            "robot_id": robot_id,
            "destination": dest,
            "direction": direction,
            "speed": speed,
            "status": "navigating"
        }
    
    async def _execute_send_to_charging(self, params: dict) -> dict:
        """Send robot to nearest charging station."""
        robot_id = params["robot_id"]
        robot = self.robots.get(robot_id)
        
        if not robot:
            return {"error": f"Robot {robot_id} not found"}
        
        # Find nearest charging station
        nearest = self._nearest_charging_station(robot.position_x, robot.position_y)
        
        # Update robot state
        robot.destination = nearest
        robot.status = "working"
        robot.task = f"Moving to charging station at {nearest}"
        
        return {
            "robot_id": robot_id,
            "charging_station": nearest,
            "current_battery": robot.battery,
            "status": "en_route_to_charging"
        }
    
    async def _execute_adjust_speed(self, params: dict) -> dict:
        """Adjust robot speed."""
        robot_id = params["robot_id"]
        speed_factor = params["speed_factor"]
        
        robot = self.robots.get(robot_id)
        if not robot:
            return {"error": f"Robot {robot_id} not found"}
        
        old_speed = robot.speed
        robot.speed = speed_factor * DomainConfig.Robotics.MAX_SPEED
        
        return {
            "robot_id": robot_id,
            "old_speed": old_speed,
            "new_speed": robot.speed,
            "speed_factor": speed_factor
        }
    
    async def _execute_reroute(self, params: dict) -> dict:
        """Reroute robot to avoid zone."""
        robot_id = params["robot_id"]
        robot = self.robots.get(robot_id)
        
        if not robot:
            return {"error": f"Robot {robot_id} not found"}
        
        # Add avoid zone to obstacles temporarily
        avoid_zone = params.get("avoid_zone", {})
        if avoid_zone:
            self.obstacles.append((avoid_zone.get("x", 0), avoid_zone.get("y", 0)))
        
        # Recalculate path
        if robot.destination:
            direction, speed = self.navigator.get_action(
                robot,
                robot.destination,
                self.obstacles,
                list(self.robots.values())
            )
            
            return {
                "robot_id": robot_id,
                "new_direction": direction,
                "new_speed": speed,
                "status": "rerouted"
            }
        
        return {"robot_id": robot_id, "status": "no_destination"}
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _nearest_charging_station(self, x: float, y: float) -> tuple[float, float]:
        """Find nearest charging station."""
        nearest = self.charging_stations[0]
        min_dist = float('inf')
        
        for station in self.charging_stations:
            dist = math.sqrt((station[0] - x)**2 + (station[1] - y)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = station
        
        return nearest
    
    async def _detect_collision_risks(self) -> list[dict]:
        """Detect pairs of robots at collision risk."""
        collisions = []
        robot_list = list(self.robots.values())
        
        for i, r1 in enumerate(robot_list):
            for r2 in robot_list[i+1:]:
                dist = math.sqrt(
                    (r1.position_x - r2.position_x)**2 +
                    (r1.position_y - r2.position_y)**2
                )
                if dist < DomainConfig.Robotics.COLLISION_RADIUS * 3:
                    collisions.append({
                        "robots": [r1.id, r2.id],
                        "distance": dist,
                        "positions": [(r1.position_x, r1.position_y), (r2.position_x, r2.position_y)]
                    })
        
        return collisions
    
    async def _detect_path_inefficiencies(self) -> list[dict]:
        """Detect suboptimal robot paths."""
        inefficiencies = []
        
        for robot in self.robots.values():
            if robot.destination and robot.status == "working":
                # Calculate direct distance
                direct = math.sqrt(
                    (robot.destination[0] - robot.position_x)**2 +
                    (robot.destination[1] - robot.position_y)**2
                )
                
                # If robot is moving but not making progress (simplified check)
                if robot.speed < 0.2 and direct > 5:
                    inefficiencies.append({
                        "robot_id": robot.id,
                        "distance_remaining": direct,
                        "speed": robot.speed,
                        "description": f"Robot {robot.id} is slow ({robot.speed:.1f} m/s) with {direct:.1f}m to go"
                    })
        
        return inefficiencies
    
    async def _simulate_robot_movement(self) -> None:
        """Simulate robot movement for demo mode."""
        for robot in self.robots.values():
            # Update battery
            if robot.status == "charging":
                robot.battery = min(100, robot.battery + DomainConfig.Robotics.CHARGING_RATE)
                if robot.battery >= 100:
                    robot.status = "idle"
                    robot.task = None
            elif robot.status == "working":
                robot.battery = max(0, robot.battery - 0.05)
            
            # Update position if working
            if robot.destination and robot.status == "working":
                dx = robot.destination[0] - robot.position_x
                dy = robot.destination[1] - robot.position_y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist < 1:
                    # Arrived
                    robot.destination = None
                    robot.status = "idle"
                    robot.task = None
                else:
                    # Move toward destination
                    speed = robot.speed * 0.1  # Scale for simulation
                    robot.position_x += (dx / dist) * speed
                    robot.position_y += (dy / dist) * speed
            
            # Stage 28 de-mock (G-082): idle robots hold position (no fabricated random wander).
            # Real robot motion comes from the VDA 5050 fleet path (Stage 16), not RNG.
            
            # Check battery warnings
            if robot.battery < DomainConfig.Robotics.BATTERY_CRITICAL and robot.status != "charging":
                robot.status = "warning"
    
    def get_fleet_visualization_data(self) -> dict:
        """Get data for 3D visualization."""
        return {
            "robots": [
                {
                    **r.to_dict(),
                    "color": self._get_robot_color(r),
                    "trail": []  # Path history for visualization
                }
                for r in self.robots.values()
            ],
            "charging_stations": [
                {"position": {"x": s[0], "y": s[1]}, "in_use": False}
                for s in self.charging_stations
            ],
            "obstacles": [
                {"position": {"x": o[0], "y": o[1]}, "radius": 1}
                for o in self.obstacles
            ],
            "collision_risks": self.detected_collisions,
            "warehouse": {
                "width": self.warehouse_bounds[0],
                "height": self.warehouse_bounds[1]
            }
        }
    
    def _get_robot_color(self, robot: RobotState) -> str:
        """Get color for robot visualization."""
        if robot.status == "error":
            return "#ff3366"  # Red
        elif robot.status == "warning":
            return "#ffaa00"  # Orange
        elif robot.status == "charging":
            return "#9933ff"  # Purple
        elif robot.status == "working":
            return "#00aaff"  # Blue
        else:
            return "#00ff88"  # Green (idle)
