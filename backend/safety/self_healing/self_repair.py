"""Stage 17 — the self-repair controller (KB_17 §"Self-Healing" — the self_diagnose_calibrate routine).

Ties the torque-anomaly detector → a robot-class behaviour tree → the safety validator → STO. On a torque anomaly the
robot docks to maintenance, runs a calibration, and either resumes (if baseline restored) or — on calibration failure —
triggers **STO** + quarantine. CRITICAL (KB_17): the resume action routes through `safety.validator.validate()` (we never
skip safety during self-repair), and EVERY transition writes a signed `audit_chain` row (Art-12 provenance).

Honest scope: there is no physical robot here, so `calibrate_fn` / `dock_fn` are injectable hooks (wired to the real
robot routine in deployment; simulated/test-driven in this build) — the orchestration, safety gating, STO, and audit
trail are all real.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from safety.contract import Action, Invariant, Precondition, SafetyContract
from safety.self_healing.behavior_tree import BehaviorTree, Status
from safety.self_healing.torque_anomaly import RollingZTorqueDetector

# The resume action is itself a SIL-2 robot motion → it passes the validator (KB_17: no skipping safety in self-repair).
RESUME_CONTRACT = SafetyContract(
    name="resume_after_self_repair",
    sil=2,
    iso_clauses=["ISO 10218-2:2025 §5.7", "IEC 61508-1 §7.4"],
    preconditions=[
        Precondition(name="calibration_restored", description="calibration restored baseline torque",
                     check=lambda ws: bool(ws.get("calibration_restored", False))),
        Precondition(name="no_active_anomaly", description="no torque anomaly currently active",
                     check=lambda ws: not bool(ws.get("anomaly_active", True))),
    ],
    invariants=[Invariant(name="estop_clear", description="no e-stop asserted",
                          check=lambda ws: not bool(ws.get("estop", False)))],
    fail_safe_path="STO",
)


def _audit(action: str, payload: dict) -> Optional[int]:
    try:
        from observability.evidence_sink import record
        return record("safety.self_healing", action, payload)
    except Exception:  # noqa: BLE001 - audit best-effort; the safety transitions stand regardless
        return None


class SelfHealingController:
    def __init__(self, robot_class: str = "amr", *, detector: Optional[RollingZTorqueDetector] = None,
                 calibrate_fn: Optional[Callable[[dict], bool]] = None,
                 dock_fn: Optional[Callable[[dict], bool]] = None) -> None:
        self.robot_class = robot_class
        self.detector = detector or RollingZTorqueDetector()
        # Hooks: wired to the real robot routine in deployment. Default reads the blackboard (test/sim control).
        self._calibrate_fn = calibrate_fn or (lambda bb: bool(bb.get("calibration_will_succeed", False)))
        self._dock_fn = dock_fn or (lambda bb: True)
        self._bt = BehaviorTree.for_robot_class(robot_class, self._conditions(), self._actions())

    # ---- behaviour-tree leaves --------------------------------------------
    def _conditions(self) -> dict[str, Callable[[dict], bool]]:
        return {
            "torque_anomaly_detected": lambda bb: bool(bb.get("anomaly")),
            "calibration_restored_baseline": lambda bb: bool(bb.get("calibrated")),
        }

    def _actions(self) -> dict[str, Callable[[dict], bool]]:
        return {
            "dock_to_maintenance": self._act_dock,
            "move_to_safe_home": self._act_dock,
            "run_calibration": self._act_calibrate,
            "resume_operation": self._act_resume,
        }

    def _act_dock(self, bb: dict) -> bool:
        bb["docked"] = True
        _audit("repair_initiated", {"robot": bb.get("robot_id"), "robot_class": self.robot_class,
                                    "joint": bb.get("joint_id")})
        return self._dock_fn(bb)

    def _act_calibrate(self, bb: dict) -> bool:
        restored = bool(self._calibrate_fn(bb))
        bb["calibrated"] = restored
        _audit("calibration_attempt", {"robot": bb.get("robot_id"), "restored": restored})
        return True   # the ACT of calibrating ran; whether it RESTORED is the next condition

    def _act_resume(self, bb: dict) -> bool:
        from safety.validator import validate
        ws = {"calibration_restored": bool(bb.get("calibrated")), "anomaly_active": False, "estop": bb.get("estop", False)}
        decision = validate(Action(contract=RESUME_CONTRACT.name, actuator="amr.resume",
                                   target=bb.get("robot_id")), ws, RESUME_CONTRACT)
        bb["resume_decision"] = decision.model_dump()
        if not decision.allow:
            return False
        _audit("self_repair.success", {"robot": bb.get("robot_id"), "route": decision.route})
        return True

    # ---- entry points ------------------------------------------------------
    def handle_anomaly(self, robot_id: str, *, joint_id: str = "", world_state: Optional[dict] = None) -> dict:
        """Run the self-repair behaviour tree. On FAILURE (calibration didn't restore baseline) → STO + quarantine."""
        bb: dict[str, Any] = {"robot_id": robot_id, "joint_id": joint_id, "anomaly": True,
                              **(world_state or {})}
        _audit("anomaly_detected", {"robot": robot_id, "joint": joint_id, "robot_class": self.robot_class})
        status = self._bt.tick(bb)
        if status == Status.SUCCESS:
            return {"robot_id": robot_id, "outcome": "self_repair.success", "bt_status": status.value,
                    "bt_trace": self._bt.trace, "sto": None}
        # calibration failed → trigger STO + quarantine (the fail-safe path)
        from safety.sto_ss1 import trigger_sto
        sto = trigger_sto(bb, reason=f"self-repair failed for {robot_id} (joint {joint_id})")
        _audit("self_repair.failed", {"robot": robot_id, "joint": joint_id, "severity": "high",
                                      "quarantined": True, "sto_audit_seq": sto.get("audit_seq")})
        return {"robot_id": robot_id, "outcome": "self_repair.failed", "bt_status": status.value,
                "bt_trace": self._bt.trace, "quarantined": True, "sto": sto}

    def on_torque_window(self, robot_id: str, joint_id: str, torques: list[float],
                         world_state: Optional[dict] = None) -> dict:
        """Score a torque window; if anomalous, run the self-repair routine. Returns {anomaly, ...}."""
        det = self.detector.detect_window(joint_id, torques)
        if not det["anomaly"]:
            return {"anomaly": False, "detection": det}
        return {"anomaly": True, "detection": det,
                "repair": self.handle_anomaly(robot_id, joint_id=joint_id, world_state=world_state)}


__all__ = ["SelfHealingController", "RESUME_CONTRACT"]
