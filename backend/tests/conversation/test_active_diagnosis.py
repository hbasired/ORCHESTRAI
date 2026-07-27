"""Stage 29 (G-026) — active-diagnosis tests: entropy/info-gain math, fault localization, abstention, timeout=fault.

Pure computation — no DB, no LLM, no network. The belief math is exact Bayes + Shannon entropy; the sensor model
is a documented noisy true-/false-positive probe model. Every property below is verified, none asserted."""
from __future__ import annotations

import math

from conversation.active_diagnosis import (
    DiagnosisModel, ProbeOutcome, entropy, make_probe_fn, run_active_diagnosis,
)


def _scripted_probe(true_fault: str):
    """A probe where only `true_fault` reads anomalous (noiseless) — the localization ground truth."""
    def probe(agent_id: str) -> ProbeOutcome:
        return ProbeOutcome(agent_id=agent_id, anomalous=(agent_id == true_fault),
                            report={"status": "broken" if agent_id == true_fault else "running"})
    return probe


def test_entropy_is_shannon():
    assert entropy({"a": 0.5, "b": 0.5}) == 1.0
    assert entropy({"a": 1.0, "b": 0.0}) == 0.0
    assert abs(entropy({"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}) - 2.0) < 1e-9


def test_uniform_initial_belief_and_hypothesis_space():
    m = DiagnosisModel(agent_ids=["s1", "s2", "s3"], include_no_fault=True)
    b = m.initial_belief()
    assert set(b) == {"fault:s1", "fault:s2", "fault:s3", "no_fault"}
    assert all(abs(p - 0.25) < 1e-9 for p in b.values())


def test_info_gain_positive_and_favours_uncertain_agents():
    m = DiagnosisModel(agent_ids=["s1", "s2", "s3"], tpr=0.9, fpr=0.1)
    b = m.initial_belief()
    # every probe has strictly positive expected information gain under a uniform prior.
    for a in m.agent_ids:
        assert m.expected_info_gain(b, a) > 0.0
    # after we become nearly certain it's s1, probing s1 gives ~no information.
    certain = {"fault:s1": 0.97, "fault:s2": 0.01, "fault:s3": 0.01, "no_fault": 0.01}
    assert m.expected_info_gain(certain, "s1") < m.expected_info_gain(b, "s1")


def test_bayes_update_shifts_toward_anomalous_agent():
    m = DiagnosisModel(agent_ids=["s1", "s2"], include_no_fault=False, tpr=0.9, fpr=0.1)
    b = m.initial_belief()
    b2 = m.update(b, "s1", anomalous=True)
    assert b2["fault:s1"] > b["fault:s1"]          # anomalous probe of s1 raises P(s1 faulty)
    assert abs(sum(b2.values()) - 1.0) < 1e-9      # still a distribution


def test_localizes_true_fault_and_commits():
    m = DiagnosisModel(agent_ids=["s1", "s2", "s3", "s4"], tpr=0.9, fpr=0.1)
    r = run_active_diagnosis(m, _scripted_probe("s3"), commit_threshold=0.85, max_probes=8)
    assert r.committed is True
    assert r.hypothesis == "fault:s3"
    assert r.confidence >= 0.85
    # entropy is monotonically consumed — the final step's entropy is below the first step's.
    assert r.steps[-1]["entropy_after_bits"] <= r.steps[0]["entropy_before_bits"]


def test_all_healthy_commits_to_no_fault():
    m = DiagnosisModel(agent_ids=["s1", "s2", "s3"], tpr=0.9, fpr=0.1)
    # no agent ever reads anomalous.
    r = run_active_diagnosis(m, lambda a: ProbeOutcome(a, anomalous=False, report={"status": "running"}),
                             commit_threshold=0.8, max_probes=10)
    assert r.hypothesis == "no_fault"
    assert r.committed is True


def test_abstains_when_evidence_is_ambiguous():
    # tpr≈fpr -> probes carry almost no information -> the loop cannot reach threshold -> honest abstention.
    m = DiagnosisModel(agent_ids=["s1", "s2", "s3", "s4"], tpr=0.55, fpr=0.45)
    r = run_active_diagnosis(m, _scripted_probe("s2"), commit_threshold=0.95, max_probes=6)
    assert r.committed is False
    assert r.abstained is True
    assert r.hypothesis is None


def test_timeout_is_treated_as_a_fault():
    class Dead:
        id = "s2"
        def self_check(self):
            raise TimeoutError("no response")

    class Alive:
        def __init__(self, i): self.id = i
        def self_check(self):
            return {"status": "running"}

    agents = {"s1": Alive("s1"), "s2": Dead(), "s3": Alive("s3")}
    probe = make_probe_fn(agents)
    out = probe("s2")
    assert out.timed_out is True and out.anomalous is True
    m = DiagnosisModel(agent_ids=["s1", "s2", "s3"], tpr=0.9, fpr=0.1)
    r = run_active_diagnosis(m, probe, commit_threshold=0.85, max_probes=8)
    assert r.hypothesis == "fault:s2"     # the non-responding agent is localized as the fault
