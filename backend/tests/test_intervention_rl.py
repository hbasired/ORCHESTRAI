"""Stage 7 — RL intervention policy tests (env, PPO, shield, glue, contract).

Fast + deterministic. The env runs with use_predictor=False (ground-truth
proximity) so these tests need neither xgboost nor the trained weights, except
the explicitly weight-dependent tests, which skip honestly when absent.
"""
from __future__ import annotations

import numpy as np
import pytest

from training.stage_07_rl_intervention.env import (
    ACT_DIM, OBS_DIM, AT_RISK_THRESHOLD, CRITICAL_PROXIMITY, EnvConfig, InterventionEnv,
    policy_none, policy_rules_priority, safety_shield,
)
from training.stage_07_rl_intervention.ppo import PPOConfig, compute_gae, train_ppo


def _cfg():
    return EnvConfig(use_predictor=False, sim_hours=1.0, n_cracks=4)


# ---- env --------------------------------------------------------------------

def test_env_obs_action_dims():
    env = InterventionEnv(_cfg(), base_seed=70000)
    obs = env.reset(0)
    assert obs.shape == (OBS_DIM,)
    assert OBS_DIM == 51 and ACT_DIM == 11


def test_env_reset_deterministic_per_seed():
    a = InterventionEnv(_cfg(), base_seed=70000); a.reset(3)
    b = InterventionEnv(_cfg(), base_seed=70000); b.reset(3)
    assert a._crack_plan == b._crack_plan


def test_env_episode_runs_and_metrics_shape():
    env = InterventionEnv(_cfg(), base_seed=70000)
    obs = env.reset(1)
    done, n = False, 0
    while not done and n < 500:
        obs, r, done, info = env.step(policy_rules_priority(obs))
        assert obs.shape == (OBS_DIM,)
        assert isinstance(r, float)
        n += 1
    m = env.episode_metrics()
    for k in ("cracks_injected", "crack_breakdowns", "crack_breakdowns_prevented",
              "unplanned_downtime_min"):
        assert k in m
    assert m["crack_breakdowns"] + m["crack_breakdowns_prevented"] == m["cracks_injected"]


def test_decision_points_are_real():
    """Every step the env hands to the agent must be a genuine decision point
    (crew free AND >=1 at-risk machine) — that is the whole point of event-driven."""
    env = InterventionEnv(_cfg(), base_seed=70000)
    obs = env.reset(2)
    if not env._done:
        # at the first decision point at least one at_risk flag is set and crew free
        crew_free = obs[-1] > 0.5
        any_at_risk = any(obs[s * 5] > 0.5 for s in range(10))
        assert crew_free and any_at_risk


# ---- PPO --------------------------------------------------------------------

def test_compute_gae_basic():
    rewards = [1.0, 1.0, 1.0]
    values = [0.0, 0.0, 0.0]
    dones = [0, 0, 1]
    adv, ret = compute_gae(rewards, values, dones, last_value=0.0, gamma=1.0, lam=1.0)
    # With zero values + gamma=lam=1, advantage_t = sum of future rewards.
    assert np.allclose(adv, [3.0, 2.0, 1.0])
    assert np.allclose(ret, [3.0, 2.0, 1.0])


def test_ppo_learns_on_bandit():
    """Sanity: PPO must learn a trivial contextual bandit (proves the optimiser
    is correct independent of the hard sim env)."""
    class Bandit:
        def __init__(self, n=4, ep_len=15):
            self.n, self.ep_len = n, ep_len
        def reset(self, ep=0):
            self.rng = np.random.default_rng(1000 + ep); self.t = 0
            self.target = int(self.rng.integers(0, self.n))
            o = np.zeros(self.n, dtype=np.float32); o[self.target] = 1.0; return o
        def step(self, a):
            r = 1.0 if a == self.target else 0.0
            self.t += 1; done = self.t >= self.ep_len
            self.target = int(self.rng.integers(0, self.n))
            o = np.zeros(self.n, dtype=np.float32); o[self.target] = 1.0
            return o, r, done, {}
    cfg = PPOConfig(obs_dim=4, act_dim=4, seed=0, lr=3e-3, entropy_coef=0.01, minibatch_size=64)
    _, hist = train_ppo(lambda: Bandit(), cfg, total_timesteps=4000, rollout_steps=500)
    assert np.mean(hist[-5:]) > np.mean(hist[:5]) + 1.0   # measurably improved


# ---- safety shield ----------------------------------------------------------

def test_shield_forces_maintenance_on_critical_proximity():
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    obs[-1] = 1.0                 # crew free
    obs[3 * 5] = 1.0              # stage 3 at-risk flag
    obs[3 * 5 + 1] = 0.95         # stage 3 risk >= CRITICAL_PROXIMITY
    # Even if the net "wanted" a wrong action, the shield forces stage 3 (action 4).
    assert safety_shield(obs, action=0) == 4
    assert safety_shield(obs, action=10) == 4


def test_shield_noop_when_crew_busy():
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    obs[-1] = 0.0                 # crew busy
    obs[3 * 5] = 1.0; obs[3 * 5 + 1] = 0.99
    assert safety_shield(obs, action=0) == 0   # cannot dispatch a busy crew


def test_shield_passthrough_below_critical():
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    obs[-1] = 1.0
    obs[2 * 5] = 1.0; obs[2 * 5 + 1] = 0.5    # at-risk but below critical
    assert safety_shield(obs, action=0) == 0   # net's choice (wait) respected


# ---- inference glue + contract ----------------------------------------------

def test_rl_policy_honest_unavailable_on_missing_weights(tmp_path):
    from ml.intervention_rl import RLInterventionPolicy, ModelUnavailableError
    pol = RLInterventionPolicy(weights_path=tmp_path / "does_not_exist.pt")
    assert pol.is_available() is False
    with pytest.raises(ModelUnavailableError):
        pol.act(np.zeros(OBS_DIM, dtype=np.float32))


def test_select_chooser_contract():
    from services.intervention_policy import select_chooser, decide_intervention, DEFAULT_CHOOSER
    assert DEFAULT_CHOOSER == "rules"
    assert select_chooser("rules") is decide_intervention
    with pytest.raises(ValueError):
        select_chooser("nonsense")


# These need the trained weights — skip honestly if absent.
def _weights_available() -> bool:
    from ml.intervention_rl import get_rl_intervention_policy
    return get_rl_intervention_policy().is_available()


needs_weights = pytest.mark.skipif(not _weights_available(),
                                   reason="trained PPO policy unavailable (honest skip)")


@needs_weights
def test_rl_policy_act_returns_valid_action():
    from ml.intervention_rl import get_rl_intervention_policy
    pol = get_rl_intervention_policy()
    out = pol.act(np.zeros(OBS_DIM, dtype=np.float32))
    assert 0 <= out["action"] < ACT_DIM
    assert "shield_fired" in out


@needs_weights
def test_rl_decide_returns_intervention_decision():
    from ml.intervention_rl import get_rl_intervention_policy
    from services.intervention_policy import InterventionDecision, PREVENTIVE_MAINTENANCE
    pol = get_rl_intervention_policy()
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    obs[-1] = 1.0; obs[5 * 5] = 1.0; obs[5 * 5 + 1] = 0.95   # stage 5 critical
    decision = pol.decide(obs, stages={})
    assert isinstance(decision, InterventionDecision)
    assert decision.kind == PREVENTIVE_MAINTENANCE
    assert decision.stage_id == 5          # shield forced the genuinely at-risk machine


@needs_weights
def test_select_chooser_rl_returns_policy():
    from services.intervention_policy import select_chooser
    from ml.intervention_rl import RLInterventionPolicy
    assert isinstance(select_chooser("rl"), RLInterventionPolicy)
