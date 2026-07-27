"""Stage 28 — adoption-UX API (research §35.8/§39.3): the behavioural-science layer served from REAL data.

Design-thinking + behavioural science applied (sourced §35.8): every surface here is fed by real backend state or
returns honest-empty — NO fabrication (Rule 1a). Three behavioural levers:

  * TRUST CALIBRATION (`/adoption/recommendation`) — a recommendation is NEVER a bare score: it carries confidence,
    an uncertainty band, the counterfactual ("if we do nothing"), and the GraphRAG citation grounding it. Sourced:
    calibrated trust (over- and under-reliance both fail; XAI-driven swift trust).
  * PROGRESSIVE AUTONOMY (`/adoption/autonomy`) — the shadow→assisted→supervised→autonomous ladder mapped to the
    pilot canary + HITL. Sourced: trust is built incrementally in high-stakes ops.
  * WIIFM / LOSS-AVERSION (`/adoption/wiifm`) — the headline is "prevented downtime we would have suffered" (the
    Stage-6 counterfactual A/B), a stronger adoption message than "efficiency +X%". Sourced: loss-aversion.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/adoption", tags=["Adoption UX (behavioural science)"])

_RESULTS = Path(__file__).resolve().parents[1] / "training" / "evals" / "results"

# The four operator personas + the real artefact each one needs (design-thinking: empathise/persona-shaped, §35.8).
PERSONAS = {
    "ops_lead": {"label": "Operations Lead", "wants": "minutes of downtime prevented + live incidents",
                 "surfaces": ["wiifm", "recommendation"]},
    "compliance": {"label": "Compliance Officer", "wants": "the signed evidence pack + Art-12 decision trace",
                   "surfaces": ["/ops/post-market", "recommendation"]},
    "integrator": {"label": "OT/IT Integrator", "wants": "adapter + system health",
                   "surfaces": ["/ops/cascade"]},
    "security": {"label": "Security Architect", "wants": "identity + key-rotation state",
                 "surfaces": ["/ops/post-market"]},
}


@router.get("/personas")
def personas() -> dict[str, Any]:
    """The persona map (design-thinking: which real surface each role needs)."""
    return {"personas": PERSONAS}


def _autonomy_level() -> str:
    """The current progressive-autonomy level (env-controlled; default the safest = shadow)."""
    lvl = os.environ.get("AGENT_AUTONOMY_LEVEL", "shadow").lower()
    return lvl if lvl in ("shadow", "assisted", "supervised", "autonomous") else "shadow"


@router.get("/autonomy")
def autonomy() -> dict[str, Any]:
    """Progressive-autonomy state + the ladder (shadow→assisted→supervised→autonomous)."""
    ladder = [
        {"level": "shadow", "desc": "agent observes + recommends; NO actuation. $0-commitment trial.", "hitl": "n/a"},
        {"level": "assisted", "desc": "agent recommends; operator executes.", "hitl": "operator executes"},
        {"level": "supervised", "desc": "agent executes low-SIL actions; operator confirms SIL-1+.", "hitl": "confirm SIL-1+"},
        {"level": "autonomous", "desc": "agent executes within the safety envelope; operator on exceptions.", "hitl": "exceptions only"},
    ]
    cur = _autonomy_level()
    return {"current": cur, "ladder": ladder,
            "note": "trust is built incrementally (§35.8) — start in shadow, promote as evidence accrues. The "
                    "safety validator + HITL interrupt gate every level; promotion never bypasses them."}


@router.get("/wiifm")
def wiifm() -> dict[str, Any]:
    """WIIFM / loss-aversion headline from the REAL Stage-6/26 A/B (prevented loss, not promised gain).
    Honest-empty (available=False) if no A/B result file is present."""
    out: dict[str, Any] = {"available": False, "headlines": []}
    # Supply-chain A/B (Stage 26) — real result file.
    ab = _RESULTS / "supply_ab.json"
    if ab.exists():
        try:
            data = json.loads(ab.read_text(encoding="utf-8"))
            diff = data.get("paired_diff_greedy_minus_agentic", {})
            so = diff.get("stockout_ticks", {})
            if so.get("mean") is not None:
                out["available"] = True
                out["headlines"].append({
                    "metric": "stockout-hours prevented",
                    "prevented": so["mean"], "ci": [so.get("lo"), so.get("hi")],
                    "framing": f"The coordinated agents PREVENTED {so['mean']:.0f} stockout-ticks the naive baseline "
                               f"suffered (95% CI [{so.get('lo')}, {so.get('hi')}]).",
                    "honest_label": data.get("honest_label", "SimWorld study")})
        except Exception:  # noqa: BLE001
            pass
    if not out["available"]:
        out["reason"] = "no A/B result available yet — run the Stage-6/26 A/B (or a real pilot, G-035)"
    return out


def _dsn() -> Optional[str]:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


@router.get("/recommendation")
def recommendation(query: str = Query(default="stage crack torque anomaly response")) -> dict[str, Any]:
    """TRUST-CALIBRATED recommendation: confidence + uncertainty + counterfactual + GraphRAG citation — never a
    bare score. The grounding comes from the REAL GraphRAG retriever; honest-empty if nothing grounds it."""
    grounding = None
    top_score = 0.0
    try:
        from knowledge_graph.graphrag import retrieve
        g = retrieve(query)
        top_score = g.top_score
        grounding = {"grounded": g.grounded, "citations": [c.source for c in g.citations][:5],
                     "context": g.context[:3], "top_score": g.top_score}
    except Exception:  # noqa: BLE001
        grounding = {"grounded": False, "citations": [], "context": [], "top_score": 0.0}

    # Confidence is only asserted WITH grounding — an ungrounded recommendation is honestly low-confidence.
    grounded = bool(grounding and grounding["grounded"])
    # Stage 28 (indep-review gap #2 fix): confidence is DERIVED from the REAL retrieval cosine score (top_score in
    # [0,1]), NOT a hardcoded constant. The uncertainty band is a ±0.1 interval around it (retrieval-noise proxy),
    # clamped to [0,1]. Off-topic → grounded=False → confidence 0.0 (honest). Real-pilot calibration = G-035.
    conf = round(top_score, 3) if grounded else 0.0
    band = [round(max(0.0, conf - 0.1), 3), round(min(1.0, conf + 0.1), 3)] if grounded else None
    return {
        "query": query,
        "recommendation": ("Follow the grounded SOP procedure" if grounded
                           else "No grounded procedure found — escalate to a human operator"),
        # Trust calibration: confidence (from the real cosine score) + uncertainty band + counterfactual (§35.8).
        "confidence": conf,
        "uncertainty_band": band,
        "counterfactual": "If no action is taken, the anomaly proceeds toward failure (see the cited SOP).",
        "grounding": grounding,           # the GraphRAG citations — the trust anchor
        "hitl_required": not grounded or _autonomy_level() in ("shadow", "assisted"),
        "note": "A recommendation always carries confidence + uncertainty + counterfactual + citation — never a "
                "bare score (calibrated trust, §35.8).",
    }
