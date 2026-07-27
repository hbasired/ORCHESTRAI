"""Stage 29 (G-023) — natural-language problem injection.

An operator describes a problem in plain English; the system parses it to a STRICT, validated structured incident
and feeds it into the SAME self-healing path any other incident takes. Design (research §40.2):

  * Parsing = Pydantic structured output (the 2026 gold standard). The LLM (Groq -> Ollama, Rule 9) is asked for a
    JSON object matching `InjectedIncident`; on validation failure it is re-asked ONCE with the error. If no LLM is
    reachable, a deterministic keyword parser handles the common cases and ABSTAINS (honest) on ambiguity.
  * Hard Rule 3 is preserved: the LLM NEVER actuates. It only produces a *proposed structured incident*; the
    incident enters `SimWorld.inject()` / the validator-gated LangGraph loop exactly like a sensor-fired one. The
    only actuator emitter remains `master.dispatch_order` (validator + trace-paired). The LLM is an input parser.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError

# The canonical incident vocabulary — mirrors simulation.entities.incident.InjectRequest (single source of the enum).
INCIDENT_TYPES = ("machine_crack", "robot_down", "late_delivery", "demand_spike", "defect_surge", "power_dip")
SEVERITIES = ("info", "warning", "critical")


class InjectedIncident(BaseModel):
    """The strict schema an NL problem is parsed into (validated before it can touch the sim)."""
    type: str = Field(description=f"one of {INCIDENT_TYPES}")
    target_id: Optional[int] = Field(default=None, description="stage/robot number if named, else null")
    severity: str = Field(default="warning", description=f"one of {SEVERITIES}")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="parser confidence in [0,1]")
    raw_text: str = Field(default="", description="the operator's original words")

    def validate_domain(self) -> None:
        if self.type not in INCIDENT_TYPES:
            raise ValueError(f"type must be one of {INCIDENT_TYPES}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}")


# ---- deterministic fallback parser (honest, abstains on ambiguity) --------------------------------------------

_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("machine_crack", ("crack", "overheat", "vibration", "torque", "bearing", "welder", "grind", "seiz")),
    ("robot_down", ("robot", "agv", "amr", "forklift", "arm down", "gripper")),
    ("late_delivery", ("late", "delivery", "delayed", "supplier", "shipment", "material short")),
    ("demand_spike", ("demand", "surge", "spike", "rush order", "backlog")),
    ("defect_surge", ("defect", "quality", "scrap", "reject", "flaw", "out of spec")),
    ("power_dip", ("power", "voltage", "outage", "brownout", "electrical")),
]
_CRIT = ("critical", "urgent", "emergency", "fire", "danger", "immediately", "down hard")
_INFO = ("minor", "slight", "small", "fyi", "low priority")


def parse_deterministic(nl: str) -> Optional[InjectedIncident]:
    """Keyword parser. Returns None (abstain) when nothing matches — never guesses a type."""
    q = (nl or "").lower()
    matched: Optional[str] = None
    for itype, kws in _KEYWORDS:
        if any(kw in q for kw in kws):
            matched = itype
            break
    if matched is None:
        return None
    # target id: "stage 3", "robot 2", "line 4", or a bare "#3"
    tid: Optional[int] = None
    m = re.search(r"(?:stage|robot|amr|agv|line|machine|unit)[ _#-]*(\d+)", q) or re.search(r"#(\d+)", q)
    if m:
        tid = int(m.group(1))
    severity = "critical" if any(w in q for w in _CRIT) else ("info" if any(w in q for w in _INFO) else "warning")
    return InjectedIncident(type=matched, target_id=tid, severity=severity, confidence=0.55, raw_text=nl)


# ---- LLM parser (Pydantic structured output + one re-ask) ------------------------------------------------------

_PARSE_SYSTEM = (
    "You convert an operator's plain-English factory problem report into a STRICT JSON object. "
    f"Fields: type (one of {list(INCIDENT_TYPES)}), target_id (integer stage/robot number or null), "
    f"severity (one of {list(SEVERITIES)}), confidence (0.0-1.0). "
    "Respond with ONLY the JSON object, no prose. If the report does not describe any of these problem types, "
    'return {"type": "none"}.'
)


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return None


async def parse_with_llm(nl: str, *, history_block: str = "") -> Optional[InjectedIncident]:
    """Parse via the free LLM into the validated schema; re-ask once on validation failure. None on abstain/failure.

    Stage 35 (C6-R3 tail): an optional `history_block` (prior dialogue turns) lets the LLM resolve coreference
    ("the same machine is still overheating" → the stage named earlier). Hard Rule 3 is unaffected — the output is
    still a validated `InjectedIncident` that enters the same validator-gated loop; history only aids the parse."""
    try:
        from agents.llm_client import get_llm_client, LLMMessage
        client = get_llm_client()
    except Exception:  # noqa: BLE001
        return None

    hist = f"{history_block}\n\n" if history_block else ""

    async def _one(extra: str = "") -> Optional[dict[str, Any]]:
        try:
            resp = await client.generate(
                [LLMMessage(role="system", content=_PARSE_SYSTEM),
                 LLMMessage(role="user", content=f"{hist}REPORT: {nl}{extra}")],
                temperature=0.0, max_tokens=200, fallback=True)
            return _extract_json(getattr(resp, "content", "") or "")
        except Exception:  # noqa: BLE001
            return None

    data = await _one()
    for attempt in range(2):
        if not data:
            break
        if data.get("type") == "none":
            return None  # LLM says it's not one of our incident types -> honest abstain
        try:
            inc = InjectedIncident(**{k: data.get(k) for k in ("type", "target_id", "severity", "confidence") if k in data},
                                   raw_text=nl)
            inc.validate_domain()
            if not inc.confidence:
                inc.confidence = 0.7
            return inc
        except (ValidationError, ValueError) as e:
            if attempt == 0:
                data = await _one(extra=f"\n\nYour previous answer was invalid: {e}. Return corrected JSON only.")
            else:
                return None
    return None


async def parse_incident(nl: str, *, use_llm: bool = True, history_block: str = "") -> tuple[Optional[InjectedIncident], str]:
    """Parse NL -> InjectedIncident. Returns (incident|None, method). None = honest abstain. `history_block` aids
    coreference in the LLM parse (Stage 35); the deterministic fallback is history-independent."""
    if use_llm:
        inc = await parse_with_llm(nl, history_block=history_block)
        if inc is not None:
            return inc, "llm"
    inc = parse_deterministic(nl)
    return (inc, "deterministic") if inc is not None else (None, "abstain")


# ---- inject + run through the validator-gated loop -------------------------------------------------------------

def _to_inject_request(inc: InjectedIncident):
    from simulation.entities.incident import InjectRequest
    return InjectRequest(type=inc.type, target_id=inc.target_id, severity=inc.severity,
                         details={"source": "nl_injection", "raw_text": inc.raw_text, "confidence": inc.confidence})


async def inject_and_run(nl: str, *, world: Optional[Any] = None, run_loop: bool = False,
                         use_llm: bool = True, session_id: Optional[str] = None) -> dict[str, Any]:
    """Parse an NL problem and feed it into the sim / self-healing loop. NEVER actuates directly (Hard Rule 3).

    Stage 35 (C6-R3 tail): if `session_id` is given, prior dialogue turns are loaded to resolve coreference in the
    parse (e.g. "the same machine"); the report + outcome are appended to the session. Hard Rule 3 unchanged."""
    history_block = ""
    if session_id and use_llm:
        import asyncio
        from conversation.session_store import recent_turns, format_history
        history_block = await asyncio.to_thread(lambda: format_history(recent_turns(session_id)))

    inc, method = await parse_incident(nl, use_llm=use_llm, history_block=history_block)
    if inc is None:
        if session_id:
            _record_inject_turn(session_id, nl, "Could not parse a known incident — abstained.")
        return {"accepted": False, "reason": "Could not parse the report into a known incident type — abstaining.",
                "method": method, "raw_text": nl, "session_id": session_id}

    out: dict[str, Any] = {"accepted": True, "method": method, "session_id": session_id,
                           "incident": inc.model_dump(), "raw_text": nl}
    if session_id:
        _record_inject_turn(session_id, nl, f"Parsed incident: {inc.type} target={inc.target_id} severity={inc.severity}")

    # 1) inject into the running sim (a state mutation, NOT an actuator command).
    if world is not None:
        try:
            created = world.inject(_to_inject_request(inc))
            out["injected"] = True
            out["incident_id"] = getattr(created, "id", None) or getattr(created, "incident_id", None)
        except Exception as e:  # noqa: BLE001
            out["injected"] = False
            out["inject_error"] = str(e)

    # 2) optionally run the incident through the validator-gated self-healing loop (decide/verify -> safety validator).
    if run_loop:
        try:
            import asyncio
            from agents.runtime.graph import run_incident
            incident_dict = {"type": inc.type, "target_id": inc.target_id, "severity": inc.severity,
                             "source": "nl_injection"}
            result = await asyncio.to_thread(run_incident, incident_dict)
            out["loop"] = {"backend": result.get("backend"), "interrupted": result.get("interrupted"),
                           "decisions": result.get("decisions", []), "audit_seqs": result.get("audit_seqs", [])}
        except Exception as e:  # noqa: BLE001
            out["loop_error"] = str(e)

    out["note"] = ("The LLM parsed the report into a proposed structured incident; it did NOT actuate. The incident "
                   "enters the same validator-gated self-healing loop as a sensor-fired one (Hard Rule 3).")
    return out


def _record_inject_turn(session_id: str, report: str, outcome: str) -> None:
    """Persist the operator's NL report + the parse outcome (best-effort; honest no-op if the store is down)."""
    try:
        from conversation.session_store import append_turn
        append_turn(session_id, "user", report)
        append_turn(session_id, "assistant", outcome)
    except Exception:  # noqa: BLE001
        pass


__all__ = ["InjectedIncident", "INCIDENT_TYPES", "SEVERITIES",
           "parse_deterministic", "parse_with_llm", "parse_incident", "inject_and_run"]
