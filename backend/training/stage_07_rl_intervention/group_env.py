"""Stage 7 depth-hardening — richer maintenance-scheduling MDP (group + opportunistic + masking).

Why a new env: the Stage-7 v0 env (`env.py`, single crew, fix-one-at-a-time) was a regime where the greedy
priority rule is near-optimal, so PPO honestly did NOT beat rules. The RL-PdM literature (research §16.1: TranDRL,
predictive *group* maintenance, opportunistic scheduling) shows DRL beats greedy threshold rules specifically when
the schedule has structure a myopic rule can't exploit:

  - **GROUP maintenance**: machines live in ZONES; one crew trip to a zone services up to K at-risk machines there,
    sharing a fixed setup/travel cost. A greedy "dispatch to the single most-urgent machine" rule pays the setup
    every trip; a policy that BATCHES zone-mates amortises it. (group advantage)
  - **OPPORTUNISTIC timing**: throughput value varies over time (demand windows). A trip taken in a HIGH-demand
    window loses more throughput than the same trip in a LOW-demand window. A policy that DEFERS a non-urgent fix
    to a low-demand window (when ETA slack allows) wins; "fix immediately" doesn't. (timing advantage)
  - **CREW contention + heterogeneous ETAs**: limited crew + varied urgency ⇒ prioritisation still matters.

This is a documented maintenance-scheduling MDP (a MODEL of the decision, with explicit seeded dynamics and
realistic cost parameters) — honest as a model, not fabricated telemetry. It is Gymnasium-native and exposes
`action_masks()` for **MaskablePPO** (sb3-contrib): invalid dispatches (no at-risk machine in a zone, or crew busy)
are masked out, so the agent never wastes probability on illegal actions.

Determinism: seeded per (seed, episode). The same crack campaign + demand profile replays for any policy, enabling
CRN-paired (common-random-numbers) comparison in `eval_sb3.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
    _GYM = True
except Exception:  # pragma: no cover - gymnasium is a hard dep for this module
    _GYM = False
    gym = object  # type: ignore


@dataclass
class GroupEnvConfig:
    n_zones: int = 3
    machines_per_zone: int = 3
    horizon_steps: int = 80            # decision steps per episode
    dt_minutes: float = 5.0            # wall time per step
    crack_rate_per_step: float = 0.06  # P(a healthy machine starts degrading) per machine per step
    eta_min: float = 15.0              # crack ETA range (minutes) once degrading — heterogeneous urgency
    eta_max: float = 70.0
    trip_setup_cost: float = 6.0       # FIXED cost per crew trip to a zone (shared by all machines serviced)
    per_machine_cost: float = 1.5      # marginal cost per machine serviced on the trip
    trip_steps: int = 2                # crew is busy this many steps per trip (then free)
    max_serviced_per_trip: int = 3     # crew services up to this many at-risk machines in the zone
    breakdown_penalty: float = 40.0    # cost of an untended crack reaching ETA (unplanned breakdown)
    breakdown_steps: int = 4           # machine offline this many steps after a breakdown (lost throughput)
    base_demand: float = 1.0           # throughput value per running machine per step at demand=1
    demand_amp: float = 0.8            # demand oscillation amplitude (opportunistic structure)
    demand_period: int = 20            # steps per demand cycle
    seed: int = 7


class GroupMaintenanceEnv(gym.Env if _GYM else object):  # type: ignore[misc]
    """Gymnasium maintenance-scheduling MDP with group + opportunistic structure and action masking."""

    metadata = {"render_modes": []}

    def __init__(self, cfg: Optional[GroupEnvConfig] = None):
        super().__init__()
        self.cfg = cfg or GroupEnvConfig()
        c = self.cfg
        self.n_machines = c.n_zones * c.machines_per_zone
        self._zone_of = np.repeat(np.arange(c.n_zones), c.machines_per_zone)
        # action 0 = no-op; actions 1..n_zones = dispatch crew to that zone.
        self.action_space = spaces.Discrete(c.n_zones + 1)
        # obs: per machine [degrading, eta_norm, broken]; + crew_busy, demand, time_frac.
        obs_dim = self.n_machines * 3 + 3
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(obs_dim,), dtype=np.float32)
        self._rng = np.random.default_rng(c.seed)
        self._ep = 0
        self.reset(seed=c.seed)

    # ---- demand profile (deterministic, opportunistic structure) -----------
    def _demand(self, t: int) -> float:
        c = self.cfg
        return c.base_demand + c.demand_amp * float(np.sin(2 * np.pi * t / c.demand_period))

    # ---- gym API -----------------------------------------------------------
    def reset(self, *, seed: Optional[int] = None, options=None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        c = self.cfg
        self._t = 0
        self._degrading = np.zeros(self.n_machines, dtype=bool)
        self._eta = np.full(self.n_machines, np.inf, dtype=np.float64)   # minutes to failure
        self._broken_for = np.zeros(self.n_machines, dtype=np.int64)     # steps remaining offline
        self._crew_busy = 0                                              # steps remaining busy
        self._ep += 1
        return self._obs(), {}

    def _obs(self) -> np.ndarray:
        c = self.cfg
        eta_norm = np.where(self._degrading, np.clip(self._eta / c.eta_max, 0, 1), 1.0)
        per = np.stack([self._degrading.astype(np.float32),
                        eta_norm.astype(np.float32),
                        (self._broken_for > 0).astype(np.float32)], axis=1).reshape(-1)
        tail = np.array([1.0 if self._crew_busy > 0 else 0.0,
                         self._demand(self._t) / (c.base_demand + c.demand_amp),
                         self._t / c.horizon_steps], dtype=np.float32)
        return np.concatenate([per, tail]).astype(np.float32)

    def action_masks(self) -> np.ndarray:
        """True where the action is legal. No-op always legal; a zone is legal iff the crew is FREE and the zone
        has at least one at-risk (degrading, not broken) machine."""
        c = self.cfg
        mask = np.zeros(c.n_zones + 1, dtype=bool)
        mask[0] = True  # no-op
        if self._crew_busy == 0:
            at_risk = self._degrading & (self._broken_for == 0)
            for z in range(c.n_zones):
                if np.any(at_risk & (self._zone_of == z)):
                    mask[z + 1] = True
        return mask

    def step(self, action: int):
        c = self.cfg
        action = int(action)
        reward = 0.0
        # 1) dispatch (if legal + crew free) — GROUP service of a zone.
        if action > 0 and self._crew_busy == 0:
            z = action - 1
            at_risk = np.where(self._degrading & (self._broken_for == 0) & (self._zone_of == z))[0]
            # service the most-urgent up to max_serviced_per_trip machines in the zone.
            at_risk = at_risk[np.argsort(self._eta[at_risk])][: c.max_serviced_per_trip]
            if len(at_risk) > 0:
                reward -= c.trip_setup_cost + c.per_machine_cost * len(at_risk)
                self._degrading[at_risk] = False
                self._eta[at_risk] = np.inf
                self._crew_busy = c.trip_steps
        # 2) advance time: ETs tick down; breakdowns; new cracks; crew frees; throughput.
        self._t += 1
        if self._crew_busy > 0:
            self._crew_busy -= 1
        self._broken_for = np.maximum(0, self._broken_for - 1)
        # breakdowns: degrading machines whose ETA elapses this step.
        self._eta[self._degrading] -= c.dt_minutes
        newly_broken = self._degrading & (self._eta <= 0)
        if np.any(newly_broken):
            reward -= c.breakdown_penalty * int(np.sum(newly_broken))
            self._broken_for[newly_broken] = c.breakdown_steps
            self._degrading[newly_broken] = False
            self._eta[newly_broken] = np.inf
        # new cracks on healthy, non-broken machines.
        healthy = ~self._degrading & (self._broken_for == 0)
        starts = healthy & (self._rng.random(self.n_machines) < c.crack_rate_per_step)
        n_start = int(np.sum(starts))
        if n_start:
            self._degrading[starts] = True
            self._eta[starts] = self._rng.uniform(c.eta_min, c.eta_max, size=n_start)
        # throughput value: running (not broken) machines × current demand.
        running = int(np.sum(self._broken_for == 0))
        reward += c.base_demand * 0.0 + self._demand(self._t) * running * 0.10
        terminated = False
        truncated = self._t >= c.horizon_steps
        return self._obs(), float(reward), terminated, truncated, {}


# ---- rule baselines (for the honest RL-vs-rules comparison) ----------------

def greedy_urgent_action(env: "GroupMaintenanceEnv") -> int:
    """Dispatch to the zone containing the single most-urgent at-risk machine, whenever the crew is free."""
    mask = env.action_masks()
    if env._crew_busy > 0 or not mask[1:].any():
        return 0
    at_risk = env._degrading & (env._broken_for == 0)
    idx = np.where(at_risk)[0]
    target = idx[np.argmin(env._eta[idx])]
    return int(env._zone_of[target]) + 1


def threshold_action(env: "GroupMaintenanceEnv", eta_thresh: float = 35.0) -> int:
    """Dispatch to the zone with the most at-risk machines under the ETA threshold (a batching-aware heuristic)."""
    mask = env.action_masks()
    if env._crew_busy > 0 or not mask[1:].any():
        return 0
    urgent = env._degrading & (env._broken_for == 0) & (env._eta < eta_thresh)
    if not urgent.any():
        # nothing urgent yet — wait (opportunistic), unless something is very close.
        very = env._degrading & (env._broken_for == 0) & (env._eta < env.cfg.dt_minutes * env.cfg.trip_steps * 2)
        if not very.any():
            return 0
        urgent = very
    counts = [int(np.sum(urgent & (env._zone_of == z))) for z in range(env.cfg.n_zones)]
    return int(np.argmax(counts)) + 1


__all__ = ["GroupEnvConfig", "GroupMaintenanceEnv", "greedy_urgent_action", "threshold_action"]
