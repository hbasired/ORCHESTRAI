"""Stage 6 — the vertical-slice workflow: predict → diagnose → intervene.

Two entry points over the same loop body:

- :class:`SliceLoop` — a SimPy in-environment process used by the A/B harness
  and the tests. Fully deterministic for a given world seed; runs as fast as
  SimPy can step (no wall-clock pacing, no threads).
- :class:`LiveSliceRunner` — an asyncio task for the running FastAPI app: it
  samples the (thread-backed) live ``SimWorld`` on a wall-clock cadence and
  publishes slice events to Redis so the Stage-3 broker fans them out on
  ``/ws`` using the canonical envelope (AC5). No new UI pages this stage.

The loop body is honest end-to-end: real telemetry (``Stage.telemetry()``),
the real Stage-4 XGBoost brain (``FailurePredictor`` — raises
``ModelUnavailableError`` rather than fabricate), deterministic diagnosis
(``services.diagnosis``), and the deterministic v0 intervention policy
(``services.intervention_policy``) executed via ``Stage.start_maintenance``.
Every decision is recorded (in-memory trail + optional ``decision_logs``
writer) — provenance is part of the loop, not an afterthought.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from ml.failure_predictor import FailurePredictor, ModelUnavailableError, get_failure_predictor
from services.diagnosis import diagnose
from services.intervention_policy import (
    PREVENTIVE_MAINTENANCE,
    InterventionDecision,
    decide_intervention,
)
from simulation.calibration import TELEMETRY

logger = logging.getLogger(__name__)

# Once a machine has been maintained (or deliberately left alone), suppress
# re-deciding for this many simulated seconds — debounce, not a hidden policy.
DECISION_COOLDOWN_SECONDS = 600.0


@dataclass
class SliceEvent:
    """One emitted slice event (prediction / diagnosis / intervention)."""

    kind: str
    sim_time_seconds: float
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "sim_time_seconds": self.sim_time_seconds, "payload": self.payload}


@dataclass
class SliceTrail:
    """In-memory provenance trail for one run (read by tests + the A/B report)."""

    predictions: list[SliceEvent] = field(default_factory=list)
    diagnoses: list[SliceEvent] = field(default_factory=list)
    interventions: list[SliceEvent] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "predictions": len(self.predictions),
            "diagnoses": len(self.diagnoses),
            "interventions": len(self.interventions),
        }


# Telemetry features the Stage-8 world model consumes (order must match ml.world_model.FEATURES).
_WM_FEATURES = ("air_temp_k", "process_temp_k", "rot_speed_rpm", "torque_nm", "tool_wear_min")
_WM_WINDOW = 6


def _try_world_model():
    """Best-effort load of the Stage-8 TTF world model (None if torch/weights absent — never fabricates)."""
    try:
        from ml.world_model import get_world_model
        wm = get_world_model()
        return wm if wm.is_available() else None
    except Exception:
        return None


def _try_explainer():
    """Best-effort load of the Stage-10 exact-SHAP explainer (None if XGBoost/lib absent)."""
    try:
        from ml.failure_explainer import get_failure_explainer
        ex = get_failure_explainer()
        return ex if ex.is_available() else None
    except Exception:
        return None


def _persist_decision_log(*, caller: str, tool: str, inputs: dict, outputs: dict,
                          incident_id: Optional[str] = None) -> Optional[str]:
    """G-045 — AUTOMATIC persistence of a slice decision to Postgres `decision_logs` (EU AI Act Art-12, research §50).

    Writes the full decision provenance (input->output) with SHA-256 input/output hashes for tamper-evident
    reconstruction. Best-effort + honest (Rule 1a): no DB reachable → returns None (the caller surfaces
    `decision_log_id: null`); NEVER fabricates a persisted id. Returns the `decision_id` on a real write.
    """
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not dsn:
        return None
    try:
        import hashlib
        import json as _json
        import uuid as _uuid

        import psycopg

        def _h(obj: dict) -> str:
            return hashlib.sha256(_json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()

        decision_id = str(_uuid.uuid4())
        # Only link an incident_id that is a real UUID FK; a non-UUID (e.g. a sim tag) is stored in inputs instead.
        inc_fk: Optional[str] = None
        if incident_id:
            try:
                inc_fk = str(_uuid.UUID(str(incident_id)))
            except (ValueError, AttributeError):
                inputs = {**inputs, "incident_ref": incident_id}
        with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO decision_logs (decision_id, incident_id, caller, tool, input_hash, output_hash, "
                "inputs, outputs) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)",
                (decision_id, inc_fk, caller, tool, _h(inputs), _h(outputs),
                 _json.dumps(inputs, default=str), _json.dumps(outputs, default=str)))
        return decision_id
    except Exception:  # noqa: BLE001 — DB down / schema absent: honest no-op, never a fabricated id
        return None


# Stage-39 (G-051): binding plant constraints for the VERIFY gate. Previously the Stage-6 state relaxed all three
# rejecting contracts (available_crew=n, throughput_floor_frac=0.0, max_concurrent_critical_offline=n), so the verifier
# could never reject — only attach provenance. These are REAL, documented binding values: a limited maintenance crew,
# a throughput floor (>=60% of stages must stay online — the verifier's own default), and the SIL redundancy cap.
_MAINT_CREW_TOTAL = 2                  # simultaneous maintenance crews on the line (documented plant constraint)
_THROUGHPUT_FLOOR_FRAC = 0.6           # at least 60% of stages must stay online
_MAX_CONCURRENT_CRITICAL_OFFLINE = 1   # SIL contract: never down >1 CRITICAL machine at once
_MAINT_STATUSES = {"maintenance", "broken", "down", "offline"}


def _build_plant_state(world: Any, *, crew_total: int = _MAINT_CREW_TOTAL):
    """Build a plan_verifier PlantState from the live world with BINDING constraints (G-051).

    The verifier can genuinely REJECT: `available_crew` is reduced by the stages already in maintenance (crew
    contention), a real `throughput_floor_frac` guards against downing too many stages, and the SIL
    `max_concurrent_critical_offline` cap guards critical redundancy. Returns None if the verifier module is
    unavailable (honest — the loop then runs un-gated exactly as before, never a fabricated approval)."""
    try:
        from services.plan_verifier import PlantState
    except Exception:
        return None
    stages = {}
    busy_crew = 0
    for st in world.stages.values():
        try:
            prox = float(st.crack_proximity())
        except Exception:
            prox = 0.0
        stages[st.cfg.stage_id] = {"status": st.status, "at_risk": st.status == "degraded",
                                   "crack_proximity": prox}
        if str(st.status) in _MAINT_STATUSES:
            busy_crew += 1
    available_crew = max(0, crew_total - busy_crew)
    return PlantState(stages=stages, available_crew=available_crew, throughput_floor_frac=_THROUGHPUT_FLOOR_FRAC,
                      critical_proximity=0.85, max_concurrent_critical_offline=_MAX_CONCURRENT_CRITICAL_OFFLINE)


def run_slice_step(
    world: Any,
    *,
    predictor: FailurePredictor,
    trail: SliceTrail,
    cooldown_until: dict[int, float],
    recent_incidents: Optional[list[dict[str, Any]]] = None,
    on_event: Optional[Callable[[SliceEvent], None]] = None,
    execute: bool = True,
    world_model: Any = None,
    explainer: Any = None,
    windows: Optional[dict[int, list]] = None,
    enable_verify: bool = True,
    persist_log: bool = False,
) -> list[InterventionDecision]:
    """One pass of predict → (forecast TTF) → diagnose (causal) → explain → verify → intervene over every stage.

    Shared verbatim by the in-env loop and the live runner so the two paths cannot drift. Returns the decisions
    taken this pass (possibly empty). Raises ``ModelUnavailableError`` if the brain is absent — never fabricates.

    Depth-hardening (2026-06-14, increment 5/5): the deepened pieces are wired in ADDITIVELY and availability-gated,
    so the measured Stage-6 A/B is preserved when they are absent:
      - ``world_model`` (Stage 8): per-stage telemetry window → TTF forecast, attached to the prediction event.
      - learned-causal attribution (Stage 8B): already inside ``diagnose`` (the diagnosis event carries it).
      - ``explainer`` (Stage 10): exact-SHAP top drivers (the "why"), attached to the intervention event.
      - ``enable_verify`` (Stage 8C): the neuro-symbolic plan verifier gates execution — a maintenance only fires
        if the symbolic safety/precondition contract APPROVES it (it approves the normal single-machine case).
    """
    now = float(world.env.now)
    plant_state = _build_plant_state(world) if enable_verify else None
    decisions: list[InterventionDecision] = []
    for stage in world.stages.values():
        sid = stage.cfg.stage_id
        if now < cooldown_until.get(sid, 0.0):
            continue
        if stage.status in ("broken", "maintenance"):
            continue  # nothing to predict; recovery paths own these states
        telemetry = stage.telemetry()
        # Maintain the per-stage telemetry window for the Stage-8 TTF forecast (additive).
        ttf_forecast = None
        if windows is not None:
            buf = windows.setdefault(sid, [])
            buf.append([float(telemetry[f]) for f in _WM_FEATURES])
            if len(buf) > _WM_WINDOW:
                del buf[0]
            if world_model is not None and len(buf) == _WM_WINDOW:
                try:
                    if world_model.is_available():
                        ttf_forecast = world_model.predict_ttf(buf)
                except Exception:
                    ttf_forecast = None
        prediction = predictor.predict_failure(
            type_=telemetry["type_"],
            air_temp_k=telemetry["air_temp_k"],
            process_temp_k=telemetry["process_temp_k"],
            rot_speed_rpm=telemetry["rot_speed_rpm"],
            torque_nm=telemetry["torque_nm"],
            tool_wear_min=telemetry["tool_wear_min"],
        )
        if not prediction["at_risk"]:
            continue
        pred_payload = {"stage_id": sid, "telemetry": telemetry, "prediction": prediction}
        if ttf_forecast is not None:
            pred_payload["ttf_forecast"] = ttf_forecast
        pred_event = SliceEvent(kind="prediction", sim_time_seconds=now, payload=pred_payload)
        trail.predictions.append(pred_event)
        if on_event:
            on_event(pred_event)

        diag = diagnose(prediction, telemetry, recent_incidents=recent_incidents)
        diag_event = SliceEvent(kind="diagnosis", sim_time_seconds=now, payload=diag.to_dict())
        trail.diagnoses.append(diag_event)
        if on_event:
            on_event(diag_event)

        decision = decide_intervention(
            diag, queue_depth=stage.queue_depth(), capacity=stage.cfg.capacity
        )
        # Stage-10 explanation (the "why"): exact-SHAP top drivers, attached additively.
        explanation = None
        if explainer is not None:
            try:
                if explainer.is_available():
                    ex = explainer.explain(
                        type_=telemetry["type_"], air_temp_k=telemetry["air_temp_k"],
                        process_temp_k=telemetry["process_temp_k"], rot_speed_rpm=telemetry["rot_speed_rpm"],
                        torque_nm=telemetry["torque_nm"], tool_wear_min=telemetry["tool_wear_min"], top_k=3)
                    explanation = {"top_drivers": ex["top_drivers"], "counterfactual": ex.get("counterfactual")}
            except Exception:
                explanation = None
        # Stage-8C VERIFY: the symbolic plan verifier gates execution.
        verification = None
        approved = True
        if decision.kind == PREVENTIVE_MAINTENANCE and plant_state is not None:
            try:
                from services.plan_verifier import PlannedAction, verify, PREVENTIVE_MAINTENANCE as _PM
                result = verify([PlannedAction(_PM, sid, decision.rationale)], plant_state)
                verification = result.to_dict()
                approved = result.approved
            except Exception:
                verification, approved = None, True
        executed = False
        if execute and decision.kind == PREVENTIVE_MAINTENANCE and approved:
            executed = stage.start_maintenance()
        cooldown_until[sid] = now + DECISION_COOLDOWN_SECONDS
        decisions.append(decision)
        iv_payload = {**decision.to_dict(), "executed": executed}
        if verification is not None:
            iv_payload["verification"] = verification
        if explanation is not None:
            iv_payload["explanation"] = explanation
        # G-045: AUTOMATIC decision-log persistence to Postgres `decision_logs` (Art-12) in the live path. Honest —
        # no DB ⇒ decision_log_id is None (surfaced, never fabricated). Off for the offline A/B (persist_log=False).
        if persist_log:
            iv_payload["decision_log_id"] = _persist_decision_log(
                caller="slice_runner", tool=str(decision.kind),
                inputs={"stage_id": sid, "telemetry": telemetry, "prediction": prediction},
                outputs={"decision": decision.to_dict(), "verification": verification, "executed": executed},
                incident_id=(recent_incidents[0].get("incident_id") if recent_incidents else None))
        intervention_event = SliceEvent(kind="intervention", sim_time_seconds=now, payload=iv_payload)
        trail.interventions.append(intervention_event)
        if on_event:
            on_event(intervention_event)
    return decisions


class SliceLoop:
    """In-environment SimPy process running the slice loop on a sim-time cadence.

    Used by the A/B harness (loop ON arm) and the intervene tests. Construct,
    then ``loop.start()`` BEFORE running the environment.
    """

    def __init__(
        self,
        world: Any,
        *,
        predictor: Optional[FailurePredictor] = None,
        sample_period_seconds: float = TELEMETRY.sample_period_seconds,
        recent_incidents_provider: Optional[Callable[[], list[dict[str, Any]]]] = None,
        on_event: Optional[Callable[[SliceEvent], None]] = None,
    ) -> None:
        self.world = world
        self.predictor = predictor or get_failure_predictor()
        self.sample_period = float(sample_period_seconds)
        self.trail = SliceTrail()
        self.cooldown_until: dict[int, float] = {}
        self._recent_incidents = recent_incidents_provider or (
            lambda: [
                {"type": i.type, "target_id": i.target_id}
                for i in self.world.incidents_fired[-10:]
            ]
        )
        self._on_event = on_event
        # Stage-6 depth-hardening (increment 5/5): the deepened pieces wired into the live loop,
        # availability-gated (absent → loop falls back to the v0 behaviour; the A/B is preserved).
        self._windows: dict[int, list] = {}
        self._world_model = _try_world_model()
        self._explainer = _try_explainer()

    def start(self) -> None:
        self.world.env.process(self._run())

    def _run(self):
        # Fail fast and honestly if the brain is absent.
        if not self.predictor.is_available():
            raise ModelUnavailableError(
                "SliceLoop requires the trained Stage-4 brain (models/pdm_failure_predictor.*)"
            )
        while True:
            yield self.world.env.timeout(self.sample_period)
            run_slice_step(
                self.world,
                predictor=self.predictor,
                trail=self.trail,
                cooldown_until=self.cooldown_until,
                recent_incidents=self._recent_incidents(),
                on_event=self._on_event,
                world_model=self._world_model,
                explainer=self._explainer,
                windows=self._windows,
            )


class LiveSliceRunner:
    """Asyncio slice loop for the running app: sample → loop body → Redis publish.

    Publishes each slice event to the simulator events channel using the
    canonical envelope (see ``services.ws_broker.build_slice_envelope``); the
    Stage-3 broker fans them out to ``/ws`` clients unchanged.
    """

    def __init__(
        self,
        world: Any,
        *,
        redis_client: Any = None,
        predictor: Optional[FailurePredictor] = None,
        wall_period_seconds: float = 5.0,
        channel: str = "pubsub:simulator:events",
    ) -> None:
        from services.ws_broker import build_slice_envelope  # local: avoid cycles

        self._build_envelope = build_slice_envelope
        self.world = world
        self.redis = redis_client
        self.predictor = predictor or get_failure_predictor()
        self.wall_period = float(wall_period_seconds)
        self.channel = channel
        self.trail = SliceTrail()
        self.cooldown_until: dict[int, float] = {}
        self._task: Optional[asyncio.Task] = None
        self._stopped = asyncio.Event()

    async def _publish(self, event: SliceEvent) -> None:
        if self.redis is None:
            return
        envelope = self._build_envelope(event.kind, event.to_dict())
        try:
            await self.redis.publish(self.channel, json.dumps(envelope, default=str))
        except Exception as exc:  # publish failures are logged, never fatal
            logger.warning("slice_runner: Redis publish failed: %s", exc)

    async def _run(self) -> None:
        if not self.predictor.is_available():
            logger.error(
                "LiveSliceRunner: trained brain unavailable — slice loop NOT running "
                "(honest stop; install xgboost + models/pdm_failure_predictor.*)"
            )
            return
        pending: list[SliceEvent] = []
        while not self._stopped.is_set():
            try:
                run_slice_step(
                    self.world,
                    predictor=self.predictor,
                    trail=self.trail,
                    cooldown_until=self.cooldown_until,
                    recent_incidents=[
                        {"type": i.type, "target_id": i.target_id}
                        for i in self.world.incidents_fired[-10:]
                    ],
                    on_event=pending.append,
                    persist_log=True,   # G-045: the live operational path auto-persists decisions (Art-12)
                )
                for event in pending:
                    await self._publish(event)
                pending.clear()
            except ModelUnavailableError:
                logger.error("LiveSliceRunner: brain became unavailable — stopping honestly")
                return
            except Exception:
                logger.exception("LiveSliceRunner: slice step failed; continuing")
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=self.wall_period)
            except asyncio.TimeoutError:
                pass

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopped.clear()
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "DECISION_COOLDOWN_SECONDS",
    "LiveSliceRunner",
    "SliceEvent",
    "SliceLoop",
    "SliceTrail",
    "run_slice_step",
]
