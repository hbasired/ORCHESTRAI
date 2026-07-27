"""Compact from-scratch PPO (discrete actions) — auditable, no heavy deps.

Standard PPO-clip with GAE-lambda, a shared-trunk actor-critic MLP, value-loss
and entropy bonus. Kept deliberately small and transparent so the independent
auditor can read every line — there is no hidden RL library doing the work.

Free-cost: torch (CPU, already pinned) + numpy only. Deterministic given a seed.
References: Schulman et al. 2017 (PPO); GAE Schulman et al. 2015.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class PPOConfig:
    obs_dim: int
    act_dim: int
    hidden: int = 64
    lr: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_eps: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    epochs_per_update: int = 4
    minibatch_size: int = 256
    max_grad_norm: float = 0.5
    seed: int = 0


class ActorCritic(nn.Module):
    """Shared-trunk MLP → (action logits, state value)."""

    def __init__(self, obs_dim: int, act_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
        )
        self.policy_head = nn.Linear(hidden, act_dim)
        self.value_head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.trunk(x)
        return self.policy_head(h), self.value_head(h).squeeze(-1)

    @torch.no_grad()
    def act(self, obs: np.ndarray, deterministic: bool = False) -> tuple[int, float, float]:
        """Return (action, log_prob, value) for one observation."""
        t = torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0)
        logits, value = self.forward(t)
        dist = torch.distributions.Categorical(logits=logits)
        action = torch.argmax(logits, dim=-1) if deterministic else dist.sample()
        return int(action.item()), float(dist.log_prob(action).item()), float(value.item())


@dataclass
class RolloutBuffer:
    obs: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    logprobs: list = field(default_factory=list)
    rewards: list = field(default_factory=list)
    values: list = field(default_factory=list)
    dones: list = field(default_factory=list)

    def add(self, obs, action, logp, reward, value, done):
        self.obs.append(obs); self.actions.append(action); self.logprobs.append(logp)
        self.rewards.append(reward); self.values.append(value); self.dones.append(done)

    def clear(self):
        self.__init__()

    def __len__(self):
        return len(self.obs)


def compute_gae(rewards, values, dones, last_value, gamma, lam):
    """Generalized Advantage Estimation. Returns (advantages, returns)."""
    n = len(rewards)
    adv = np.zeros(n, dtype=np.float32)
    last_gae = 0.0
    for t in reversed(range(n)):
        next_value = last_value if t == n - 1 else values[t + 1]
        next_nonterminal = 1.0 - float(dones[t])
        delta = rewards[t] + gamma * next_value * next_nonterminal - values[t]
        last_gae = delta + gamma * lam * next_nonterminal * last_gae
        adv[t] = last_gae
    returns = adv + np.asarray(values, dtype=np.float32)
    return adv, returns


class PPO:
    """PPO trainer. Collects rollouts via a step-callback and updates the net."""

    def __init__(self, cfg: PPOConfig) -> None:
        self.cfg = cfg
        torch.manual_seed(cfg.seed)
        np.random.seed(cfg.seed)
        self.net = ActorCritic(cfg.obs_dim, cfg.act_dim, cfg.hidden)
        self.opt = torch.optim.Adam(self.net.parameters(), lr=cfg.lr)

    def update(self, buf: RolloutBuffer, last_value: float) -> dict:
        cfg = self.cfg
        adv, returns = compute_gae(buf.rewards, buf.values, buf.dones, last_value,
                                   cfg.gamma, cfg.gae_lambda)
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)

        obs = torch.as_tensor(np.array(buf.obs), dtype=torch.float32)
        actions = torch.as_tensor(np.array(buf.actions), dtype=torch.int64)
        old_logp = torch.as_tensor(np.array(buf.logprobs), dtype=torch.float32)
        adv_t = torch.as_tensor(adv, dtype=torch.float32)
        ret_t = torch.as_tensor(returns, dtype=torch.float32)

        n = len(buf)
        idx = np.arange(n)
        last = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
        for _ in range(cfg.epochs_per_update):
            np.random.shuffle(idx)
            for start in range(0, n, cfg.minibatch_size):
                mb = idx[start:start + cfg.minibatch_size]
                logits, values = self.net(obs[mb])
                dist = torch.distributions.Categorical(logits=logits)
                new_logp = dist.log_prob(actions[mb])
                ratio = torch.exp(new_logp - old_logp[mb])
                surr1 = ratio * adv_t[mb]
                surr2 = torch.clamp(ratio, 1 - cfg.clip_eps, 1 + cfg.clip_eps) * adv_t[mb]
                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = F.mse_loss(values, ret_t[mb])
                entropy = dist.entropy().mean()
                loss = policy_loss + cfg.value_coef * value_loss - cfg.entropy_coef * entropy
                self.opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.net.parameters(), cfg.max_grad_norm)
                self.opt.step()
                last = {"policy_loss": float(policy_loss.item()),
                        "value_loss": float(value_loss.item()),
                        "entropy": float(entropy.item())}
        return last

    def save(self, path: str) -> None:
        torch.save({"state_dict": self.net.state_dict(),
                    "obs_dim": self.cfg.obs_dim, "act_dim": self.cfg.act_dim,
                    "hidden": self.cfg.hidden}, path)

    @staticmethod
    def load_net(path: str, map_location: str = "cpu") -> ActorCritic:
        # weights_only=True: the checkpoint holds only tensors + ints (no pickled
        # objects), so we load under the safe path — no arbitrary-code-execution
        # risk on torch.load (the project blocks .pkl for the same reason).
        ckpt = torch.load(path, map_location=map_location, weights_only=True)
        net = ActorCritic(int(ckpt["obs_dim"]), int(ckpt["act_dim"]), int(ckpt.get("hidden", 64)))
        net.load_state_dict(ckpt["state_dict"])
        net.eval()
        return net


def train_ppo(env_factory: Callable[[], object], cfg: PPOConfig, *,
              total_timesteps: int, rollout_steps: int = 2048,
              on_update: Optional[Callable[[int, dict, float], None]] = None) -> tuple[PPO, list]:
    """Train PPO against an env exposing reset(episode_index)->obs and
    step(action)->(obs, reward, done, info). Returns (ppo, return_history)."""
    ppo = PPO(cfg)
    buf = RolloutBuffer()
    return_history: list[float] = []

    env = env_factory()
    episode_index = 0
    obs = env.reset(episode_index)
    ep_return = 0.0
    steps = 0
    updates = 0
    while steps < total_timesteps:
        buf.clear()
        for _ in range(rollout_steps):
            action, logp, value = ppo.net.act(obs)
            next_obs, reward, done, _info = env.step(action)
            buf.add(obs, action, logp, reward, value, done)
            obs = next_obs
            ep_return += reward
            steps += 1
            if done:
                return_history.append(ep_return)
                ep_return = 0.0
                episode_index += 1
                obs = env.reset(episode_index)
        with torch.no_grad():
            _, last_value = ppo.net(torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0))
            last_value = float(last_value.item())
        stats = ppo.update(buf, last_value)
        updates += 1
        recent = float(np.mean(return_history[-10:])) if return_history else ep_return
        if on_update:
            on_update(updates, stats, recent)
    return ppo, return_history


__all__ = ["PPO", "PPOConfig", "ActorCritic", "RolloutBuffer", "compute_gae", "train_ppo"]
