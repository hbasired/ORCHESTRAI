# SOP-003 — AMR / Robot Fault Handling

Applies to: mobile robots (AMR) transporting material between stages.

Procedure:
1. A robot in status=fault must not receive new transport tasks.
2. If battery falls below the charge threshold, route the robot to a charging station before further tasks.
3. A stuck or faulted AMR is handled by the self_diagnose_calibrate behaviour tree; failing that, STO + quarantine.
4. VDA 5050 orders are only dispatched to robots whose connection is ONLINE and fresh (anti-spoof).

Related equipment: AMR robots, charging stations, VDA 5050 fleet boundary.
