"""Stage 14 — A2A federation: two identities exchange + verify cards, invoke a capability, revoke (no infra).

The crypto layer is infra-free, so a genuine two-identity federation runs in-process: each "peer" signs its card
under its OWN keystore; verification is pure (against the card's embedded ML-DSA-65 public key). The Docker
two-instance path is provided but skipped (host Docker is down — G-069).
"""
import os
from datetime import datetime, timedelta, timezone

import pytest

from a2a.agent_card import AgentCard, sign_card, verify_card


def _sign_card_as(keystore_dir, name, monkeypatch) -> AgentCard:
    """Sign a card under a distinct keystore identity (its own ML-DSA-65 key)."""
    monkeypatch.setenv("KEY_STORE_DIR", str(keystore_dir))
    from crypto.key_provider import _reset_provider_for_tests
    _reset_provider_for_tests()
    card = AgentCard(name=name, version="1.0", capabilities=["forecast_oee"],
                     endpoints={"a2a": f"http://{name}:8000/a2a/v1/rpc"},
                     expiry=datetime.now(timezone.utc) + timedelta(days=30))
    return sign_card(card)


def test_two_identity_card_exchange_verify_and_revoke(tmp_path, monkeypatch):
    # Two peers, two separate identities/keystores.
    card_a = _sign_card_as(tmp_path / "ks_a", "agent-a", monkeypatch)
    card_b = _sign_card_as(tmp_path / "ks_b", "agent-b", monkeypatch)
    assert card_a.public_key_b64 != card_b.public_key_b64    # genuinely distinct identities

    # A verifies B's card (pure verify against B's embedded key) and pins it.
    assert verify_card(card_b, pinned_roots={card_b.public_key_b64}) is True
    # ... and B verifies A's.
    assert verify_card(card_a, pinned_roots={card_a.public_key_b64}) is True

    # A revokes B → A refuses B's card.
    from a2a.revocation import RevocationList
    rev = RevocationList()
    rev.revoke(card_b.public_key_b64)
    assert verify_card(card_b, is_revoked=rev.is_revoked) is False
    assert verify_card(card_a, is_revoked=rev.is_revoked) is True   # A still trusted


def _client():
    """A minimal FastAPI app with ONLY the A2A router (avoids the full app lifespan)."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from a2a.server import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_agent_card_endpoint_serves_a_verifiable_card():
    resp = _client().get("/.well-known/agent.json")
    assert resp.status_code == 200
    card = AgentCard(**resp.json())
    assert "forecast_oee" in card.capabilities
    assert verify_card(card) is True       # the served card is genuinely ML-DSA-65 signed


def test_jsonrpc_exposes_capability_but_not_mcp_tools():
    client = _client()
    # an exposed capability works (forecast_oee with a supplied snapshot → real OEE)
    snap = {"sim_time_seconds": 3600.0,
            "stages": [{"stage_id": 0, "name": "intake", "units_produced": 40, "units_defective": 1,
                        "time_broken_seconds": 0.0, "time_maintenance_seconds": 0.0}]}
    ok = client.post("/a2a/v1/rpc", json={"jsonrpc": "2.0", "method": "forecast_oee",
                                          "params": {"state": snap}, "id": 1}).json()
    assert ok["id"] == 1 and ok["result"]["available"] is True and 0.0 <= ok["result"]["plant_oee"] <= 1.0
    # an MCP tool is NOT reachable via A2A (trust boundary) → JSON-RPC method-not-found
    deny = client.post("/a2a/v1/rpc", json={"jsonrpc": "2.0", "method": "predict_failure",
                                            "params": {}, "id": 2}).json()
    assert deny["error"]["code"] == -32601


def test_jsonrpc_rejects_malformed_request():
    bad = _client().post("/a2a/v1/rpc", json={"method": "forecast_oee"}).json()  # missing jsonrpc:2.0
    assert bad["error"]["code"] == -32600


@pytest.mark.skipif(not os.environ.get("A2A_DOCKER_FEDERATION"),
                    reason="two-instance federation: set A2A_DOCKER_FEDERATION=1 with two live peers on :8000/:8100 (G-071)")
def test_two_instance_federation_over_http():
    """Real two-instance federation over the WIRE (two independent agent identities on :8000 + :8100): card
    exchange + verify + a capability call + the trust boundary — all over real HTTP (G-071)."""
    import httpx
    a = AgentCard(**httpx.get("http://127.0.0.1:8000/.well-known/agent.json", timeout=5).json())
    b = AgentCard(**httpx.get("http://127.0.0.1:8100/.well-known/agent.json", timeout=5).json())
    assert a.public_key_b64 and b.public_key_b64 and a.public_key_b64 != b.public_key_b64  # distinct identities
    assert verify_card(a) and verify_card(b)                                                # both verify over the wire
    # peer A invokes peer B's capability over HTTP → real OEE
    snap = {"sim_time_seconds": 3600.0,
            "stages": [{"stage_id": 0, "name": "intake", "units_produced": 40, "units_defective": 1,
                        "time_broken_seconds": 0.0, "time_maintenance_seconds": 0.0}]}
    r = httpx.post("http://127.0.0.1:8100/a2a/v1/rpc",
                   json={"jsonrpc": "2.0", "method": "forecast_oee", "params": {"state": snap}, "id": 1},
                   timeout=5).json()
    assert r["result"]["available"] is True
    # the trust boundary holds over the wire: an MCP tool is refused
    d = httpx.post("http://127.0.0.1:8100/a2a/v1/rpc",
                   json={"jsonrpc": "2.0", "method": "predict_failure", "params": {}, "id": 2}, timeout=5).json()
    assert d["error"]["code"] == -32601
