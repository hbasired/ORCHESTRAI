"""Robot SimPy process — AMR with battery + task queue + charging logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Optional

import simpy

from ..calibration import SIM_WORLD

if TYPE_CHECKING:
    from numpy.random import Generator


RobotStatus = Literal["idle", "moving", "charging", "fault"]


@dataclass
class Task:
    """Inter-stage transport job."""

    task_id: int
    from_stage: int
    to_stage: int
    duration_seconds: float


@dataclass
class Robot:
    """AMR entity. Owned by a SimPy environment; do not share across envs."""

    id: int
    env: simpy.Environment
    rng: "Generator"
    charging_stations: simpy.Resource
    battery: float = 1.0
    status: RobotStatus = "idle"
    queue: list[Task] = field(default_factory=list)
    fault_until: Optional[float] = None  # simulated-time absolute deadline
    completed_tasks: int = 0
    charge_cycles: int = 0
    _process: Optional[simpy.Process] = field(default=None, init=False, repr=False)

    def start(self) -> None:
        """Start the SimPy process. Called once after construction."""
        if self._process is None:
            self._process = self.env.process(self._run())

    def enqueue(self, task: Task) -> None:
        self.queue.append(task)

    def force_down(self, recovery_seconds: float) -> None:
        """Operator-injected robot_down event."""
        self.battery = 0.0
        self.status = "fault"
        self.fault_until = self.env.now + recovery_seconds

    def utilization(self) -> float:
        """Fraction of tasks completed per simulated minute, normalised to [0,1].

        Used by the calibration test; rough proxy.
        """
        elapsed_min = max(1.0, self.env.now / 60.0)
        return min(1.0, self.completed_tasks / elapsed_min)

    def _run(self):  # SimPy generator
        while True:
            if self.status == "fault":
                if self.fault_until is None or self.env.now >= self.fault_until:
                    self.status = "idle"
                    self.fault_until = None
                    self.battery = 0.05  # comes back online almost-empty
                else:
                    yield self.env.timeout(1.0)
                    continue

            if self.battery <= SIM_WORLD.robot_battery_low_threshold and self.status != "charging":
                yield self.env.process(self._charge())
                continue

            if not self.queue:
                self.status = "idle"
                yield self.env.timeout(1.0)
                self.battery = max(0.0, self.battery - SIM_WORLD.robot_battery_drain_per_sec * 0.1)  # idle drain
                continue

            task = self.queue.pop(0)
            self.status = "moving"
            t_left = task.duration_seconds
            while t_left > 0 and self.battery > 0.05:
                step = min(t_left, 1.0)
                yield self.env.timeout(step)
                self.battery = max(0.0, self.battery - SIM_WORLD.robot_battery_drain_per_sec * step)
                t_left -= step

            if t_left <= 0:
                self.completed_tasks += 1
                self.status = "idle"
            else:
                # Mid-task brownout: re-queue at front.
                self.queue.insert(0, task)
                self.status = "idle"

    def _charge(self):
        self.status = "charging"
        with self.charging_stations.request() as req:
            yield req
            while self.battery < 0.95:
                yield self.env.timeout(1.0)
                self.battery = min(1.0, self.battery + SIM_WORLD.robot_charge_per_sec)
        self.charge_cycles += 1
        self.status = "idle"

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "battery": round(self.battery, 3),
            "status": self.status,
            "queue_len": len(self.queue),
            "completed_tasks": self.completed_tasks,
            "charge_cycles": self.charge_cycles,
        }
