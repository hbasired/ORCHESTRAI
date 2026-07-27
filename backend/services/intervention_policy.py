"""Stage 6 — deterministic intervention policy v0 (INTERVENE step of KB_25).

The single source of truth for "given a diagnosis, what does the coordinator
do?". `EmbodiedAgent.decide_intervention` delegates here (live path) and the
A/B harness calls it directly (sim path) — one policy, two entry points.

v0 is rule-based and sim-only: the only actuator is `Stage.start_maintenance`
inside SimPy (no real actuator paths exist yet, so the Stage-17 safety wrapper
is not required — see the task doc). Stage 11 adds HITL + durable workflow.

Stage 7 update (2026-06-12): a PPO chooser now exists (`ml.intervention_rl`). It
operates at FLEET granularity (which machine gets the single maintenance crew),
whereas these rules are PER-MACHINE. The Stage-7 eval found the rules near-optimal
at v0 scope and PPO does NOT beat them, so the **rules remain the default chooser**
(`DEFAULT_CHOOSER`). `select_chooser()` is the documented seam to plug either in;
the RL chooser ships as the learnable substrate for Stage 8's richer action space.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from services.diagnosis import (
    EXTERNAL_POWER_EVENT,
    NO_FAULT_FOUND,
    Diagnosis,
)

# Decision kinds (stable contract for the envelope + decision_logs).
PREVENTIVE_MAINTENANCE = "preventive_maintenance"
WAIT_EXTERNAL = "wait_external"
MONITOR = "monitor"


@dataclass(frozen=True)
class InterventionDecision:
    """The coordinator's decision for one diagnosed machine."""

    stage_id: int
    kind: str                       # PREVENTIVE_MAINTENANCE | WAIT_EXTERNAL | MONITOR
    rationale: str                  # human-readable, evidence-backed
    diagnosis: dict[str, Any]       # the full diagnosis payload (provenance)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "kind": self.kind,
            "rationale": self.rationale,
            "diagnosis": self.diagnosis,
        }


def decide_intervention(
    diagnosis: Diagnosis,
    *,
    queue_depth: Optional[int] = None,
    capacity: Optional[int] = None,
) -> InterventionDecision:
    """Deterministic v0 policy.

    Rules (in order):
      1. Not at risk → MONITOR.
      2. Primary cause is an external power event → WAIT_EXTERNAL (fixing the
         machine would not fix the plant-wide cause).
      3. Primary cause is no-fault-found AND the model signal is weak
         (p_fail < 0.9) → MONITOR (don't take a machine down on a thin signal
         with no corroborating physics).
      4. Otherwise → PREVENTIVE_MAINTENANCE. Load is noted in the rationale:
         v0 maintains immediately because the degraded machine is already the
         line's slow point (slow-and-catch-up scheduling arrives with the
         Stage-7 RL chooser over this same contract).
    """
    primary = diagnosis.primary

    if not diagnosis.at_risk:
        return InterventionDecision(
            stage_id=diagnosis.stage_id,
            kind=MONITOR,
            rationale=f"not at risk (p_fail={diagnosis.p_fail:.3f}); continue monitoring",
            diagnosis=diagnosis.to_dict(),
        )

    if primary.cause == EXTERNAL_POWER_EVENT:
        return InterventionDecision(
            stage_id=diagnosis.stage_id,
            kind=WAIT_EXTERNAL,
            rationale=(
                "anomaly attributed to an active plant-wide power event; "
                "machine maintenance would not address the cause. Evidence: "
                + "; ".join(primary.evidence)
            ),
            diagnosis=diagnosis.to_dict(),
        )

    if primary.cause == NO_FAULT_FOUND and diagnosis.p_fail < 0.9:
        return InterventionDecision(
            stage_id=diagnosis.stage_id,
            kind=MONITOR,
            rationale=(
                f"model flags risk (p_fail={diagnosis.p_fail:.3f}) but no physical rule "
                "corroborates and the signal is below the act-alone bar (0.9); monitoring"
            ),
            diagnosis=diagnosis.to_dict(),
        )

    load_note = ""
    if queue_depth is not None and capacity:
        load_note = f" (load {queue_depth}/{capacity} at decision time)"
    return InterventionDecision(
        stage_id=diagnosis.stage_id,
        kind=PREVENTIVE_MAINTENANCE,
        rationale=(
            f"primary cause '{primary.cause}' (score {primary.score:.2f}); planned "
            f"maintenance now avoids a crack-induced breakdown costing "
            f"~2.5× MTTR{load_note}. Evidence: " + "; ".join(primary.evidence)
        ),
        diagnosis=diagnosis.to_dict(),
    )


# Default chooser (Stage-7 finding: rules near-optimal; PPO does not beat them at v0).
DEFAULT_CHOOSER = "rules"


def select_chooser(policy: str = DEFAULT_CHOOSER):
    """Return an intervention chooser. Both produce `InterventionDecision`, but at
    DIFFERENT granularity (documented honestly — they are not drop-in interchangeable):

      - "rules" → the per-machine `decide_intervention(diagnosis, ...)` here (DEFAULT).
      - "rl"    → the fleet-level `RLInterventionPolicy.decide(obs, stages, diagnoses)`
                  from `ml.intervention_rl` (PPO + safety shield). Raises
                  `ModelUnavailableError` if the trained policy/torch is absent.

    The slice's per-machine loop uses "rules"; the fleet RL chooser is exercised by
    the Stage-7 eval and is the seam for Stage 8. Choosing "rl" returns the policy
    object (caller invokes `.decide(...)`), not the per-machine function.
    """
    if policy == "rules":
        return decide_intervention
    if policy == "rl":
        from ml.intervention_rl import get_rl_intervention_policy
        return get_rl_intervention_policy()
    raise ValueError(f"unknown chooser policy: {policy!r} (expected 'rules' or 'rl')")


__all__ = [
    "InterventionDecision",
    "decide_intervention",
    "select_chooser",
    "DEFAULT_CHOOSER",
    "PREVENTIVE_MAINTENANCE",
    "WAIT_EXTERNAL",
    "MONITOR",
]
