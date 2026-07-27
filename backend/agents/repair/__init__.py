"""Stage 30 (G-005) — cross-fleet repair-robot dispatch: the KB_25 step-4 recovery action.

When a machine goes down, the coordinator dispatches the best available repair robot (sealed-bid Contract-Net over
REAL robot state — availability/battery/queue), routes the award through the safety validator (Hard Rule 3), and the
robot travels + repairs, cutting the remaining downtime vs. the passive MTTR timer. Research §41.1.
"""
