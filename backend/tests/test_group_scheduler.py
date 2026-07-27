"""Stage 7 depth-hardening — group maintenance env + MaskablePPO scheduler tests.

The env-mechanics + masking + determinism tests need no trained policy. The scheduler accuracy/availability
tests skip honestly when the SB3 policy is absent.
"""
from __future__ import annotations

import numpy as np
import pytest

from training.stage_07_rl_intervention.group_env import (
    GroupMaintenanceEnv, GroupEnvConfig, greedy_urgent_action, threshold_action,
)
from ml.group_scheduler_rl import GroupSchedulerRL, get_group_scheduler_rl, ModelUnavailableError


# ---- env mechanics (no policy needed) --------------------------------------

def test_action_mask_noop_always_legal_and_shape():
    env = GroupMaintenanceEnv(GroupEnvConfig(seed=1))
    env.reset(seed=1)
    m = env.action_masks()
    assert m.shape == (env.cfg.n_zones + 1,)
    assert bool(m[0]) is True  # no-op always legal


def test_crew_busy_masks_all_dispatch():
    env = GroupMaintenanceEnv(GroupEnvConfig(seed=2))
    env.reset(seed=2)
    env._crew_busy = 2  # force busy
    m = env.action_masks()
    assert bool(m[0]) is True
    assert not m[1:].any(), "no dispatch should be legal while the crew is busy"


def test_env_is_deterministic_per_seed():
    def run(seed):
        env = GroupMaintenanceEnv(GroupEnvConfig(seed=seed)); env.reset(seed=seed)
        R, done = 0.0, False
        while not done:
            _, r, term, trunc, _ = env.step(0)  # no-op policy
            R += r; done = term or trunc
        return R
    assert run(5) == run(5)            # same seed → identical return
    assert run(5) != run(6)            # different seed → different campaign


def test_batching_rule_beats_greedy_on_average():
    """The env has genuine GROUP structure: a batching-aware rule should beat fix-one-at-a-time greedy."""
    def run(policy, seeds):
        outs = []
        for s in seeds:
            env = GroupMaintenanceEnv(GroupEnvConfig(seed=s)); obs, _ = env.reset(seed=s)
            R, done = 0.0, False
            while not done:
                obs, r, term, trunc, _ = env.step(policy(env)); R += r; done = term or trunc
            outs.append(R)
        return float(np.mean(outs))
    seeds = range(200, 220)
    assert run(threshold_action, seeds) > run(greedy_urgent_action, seeds)


# ---- scheduler inference glue ----------------------------------------------

def test_scheduler_honest_unavailable(tmp_path):
    s = GroupSchedulerRL(weights_path=tmp_path / "missing.zip")
    assert s.is_available() is False
    with pytest.raises(ModelUnavailableError):
        s.act(np.zeros(env_obs_dim(), dtype=np.float32), action_masks=np.array([True, True, False, False]))


def env_obs_dim() -> int:
    e = GroupMaintenanceEnv(GroupEnvConfig()); return e.observation_space.shape[0]


@pytest.mark.skipif(not get_group_scheduler_rl().is_available(),
                    reason="trained MaskablePPO unavailable (honest skip)")
def test_scheduler_runs_and_beats_noop():
    """A sanity floor: the trained policy must massively beat the do-nothing policy on held-out seeds."""
    sched = get_group_scheduler_rl()
    def ret(policy, seeds):
        outs = []
        for s in seeds:
            env = GroupMaintenanceEnv(GroupEnvConfig(seed=s)); obs, _ = env.reset(seed=s)
            R, done = 0.0, False
            while not done:
                a = policy(env, obs); obs, r, term, trunc, _ = env.step(a); R += r; done = term or trunc
            outs.append(R)
        return float(np.mean(outs))
    seeds = range(150, 160)
    rl = ret(lambda e, o: sched.act(o, e.action_masks()), seeds)
    noop = ret(lambda e, o: 0, seeds)
    assert rl > noop, f"trained RL ({rl:.1f}) must beat no-op ({noop:.1f})"
