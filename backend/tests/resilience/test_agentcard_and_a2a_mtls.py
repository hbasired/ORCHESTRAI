"""Stage 27 — Kagenti/A2A-spec AgentCard export + A2A XFCC mTLS authentication (R4/G-4 closure at the endpoint)."""
from __future__ import annotations

import base64
import datetime

import pytest
from fastapi.testclient import TestClient

from a2a.agent_card import AgentCard
from a2a.agent_card_cnstyle import to_a2a_spec_card, to_kagenti_crd


def _card() -> AgentCard:
    return AgentCard(name="AI Embodied Agent", version="1.0.0", capabilities=["forecast_oee"],
                     endpoints={"a2a": "https://host/a2a/v1/rpc"},
                     public_key_b64="UEsxOTUy", signature_b64="c2lnMzMwOQ==")


# ---------------------------------------------------------------------------
# AgentCard export shapes (channel-fit)
# ---------------------------------------------------------------------------

def test_a2a_spec_card_carries_skills_mtls_scheme_and_ml_dsa_signature():
    out = to_a2a_spec_card(_card(), description="test")
    assert out["name"] == "AI Embodied Agent" and out["version"] == "1.0.0"
    assert {"spiffe-mtls"} <= set(out["securitySchemes"])
    assert out["securitySchemes"]["spiffe-mtls"]["type"] == "mutualTLS"
    assert any(s["id"] == "forecast_oee" for s in out["skills"])
    assert out["signatures"][0]["algorithm"] == "ML-DSA-65"
    assert out["signatures"][0]["publicKey"] == "UEsxOTUy"


def test_kagenti_crd_binds_dual_identity():
    crd = to_kagenti_crd(_card())
    assert crd["kind"] == "Agent" and crd["apiVersion"].startswith("kagenti")
    ident = crd["spec"]["identity"]
    assert ident["spiffeId"].startswith("spiffe://")          # transport identity
    assert ident["evidenceSignature"]["algorithm"] == "ML-DSA-65"  # evidence identity
    assert ident["evidenceSignature"]["publicKey"] == "UEsxOTUy"
    assert crd["spec"]["security"]["transport"] == "spiffe-mtls"


# ---------------------------------------------------------------------------
# A2A endpoint: XFCC mTLS authentication (R4/G-4 closure on the request path)
# ---------------------------------------------------------------------------

def _xfcc_der(spiffe_uri: str | None) -> str:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    key = ec.generate_private_key(ec.SECP256R1())
    n = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "peer")])
    b = (x509.CertificateBuilder().subject_name(n).issuer_name(n).public_key(key.public_key())
         .serial_number(x509.random_serial_number())
         .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
         .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)))
    if spiffe_uri:
        b = b.add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(spiffe_uri)]), critical=False)
    der = b.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.DER)
    return "Cert=\"" + base64.b64encode(der).decode() + "\""


@pytest.fixture()
def client():
    from a2a.server import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_foreign_trust_domain_peer_is_rejected(client):
    from security.spiffe_identity import TRUST_DOMAIN  # noqa: F401
    xfcc = _xfcc_der("spiffe://evil.example/attacker")
    r = client.post("/a2a/v1/rpc", headers={"X-Forwarded-Client-Cert": xfcc},
                    json={"jsonrpc": "2.0", "method": "forecast_oee", "params": {}, "id": 1})
    body = r.json()
    assert "error" in body and "authentication failed" in body["error"]["message"]


def test_authenticated_svid_peer_is_admitted_to_governance(client, monkeypatch):
    # A valid in-domain SVID authenticates; the request then proceeds into the governance layer (it may still be
    # governance-denied, but it is NOT rejected for identity — that is the R4/G-4 closure).
    from security.spiffe_identity import TRUST_DOMAIN
    xfcc = _xfcc_der(f"spiffe://{TRUST_DOMAIN}/a2a-client")
    r = client.post("/a2a/v1/rpc", headers={"X-Forwarded-Client-Cert": xfcc},
                    json={"jsonrpc": "2.0", "method": "forecast_oee", "params": {}, "id": 2})
    body = r.json()
    # Not an auth failure: either a real result or a governance/handler outcome — never "authentication failed".
    assert not ("error" in body and "authentication failed" in body.get("error", {}).get("message", ""))


def test_no_xfcc_falls_back_to_anonymous_confinement(client):
    # Without an mTLS-terminating front, the endpoint still serves under the Stage-24 confinement posture
    # (anonymous L0) — honestly weaker, not a crash.
    r = client.post("/a2a/v1/rpc",
                    json={"jsonrpc": "2.0", "method": "forecast_oee", "params": {}, "id": 3})
    assert r.status_code == 200  # served (governed), not an identity rejection
