# SOP-001 — Stage Crack / Torque-Anomaly Response

Applies to: production stages (WorkUnit) exhibiting a rising torque signature or a scheduled crack.

Procedure:
1. When a stage's rolling-Z torque anomaly exceeds threshold, the stage is a crack-risk candidate.
2. Route the intervention through backend/safety/validator.py BEFORE any actuation (Hard Rule 3).
3. If throughput headroom allows, dock the affected stage to maintenance (dock_to_maintenance) and run calibration.
4. If calibration restores the baseline, resume operation (validator-gated). Otherwise trigger STO + quarantine.

Related equipment: any WorkUnit stage. Failure mode: crack_proximity rising toward 1.0.
Escalation: two critical stages down simultaneously violates the one-crew capacity invariant.
