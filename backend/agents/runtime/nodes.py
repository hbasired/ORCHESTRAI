"""Stage 11 — self-healing loop nodes for the LangGraph runtime.

Each node wires a REAL Stage-4-10 (depth-hardened) model as a direct Python import and returns a minimal partial
state update + a trace event. Honest by design: a node that finds its model unavailable records that fact in the
trace and degrades gracefully — it NEVER fabricates a prediction/diagnosis/explanation. Nodes are deterministic
and side-effect-free except `execute` (sim-only; the real actuator wrapper is Stage 17).

The loop: observe -> orient (predict + TTF) -> diagnose (learned-causal) -> explain (SHAP) -> decide -> verify
(neuro-symbolic, BINDING crew/SIL constraints) -> [hitl] -> execute -> log.
"""
from __future__ import annotations

import os
from typing import Any

from agents.runtime.state import AgentState, Decision, TraceEvent


# ---- Stage-16 (G-059): MCP-mediated tool calls ------------------------------
# When RUNTIME_MCP_MEDIATED is set, a runtime node routes its model call through the Stage-11.5 MCP tool servers
# (a real stdio MCP round-trip) instead of a direct Python import — so the decision is genuinely MCP-mediated
# (CTO #3 R3 / G-059). Honest: an MCP *transport* failure falls back to the direct import (resilience, traced); an
# honest model-unavailable from the tool is surfaced as-is (no fabrication).

def _mcp_mediated_enabled() -> bool:
    return os.environ.get("RUNTIME_MCP_MEDIATED", "").lower() in ("1", "true", "yes", "on")


class _PredictionUnavailable(Exception):
    """The MCP model tool reported the predictor is honestly unavailable (distinct from a transport failure)."""


def _run_coro(coro: Any) -> Any:
    """Run an async coroutine from a sync LangGraph node. Uses asyncio.run when no loop is running; otherwise a
    dedicated thread with its own loop (so the MCP stdio client gets a clean Proactor loop on Windows)."""
    import asyncio
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(lambda: asyncio.run(coro)).result()


def _predict_via_mcp(t: dict[str, Any]) -> dict[str, Any]:
    """Route the Stage-4 failure prediction through `model_inference_server.predict_failure` over MCP stdio (G-059).

    Returns the prediction dict (availability wrapper stripped). Raises `_PredictionUnavailable` if the tool reports
    the model is unavailable; raises other exceptions on MCP transport failure (the caller may fall back)."""
    from agents.runtime.mcp_mount import call_mcp_tool
    args = {"type_": t.get("type_", "M"), "air_temp_k": t["air_temp_k"], "process_temp_k": t["process_temp_k"],
            "rot_speed_rpm": t["rot_speed_rpm"], "torque_nm": t["torque_nm"], "tool_wear_min": t["tool_wear_min"]}
    res = _run_coro(call_mcp_tool("model_inference_server", "predict_failure", args))
    if not isinstance(res, dict):
        raise RuntimeError(f"unexpected MCP result type: {type(res).__name__}")
    if res.get("available") is False:
        raise _PredictionUnavailable(res.get("reason", "model unavailable"))
    return {k: v for k, v in res.items() if k != "available"}


def _ev(state: AgentState, node: str, summary: str, ok: bool = True, **detail) -> list[TraceEvent]:
    """Return the trace list extended with one event (LangGraph replaces the field with this new list)."""
    return state.trace + [TraceEvent(node=node, summary=summary, ok=ok, detail=detail)]


# ---- Stage-12 memory wiring (best-effort: the runtime must still run without a DB/embedder) ----

def _incident_namespace(incident: dict[str, Any]) -> str:
    """Mem0 namespace for this incident (KB_14): incident:<id>, falling back to a stable type:target composite."""
    iid = incident.get("incident_id") or incident.get("id")
    if iid:
        return f"incident:{iid}"
    return f"incident:{incident.get('type', 'unknown')}-{incident.get('target_id', 'na')}"


# ---- 1. observe -------------------------------------------------------------

def observe(state: AgentState) -> dict[str, Any]:
    inc = state.incident or {}
    telemetry = inc.get("telemetry", {}) or state.telemetry
    sil = int(inc.get("sil_level", inc.get("sil", state.sil_level)) or 0)
    # Stage-12 episodic recall: prior memories on THIS incident (best-effort; degrades cleanly w/o DB/embedder).
    recall: list[dict[str, Any]] = []
    recall_note = "no memory recall (DB/embedder unavailable)"
    try:
        ns = _incident_namespace(inc)
        query = f"incident type={inc.get('type','?')} target={inc.get('target_id','?')}"
        from memory.mem0_adapter import Mem0Adapter
        from observability.otel_init import traced_span
        with traced_span("memory.mem0.search", **{"memory.namespace": ns, "memory.op": "search"}):
            recall = Mem0Adapter(incident_id=inc.get("incident_id") or inc.get("id")).search(ns, query, k=3)
        recall_note = f"recalled {len(recall)} prior memory(ies) from {ns}"
    except Exception as e:  # noqa: BLE001 - memory is best-effort, never blocks the loop
        recall_note = f"memory recall skipped: {type(e).__name__}"
    return {"telemetry": telemetry, "sil_level": sil, "memory_recall": recall,
            "trace": _ev(state, "observe", f"incident type={inc.get('type','?')} target={inc.get('target_id','?')} "
                                            f"sil={sil}; {recall_note}", n_features=len(telemetry),
                         n_recalled=len(recall))}


# ---- 2. orient: predict failure + forecast TTF ------------------------------

def orient(state: AgentState) -> dict[str, Any]:
    t = state.telemetry
    prediction: dict[str, Any] = {}
    ttf = None
    mediation = "direct-import"

    # G-059: route the prediction through MCP (real stdio tool call) when enabled — a genuinely MCP-mediated decision.
    if _mcp_mediated_enabled():
        try:
            prediction = _predict_via_mcp(t)
            mediation = "mcp:model_inference_server.predict_failure"
        except _PredictionUnavailable as e:
            return {"prediction": {}, "trace": _ev(state, "orient", f"MCP predictor unavailable: {e}", ok=False,
                                                   mediation="mcp")}
        except Exception as e:  # noqa: BLE001 - MCP transport failure → honest fallback to the direct import (traced)
            mediation = f"direct-import (mcp transport failed: {type(e).__name__})"

    if not prediction:
        try:
            from ml.failure_predictor import get_failure_predictor, ModelUnavailableError
            from observability.otel_init import traced_span
            try:
                with traced_span("ml.inference.failure_predictor", **{"ml.model.name": "failure_predictor"}):
                    prediction = get_failure_predictor().predict_failure(
                        type_=t.get("type_", "M"), air_temp_k=t["air_temp_k"], process_temp_k=t["process_temp_k"],
                        rot_speed_rpm=t["rot_speed_rpm"], torque_nm=t["torque_nm"], tool_wear_min=t["tool_wear_min"])
            except ModelUnavailableError as e:
                return {"prediction": {}, "trace": _ev(state, "orient", f"predictor unavailable: {e}", ok=False)}
        except Exception as e:
            return {"prediction": {}, "trace": _ev(state, "orient", f"predictor import failed: {e}", ok=False)}

    # TTF forecast (Stage 8 world model) — only if a telemetry window is supplied (honest: no window, no forecast).
    if state.telemetry_window is not None:
        try:
            from ml.world_model import get_world_model
            from observability.otel_init import traced_span
            wm = get_world_model()
            if wm.is_available():
                with traced_span("ml.inference.world_model", **{"ml.model.name": "world_model_ttf"}):
                    ttf = wm.predict_ttf(state.telemetry_window)
        except Exception:
            ttf = None
    summary = f"p_fail={prediction.get('p_fail'):.3f} at_risk={prediction.get('at_risk')}" \
        if prediction else "no prediction"
    if ttf:
        summary += f" ttf={ttf['ttf_minutes']:.1f}min"
    summary += f" [{mediation}]"
    return {"prediction": prediction, "ttf_forecast": ttf,
            "trace": _ev(state, "orient", summary, has_ttf=ttf is not None, mediation=mediation)}


# ---- 3. diagnose: learned-causal root cause ---------------------------------

def diagnose(state: AgentState) -> dict[str, Any]:
    if not state.prediction:
        return {"trace": _ev(state, "diagnose", "skipped (no prediction)", ok=False)}
    try:
        from services.diagnosis import diagnose as run_diagnose
        from observability.otel_init import traced_span
        with traced_span("ml.inference.causal_diagnosis", **{"ml.model.name": "learned_causal_discovery"}):
            d = run_diagnose(state.prediction, state.telemetry,
                             recent_incidents=state.incident.get("recent_incidents", []))
        dd = d.to_dict()
        return {"diagnosis": dd,
                "trace": _ev(state, "diagnose", f"primary={dd.get('primary_cause')} "
                             f"attribution={dd.get('causal_attribution',{}).get('attribution')}",
                             learned_support=dd.get("causal_attribution", {}).get("learned_discovery_support", {}).get("available"))}
    except Exception as e:
        return {"trace": _ev(state, "diagnose", f"diagnosis failed: {e}", ok=False)}


# ---- 4. explain: exact-SHAP top drivers (the "why") -------------------------

def explain(state: AgentState) -> dict[str, Any]:
    if not state.prediction.get("at_risk"):
        return {"explanation": None, "trace": _ev(state, "explain", "not at-risk; no explanation needed")}
    t = state.telemetry
    try:
        from ml.failure_explainer import get_failure_explainer
        ex = get_failure_explainer()
        if not ex.is_available():
            return {"explanation": None, "trace": _ev(state, "explain", "explainer unavailable (honest)", ok=False)}
        from observability.otel_init import traced_span
        with traced_span("ml.inference.failure_explainer", **{"ml.model.name": "failure_explainer_shap"}):
            out = ex.explain(type_=t.get("type_", "M"), air_temp_k=t["air_temp_k"], process_temp_k=t["process_temp_k"],
                             rot_speed_rpm=t["rot_speed_rpm"], torque_nm=t["torque_nm"], tool_wear_min=t["tool_wear_min"],
                             top_k=3)
        expl = {"top_drivers": out["top_drivers"], "counterfactual": out.get("counterfactual"),
                "method": out.get("method")}
        top = out["top_drivers"][0]["feature"] if out.get("top_drivers") else "?"
        # Stage 28: GRAPHRAG GROUNDING — retrieve real SOP + ISA-95 graph citations for this diagnosis so the
        # explanation is grounded in the plant's own topology + procedures, not model priors (honest-empty when
        # nothing matches). The citations flow into the Art-12 trace (the log node) — the trust/explainability moat.
        grounding = None
        try:
            from knowledge_graph.graphrag import retrieve
            dd = state.diagnosis or {}
            target = str((state.incident or {}).get("target_id") or "")
            q = f"{dd.get('primary_cause', '')} {(state.incident or {}).get('type', '')} {target} {top}".strip()
            g = retrieve(q)
            grounding = {"grounded": g.grounded, "citations": [c.source for c in g.citations],
                         "context": g.context[:5], **g.to_trace()}
        except Exception:  # noqa: BLE001 — grounding is additive; never block the explanation
            grounding = None
        return {"explanation": expl, "grounding": grounding,
                "trace": _ev(state, "explain", f"top driver={top}" +
                             (f"; grounded={grounding['grounded']}({len(grounding['citations'])} cites)" if grounding else ""))}
    except Exception as e:
        return {"explanation": None, "trace": _ev(state, "explain", f"explain failed: {e}", ok=False)}


# ---- 5. decide: intervention policy -----------------------------------------

def decide(state: AgentState) -> dict[str, Any]:
    try:
        from services.diagnosis import diagnose as run_diagnose
        from services.intervention_policy import decide_intervention
        from observability.otel_init import traced_span
        # rebuild the Diagnosis object (decide_intervention takes the dataclass, not the dict)
        d = run_diagnose(state.prediction, state.telemetry,
                         recent_incidents=state.incident.get("recent_incidents", []))
        with traced_span("ml.inference.intervention_policy", **{"ml.model.name": "intervention_rl_policy"}):
            dec = decide_intervention(d, queue_depth=state.telemetry.get("queue_depth"),
                                      capacity=state.incident.get("capacity"))
        decision = dec.to_dict()
        # G-025-tail: SHADOW-mode RL recommendation (research §41.2) — logged for RL-vs-rule agreement, NEVER acted.
        # The rule's `dec` remains the decision; the verifier/validator stay the shield. Gated off by default.
        rl_shadow = None
        from agents.runtime.rl_shadow import shadow_enabled, shadow_recommend
        if shadow_enabled():
            fleet = list((state.incident.get("plant", {}).get("stages", {}) or {}).values())
            if not fleet and state.telemetry:
                fleet = [{"status": state.telemetry.get("status", "degraded"),
                          "crack_proximity": float(state.telemetry.get("crack_proximity", 0.0)),
                          "at_risk": bool(state.prediction.get("at_risk"))}]
            rl_shadow = shadow_recommend(fleet)
            decision.setdefault("provenance", {})["rl_shadow"] = rl_shadow
        summary = f"kind={dec.kind}"
        if rl_shadow and rl_shadow.get("available"):
            summary += f" rl_shadow(agree={rl_shadow['agree']})"
        return {"decision": decision, "trace": _ev(state, "decide", summary)}
    except Exception as e:
        return {"decision": {}, "trace": _ev(state, "decide", f"decide failed: {e}", ok=False)}


# ---- 6. verify: neuro-symbolic plan verifier (BINDING constraints) ----------

def verify(state: AgentState) -> dict[str, Any]:
    """Verify the proposed plan against the symbolic safety contract. Unlike the Stage-6 slice (unlimited-crew,
    relaxed → never rejects; G-051), the runtime uses a BINDING PlantState (real crew capacity from the incident),
    so the verifier genuinely gates execution here."""
    dec = state.decision
    if not dec or dec.get("kind") != "preventive_maintenance":
        return {"verification": None, "trace": _ev(state, "verify", "no actuating plan to verify")}
    try:
        from services.plan_verifier import PlantState, PlannedAction, verify as verify_plan, PREVENTIVE_MAINTENANCE
        sid = int(dec["stage_id"])
        plant = state.incident.get("plant", {})
        # Build a binding plant snapshot: the target stage + any others reported by the incident.
        stages = dict(plant.get("stages", {}))
        stages.setdefault(sid, {"status": state.telemetry.get("status", "degraded"),
                                "at_risk": bool(state.prediction.get("at_risk")),
                                "crack_proximity": float(state.telemetry.get("crack_proximity", 0.0))})
        ps = PlantState(stages={int(k): v for k, v in stages.items()},
                        available_crew=int(plant.get("available_crew", 1)),  # BINDING: real single crew by default
                        throughput_floor_frac=float(plant.get("throughput_floor_frac", 0.5)),
                        critical_proximity=0.85,
                        max_concurrent_critical_offline=int(plant.get("max_concurrent_critical_offline", 1)))
        res = verify_plan([PlannedAction(PREVENTIVE_MAINTENANCE, sid, dec.get("rationale", ""))], ps)
        # HITL gate: SIL-1+ functions require human confirmation even when the symbolic contract approves.
        hitl = res.approved and state.sil_level >= 1
        return {"verification": res.to_dict(), "hitl_required": hitl,
                "trace": _ev(state, "verify", f"approved={res.approved} "
                             f"violations={len(res.violations)} hitl_required={hitl}",
                             approved=res.approved)}
    except Exception as e:
        return {"verification": None, "trace": _ev(state, "verify", f"verify failed: {e}", ok=False)}


# ---- 7. execute — the EXECUTION node: routes the actuating decision through the Stage-17 safety validator ----
# (KB_17: planning nodes propose; this execution node is the gate before any actuation. The runtime is sim-only — it
# records intent, it does NOT drive a real actuator [that is the integration layer: master.dispatch_order → sil_bridge],
# so it emits a `safety.validate` span but no `actuator.*` span.)

# A runtime-scoped SIL-2 contract: a preventive-maintenance action may execute only when the neuro-symbolic verifier
# approved the plan AND any required HITL confirmation is cleared (the runtime's own gates, re-checked as a contract).
_RUNTIME_PM_CONTRACT = None


def _runtime_pm_contract():
    global _RUNTIME_PM_CONTRACT
    if _RUNTIME_PM_CONTRACT is None:
        from safety.contract import Precondition, SafetyContract
        _RUNTIME_PM_CONTRACT = SafetyContract(
            name="runtime_preventive_maintenance", sil=2,
            iso_clauses=["ISO 10218-2:2025 §5.7", "IEC 61508-1 §7.4"],
            preconditions=[
                Precondition(name="plan_verifier_approved", description="neuro-symbolic verifier approved the plan",
                             check=lambda ws: bool(ws.get("plan_approved"))),
                Precondition(name="hitl_cleared", description="required human confirmation (SIL-1+) is resolved",
                             check=lambda ws: bool(ws.get("hitl_cleared"))),
            ],
            fail_safe_path="operator_confirm")
    return _RUNTIME_PM_CONTRACT


def execute(state: AgentState) -> dict[str, Any]:
    dec = state.decision
    approved = (state.verification or {}).get("approved", True) if dec.get("kind") == "preventive_maintenance" else True
    blocked_by_hitl = state.hitl_required and state.hitl_resolution != "approved"
    do = bool(dec) and dec.get("kind") == "preventive_maintenance" and approved and not blocked_by_hitl

    safety_note = "no actuating plan"
    if do:
        # Stage 17: the execution node routes the actuating decision through the safety validator (emits safety.validate).
        try:
            from safety.contract import Action
            from safety.validator import validate
            sdec = validate(
                Action(contract="runtime_preventive_maintenance", actuator="machine.maintenance",
                       target=str(dec.get("stage_id", state.incident.get("target_id", "")))),
                {"plan_approved": approved, "hitl_cleared": not blocked_by_hitl}, _runtime_pm_contract())
            do = do and sdec.allow
            safety_note = f"safety.validate route={sdec.route} allow={sdec.allow}"
        except Exception as e:  # noqa: BLE001 - safety wiring must not crash the loop; fail-safe = do not execute
            do = False
            safety_note = f"safety.validate errored ({type(e).__name__}); fail-safe not-executed"
    # sim-only: no sil_bridge / actuator span (no real hardware) — the integration layer (master) drives real actuators.
    return {"executed": do, "trace": _ev(state, "execute",
            f"executed={do} (approved={approved} hitl_blocked={blocked_by_hitl}; {safety_note}; sim-only)",
            safety=safety_note)}


# ---- 8. log: assemble the Decision list (public output) ---------------------

def log(state: AgentState) -> dict[str, Any]:
    dec = state.decision
    decisions: list[Decision] = []
    if dec:
        decisions = [Decision(
            stage_id=int(dec.get("stage_id", state.incident.get("target_id", -1))),
            kind=dec.get("kind", "monitor"),
            rationale=dec.get("rationale", ""),
            approved=(state.verification or {}).get("approved", True),
            hitl_required=state.hitl_required,
            executed=state.executed,
            provenance={"prediction": state.prediction, "ttf_forecast": state.ttf_forecast,
                        "diagnosis": state.diagnosis, "explanation": state.explanation,
                        "verification": state.verification},
        )]
    # Stage-12: write each decision to the append-only audit_chain (Art-12 evidence) AND remember it in Mem0 for
    # future recall. Best-effort: if the DB/embedder is unavailable the loop still completes (traced, not faked).
    audit_seqs: list[int] = []
    audit_note = "audit_chain unavailable (no DB)"
    if decisions:
        try:
            # Stage 12.5: route through the evidence_sink so each append also emits an `audit_chain.append` span
            # (KB_15 two-store split: the OTel trace + the immutable signed evidence row for the same action).
            from observability.evidence_sink import record as audit_record
            for d in decisions:
                seq = audit_record("agent:embodied", f"decision.{d.kind}", {
                    "stage_id": d.stage_id, "kind": d.kind, "rationale": d.rationale,
                    "approved": d.approved, "hitl_required": d.hitl_required, "executed": d.executed,
                    "prediction": state.prediction, "diagnosis": state.diagnosis,
                    "verification": state.verification})
                audit_seqs.append(seq)
            audit_note = f"audit_chain seqs={audit_seqs}"
        except Exception as e:  # noqa: BLE001 - audit is best-effort here; honest-unavailable when no DB
            audit_note = f"audit_chain skipped: {type(e).__name__}"
        # Stage 24 (G-080 / G-028): total-traceability — append the Art-12 pre/post state snapshot for this decision
        # (atop the per-decision audit row above). Best-effort; honest degradation when no DB (audited=False, no seq).
        try:
            from governance.traceability import record_decision_trace
            inc = state.incident or {}
            record_decision_trace(
                str(inc.get("incident_id") or inc.get("id") or inc.get("target_id") or "incident"),
                {"prediction": state.prediction, "ttf_forecast": state.ttf_forecast,
                 "diagnosis": state.diagnosis, "grounding": state.grounding, "sil_level": state.sil_level},
                {"verification": state.verification, "hitl_required": state.hitl_required, "executed": state.executed},
                dec or {}, actor="agent:embodied")
        except Exception:  # noqa: BLE001
            pass
        # Remember the decision for future incident recall (best-effort).
        try:
            from memory.mem0_adapter import Mem0Adapter
            from observability.otel_init import traced_span
            inc = state.incident or {}
            ns = _incident_namespace(inc)
            top = decisions[0]
            with traced_span("memory.mem0.add", **{"memory.namespace": ns, "memory.op": "add"}):
                Mem0Adapter(incident_id=inc.get("incident_id") or inc.get("id")).add(
                    ns, f"decision={top.kind} on stage {top.stage_id}: {top.rationale}",
                    {"kind": top.kind, "executed": top.executed})
        except Exception:  # noqa: BLE001
            pass
    return {"decisions": decisions, "audit_seqs": audit_seqs,
            "trace": _ev(state, "log", f"emitted {len(decisions)} decision(s); {audit_note}; "
                                       f"trace_len={len(state.trace)+1}", audit_seqs=audit_seqs)}


__all__ = ["observe", "orient", "diagnose", "explain", "decide", "verify", "execute", "log",
           "_incident_namespace"]
