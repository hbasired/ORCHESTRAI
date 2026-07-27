"""Calibration constants for the SimPy plant simulator.

All tunable plant parameters live here so retuning is a one-PR change.
Targets (Stage 2 task doc):
  - Baseline throughput ~500 units/hr.
  - Stable queues (no monotonic growth over 30 simulated minutes).
  - AMR utilization >= 60%.
  - Inject-to-WS-delta latency <= 250 ms p95.

References:
  - KB_05_Simulation_Spec.md (entity model + event catalog).
  - knowledge-base/KB_10_Production_Hardening.md (latency budget).
  - AI4I 2020 dataset (open) fitted MTBF distributions; can be re-fit from
    a pilot's real CMMS export in Stage 14.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IncidentType = Literal[
    "machine_crack",
    "robot_down",
    "late_delivery",
    "demand_spike",
    "defect_surge",
    "power_dip",
]
INCIDENT_TYPES: tuple[IncidentType, ...] = (
    "machine_crack",
    "robot_down",
    "late_delivery",
    "demand_spike",
    "defect_surge",
    "power_dip",
)


@dataclass(frozen=True)
class StageCalibration:
    """Per-stage cycle-time + MTBF/MTTR distribution parameters."""

    stage_id: int
    name: str
    # Cycle time: log-normal with mu, sigma (in seconds).
    cycle_mu_log_seconds: float
    cycle_sigma_log: float
    capacity: int
    # MTBF / MTTR: exponential mean (in simulated seconds).
    mtbf_seconds: float
    mttr_seconds: float
    # Defect rate: probability per output unit (0..1).
    defect_rate: float
    # Power consumption: kW at full utilisation.
    nominal_kw: float


@dataclass(frozen=True)
class SimWorldCalibration:
    """Top-level plant calibration.

    These numbers are baseline targets, not real-factory measurements.
    Stage 14 (production hardening) will retune against a pilot's CMMS.
    """

    n_stages: int = 10
    n_robots: int = 20
    n_charging_stations: int = 2
    # Poisson rate for order arrivals (orders per simulated second).
    order_arrival_lambda_per_sec: float = 8.0 / 3600.0  # ~8 orders/hr per SKU
    n_skus: int = 12
    # Robot kinematics.
    robot_max_speed_m_s: float = 1.4  # ~5 km/h, typical AMR
    robot_battery_drain_per_sec: float = 1.0 / (45.0 * 60.0)  # full drain in 45 min of motion
    robot_charge_per_sec: float = 1.0 / (30.0 * 60.0)  # 0 → full in 30 min
    robot_battery_low_threshold: float = 0.25  # head to charger below this
    # Supplier distribution.
    n_suppliers: int = 6
    supplier_lead_mu_log_seconds: float = 8.0  # exp(8) ≈ 50 minutes
    supplier_lead_sigma_log: float = 0.4
    supplier_reliability: float = 0.95
    # Simulator tick.
    tick_seconds: float = 0.5  # wall-clock period; SimPy time-step is variable
    # Inject-latency target (used by tests, not the sim itself).
    inject_to_delta_p95_ms: float = 250.0
    # Default RNG seed for tests (constructor argument overrides).
    default_seed: int = 20260524


# Ten production stages — a representative discrete-manufacturing line.
# Cycle-time mu chosen so total throughput is ~500 units/hr at full utilization:
# 500 units/hr / 60min / 10 stages ≈ 0.83 units/min/stage ≈ 72 s/unit/stage mean.
STAGES: tuple[StageCalibration, ...] = (
    StageCalibration(0, "intake", cycle_mu_log_seconds=3.9, cycle_sigma_log=0.2, capacity=30, mtbf_seconds=4 * 3600, mttr_seconds=12 * 60, defect_rate=0.005, nominal_kw=2.0),
    StageCalibration(1, "press", cycle_mu_log_seconds=4.2, cycle_sigma_log=0.25, capacity=20, mtbf_seconds=3 * 3600, mttr_seconds=15 * 60, defect_rate=0.012, nominal_kw=14.0),
    StageCalibration(2, "weld", cycle_mu_log_seconds=4.3, cycle_sigma_log=0.3, capacity=20, mtbf_seconds=3 * 3600, mttr_seconds=20 * 60, defect_rate=0.020, nominal_kw=18.0),
    StageCalibration(3, "machining", cycle_mu_log_seconds=4.4, cycle_sigma_log=0.3, capacity=15, mtbf_seconds=2.5 * 3600, mttr_seconds=25 * 60, defect_rate=0.018, nominal_kw=22.0),
    StageCalibration(4, "wash", cycle_mu_log_seconds=3.8, cycle_sigma_log=0.2, capacity=25, mtbf_seconds=6 * 3600, mttr_seconds=10 * 60, defect_rate=0.003, nominal_kw=8.0),
    StageCalibration(5, "paint", cycle_mu_log_seconds=4.5, cycle_sigma_log=0.35, capacity=15, mtbf_seconds=4 * 3600, mttr_seconds=30 * 60, defect_rate=0.015, nominal_kw=12.0),
    StageCalibration(6, "cure", cycle_mu_log_seconds=4.7, cycle_sigma_log=0.25, capacity=18, mtbf_seconds=5 * 3600, mttr_seconds=20 * 60, defect_rate=0.008, nominal_kw=20.0),
    StageCalibration(7, "assembly", cycle_mu_log_seconds=4.3, cycle_sigma_log=0.35, capacity=20, mtbf_seconds=3 * 3600, mttr_seconds=18 * 60, defect_rate=0.022, nominal_kw=6.0),
    StageCalibration(8, "qc", cycle_mu_log_seconds=4.0, cycle_sigma_log=0.2, capacity=25, mtbf_seconds=8 * 3600, mttr_seconds=8 * 60, defect_rate=0.0, nominal_kw=3.0),
    StageCalibration(9, "packaging", cycle_mu_log_seconds=3.9, cycle_sigma_log=0.2, capacity=30, mtbf_seconds=10 * 3600, mttr_seconds=6 * 60, defect_rate=0.002, nominal_kw=4.0),
)


# Event-impact constants — how an incident perturbs the plant.
@dataclass(frozen=True)
class EventImpact:
    """Per-event-type impact parameters (used by entities/incident.py)."""

    # machine_crack: stage degrades over eta_minutes, then fails.
    machine_crack_default_eta_minutes: float = 12.0
    machine_crack_throughput_drop_factor: float = 0.4  # 40% slowdown while degrading
    # Unplanned crack-induced breakdown causes secondary damage → repair takes a
    # multiple of the routine MTTR (vs. exponential(mttr) for natural MTBF stops).
    # Stage 6 slice: this is the cost the preventive intervention avoids.
    machine_crack_repair_multiplier: float = 2.5
    # Planned (preventive) maintenance is shorter than a mean repair: the crew is
    # scheduled, parts staged, no secondary damage. Fraction of cfg.mttr_seconds.
    preventive_maintenance_factor: float = 0.5

    # robot_down: battery jumps to ~0 or fault status flag set.
    robot_down_residual_battery: float = 0.0
    robot_down_recovery_seconds: float = 12 * 60.0

    # late_delivery: lead time increases by delay_minutes.
    late_delivery_default_delay_minutes: float = 25.0

    # demand_spike: order arrival lambda multiplied by `multiplier` for `duration_minutes`.
    demand_spike_default_multiplier: float = 3.0
    demand_spike_default_duration_minutes: float = 20.0

    # defect_surge: stage defect rate multiplied for `duration_minutes`.
    defect_surge_default_multiplier: float = 6.0
    defect_surge_default_duration_minutes: float = 15.0

    # power_dip: cap total throughput at `max_throughput_pct` for `duration_minutes`.
    power_dip_default_pct: float = 0.6
    power_dip_default_duration_minutes: float = 10.0


# Machine-telemetry model (Stage 6 vertical slice) — maps simulator state onto
# AI4I-2020-unit signals so the Stage-4 failure brain judges REAL simulator
# state. The mapping is physics-motivated, not tuned to flatter the model:
# a degrading (cracked) machine slows (rpm down), overstrains (torque up),
# wears its tool faster, and loses heat-dissipation margin (temp_diff down) —
# the same regimes AI4I labels TWF / OSF / HDF. Sensor noise is seeded
# numpy rng (deterministic per world seed). Documented in KB_05.
@dataclass(frozen=True)
class TelemetryCalibration:
    """Per-stage machine-telemetry baselines + degradation drift (AI4I units)."""

    # Nominal operating point (mid-range of AI4I healthy population).
    base_air_temp_k: float = 300.0
    base_process_temp_k: float = 310.0
    base_rot_speed_rpm: float = 1550.0
    base_torque_nm: float = 40.0
    # Tool wear accumulates with real production: minutes of wear per unit.
    tool_wear_min_per_unit: float = 0.25
    # Sensor noise (1σ, seeded rng — same determinism pattern as the rest of the sim).
    noise_air_temp_k: float = 0.3
    noise_process_temp_k: float = 0.4
    noise_rpm: float = 12.0
    noise_torque_nm: float = 1.2
    # Degradation drift at full crack proximity (prox = 1.0 just before failure):
    # rpm sinks below the AI4I HDF threshold (1380), torque climbs toward the
    # OSF regime, wear jumps toward the TWF band (200–240 min), and the
    # process/air temperature gap collapses toward the HDF band (< 8.6 K).
    degraded_rpm_drop_frac: float = 0.35
    degraded_torque_rise_frac: float = 0.9
    degraded_extra_wear_min: float = 190.0
    degraded_temp_gap_collapse_k: float = 6.0
    # Slice sampling cadence (simulated seconds between telemetry samples).
    sample_period_seconds: float = 30.0


SIM_WORLD = SimWorldCalibration()
EVENT_IMPACT = EventImpact()
TELEMETRY = TelemetryCalibration()
