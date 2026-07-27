"""Generate (telemetry-window -> true time-to-failure) data from SimWorld rollouts.

For each seeded rollout we inject a machine_crack with a RANDOMISED eta, then sample
the machine's AI4I-unit telemetry every `sample_period_s` during the degrading window
and label each length-`window_len` sequence with the TRUE remaining time-to-failure
(`crack_failure_at - now`, in minutes) at the window's end.

Honesty notes:
- The label is ground truth from the sim's own crack schedule — no fabrication.
- eta is VARIED across rollouts, so telemetry (which reflects crack *proximity*, not
  absolute time) under-determines TTF: the model can only learn EXPECTED TTF given the
  telemetry. It still beats a naive mean-TTF baseline because telemetry carries
  proximity information — that gap is the genuine, measurable win (eval.py).
- Deterministic per seed. The same physics-motivated telemetry mapping as Stage 6 (KB_05).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from simulation.calibration import STAGES
from simulation.entities import Incident, InjectRequest
from simulation.sim_world import SimWorld

# AI4I telemetry features used as the world-model input (same set the predictor uses).
FEATURES = ("air_temp_k", "process_temp_k", "rot_speed_rpm", "torque_nm", "tool_wear_min")
N_FEATURES = len(FEATURES)


@dataclass
class RolloutConfig:
    window_len: int = 6                 # samples of history fed to the LSTM
    sample_period_s: float = 30.0
    eta_min_minutes: float = 8.0        # randomised crack ETA range (varies TTF honestly)
    eta_max_minutes: float = 20.0
    warmup_s: float = 60.0              # let the plant settle before injecting
    min_proximity: float = 0.05         # start labelling once degradation is observable
    max_proximity: float = 0.97         # stop just before the break


def _telemetry_vector(stage) -> list[float]:
    t = stage.telemetry()
    return [float(t[f]) for f in FEATURES]


def generate_rollout(seed: int, stage_id: int, cfg: RolloutConfig,
                     rng: np.random.Generator) -> tuple[list[np.ndarray], list[float]]:
    """One rollout. Returns (windows, ttfs): each window is (window_len, N_FEATURES);
    each ttf is remaining minutes-to-failure at the window's last sample."""
    world = SimWorld(seed=seed)
    eta_min = float(rng.uniform(cfg.eta_min_minutes, cfg.eta_max_minutes))
    world.env.run(until=cfg.warmup_s)
    stage = world.stages[stage_id]
    world._apply_incident(Incident.from_request(
        InjectRequest(type="machine_crack", target_id=stage_id,
                      details={"eta_minutes": eta_min}, severity="warning")))
    fail_at = stage.crack_failure_at
    if fail_at is None:
        return [], []

    samples: list[tuple[float, list[float]]] = []   # (sim_time, feature_vector)
    t = world.env.now
    while t < fail_at - 1.0:
        world.env.run(until=t + cfg.sample_period_s)
        t = world.env.now
        if stage.status != "degraded":
            break
        prox = stage.crack_proximity()
        if prox < cfg.min_proximity:
            continue
        if prox > cfg.max_proximity:
            break
        samples.append((t, _telemetry_vector(stage)))

    windows, ttfs = [], []
    for i in range(cfg.window_len - 1, len(samples)):
        seq = np.array([samples[j][1] for j in range(i - cfg.window_len + 1, i + 1)],
                       dtype=np.float32)
        ttf_minutes = (fail_at - samples[i][0]) / 60.0
        if ttf_minutes <= 0:
            continue
        windows.append(seq)
        ttfs.append(float(ttf_minutes))
    return windows, ttfs


def build_dataset(seeds: list[int], cfg: Optional[RolloutConfig] = None,
                  stages_per_seed: Optional[list[int]] = None) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate many rollouts into (X, y). X: (N, window_len, N_FEATURES); y: (N,) TTF minutes."""
    cfg = cfg or RolloutConfig()
    if stages_per_seed is None:
        # A spread of stages (different cycle/MTBF profiles) for variety.
        stages_per_seed = [1, 3, 5, 7]
    all_w, all_t = [], []
    for seed in seeds:
        rng = np.random.default_rng(seed ^ 0x9E3779B9)
        for sid in stages_per_seed:
            if sid >= len(STAGES):
                continue
            w, t = generate_rollout(seed, sid, cfg, rng)
            all_w.extend(w)
            all_t.extend(t)
    if not all_w:
        return np.empty((0, cfg.window_len, N_FEATURES), dtype=np.float32), np.empty((0,), dtype=np.float32)
    return np.stack(all_w), np.asarray(all_t, dtype=np.float32)


__all__ = ["RolloutConfig", "FEATURES", "N_FEATURES", "generate_rollout", "build_dataset"]
