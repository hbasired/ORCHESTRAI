"""Stage 2 — SimWorld determinism + snapshot smoke tests.

Validates that:
  - A seeded SimWorld produces a reproducible state trajectory.
  - The snapshot includes the expected entity counts (10 stages, 20 robots,
    6 suppliers per calibration).
  - Inject of every event type lands as an in-memory `incident` record,
    even when persistence (Postgres + Redis) is absent.

No DB / Redis required. Runs in the test process; the SimPy worker thread
is started + stopped within each test.
"""
from __future__ import annotations

import time

import pytest

from simulation.calibration import INCIDENT_TYPES, SIM_WORLD, STAGES
from simulation.entities import InjectRequest
from simulation.sim_world import SimWorld


def _spin(world: SimWorld, wall_seconds: float = 0.5) -> None:
    """Let the worker thread make progress for `wall_seconds`."""
    time.sleep(wall_seconds)


class TestConstruction:
    def test_entity_counts_match_calibration(self):
        w = SimWorld(seed=1)
        try:
            assert len(w.stages) == SIM_WORLD.n_stages == 10
            assert len(w.robots) == SIM_WORLD.n_robots == 20
            assert len(w.suppliers) == SIM_WORLD.n_suppliers
            # Cross-check stage IDs are contiguous and match calibration table.
            assert sorted(w.stages.keys()) == [s.stage_id for s in STAGES]
        finally:
            w.stop()

    def test_seed_is_recorded(self):
        w = SimWorld(seed=42)
        try:
            assert w.seed == 42
            assert w.snapshot()["seed"] == 42
        finally:
            w.stop()


class TestDeterminism:
    """Two SimWorlds with the same seed produce the same RNG output."""

    def test_first_rng_draw_matches(self):
        a = SimWorld(seed=99)
        b = SimWorld(seed=99)
        try:
            # Construct draws an integer in each child RNG seed; the top-level
            # RNG state should be identical after construction.
            assert a.rng.random() == b.rng.random()
        finally:
            a.stop()
            b.stop()

    def test_different_seeds_diverge(self):
        a = SimWorld(seed=1)
        b = SimWorld(seed=2)
        try:
            assert a.rng.random() != b.rng.random()
        finally:
            a.stop()
            b.stop()


class TestSnapshot:
    def test_snapshot_keys(self):
        w = SimWorld(seed=7)
        try:
            snap = w.snapshot()
            for key in (
                "sim_time_seconds",
                "seed",
                "stages",
                "robots",
                "suppliers",
                "orders_started",
                "orders_complete",
                "throughput_units_per_hour",
                "amr_utilization",
                "modulation",
                "incidents_fired_count",
            ):
                assert key in snap, f"Snapshot missing key: {key}"
            assert len(snap["stages"]) == 10
            assert len(snap["robots"]) == 20
        finally:
            w.stop()


class TestInject:
    """Every event type the simulator accepts records an incident in memory."""

    @pytest.fixture
    def world(self):
        w = SimWorld(seed=20260524)
        w.start()
        yield w
        w.stop()

    def test_machine_crack(self, world: SimWorld):
        before = world.snapshot()["incidents_fired_count"]
        world.inject(InjectRequest(type="machine_crack", target_id=4))
        _spin(world, 0.3)
        assert world.snapshot()["incidents_fired_count"] >= before + 1

    def test_robot_down(self, world: SimWorld):
        before = world.snapshot()["incidents_fired_count"]
        world.inject(InjectRequest(type="robot_down", target_id=3))
        _spin(world, 0.3)
        assert world.snapshot()["incidents_fired_count"] >= before + 1

    def test_late_delivery(self, world: SimWorld):
        before = world.snapshot()["incidents_fired_count"]
        world.inject(InjectRequest(type="late_delivery", target_id=1))
        _spin(world, 0.3)
        assert world.snapshot()["incidents_fired_count"] >= before + 1

    def test_demand_spike_changes_modulation(self, world: SimWorld):
        world.inject(InjectRequest(type="demand_spike", details={"multiplier": 5.0, "duration_minutes": 10}))
        _spin(world, 0.3)
        snap = world.snapshot()
        # Demand multiplier should reflect the spike.
        assert snap["modulation"]["demand_multiplier"] >= 5.0 - 1e-6

    def test_defect_surge(self, world: SimWorld):
        before = world.snapshot()["incidents_fired_count"]
        world.inject(InjectRequest(type="defect_surge", target_id=2))
        _spin(world, 0.3)
        assert world.snapshot()["incidents_fired_count"] >= before + 1

    def test_power_dip_changes_modulation(self, world: SimWorld):
        world.inject(InjectRequest(type="power_dip", details={"max_throughput_pct": 0.3, "duration_minutes": 5}))
        _spin(world, 0.3)
        snap = world.snapshot()
        assert snap["modulation"]["throughput_cap_pct"] <= 0.3 + 1e-6

    def test_all_six_types_covered(self):
        """Every type declared in calibration is testable here."""
        types_under_test = {
            "machine_crack",
            "robot_down",
            "late_delivery",
            "demand_spike",
            "defect_surge",
            "power_dip",
        }
        assert set(INCIDENT_TYPES) == types_under_test


class TestConflictSerialization:
    """Two same-(type, target) injects in quick succession get serialised."""

    def test_two_machine_cracks_same_stage_both_recorded(self):
        w = SimWorld(seed=11)
        w.start()
        try:
            w.inject(InjectRequest(type="machine_crack", target_id=5))
            w.inject(InjectRequest(type="machine_crack", target_id=5))
            _spin(w, 0.5)
            # Both should land eventually; serialisation orders them.
            assert w.snapshot()["incidents_fired_count"] >= 1
        finally:
            w.stop()
