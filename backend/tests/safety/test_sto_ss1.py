"""Stage 17 — STO / SS1 safe-motion round-trip + signed audit_chain row (KB_17)."""
import os

import pytest

from safety import sto_ss1

_HAS_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"))


def test_trigger_sto_returns_triggered():
    res = sto_ss1.trigger_sto({"zone": "A", "robot": "AMR-1"}, reason="unit-test")
    assert res["function"] == "STO" and res["triggered"] is True
    assert res["reason"] == "unit-test" and "audit_recorded" in res


def test_trigger_ss1_decelerates_then_stos():
    res = sto_ss1.trigger_ss1({"decel_mps2": 2.0}, {"zone": "A"}, reason="unit-test")
    assert res["function"] == "SS1" and res["triggered"] is True
    assert res["terminal_sto"]["function"] == "STO" and res["terminal_sto"]["triggered"] is True


@pytest.mark.skipif(not _HAS_DB, reason="no DATABASE_URL — audit_chain DB write not exercisable (honest skip)")
def test_sto_writes_signed_audit_chain_row():
    """KB_17: every STO/SS1 trigger writes a signed audit_chain row. With a DB up, the row is actually persisted."""
    res = sto_ss1.trigger_sto({"zone": "B"}, reason="audit-test")
    assert res["audit_recorded"] is True and isinstance(res["audit_seq"], int)
    # the row is part of the hash chain (verify the chain up to + including the new row)
    from memory.audit_chain import verify_range
    report = verify_range(res["audit_seq"], res["audit_seq"])
    assert report.ok is True
