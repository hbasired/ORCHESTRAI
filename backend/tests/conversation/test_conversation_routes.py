"""Stage 29 — conversation API route tests (TestClient). Honest degradation everywhere: ask honest-empty,
inject deterministic-or-abstain, diagnose honest-unavailable without a live sim."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.conversation_routes import router


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_ask_honest_empty(client):
    r = client.post("/factory/ask", json={"question": "what is the meaning of life", "use_llm": False}).json()
    assert r["grounded"] is False
    assert r["answer"] == "I have no evidence for that."


def test_inject_parses_deterministically(client):
    r = client.post("/factory/inject", json={"report": "robot 2 is down", "run_loop": False, "use_llm": False}).json()
    assert r["accepted"] is True
    assert r["incident"]["type"] == "robot_down"
    assert r["method"] == "deterministic"
    # Hard Rule 3: the response explicitly documents that the LLM did not actuate.
    assert "did NOT actuate" in r["note"]


def test_inject_abstains_on_unknown(client):
    r = client.post("/factory/inject", json={"report": "how are you today", "use_llm": False}).json()
    assert r["accepted"] is False
    assert r["method"] == "abstain"


def test_diagnose_honest_unavailable_without_world(client):
    # No sim bound in this minimal app -> honest-unavailable, not a fabricated diagnosis.
    r = client.post("/factory/diagnose", json={}).json()
    assert r["available"] is False
    assert "no live simulation" in r["reason"]


def test_diagnose_localizes_over_a_bound_sim(client, monkeypatch):
    # Bind a tiny fake world with one broken stage; the route must localize to it via real probes.
    class _Stage:
        def __init__(self, sid, status): self.sid, self.status = sid, status
        def snapshot(self):
            return {"stage_id": self.sid, "status": self.status,
                    "time_broken_seconds": 12.0 if self.status == "broken" else 0.0,
                    "defect_rate_effective": 0.01}

    class _World:
        def __init__(self):
            self.stages = {1: _Stage(1, "running"), 2: _Stage(2, "broken"), 3: _Stage(3, "running")}

    import api.conversation_routes as cr
    monkeypatch.setattr(cr, "_world", lambda: _World())
    r = client.post("/factory/diagnose", json={"commit_threshold": 0.85}).json()
    assert r["available"] is True
    assert r["committed"] is True
    assert r["hypothesis"] == "fault:stage-2"


# ---- G-024: bidirectional CDC db-edit route (Stage 37) --------------------------------------------------------

def test_db_edit_diagnoses_defect_surge(client):
    r = client.post("/factory/db-edit", json={"table": "stages", "column": "defect_rate",
                                              "old_value": 0.02, "new_value": 0.15, "target_id": 3}).json()
    assert r["diagnosed"] is True
    assert r["problem"]["type"] == "defect_surge" and r["problem"]["severity"] == "critical"
    # Hard Rule 3: the note affirms the reasoner proposes but never actuates.
    assert "never actuates" in r["note"]


def test_db_edit_benign_edit_is_honest(client):
    r = client.post("/factory/db-edit", json={"table": "stages", "column": "utilization",
                                              "old_value": 0.9, "new_value": 0.95, "target_id": 3}).json()
    assert r["diagnosed"] is False and "benign" in r["reason"].lower()


def test_db_edit_inventory_needs_reorder_context(client):
    # Without a reorder_point context we cannot honestly diagnose a stockout — no fabricated problem.
    r = client.post("/factory/db-edit", json={"table": "inventory", "column": "current_stock",
                                              "old_value": 800, "new_value": 100, "target_id": 7}).json()
    assert r["diagnosed"] is False
    r2 = client.post("/factory/db-edit", json={"table": "inventory", "column": "current_stock", "old_value": 800,
                                               "new_value": 100, "target_id": 7, "context": {"reorder_point": 600}}).json()
    assert r2["diagnosed"] is True and r2["problem"]["type"] == "late_delivery"
