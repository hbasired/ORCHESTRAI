"""InterventionEnv — a headless, seeded RL environment over SimWorld.

The decision problem (KB_25 step 4, INTERVENE): a plant has ONE maintenance crew
(capacity constraint) and several machines that crack at near-overlapping times.
At each decision step the agent either does nothing or dispatches the crew to one
at-risk machine for preventive maintenance. A crack left untended past its ETA
becomes an unplanned breakdown costing 2.5x MTTR (secondary damage); preventive
maintenance costs 0.5x MTTR. With the crew contended, a greedy "fix the first
at-risk machine" rule mis-prioritises and lets the more-urgent machine fail —
that is the gap a learned priority policy can close. This is the regime where RL
can genuinely beat the near-optimal Stage-6 rules, and it is measured in
crack-breakdowns-prevented (the robust metric, per the Stage-6 independent audit).

Design notes (honesty):
- The crew-capacity constraint lives HERE, not in SimWorld — Stage 6 behaviour
  (unlimited implicit crew) is unchanged, so no Stage-6 test or A/B regresses.
- The per-machine risk score is the real failure-predictor `p_fail` when the
  trained brain is available; otherwise it falls back to the ground-truth
  `crack_proximity` from the sim (so the env + PPO are testable without xgboost).
  Which signal was used is recorded by the caller into the model metrics — the
  train/inference signal gap is disclosed in the model card.
- Deterministic per (seed, episode_index): same crack campaign, same sim RNG.

The env is plain (reset/step) — no gymnasium dependency. Observations and actions
are numpy; PPO consumes them directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from ml.failure_predictor import FailurePredictor, get_failure_predictor
from simulation.calibration import STAGES
from simulation.entities import Incident, InjectRequest
from simulation.sim_world import SimWorld

N_STAGES = len(STAGES)               # 10
FEATURES_PER_STAGE = 5               # at_risk, risk_score, tool_wear_norm, queue_load, busy/broken
OBS_DIM = N_STAGES * FEATURES_PER_STAGE + 1   # + crew_free flag
ACT_DIM = N_STAGES + 1               # 0 = no-op; k = dispatch crew to stage (k-1)

# Risk gate: a machine counts as "at-risk" once its risk score crosses this.
AT_RISK_THRESHOLD = 0.30
# Safety-shield critical proximity: at/above this the shield forces maintenance
# (used at inference, and as the env's notion of "should obviously act").
CRITICAL_PROXIMITY = 0.85


@dataclass
class EnvConfig:
    """Episode shape + reward weights (mirrored into config.yaml)."""

    sim_hours: float = 2.5
    decision_interval_s: float = 90.0
    crew_capacity: int = 1
    n_cracks: int = 4
    crack_eta_minutes: float = 12.0
    # Reward weights.
    #   - Outcome terms (the true objective): breakdown penalty + throughput.
    #   - Shaping term (objective-aligned, dense): risk_exposure_cost penalises
    #     leaving at-risk machines unattended each step. It does NOT tell the
    #     agent WHICH machine to pick — prioritising the highest-risk one to
    #     minimise breakdowns is still learned. Documented in the ADR + card.
    throughput_reward_per_unit: float = 0.02
    breakdown_penalty: float = 50.0
    maintenance_step_cost: float = 0.10
    invalid_action_cost: float = 0.05
    risk_exposure_cost: float = 2.0   # dense shaping: -cost * sum(risk of unattended at-risk machines)
    use_predictor: bool = True


class InterventionEnv:
    """Headless SimWorld RL env. Construct, then `reset(episode_index)` / `step(action)`."""

    obs_dim = OBS_DIM
    act_dim = ACT_DIM

    def __init__(self, config: Optional[EnvConfig] = None, *,
                 base_seed: int = 70000, predictor: Optional[FailurePredictor] = None) -> None:
        self.cfg = config or EnvConfig()
        self.base_seed = int(base_seed)
        self._predictor = predictor
        self._predictor_ready: Optional[bool] = None
        self._risk_cache: dict = {}
        self.world: Optional[SimWorld] = None
        self._t = 0.0
        self._horizon = self.cfg.sim_hours * 3600.0
        self._crack_plan: list[tuple[float, int]] = []
        self._in_maintenance: dict[int, float] = {}   # stage_id -> maintenance_end_time
        self._last_units_complete = 0
        self._last_crack_breakdowns = 0
        self._episode_index = 0

    # ---- predictor (optional; falls back to ground-truth proximity) ---------

    def _risk_score(self, stage) -> float:
        """Per-machine risk in [0,1]: predictor p_fail if available, else proximity.

        Memoised per (stage_id, sim-time) — within one decision sub-step the same
        machine's risk is queried by `_observe`, `_is_decision_point` and
        `_accrue_reward`; caching avoids redundant XGBoost calls (keeps the
        predictor-fed path fast enough to train/eval on CPU).
        """
        key = (stage.cfg.stage_id, round(float(self._t), 1))
        cached = self._risk_cache.get(key)
        if cached is not None:
            return cached
        val = self._risk_score_uncached(stage)
        self._risk_cache[key] = val
        return val

    def _risk_score_uncached(self, stage) -> float:
        if self.cfg.use_predictor:
            if self._predictor is None:
                self._predictor = get_failure_predictor()
            if self._predictor_ready is None:
                self._predictor_ready = self._predictor.is_available()
            if self._predictor_ready:
                t = stage.telemetry()
                try:
                    p = self._predictor.predict_failure(
                        type_=t["type_"], air_temp_k=t["air_temp_k"],
                        process_temp_k=t["process_temp_k"], rot_speed_rpm=t["rot_speed_rpm"],
                        torque_nm=t["torque_nm"], tool_wear_min=t["tool_wear_min"],
                    )
                    return float(p["p_fail"])
                except Exception:
                    pass
        # Honest fallback: ground-truth degradation proximity (real sim state).
        return float(stage.crack_proximity())

    # ---- crack campaign (deterministic per (seed, episode)) -----------------

    def _make_crack_plan(self, rng: np.random.Generator) -> list[tuple[float, int]]:
        """Schedule n_cracks at randomized times/stages, with some near-overlaps
        so the single crew is genuinely contended."""
        plan = []
        # Cluster two cracks early + close together to force crew contention.
        clustered_t = float(rng.uniform(300, 600))
        s1, s2 = rng.choice(N_STAGES, size=2, replace=False)
        plan.append((clustered_t, int(s1)))
        plan.append((clustered_t + float(rng.uniform(30, 120)), int(s2)))
        for _ in range(max(0, self.cfg.n_cracks - 2)):
            t = float(rng.uniform(600, self._horizon - 1200))
            s = int(rng.integers(0, N_STAGES))
            plan.append((t, s))
        plan.sort()
        return plan

    # ---- gym-like API -------------------------------------------------------

    SUB_STEP_S = 30.0   # sim granularity while advancing to the next decision point

    def reset(self, episode_index: int = 0) -> np.ndarray:
        self._episode_index = int(episode_index)
        seed = self.base_seed + self._episode_index
        self.world = SimWorld(seed=seed)
        self._t = 0.0
        self._risk_cache = {}
        self._in_maintenance = {}
        self._last_units_complete = 0
        self._last_crack_breakdowns = 0
        plan_rng = np.random.default_rng(seed ^ 0x5DEECE66D)
        self._crack_plan = self._make_crack_plan(plan_rng)
        self._injected = [False] * len(self._crack_plan)
        # Event-driven: advance to the first real decision point (≥1 at-risk
        # machine AND crew free). Reward accrued en route is discarded (no action
        # was possible before the first decision); `_done` carries terminal state.
        self._done = False
        self._advance_to_decision()
        return self._observe()

    def _is_decision_point(self) -> bool:
        """A decision is meaningful only when the crew is free AND ≥1 machine is at-risk."""
        if self._crew_busy_count() >= self.cfg.crew_capacity:
            return False
        return len(self._at_risk_stage_ids()) > 0

    def _advance_one_substep(self) -> None:
        """Advance the sim by one sub-step, injecting any cracks that fall due."""
        target = min(self._t + self.SUB_STEP_S, self._horizon)
        while True:
            next_due = None
            for i, (at, _sid) in enumerate(self._crack_plan):
                if not self._injected[i] and at <= target:
                    next_due = (i, at)
                    break
            if next_due is None:
                break
            i, at = next_due
            if at > self._t:
                self.world.env.run(until=at)
                self._t = at
            self._inject_due_cracks()
        if target > self._t:
            self.world.env.run(until=target)
        self._t = target

    def _accrue_reward(self) -> float:
        """Reward accrued since the last call: +throughput, −breakdowns,
        −maintenance occupancy, −outstanding-risk exposure (dense shaping)."""
        reward = 0.0
        units_now = self.world.total_orders_complete
        reward += self.cfg.throughput_reward_per_unit * (units_now - self._last_units_complete)
        self._last_units_complete = units_now

        crack_bd_now = sum(s.crack_breakdown_count for s in self.world.stages.values())
        new_breakdowns = crack_bd_now - self._last_crack_breakdowns
        if new_breakdowns > 0:
            reward -= self.cfg.breakdown_penalty * new_breakdowns
        self._last_crack_breakdowns = crack_bd_now

        reward -= self.cfg.maintenance_step_cost * self._crew_busy_count()

        outstanding = 0.0
        for stage in self.world.stages.values():
            if stage.status == "degraded":
                r = self._risk_score(stage)
                if r >= AT_RISK_THRESHOLD:
                    outstanding += r
        reward -= self.cfg.risk_exposure_cost * outstanding
        return reward

    def _advance_to_decision(self) -> float:
        """Run the sim forward (sub-step by sub-step, accruing reward) until the
        next decision point or the horizon. Always advances ≥1 sub-step so that
        a 'wait' action costs real time. Sets self._done at the horizon."""
        total = 0.0
        while self._t < self._horizon:
            self._advance_one_substep()
            total += self._accrue_reward()
            if self._t >= self._horizon:
                break
            if self._is_decision_point():
                break
        if self._t >= self._horizon:
            self._done = True
        return total

    def _inject_due_cracks(self) -> None:
        for i, (at, sid) in enumerate(self._crack_plan):
            if not self._injected[i] and self._t >= at:
                stage = self.world.stages[sid]
                if stage.status == "nominal":   # only crack a healthy machine
                    self.world._apply_incident(Incident.from_request(
                        InjectRequest(type="machine_crack", target_id=sid,
                                      details={"eta_minutes": self.cfg.crack_eta_minutes},
                                      severity="warning")))
                self._injected[i] = True

    def _crew_busy_count(self) -> int:
        # A stage is occupying the crew while it is in our tracked maintenance window.
        return sum(1 for sid, end in self._in_maintenance.items() if self._t < end)

    def _at_risk_stage_ids(self) -> list[int]:
        out = []
        for sid, stage in self.world.stages.items():
            if stage.status == "degraded" and self._risk_score(stage) >= AT_RISK_THRESHOLD:
                out.append(sid)
        return out

    def _observe(self) -> np.ndarray:
        obs = np.zeros(OBS_DIM, dtype=np.float32)
        for sid, stage in self.world.stages.items():
            base = sid * FEATURES_PER_STAGE
            degraded = stage.status == "degraded"
            risk = self._risk_score(stage) if degraded else 0.0
            at_risk = 1.0 if (degraded and risk >= AT_RISK_THRESHOLD) else 0.0
            wear_norm = min(1.0, stage.tool_wear_accum_min / 240.0)
            queue_load = stage.queue_depth() / max(1, stage.cfg.capacity)
            busy = 1.0 if stage.status in ("broken", "maintenance") else 0.0
            obs[base:base + FEATURES_PER_STAGE] = [at_risk, risk, wear_norm, queue_load, busy]
        crew_free = 1.0 if self._crew_busy_count() < self.cfg.crew_capacity else 0.0
        obs[-1] = crew_free
        return obs

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict]:
        """One DECISION-POINT step (event-driven). At entry the crew is free and
        ≥1 machine is at-risk. action: 0 = wait (don't dispatch now); k = dispatch
        the crew to stage (k-1). After applying the action the sim advances to the
        next decision point (or the horizon), accruing reward en route.
        """
        reward = 0.0
        info: dict[str, Any] = {"invalid": False, "maintained": None}

        # 1. Apply the dispatch action at this decision point.
        if action != 0:
            sid = action - 1
            stage = self.world.stages.get(sid)
            crew_free = self._crew_busy_count() < self.cfg.crew_capacity
            if crew_free and stage is not None and stage.status == "degraded":
                duration = 0.5 * stage.cfg.mttr_seconds  # preventive maintenance cost
                if stage.start_maintenance(duration_seconds=duration):
                    self._in_maintenance[sid] = self._t + duration
                    info["maintained"] = sid
                else:
                    reward -= self.cfg.invalid_action_cost
                    info["invalid"] = True
            else:
                # Dispatched to a machine that is not at-risk / crew busy: invalid.
                reward -= self.cfg.invalid_action_cost
                info["invalid"] = True

        # 2. Advance to the next decision point, accruing reward over the interval.
        reward += self._advance_to_decision()

        info["t"] = self._t
        info["crack_breakdowns"] = self._last_crack_breakdowns
        return self._observe(), float(reward), self._done, info

    # ---- episode-level metrics (for eval) -----------------------------------

    def episode_metrics(self) -> dict:
        broken_s = 0.0
        maint_s = 0.0
        crack_bd = 0
        for stage in self.world.stages.values():
            broken_s += stage.time_broken_seconds
            maint_s += stage.time_maintenance_seconds
            crack_bd += stage.crack_breakdown_count
            if stage.status == "broken" and stage.last_mtbf_failure_at is not None:
                broken_s += self.world.env.now - stage.last_mtbf_failure_at
        return {
            "cracks_injected": len(self._crack_plan),
            "crack_breakdowns": crack_bd,
            "crack_breakdowns_prevented": len(self._crack_plan) - crack_bd,
            "unplanned_downtime_min": round(broken_s / 60.0, 2),
            "planned_maintenance_min": round(maint_s / 60.0, 2),
            "orders_complete": self.world.total_orders_complete,
        }


# --- baseline policies used by eval (no learning) ----------------------------

def policy_none(obs: np.ndarray) -> int:
    """Never intervene (the negative control)."""
    return 0


def policy_rules_greedy(obs: np.ndarray) -> int:
    """Greedy/FIFO rule: dispatch the crew to the FIRST at-risk machine (lowest
    stage id), if the crew is free. This is the capacity-constrained analogue of
    the Stage-6 "maintain on first at-risk detection" behaviour — the baseline
    PPO must beat to earn the default chooser slot."""
    crew_free = obs[-1] > 0.5
    if not crew_free:
        return 0
    for sid in range(N_STAGES):
        base = sid * FEATURES_PER_STAGE
        if obs[base] > 0.5:   # at_risk flag
            return sid + 1
    return 0


def policy_rules_priority(obs: np.ndarray) -> int:
    """Stronger rule: dispatch to the HIGHEST-risk at-risk machine. This is the
    smart human heuristic; PPO matching it is a success, beating it is a bonus."""
    crew_free = obs[-1] > 0.5
    if not crew_free:
        return 0
    best_sid, best_risk = None, -1.0
    for sid in range(N_STAGES):
        base = sid * FEATURES_PER_STAGE
        if obs[base] > 0.5 and obs[base + 1] > best_risk:
            best_risk = obs[base + 1]
            best_sid = sid
    return (best_sid + 1) if best_sid is not None else 0


def safety_shield(obs: np.ndarray, action: int, env: Optional[InterventionEnv] = None,
                  critical: float = CRITICAL_PROXIMITY) -> int:
    """Hard safety override (ml-engineer mandate). If the crew is free and some
    at-risk machine's risk score >= critical, FORCE maintenance on the highest-risk
    one regardless of the sampled `action`. Guarantees the shipped policy never
    ignores a near-certain failure even though the learned net is stochastic."""
    crew_free = obs[-1] > 0.5
    if not crew_free:
        return action
    best_sid, best_risk = None, -1.0
    for sid in range(N_STAGES):
        base = sid * FEATURES_PER_STAGE
        if obs[base] > 0.5 and obs[base + 1] > best_risk:
            best_risk = obs[base + 1]
            best_sid = sid
    if best_sid is not None and best_risk >= critical:
        return best_sid + 1
    return action


__all__ = [
    "InterventionEnv", "EnvConfig", "OBS_DIM", "ACT_DIM", "N_STAGES",
    "FEATURES_PER_STAGE", "AT_RISK_THRESHOLD", "CRITICAL_PROXIMITY",
    "policy_none", "policy_rules_greedy", "policy_rules_priority", "safety_shield",
]
