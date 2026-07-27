"""Stage 29 — Conversational Factory Intelligence API (research §40).

  * POST /factory/ask       (G-022) — grounded operational QA + "why did X happen?" (Verifier honest-empty).
  * POST /factory/inject    (G-023) — NL problem injection into the validator-gated self-healing loop (Hard Rule 3).
  * POST /factory/diagnose  (G-026) — information-gain active diagnosis over the LIVE sim stages before intervening.

All free/local (Groq->Ollama, Rule 9). Every surface answers from real data or degrades honestly (503 / abstain).
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/factory", tags=["Conversational Factory Intelligence (Stage 29)"])


def _world() -> Optional[Any]:
    """The live SimWorld if one is bound to the app (shared with the simulation routes), else None."""
    try:
        from api.simulation_routes import get_sim_world
        return get_sim_world()
    except Exception:  # noqa: BLE001
        return None


# ---- G-022: ask the factory -----------------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(min_length=1, description="operator's natural-language question")
    use_llm: bool = True
    session_id: Optional[str] = Field(default=None, description="opt-in multi-turn dialogue session (Stage 35)")


@router.post("/ask")
async def ask(req: AskRequest) -> dict[str, Any]:
    """Answer an operator question grounded in real evidence (decision traces / SOPs / live sim). Honest-empty if none.
    Pass `session_id` for a multi-turn dialogue (history aids phrasing/coreference; grounding stays per-question)."""
    from conversation.ask import ask_factory
    return await ask_factory(req.question, world=_world(), use_llm=req.use_llm, session_id=req.session_id)


# ---- G-023: NL problem injection ------------------------------------------------------------------------------

class InjectRequestBody(BaseModel):
    report: str = Field(min_length=1, description="operator's plain-English problem report")
    run_loop: bool = Field(default=False, description="also run it through the self-healing loop")
    use_llm: bool = True
    session_id: Optional[str] = Field(default=None, description="opt-in multi-turn dialogue session (Stage 35)")


@router.post("/inject")
async def inject(req: InjectRequestBody) -> dict[str, Any]:
    """Parse an NL problem into a validated structured incident and feed it into the sim / self-healing loop.

    Hard Rule 3: the LLM never actuates — it produces a proposed structured incident that enters the same
    validator-gated loop as a sensor-fired one. Pass `session_id` for coreference resolution across turns.
    """
    from conversation.nl_inject import inject_and_run
    return await inject_and_run(req.report, world=_world(), run_loop=req.run_loop, use_llm=req.use_llm,
                                session_id=req.session_id)


# ---- G-026: active diagnosis over the live sim ----------------------------------------------------------------

class DiagnoseRequest(BaseModel):
    commit_threshold: float = Field(default=0.85, ge=0.5, le=0.999)
    max_probes: int = Field(default=8, ge=1, le=32)
    tpr: float = Field(default=0.9, ge=0.5, le=1.0, description="probe true-positive rate")
    fpr: float = Field(default=0.1, ge=0.0, le=0.5, description="probe false-positive rate")


def _stage_anomalous(report: dict[str, Any]) -> bool:
    """Anomaly classifier for a stage health vector (real thresholds on the sim snapshot)."""
    status = str(report.get("status", "")).lower()
    if status and status not in ("running", "idle", "ok", "operational", "healthy"):
        return True
    if isinstance(report.get("time_broken_seconds"), (int, float)) and report["time_broken_seconds"] > 0.0:
        return True
    dr = report.get("defect_rate_effective")
    if isinstance(dr, (int, float)) and dr >= 0.08:
        return True
    return False


class _StageProbe:
    """A Probeable wrapper over a live sim stage — `self_check()` re-reads its current snapshot (diagnose.request)."""
    def __init__(self, agent_id: str, world: Any, stage_key: Any):
        self.id = agent_id
        self._world = world
        self._key = stage_key

    def self_check(self) -> dict[str, Any]:
        stage = self._world.stages.get(self._key)
        if stage is None:
            raise RuntimeError("stage not found")  # -> timeout/fault
        return stage.snapshot()


@router.post("/diagnose")
async def diagnose(req: DiagnoseRequest) -> dict[str, Any]:
    """Run information-gain active diagnosis over the live sim stages: probe -> reason -> commit/abstain (KB_25 §1b)."""
    world = _world()
    if world is None or not getattr(world, "stages", None):
        return {"available": False, "reason": "no live simulation bound — active diagnosis needs running agents to probe."}

    from conversation.active_diagnosis import DiagnosisModel, make_probe_fn, run_active_diagnosis

    stage_keys = list(world.stages.keys())
    agents = {f"stage-{k}": _StageProbe(f"stage-{k}", world, k) for k in stage_keys}
    model = DiagnosisModel(agent_ids=list(agents.keys()), include_no_fault=True, tpr=req.tpr, fpr=req.fpr)
    probe_fn = make_probe_fn(agents, anomaly_classifier=_stage_anomalous)
    result = run_active_diagnosis(model, probe_fn, commit_threshold=req.commit_threshold,
                                  max_probes=req.max_probes, audit=True)
    out = result.to_dict()
    out["available"] = True
    out["agents_probed"] = list({s["probe"] for s in result.steps})
    out["note"] = ("Entropy-driven probe selection (mutual information) + exact Bayesian belief update; commits only "
                   "above the confidence threshold, else abstains/escalates. Misdiagnosis is a recorded outcome.")
    return out


# ---- G-024: bidirectional CDC — a DB value-edit → diagnose → self-optimize (Stage 37) -------------------------

class DbEditRequest(BaseModel):
    table: str = Field(min_length=1, description="edited table: stages | inventory | suppliers")
    column: str = Field(min_length=1, description="edited value column, e.g. defect_rate / current_stock / reliability_score")
    old_value: Optional[float] = Field(default=None, description="prior value (optional)")
    new_value: float = Field(description="the new value the operator wrote")
    target_id: Optional[int] = Field(default=None, description="row id (stage/inventory/supplier)")
    context: Optional[dict[str, Any]] = Field(default=None, description="e.g. {'reorder_point': 600} for inventory")
    run_loop: bool = Field(default=False, description="also drive the diagnosed problem through the self-healing loop")


@router.post("/db-edit")
async def db_edit(req: DbEditRequest) -> dict[str, Any]:
    """Diagnose the problem an operator's DB value-edit induced, then (optionally) self-optimize (G-024, bidirectional CDC).

    This is the API view of the same reasoning the live CDC trigger drives: a value edit → root-cause diagnosis →
    the validator-gated self-healing loop. Hard Rule 3: the reasoner proposes; it never actuates. A benign edit
    returns `diagnosed=False` (honest — no fabricated problem).
    """
    import asyncio as _asyncio

    from ingestion.cdc_reasoner import process_value_edit
    return await _asyncio.to_thread(
        process_value_edit, req.table, req.column, req.old_value, req.new_value,
        target_id=req.target_id, context=req.context, run_loop=req.run_loop)


__all__ = ["router"]
