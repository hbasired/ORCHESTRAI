"""Stage 17 — self-healing: torque-anomaly detection → behaviour-tree self-repair → resume OR STO (KB_17 extension)."""
from safety.self_healing.self_repair import SelfHealingController
from safety.self_healing.torque_anomaly import RollingZTorqueDetector


def test_torque_detector_flags_spike_not_stable():
    d = RollingZTorqueDetector(window=30, z_threshold=3.0, min_samples=10)
    stable = [10.0 + 0.05 * ((i % 5) - 2) for i in range(25)]
    assert d.detect_window("j1", stable)["anomaly"] is False
    assert d.detect_window("j1", stable + [25.0])["anomaly"] is True   # a clear torque spike


def test_self_repair_success_resumes_via_validator():
    """anomaly → dock → calibrate (restores) → resume (passes safety.validator) → self_repair.success."""
    ctrl = SelfHealingController("amr")
    out = ctrl.handle_anomaly("AMR-1", joint_id="j1", world_state={"calibration_will_succeed": True})
    assert out["outcome"] == "self_repair.success" and out["bt_status"] == "SUCCESS"
    # the resume action went through the validator (KB_17: never skip safety during self-repair)
    assert any(node == "resume_operation" and status == "SUCCESS" for node, status in out["bt_trace"])


def test_self_repair_failure_triggers_sto_and_quarantine():
    """anomaly → calibrate FAILS → STO + quarantine → self_repair.failed (the fail-safe path)."""
    ctrl = SelfHealingController("amr")
    out = ctrl.handle_anomaly("AMR-2", joint_id="j2", world_state={"calibration_will_succeed": False})
    assert out["outcome"] == "self_repair.failed"
    assert out["quarantined"] is True
    assert out["sto"]["function"] == "STO" and out["sto"]["triggered"] is True


def test_resume_blocked_if_calibration_not_restored_even_if_bt_reached_resume():
    """Defence-in-depth: the resume contract itself blocks if calibration didn't restore baseline."""
    from safety.self_healing.self_repair import RESUME_CONTRACT
    from safety.contract import Action
    from safety.validator import validate
    d = validate(Action(contract=RESUME_CONTRACT.name, actuator="amr.resume"),
                 {"calibration_restored": False, "anomaly_active": False}, RESUME_CONTRACT)
    assert d.allow is False and d.fail_safe_path == "STO"


def test_manipulator_class_tree_loads_and_runs():
    ctrl = SelfHealingController("manipulator")
    out = ctrl.handle_anomaly("ARM-1", joint_id="j3", world_state={"calibration_will_succeed": True})
    assert out["outcome"] == "self_repair.success"


def test_on_torque_window_no_anomaly_no_repair():
    ctrl = SelfHealingController("amr")
    stable = [5.0 + 0.02 * ((i % 4) - 2) for i in range(20)]
    out = ctrl.on_torque_window("AMR-3", "j4", stable)
    assert out["anomaly"] is False and "repair" not in out
