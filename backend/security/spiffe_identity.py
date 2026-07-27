"""Stage 27 — SPIFFE workload identity + SVID-mTLS for the A2A boundary (research §38.1/§38.2).

DUAL-IDENTITY MODEL (the Kagenti pattern adapted to our spine):
  * SPIFFE X509-SVID  = TRANSPORT authentication — short-lived, auto-rotated by SPIRE; proves *who is calling*
    on the wire (mutual TLS; closes R4/G-4: the A2A endpoint becomes AUTHENTICATED, not merely RBAC-confined).
  * ML-DSA-65         = EVIDENCE signing — audit rows, agent cards, ADRs (post-quantum, Stage 13.5+).
  The AgentCard binds both (the SVID's SPIFFE ID + the ML-DSA public key), so a peer can verify transport
  identity AND evidence signatures belong to the same agent.

DEPLOYMENT PATHS (honest scope):
  * Containerised (the load-bearing production shape): py-spiffe `X509Source` against the SPIRE Workload API
    unix socket — continuous SVID rotation, no restarts (`workload_x509_source()`).
  * Dev-host (Windows — unix sockets unavailable to the host): real SVIDs are FETCHED from the running SPIRE
    agent (`fetch_svid_via_docker`) and used as PEM files. Same certificates, same CA bundle, same verification
    logic; only the delivery differs. Labelled wherever used.

No fabrication: every function raises `SpiffeUnavailable` when SPIRE isn't reachable — never a fake identity.
"""
from __future__ import annotations

import os
import ssl
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

TRUST_DOMAIN = os.environ.get("SPIFFE_TRUST_DOMAIN", "ai-agent.local")


class SpiffeUnavailable(RuntimeError):
    """SPIRE / the Workload API is not reachable — identity is honestly unavailable (never faked)."""


# ---------------------------------------------------------------------------
# SVID acquisition
# ---------------------------------------------------------------------------

def workload_x509_source():
    """Containerised path: a py-spiffe X509Source bound to the Workload API socket (auto-rotating SVIDs).
    Raises SpiffeUnavailable when the socket is absent (e.g., on the dev host)."""
    socket_path = os.environ.get("SPIFFE_ENDPOINT_SOCKET", "unix:///tmp/spire/agent/public/api.sock")
    try:
        from spiffe import X509Source
        return X509Source(socket_path=socket_path)
    except Exception as e:  # noqa: BLE001
        raise SpiffeUnavailable(f"Workload API not reachable at {socket_path}: {e}") from e


@dataclass
class SvidFiles:
    """PEM-file form of an SVID (cert chain, private key, trust bundle) + its SPIFFE ID."""
    spiffe_id: str
    cert_path: Path
    key_path: Path
    bundle_path: Path


def fetch_svid_via_docker(out_dir: Optional[Path] = None, agent_container: str = "spire-agent") -> SvidFiles:
    """Dev-host path: fetch REAL SVID PEMs from the running SPIRE agent container.

    Runs `spire-agent api fetch x509 -write` inside the container and copies the PEMs out. The certificates are
    genuine SPIRE-issued SVIDs (short TTL, rotated on re-fetch); only the transport to the host differs from the
    containerised X509Source path. Raises SpiffeUnavailable if the agent isn't up or no entry matches."""
    out_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="svid-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        # The SPIRE agent image is distroless (no shell): call the binary directly and -write into the agent's
        # data_dir, a guaranteed-existing mounted path. Emits svid.0.pem / svid.0.key / bundle.0.pem there.
        fetch = subprocess.run(
            ["docker", "exec", agent_container, "/opt/spire/bin/spire-agent", "api", "fetch", "x509",
             "-socketPath", "/tmp/spire/agent/public/api.sock", "-write", "/opt/spire/data"],
            capture_output=True, text=True, timeout=30)
        if fetch.returncode != 0 or "Received" not in fetch.stdout:
            raise SpiffeUnavailable(f"SVID fetch failed: {fetch.stdout} {fetch.stderr}")
        spiffe_id = next((ln.split('"')[1] for ln in fetch.stdout.splitlines() if 'SPIFFE ID:' in ln and '"' in ln),
                         None)
        if spiffe_id is None:  # fetch output format: 'SPIFFE ID:\t\t spiffe://...'
            spiffe_id = next((ln.split()[-1] for ln in fetch.stdout.splitlines() if "SPIFFE ID" in ln), "")
        for name in ("svid.0.pem", "svid.0.key", "bundle.0.pem"):
            cp = subprocess.run(["docker", "cp", f"{agent_container}:/opt/spire/data/{name}", str(out_dir / name)],
                                capture_output=True, text=True, timeout=30)
            if cp.returncode != 0:
                raise SpiffeUnavailable(f"docker cp {name} failed: {cp.stderr}")
        return SvidFiles(spiffe_id=spiffe_id, cert_path=out_dir / "svid.0.pem",
                         key_path=out_dir / "svid.0.key", bundle_path=out_dir / "bundle.0.pem")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise SpiffeUnavailable(f"SPIRE agent container not reachable: {e}") from e


# ---------------------------------------------------------------------------
# SVID-mTLS contexts + peer authentication (the R4/G-4 closure)
# ---------------------------------------------------------------------------

def server_mtls_context(svid: SvidFiles) -> ssl.SSLContext:
    """TLS server context that REQUIRES a client certificate signed by the SPIRE trust bundle."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=str(svid.cert_path), keyfile=str(svid.key_path))
    ctx.load_verify_locations(cafile=str(svid.bundle_path))
    ctx.verify_mode = ssl.CERT_REQUIRED     # no client SVID -> handshake FAILS (authenticated, not just confined)
    return ctx


def client_mtls_context(svid: SvidFiles) -> ssl.SSLContext:
    """TLS client context presenting the workload's SVID and verifying the server against the SPIRE bundle."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_cert_chain(certfile=str(svid.cert_path), keyfile=str(svid.key_path))
    ctx.load_verify_locations(cafile=str(svid.bundle_path))
    ctx.check_hostname = False              # SPIFFE verifies the URI SAN (SPIFFE ID), not DNS hostnames
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def spiffe_id_from_der(der_cert: bytes) -> Optional[str]:
    """Extract the SPIFFE ID (URI SAN) from a peer certificate."""
    from cryptography import x509
    from cryptography.x509.oid import ExtensionOID
    cert = x509.load_der_x509_certificate(der_cert)
    try:
        san = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
        uris = san.get_values_for_type(x509.UniformResourceIdentifier)
        return next((u for u in uris if u.startswith("spiffe://")), None)
    except x509.ExtensionNotFound:
        return None


def authenticate_peer(der_cert: bytes, *, allowed_peers: Optional[set[str]] = None) -> str:
    """The A2A peer-authentication gate: peer certificate -> SPIFFE ID -> trust-domain + allowlist check.

    Returns the authenticated SPIFFE ID or raises PermissionError (named refusal — the caller maps it to the
    JSON-RPC auth error). This is what makes the A2A boundary AUTHENTICATED (R4/G-4): the TLS layer already proved
    key possession + SPIRE-CA signature; this binds the identity to peer_state semantics."""
    sid = spiffe_id_from_der(der_cert)
    if not sid:
        raise PermissionError("peer certificate carries no SPIFFE ID (not a workload SVID)")
    if not sid.startswith(f"spiffe://{TRUST_DOMAIN}/"):
        raise PermissionError(f"peer {sid!r} is outside trust domain {TRUST_DOMAIN!r}")
    if allowed_peers is not None and sid not in allowed_peers:
        raise PermissionError(f"peer {sid!r} not in the allowed peer set")
    return sid


__all__ = ["SpiffeUnavailable", "SvidFiles", "workload_x509_source", "fetch_svid_via_docker",
           "server_mtls_context", "client_mtls_context", "spiffe_id_from_der", "authenticate_peer",
           "TRUST_DOMAIN"]
