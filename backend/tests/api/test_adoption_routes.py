"""Stage 28 — adoption-UX API tests: trust calibration (real citations, honest low-confidence),
progressive autonomy, WIIFM from the real A/B. No fabrication anywhere."""
from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.adoption_routes import router


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


requires_embedder = pytest.mark.skipif(
    os.environ.get("MEM0_EMBED_MODEL") is None,
    reason="grounding needs the bge-small embedder (MEM0_EMBED_MODEL)")


def test_personas_are_role_shaped(client):
    p = client.get("/adoption/personas").json()["personas"]
    assert set(p) == {"ops_lead", "compliance", "integrator", "security"}
    assert all("wants" in v and "surfaces" in v for v in p.values())


def test_autonomy_ladder_starts_safest_and_gates_every_level(client):
    a = client.get("/adoption/autonomy").json()
    assert a["current"] == "shadow"                    # safest default
    assert [l["level"] for l in a["ladder"]] == ["shadow", "assisted", "supervised", "autonomous"]
    assert a["ladder"][0]["desc"].startswith("agent observes")  # shadow = no actuation


@requires_embedder
def test_recommendation_is_trust_calibrated_not_a_bare_score(client):
    r = client.get("/adoption/recommendation", params={"query": "stage crack torque anomaly response"}).json()
    # A recommendation MUST carry confidence + uncertainty + counterfactual + citation — never a bare score.
    assert r["grounding"]["grounded"] is True
    assert r["confidence"] > 0 and r["uncertainty_band"] is not None
    assert r["counterfactual"] and r["grounding"]["citations"]


@requires_embedder
def test_ungrounded_recommendation_is_honest_low_confidence_and_hitl(client):
    r = client.get("/adoption/recommendation", params={"query": "best pizza recipe"}).json()
    assert r["grounding"]["grounded"] is False
    assert r["confidence"] == 0.0                       # honest: no grounding → no confidence
    assert r["hitl_required"] is True                  # escalate to a human
    assert "escalate to a human" in r["recommendation"]


def test_wiifm_is_loss_framed_from_real_ab_or_honest_empty(client):
    w = client.get("/adoption/wiifm").json()
    if w["available"]:
        # loss-aversion framing: "prevented" language, tied to a real A/B result with a CI + honest label
        h = w["headlines"][0]
        assert "prevent" in h["framing"].lower()
        assert h["ci"] and h["honest_label"]
    else:
        assert "reason" in w                            # honest-empty names why (no A/B yet)
