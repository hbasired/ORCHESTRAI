"""Stage 23 — governance MAC/RBAC/traceability tests (pure logic; DB-free → audited=False is the honest path here)."""
from __future__ import annotations

import pytest

from governance.mac import (SecurityLabel, can_read, can_write, dominates, require_read, require_write, MacViolation)
from governance.rbac import (AgentTier, check_function_access, require_function, RbacViolation)
from governance import traceability


# --- Bell-LaPadula MAC (G-030) -----------------------------------------------

def test_dominance_level_and_categories():
    hi = SecurityLabel.of("restricted", {"ot", "safety"})
    lo = SecurityLabel.of("internal", {"ot"})
    assert dominates(hi, lo) is True              # higher level + superset categories
    assert dominates(lo, hi) is False
    # incomparable: higher level but missing a category
    side = SecurityLabel.of("restricted", {"finance"})
    assert dominates(side, lo) is False           # lacks 'ot'


def test_no_read_up():
    subj = SecurityLabel.of("confidential", {"ot"})
    high = SecurityLabel.of("restricted", {"ot"})
    low = SecurityLabel.of("internal", {"ot"})
    assert can_read(subj, low, audit=False).allow is True          # read down OK
    assert can_read(subj, high, audit=False).allow is False        # READ-UP blocked
    assert can_read(subj, subj, audit=False).allow is True         # read equal OK


def test_no_write_down():
    subj = SecurityLabel.of("confidential", {"ot"})
    high = SecurityLabel.of("restricted", {"ot"})
    low = SecurityLabel.of("internal", {"ot"})
    assert can_write(subj, high, audit=False).allow is True        # write up OK (object dominates subject)
    assert can_write(subj, low, audit=False).allow is False        # WRITE-DOWN blocked (⋆-property)


def test_require_raises_on_violation():
    subj = SecurityLabel.of("internal", set())
    secret = SecurityLabel.of("safety_critical", {"safety"})
    with pytest.raises(MacViolation):
        require_read(subj, secret)
    with pytest.raises(MacViolation):
        require_write(SecurityLabel.of("safety_critical", {"safety"}), SecurityLabel.of("public", set()))


# --- agent-hierarchy RBAC (G-029) --------------------------------------------

def test_tier_minimum_enforced():
    # a worker cannot actuate (needs L3)
    d = check_function_access("w1", AgentTier.L1_WORKER, {"actuate"}, "actuate", audit=False)
    assert d.allow is False and "minimum" in d.reason
    # the embodied agent can, when granted
    d2 = check_function_access("e1", AgentTier.L3_EMBODIED, {"actuate"}, "actuate", audit=False)
    assert d2.allow is True


def test_least_privilege_grant_required():
    # right tier but not granted the function
    d = check_function_access("h1", AgentTier.L2_HEAD, {"observe"}, "recommend", audit=False)
    assert d.allow is False and "grant set" in d.reason


def test_l0_peer_confined_to_a2a_capability():
    d = check_function_access("peer", AgentTier.L0_PEER, {"observe", "diagnose"}, "diagnose", audit=False)
    assert d.allow is False and "L0" in d.reason          # assume-breach: peer can't reach internal functions
    d2 = check_function_access("peer", AgentTier.L0_PEER, {"a2a_capability"}, "a2a_capability", audit=False)
    assert d2.allow is True


def test_unknown_function_denied():
    assert check_function_access("x", AgentTier.L3_EMBODIED, {"actuate"}, "rm_rf", audit=False).allow is False
    with pytest.raises(RbacViolation):
        require_function("x", AgentTier.L1_WORKER, set(), "nope")


# --- total traceability (G-028) ----------------------------------------------

def test_trace_record_snapshots_and_degrades_honestly(monkeypatch):
    # force the audit append to be unavailable -> honest: seq None, audited False, but the snapshot is still produced
    import memory.audit_chain as ac
    def _boom(*a, **k):
        raise RuntimeError("no DB")
    monkeypatch.setattr(ac, "append", _boom)
    rec = traceability.record_decision_trace(
        "INC-1",
        {"prediction": {"p_fail": 0.8}, "sil_level": 1, "secret_obj": object()},
        {"verification": {"approved": True}, "hitl_required": False},
        {"kind": "preventive_maintenance", "approved": True, "rationale": "p_fail high"},
    )
    assert rec.audited is False and rec.seq is None
    assert rec.decision["kind"] == "preventive_maintenance"
    assert rec.state_pre["sil_level"] == 1
    assert "prediction" in rec.state_pre and "verification" in rec.state_post  # pre/post snapshots captured
