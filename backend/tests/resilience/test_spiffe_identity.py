"""Stage 27 — SPIFFE identity + SVID-mTLS tests (research §38.1/§38.2).

Infra-free legs test the peer-authentication gate (the R4/G-4 logic) with synthetic SPIFFE certs. The SPIRE-gated
leg fetches REAL SVIDs from the running agent and drives a genuine mutual-TLS handshake: a valid client SVID is
authenticated, an unidentified client is REFUSED at the handshake — proving the A2A boundary is AUTHENTICATED, not
merely RBAC-confined."""
from __future__ import annotations

import datetime
import shutil
import socket
import ssl
import subprocess
import threading

import pytest

from security.spiffe_identity import (
    SpiffeUnavailable, TRUST_DOMAIN, authenticate_peer, fetch_svid_via_docker,
    server_mtls_context, client_mtls_context, spiffe_id_from_der,
)


# ---------------------------------------------------------------------------
# Peer-authentication gate (synthetic certs — the R4/G-4 decision logic)
# ---------------------------------------------------------------------------

def _mk_cert(spiffe_uri: str | None) -> bytes:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    builder = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
               .public_key(key.public_key()).serial_number(x509.random_serial_number())
               .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
               .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)))
    if spiffe_uri:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(spiffe_uri)]), critical=False)
    cert = builder.sign(key, hashes.SHA256())
    return cert.public_bytes(__import__("cryptography").x509.Encoding.DER if False else
                             __import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.DER)


def test_extracts_spiffe_id_from_uri_san():
    der = _mk_cert(f"spiffe://{TRUST_DOMAIN}/a2a-client")
    assert spiffe_id_from_der(der) == f"spiffe://{TRUST_DOMAIN}/a2a-client"


def test_authenticate_accepts_in_domain_peer():
    der = _mk_cert(f"spiffe://{TRUST_DOMAIN}/a2a-client")
    assert authenticate_peer(der) == f"spiffe://{TRUST_DOMAIN}/a2a-client"


def test_authenticate_rejects_no_spiffe_id():
    der = _mk_cert(None)   # a plain cert with no SPIFFE SAN
    with pytest.raises(PermissionError, match="no SPIFFE ID"):
        authenticate_peer(der)


def test_authenticate_rejects_foreign_trust_domain():
    der = _mk_cert("spiffe://evil.example/a2a-client")
    with pytest.raises(PermissionError, match="outside trust domain"):
        authenticate_peer(der)


def test_authenticate_enforces_allowlist():
    der = _mk_cert(f"spiffe://{TRUST_DOMAIN}/stranger")
    with pytest.raises(PermissionError, match="not in the allowed peer set"):
        authenticate_peer(der, allowed_peers={f"spiffe://{TRUST_DOMAIN}/a2a-client"})


# ---------------------------------------------------------------------------
# SPIRE-gated: REAL SVID mutual-TLS handshake (the R4/G-4 closure, end-to-end)
# ---------------------------------------------------------------------------

def _spire_up() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=10)
        return "spire-agent" in r.stdout
    except Exception:  # noqa: BLE001
        return False


requires_spire = pytest.mark.skipif(not _spire_up(), reason="SPIRE agent not running (bootstrap-spire.sh)")


@requires_spire
def test_real_svid_mtls_authenticates_a_valid_client_and_refuses_an_anonymous_one():
    try:
        svid = fetch_svid_via_docker()
    except SpiffeUnavailable as e:
        pytest.skip(f"SVID fetch unavailable: {e}")

    server_ctx = server_mtls_context(svid)   # REQUIRES a client cert from the SPIRE bundle
    client_ctx = client_mtls_context(svid)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(2)
    port = srv.getsockname()[1]
    peer_ids: list = []
    errors: list = []

    def serve(expect_client_cert: bool):
        try:
            raw, _ = srv.accept()
            with server_ctx.wrap_socket(raw, server_side=True) as tls:
                der = tls.getpeercert(binary_form=True)
                peer_ids.append(authenticate_peer(der))
                tls.sendall(b"ok")
        except (ssl.SSLError, OSError) as e:
            errors.append(type(e).__name__)

    # 1) authenticated client presenting a real SVID -> handshake succeeds, peer is identified
    t = threading.Thread(target=serve, args=(True,)); t.start()
    with socket.create_connection(("127.0.0.1", port), timeout=10) as c:
        with client_ctx.wrap_socket(c, server_hostname="a2a-server") as tc:
            der = tc.getpeercert(binary_form=True)
            assert spiffe_id_from_der(der).startswith(f"spiffe://{TRUST_DOMAIN}/")
            assert tc.recv(8) == b"ok"
    t.join(timeout=10)
    assert peer_ids and peer_ids[0].startswith(f"spiffe://{TRUST_DOMAIN}/")

    # 2) anonymous client (NO SVID) -> the mTLS handshake FAILS. The AUTHORITATIVE proof is server-side: the
    # server REQUIRES a client cert, so it aborts the handshake and identifies no peer. (The client may or may not
    # observe the abort before its own send, depending on TLS-record timing — so we assert on the server.)
    peer_ids.clear(); errors.clear()
    t2 = threading.Thread(target=serve, args=(False,)); t2.start()
    anon = ssl.create_default_context()
    anon.check_hostname = False
    anon.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=10) as c:
            tc = anon.wrap_socket(c, server_hostname="a2a-server")
            try:
                tc.recv(8)   # force I/O so the server's rejection propagates
            except (ssl.SSLError, OSError):
                pass
    except (ssl.SSLError, OSError):
        pass
    t2.join(timeout=10)
    srv.close()
    assert errors, "server must REJECT an anonymous client (client-cert required = authenticated boundary)"
    assert not peer_ids, "no peer identity may be established without a client SVID"
