"""Stage 17 — self-healing robotics (KB_17 §"Self-Healing Robotics" extension).

Introspection on actuator state + automated remediation BEFORE a failure cascades to safety:
- `torque_anomaly.py` — per-joint torque-variance anomaly detection (robust rolling-Z, > 3σ).
- `behavior_tree.py` — a tiny declarative behaviour-tree executor; trees in `behavior_trees/<class>.yaml`.
- `self_repair.py` — the `self_diagnose_calibrate` routine: anomaly → calibrate → resume, OR calibrate-fail → STO +
  quarantine. The self-repair action ITSELF passes `safety.validator` (we never skip safety during self-repair), and
  every transition writes a signed `audit_chain` row (EU AI Act Art-12 provenance).
"""
