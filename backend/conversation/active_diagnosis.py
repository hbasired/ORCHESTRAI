"""Stage 29 (G-026) — active diagnosis: probe -> reason -> commit/abstain (KB_25 §1b).

Prediction can be wrong or uncertain, so before committing to an intervention the coordinator ACTIVELY interrogates
suspect agents. This implements the SOTA active-diagnosis formulation (research §40.3): select the next
`diagnose.request` that MAXIMISES expected information gain (mutual information between the probe outcome and the
fault hypothesis == entropy reduction), read the `diagnose.report`, Bayes-update the belief, and only COMMIT to a
cause when the posterior clears a confidence threshold — otherwise ABSTAIN/escalate. A wrong prediction is caught by
the diagnostic round-trip instead of triggering an unnecessary intervention; misdiagnosis is a *recorded* outcome.

This is pure computation over the existing agent-message bus (KB_06 `diagnose.request`/`diagnose.report`) — free,
local, deterministic, and fully testable. The noisy sensor model (true-/false-positive probe rates) is the honest
diagnostic knowledge; the belief math is exact Bayes + Shannon entropy, no fabrication.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol


# ---- the agent-probe interface (KB_06 diagnose.request/report) --------------------------------------------------

class Probeable(Protocol):
    """An agent that can run a named self-check and report. Timeout/exception -> treated as anomalous (a fault)."""
    id: str
    def self_check(self) -> dict[str, Any]: ...   # returns a health vector; may raise/timeout


@dataclass
class ProbeOutcome:
    agent_id: str
    anomalous: bool
    report: dict[str, Any]
    timed_out: bool = False


# ---- the belief + information-gain machinery --------------------------------------------------------------------

def entropy(dist: dict[str, float]) -> float:
    """Shannon entropy (bits) of a discrete distribution."""
    h = 0.0
    for p in dist.values():
        if p > 0.0:
            h -= p * math.log2(p)
    return h


def _normalize(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values())
    if s <= 0:
        n = len(d)
        return {k: 1.0 / n for k in d}
    return {k: v / s for k, v in d.items()}


@dataclass
class DiagnosisModel:
    """Fault-localization hypothesis space + a noisy probe sensor model.

    Hypotheses: one per candidate faulty agent id, plus optional "no_fault". Probe outcome is binary
    (anomalous / normal). Sensor model: probing the truly-faulty agent reads anomalous w.p. `tpr` (true-positive);
    probing a healthy agent reads anomalous w.p. `fpr` (false-positive). These rates encode real probe reliability.
    """
    agent_ids: list[str]
    include_no_fault: bool = True
    tpr: float = 0.9         # P(anomalous report | this agent is the fault, probing it)
    fpr: float = 0.1         # P(anomalous report | this agent is healthy, probing it)
    prior: dict[str, float] = field(default_factory=dict)

    def hypotheses(self) -> list[str]:
        hs = [f"fault:{a}" for a in self.agent_ids]
        if self.include_no_fault:
            hs.append("no_fault")
        return hs

    def initial_belief(self) -> dict[str, float]:
        hs = self.hypotheses()
        if self.prior:
            return _normalize({h: float(self.prior.get(h, 1e-6)) for h in hs})
        return {h: 1.0 / len(hs) for h in hs}

    def p_anomalous(self, hypothesis: str, probe_agent: str) -> float:
        """P(probe of `probe_agent` reads anomalous | `hypothesis` is true)."""
        if hypothesis == "no_fault":
            return self.fpr
        faulty = hypothesis.split("fault:", 1)[1]
        return self.tpr if faulty == probe_agent else self.fpr

    def expected_info_gain(self, belief: dict[str, float], probe_agent: str) -> float:
        """Mutual information I(hypothesis; outcome) for probing `probe_agent` under `belief` (bits, >= 0)."""
        h_before = entropy(belief)
        # marginal P(anomalous) and the two posteriors.
        p_anom = sum(belief[h] * self.p_anomalous(h, probe_agent) for h in belief)
        p_norm = 1.0 - p_anom
        h_after = 0.0
        for outcome_p, anom in ((p_anom, True), (p_norm, False)):
            if outcome_p <= 0.0:
                continue
            post = {}
            for h in belief:
                like = self.p_anomalous(h, probe_agent) if anom else (1.0 - self.p_anomalous(h, probe_agent))
                post[h] = belief[h] * like
            post = _normalize(post)
            h_after += outcome_p * entropy(post)
        return max(0.0, h_before - h_after)

    def update(self, belief: dict[str, float], probe_agent: str, anomalous: bool) -> dict[str, float]:
        """Exact Bayes update of `belief` given a probe of `probe_agent` with the observed outcome."""
        post = {}
        for h in belief:
            like = self.p_anomalous(h, probe_agent) if anomalous else (1.0 - self.p_anomalous(h, probe_agent))
            post[h] = belief[h] * like
        return _normalize(post)


@dataclass
class DiagnosisResult:
    committed: bool
    hypothesis: Optional[str]         # e.g. "fault:stage-3" or "no_fault" or None (abstained)
    confidence: float
    steps: list[dict[str, Any]] = field(default_factory=list)   # the probe transcript (observable/ledgerable)
    abstained: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"committed": self.committed, "hypothesis": self.hypothesis, "confidence": round(self.confidence, 4),
                "abstained": self.abstained, "reason": self.reason, "steps": self.steps}


def _default_anomaly_classifier(report: dict[str, Any]) -> bool:
    """Map a health vector to anomalous/normal (real signal thresholds). Missing report -> anomalous (timeout=fault)."""
    if not report:
        return True
    status = str(report.get("status", "")).lower()
    if status and status not in ("running", "idle", "ok", "operational", "healthy"):
        return True
    if bool(report.get("blocked")):
        return True
    for key, thr in (("torque_z", 3.0), ("error_rate", 0.2), ("vibration_z", 3.0), ("temp_c", 85.0)):
        v = report.get(key)
        if isinstance(v, (int, float)) and v >= thr:
            return True
    return False


def run_active_diagnosis(
    model: DiagnosisModel,
    probe_fn: Callable[[str], ProbeOutcome],
    *,
    commit_threshold: float = 0.85,
    max_probes: int = 8,
    min_info_gain: float = 1e-3,
    audit: bool = False,
) -> DiagnosisResult:
    """Run the entropy-driven probe loop. `probe_fn(agent_id)` issues a diagnose.request and returns a ProbeOutcome.

    Terminates when a hypothesis posterior >= `commit_threshold` (COMMIT), or no probe yields useful information, or
    the probe budget is exhausted (ABSTAIN). Every step is recorded (probe chosen, info gain, outcome, posterior).
    """
    belief = model.initial_belief()
    steps: list[dict[str, Any]] = []
    probed: list[str] = []

    for _ in range(max_probes):
        # already confident? commit.
        top_h = max(belief, key=belief.get)
        if belief[top_h] >= commit_threshold:
            break

        # choose the probe with maximum expected information gain (skip already-probed agents once informative gain is gone).
        candidates = model.agent_ids
        gains = {a: model.expected_info_gain(belief, a) for a in candidates}
        # prefer un-probed agents on ties to gather breadth.
        best_agent = max(candidates, key=lambda a: (gains[a], a not in probed))
        best_gain = gains[best_agent]
        if best_gain < min_info_gain:
            break  # no probe can disambiguate further -> stop (will abstain unless already over threshold)

        outcome = probe_fn(best_agent)
        probed.append(best_agent)
        h_before = entropy(belief)
        belief = model.update(belief, best_agent, outcome.anomalous)
        top_h = max(belief, key=belief.get)
        steps.append({
            "probe": best_agent, "expected_info_gain_bits": round(best_gain, 4),
            "outcome": "anomalous" if outcome.anomalous else "normal", "timed_out": outcome.timed_out,
            "entropy_before_bits": round(h_before, 4), "entropy_after_bits": round(entropy(belief), 4),
            "top_hypothesis": top_h, "top_confidence": round(belief[top_h], 4),
            "report": outcome.report,
        })
        if audit:
            _audit_probe(best_agent, outcome, belief[top_h])

    top_h = max(belief, key=belief.get)
    conf = belief[top_h]
    if conf >= commit_threshold:
        return DiagnosisResult(committed=True, hypothesis=top_h, confidence=conf, steps=steps,
                               reason=f"posterior {conf:.3f} >= {commit_threshold} after {len(steps)} probe(s)")
    return DiagnosisResult(committed=False, hypothesis=None, confidence=conf, steps=steps, abstained=True,
                           reason=f"no hypothesis reached {commit_threshold} (best {top_h} at {conf:.3f}) — abstaining/escalating")


def _audit_probe(agent_id: str, outcome: ProbeOutcome, confidence: float) -> None:
    """Best-effort ledger of a diagnose round-trip (observable, KB_25). Honest no-op if the store is down."""
    try:
        from memory.audit_chain import append
        append("active_diagnosis", "diagnose.report",
               {"agent_id": agent_id, "anomalous": outcome.anomalous, "timed_out": outcome.timed_out,
                "confidence": round(confidence, 4)})
    except Exception:  # noqa: BLE001
        pass


# ---- probe adapters --------------------------------------------------------------------------------------------

def make_probe_fn(agents: dict[str, Any], *,
                  anomaly_classifier: Callable[[dict[str, Any]], bool] = _default_anomaly_classifier,
                  timeout_as_fault: bool = True) -> Callable[[str], ProbeOutcome]:
    """Build a probe_fn over a dict of {agent_id: Probeable}. `self_check()` raising/timing out -> anomalous (fault)."""
    def probe(agent_id: str) -> ProbeOutcome:
        agent = agents.get(agent_id)
        if agent is None:
            return ProbeOutcome(agent_id=agent_id, anomalous=timeout_as_fault, report={}, timed_out=True)
        try:
            report = agent.self_check()
        except Exception:  # noqa: BLE001 - a non-responding agent is itself the fault
            return ProbeOutcome(agent_id=agent_id, anomalous=timeout_as_fault, report={}, timed_out=True)
        return ProbeOutcome(agent_id=agent_id, anomalous=anomaly_classifier(report), report=report)
    return probe


__all__ = ["Probeable", "ProbeOutcome", "DiagnosisModel", "DiagnosisResult",
           "entropy", "run_active_diagnosis", "make_probe_fn"]
