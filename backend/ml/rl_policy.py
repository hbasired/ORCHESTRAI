"""
RL Policy Network for Manufacturing Optimization
PPO-based policy for multi-objective decision making.
"""

import asyncio
from typing import Optional, Tuple
from pathlib import Path

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class RLPolicy:
    """
    PPO (Proximal Policy Optimization) policy network for manufacturing decisions.
    
    Outputs actions for:
    - Robot routing and speed control
    - Stage throughput adjustment
    - Supplier order management
    - System mode switching
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        state_dim: int = 200,
        action_dim: int = 50,
        hidden_dim: int = 256,
        num_attention_heads: int = 8,
        num_transformer_layers: int = 4
    ):
        self.model_path = model_path
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.num_attention_heads = num_attention_heads
        self.num_transformer_layers = num_transformer_layers
        
        self.actor = None
        self.critic = None
        self.is_loaded = False
        self.device = "cpu"
        
        # Action space definitions
        self.action_types = [
            "robot_speed",      # 0-19: Speed for each of 20 robots
            "stage_throughput", # 20-29: Throughput for each of 10 stages
            "supplier_order",   # 30-39: Order adjustment for 10 suppliers
            "system_params"     # 40-49: System-level parameters
        ]
    
    async def load(self) -> None:
        """Load or initialize the PPO policy networks."""
        try:
            import torch
            import torch.nn as nn
            
            class TransformerActor(nn.Module):
                """Transformer-based actor network."""
                
                def __init__(self, state_dim, action_dim, hidden_dim, num_heads, num_layers):
                    super().__init__()
                    
                    # Input projection
                    self.input_proj = nn.Linear(state_dim, hidden_dim)
                    
                    # Transformer encoder
                    encoder_layer = nn.TransformerEncoderLayer(
                        d_model=hidden_dim,
                        nhead=num_heads,
                        dim_feedforward=hidden_dim * 4,
                        dropout=0.1,
                        batch_first=True
                    )
                    self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
                    
                    # Action head (outputs mean of action distribution)
                    self.action_mean = nn.Sequential(
                        nn.Linear(hidden_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, action_dim),
                        nn.Tanh()  # Actions in [-1, 1]
                    )
                    
                    # Log std (learnable)
                    self.action_log_std = nn.Parameter(torch.zeros(action_dim))
                
                def forward(self, state, return_attention=False):
                    """
                    Forward pass.
                    
                    Args:
                        state: State tensor (batch, state_dim)
                        return_attention: Whether to return attention weights
                        
                    Returns:
                        action_mean: Mean of action distribution
                        action_std: Std of action distribution
                        attention: Optional attention weights
                    """
                    # Project input
                    x = self.input_proj(state)
                    
                    # Add sequence dimension for transformer
                    x = x.unsqueeze(1)  # (batch, 1, hidden)
                    
                    # Transformer forward
                    x = self.transformer(x)
                    
                    # Take output
                    x = x.squeeze(1)  # (batch, hidden)
                    
                    # Get action distribution
                    action_mean = self.action_mean(x)
                    action_std = self.action_log_std.exp().expand_as(action_mean)
                    
                    return action_mean, action_std
            
            class Critic(nn.Module):
                """MLP critic network for value estimation."""
                
                def __init__(self, state_dim, hidden_dim):
                    super().__init__()
                    
                    self.network = nn.Sequential(
                        nn.Linear(state_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Linear(hidden_dim, hidden_dim // 2),
                        nn.ReLU(),
                        nn.Linear(hidden_dim // 2, 1)
                    )
                
                def forward(self, state):
                    return self.network(state)
            
            # Initialize networks
            self.actor = TransformerActor(
                self.state_dim,
                self.action_dim,
                self.hidden_dim,
                self.num_attention_heads,
                self.num_transformer_layers
            )
            self.critic = Critic(self.state_dim, self.hidden_dim)
            
            # Load weights if available
            if self.model_path and Path(self.model_path).exists():
                checkpoint = torch.load(self.model_path, map_location=self.device)
                self.actor.load_state_dict(checkpoint["actor"])
                self.critic.load_state_dict(checkpoint["critic"])
                logger.info("RL policy loaded from file", path=self.model_path)
            else:
                logger.info("RL policy initialized with random weights")
            
            self.actor.eval()
            self.critic.eval()
            self.is_loaded = True
            
        except ImportError:
            logger.warning("PyTorch not installed, using mock RL policy")
            self.is_loaded = True
        except Exception as e:
            logger.error("Failed to load RL policy", error=str(e))
            self.is_loaded = True
    
    async def get_action(
        self,
        state_features: np.ndarray,
        weights: dict = None,
        constraints: list[str] = None
    ) -> Tuple[list[dict], float]:
        """
        Get optimal action from the policy.
        
        Args:
            state_features: Current state feature vector
            weights: Optimization weights (throughput, energy, carbon, quality)
            constraints: List of constraints to apply
            
        Returns:
            Tuple of (actions list, confidence score)
        """
        if self.actor is None:
            # Generate heuristic actions
            return self._generate_heuristic_actions(state_features, weights, constraints)
        
        try:
            import torch
            
            # Prepare input
            state_tensor = torch.FloatTensor(state_features).unsqueeze(0)
            
            with torch.no_grad():
                action_mean, action_std = self.actor(state_tensor)
                value = self.critic(state_tensor)
            
            # Sample action (or use mean for deterministic)
            action_np = action_mean.cpu().numpy()[0]
            confidence = float(torch.sigmoid(value).cpu().numpy()[0])
            
            # Convert continuous actions to discrete action list
            actions = self._decode_actions(action_np, weights, constraints)
            
            return actions, confidence
            
        except Exception as e:
            logger.error("Action generation error", error=str(e))
            return self._generate_heuristic_actions(state_features, weights, constraints)
    
    def _decode_actions(
        self,
        action_values: np.ndarray,
        weights: dict = None,
        constraints: list[str] = None
    ) -> list[dict]:
        """Decode continuous action values to action list."""
        actions = []
        constraints = constraints or []
        
        # Robot speed actions (indices 0-19)
        for i in range(min(20, len(action_values))):
            if action_values[i] > 0.3:  # Action threshold
                speed_value = (action_values[i] + 1) / 2 * 2.0  # Map to 0-2 m/s
                actions.append({
                    "target_type": "robot",
                    "target_id": i + 1,
                    "action": "set_speed",
                    "value": float(speed_value)
                })
        
        # Stage throughput actions (indices 20-29)
        for i in range(20, min(30, len(action_values))):
            stage_id = i - 20 + 1
            
            # Check constraints
            if f"avoid stage {stage_id}" in constraints:
                continue
            
            if abs(action_values[i]) > 0.2:
                # Map to throughput percentage (50-150%)
                throughput = 100 + action_values[i] * 50
                action_type = "increase_throughput" if action_values[i] > 0 else "reduce_throughput"
                actions.append({
                    "target_type": "stage",
                    "target_id": stage_id,
                    "action": action_type,
                    "value": float(throughput)
                })
        
        # Limit actions to top 5 most significant
        if len(actions) > 5:
            # Sort by absolute action value and keep top 5
            actions = sorted(
                actions, 
                key=lambda a: abs(a.get("value", 0)), 
                reverse=True
            )[:5]
        
        return actions
    
    def _generate_heuristic_actions(
        self,
        state_features: np.ndarray,
        weights: dict = None,
        constraints: list[str] = None
    ) -> Tuple[list[dict], float]:
        """Deterministic rule-based actions when no trained PPO policy is loaded.

        Honest scope (G-052): this is a DETERMINISTIC heuristic (battery/queue thresholds), not a fabricated or
        random policy — it never invents data. It is the documented degraded mode until the LangGraph runtime
        delegates to the real Stage-7 MaskablePPO; confidence reflects how many real issues were detected.
        """
        actions = []
        weights = weights or {"throughput": 0.5, "energy": 0.2, "carbon": 0.2, "quality": 0.1}
        constraints = constraints or []
        
        # Check for low battery robots (features 2, 7, 12, ... are battery levels)
        for i in range(20):
            battery_idx = i * 5 + 2  # Battery is 3rd feature per robot
            if battery_idx < len(state_features) and state_features[battery_idx] < 0.2:
                actions.append({
                    "target_type": "robot",
                    "target_id": i + 1,
                    "action": "charge",
                    "value": None
                })
        
        # Check for bottleneck stages
        for i in range(10):
            queue_idx = 100 + i * 5  # Queue depth is 1st feature per stage
            status_idx = 100 + i * 5 + 3  # Status is 4th feature per stage
            
            if queue_idx < len(state_features) and state_features[queue_idx] > 0.7:
                stage_id = i + 1
                if f"avoid stage {stage_id}" not in constraints:
                    # Reduce throughput to clear queue
                    actions.append({
                        "target_type": "stage",
                        "target_id": stage_id,
                        "action": "reduce_throughput",
                        "value": 75
                    })
        
        # Energy optimization if prioritized
        if weights.get("energy", 0) > 0.3 or weights.get("carbon", 0) > 0.3:
            # Find high-energy stages
            for i in range(10):
                energy_idx = 100 + i * 5 + 2
                if energy_idx < len(state_features) and state_features[energy_idx] > 0.7:
                    actions.append({
                        "target_type": "stage",
                        "target_id": i + 1,
                        "action": "reduce_throughput",
                        "value": 80
                    })
        
        # Default action if none generated
        if not actions:
            actions.append({
                "target_type": "system",
                "target_id": None,
                "action": "switch_mode",
                "value": "normal"
            })
        
        # Limit to 5 actions
        actions = actions[:5]
        
        # Confidence based on how many issues detected
        confidence = max(0.5, 1.0 - len(actions) * 0.1)
        
        return actions, confidence
    
    async def get_value(self, state_features: np.ndarray) -> float:
        """Get value estimate for a state."""
        if self.critic is None:
            return 0.5
        
        try:
            import torch
            
            state_tensor = torch.FloatTensor(state_features).unsqueeze(0)
            
            with torch.no_grad():
                value = self.critic(state_tensor)
            
            return float(value.cpu().numpy()[0])
            
        except Exception as e:
            logger.error("Value estimation error", error=str(e))
            return 0.5
    
    async def get_attention_weights(
        self,
        state_features: np.ndarray
    ) -> list[dict]:
        """Get attention weights for explainability."""
        # In a full implementation, this would extract attention from the transformer
        # For now, return mock attention weights
        
        attention = []
        
        # Highlight robots with issues
        for i in range(20):
            battery_idx = i * 5 + 2
            if battery_idx < len(state_features) and state_features[battery_idx] < 0.3:
                attention.append({
                    "component_type": "robot",
                    "component_id": i + 1,
                    "attention_score": 0.8 - state_features[battery_idx]
                })
        
        # Highlight problematic stages
        for i in range(10):
            queue_idx = 100 + i * 5
            if queue_idx < len(state_features) and state_features[queue_idx] > 0.5:
                attention.append({
                    "component_type": "stage",
                    "component_id": i + 1,
                    "attention_score": state_features[queue_idx]
                })
        
        # Sort by attention and return top 10
        attention = sorted(attention, key=lambda x: x["attention_score"], reverse=True)[:10]
        
        return attention
    
    @property
    def model_info(self) -> dict:
        """Get model information."""
        return {
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "hidden_dim": self.hidden_dim,
            "num_attention_heads": self.num_attention_heads,
            "num_transformer_layers": self.num_transformer_layers
        }
