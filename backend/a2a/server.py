"""Stage 14 — A2A FastAPI surface: signed agent card + JSON-RPC 2.0 dispatch (KB_16).

- `GET /.well-known/agent.json` → our ML-DSA-65-signed `AgentCard` (discovery).
- `POST /a2a/v1/rpc` → JSON-RPC 2.0 dispatch to the DELIBERATE capability subset (`a2a.skills.SKILLS`). A method that
  is not an exposed capability returns JSON-RPC error -32601 — the trust asymmetry (KB_16): external peers reach
  capabilities, NEVER the internal MCP tool surface. Peer-identity enforcement (mTLS client cert → peer_state) lands
  with the Stage-18 hybrid-TLS sidecar; an optional `X-A2A-Peer-Key` header check is wired here for the meantime.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from a2a.agent_card import AgentCard, sign_card
from a2a.skills import CAPABILITIES, SKILLS

router = APIRouter(tags=["a2a"])

# JSON-RPC 2.0 error codes
_PARSE_ERROR, _INVALID_REQUEST, _METHOD_NOT_FOUND, _INVALID_PARAMS, _INTERNAL = -32700, -32600, -32601, -32602, -32603


def build_agent_card() -> AgentCard:
    """Build + ML-DSA-65-sign our agent card."""
    base = os.environ.get("A2A_PUBLIC_URL", "http://localhost:8000")
    card = AgentCard(
        name=os.environ.get("A2A_AGENT_NAME", "ai-embodied-agent"),
        version=os.environ.get("APP_VERSION", "0.1.0"),
        capabilities=CAPABILITIES,
        endpoints={"a2a": f"{base}/a2a/v1/rpc", "discovery": f"{base}/.well-known/agent.json"},
        provenance={"git_sha": os.environ.get("GIT_SHA", "dev"), "build": "self-hosted"},
        expiry=datetime.now(timezone.utc) + timedelta(days=int(os.environ.get("A2A_CARD_TTL_DAYS", "90"))),
        revocation_list_url=os.environ.get("A2A_REVOCATION_URL"),
    )
    return sign_card(card)


@router.get("/.well-known/agent.json")
def agent_card_endpoint() -> JSONResponse:
    """Discovery: return our signed agent card (honest 503 if the ML-DSA-65 signer is unavailable)."""
    try:
        return JSONResponse(build_agent_card().model_dump(mode="json"))
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": f"agent card signing unavailable: {e}"}, status_code=503)


def _err(id_: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id_}


@router.post("/a2a/v1/rpc")
async def a2a_rpc(request: Request) -> JSONResponse:
    """JSON-RPC 2.0 dispatch to the exposed capabilities ONLY (the trust boundary)."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse(_err(None, _PARSE_ERROR, "parse error"), status_code=200)
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0" or "method" not in body:
        return JSONResponse(_err(body.get("id") if isinstance(body, dict) else None,
                                 _INVALID_REQUEST, "invalid JSON-RPC 2.0 request"), status_code=200)
    rid, method, params = body.get("id"), body["method"], body.get("params", {})

    # Optional peer-identity gate (full mTLS client identity at Stage 18): a quarantined/revoked peer is refused.
    peer_key = request.headers.get("X-A2A-Peer-Key")
    if peer_key:
        from a2a.peer_state import get_peer_registry
        reg = get_peer_registry()
        if reg.state(peer_key) is not None and not reg.is_callable(peer_key):
            return JSONResponse(_err(rid, _INVALID_REQUEST, "peer not permitted (quarantined/revoked)"), status_code=200)

    handler = SKILLS.get(method)
    if handler is None:
        # NOT an exposed capability — MCP tools are deliberately unreachable here (KB_16 trust asymmetry).
        return JSONResponse(_err(rid, _METHOD_NOT_FOUND, f"method {method!r} is not an A2A-exposed capability"),
                            status_code=200)
    if not isinstance(params, dict):
        return JSONResponse(_err(rid, _INVALID_PARAMS, "params must be an object"), status_code=200)

    # Stage 27 (R4/G-4 CLOSURE): SVID-mTLS AUTHENTICATION. When the deployment terminates mutual TLS with SPIFFE
    # SVIDs (the mesh/sidecar path — docker-compose.spire.yml + a hybrid-TLS front proxy), the peer's verified client
    # certificate arrives as a header (`X-Forwarded-Client-Cert`, the standard mesh convention). We extract the
    # SPIFFE ID from it and AUTHENTICATE the peer (trust-domain + allowlist) — the peer_id below is then a proven
    # identity, not a self-asserted key. Absent an mTLS-terminating front (dev/no-mesh), we fall back to the
    # Stage-24 CONFINEMENT posture (anonymous L0, read-only) — honestly weaker, and named as such.
    authenticated_sid: Optional[str] = None
    xfcc = request.headers.get("X-Forwarded-Client-Cert") or request.headers.get("x-forwarded-client-cert")
    if xfcc:
        try:
            import base64 as _b64
            from security.spiffe_identity import authenticate_peer
            # XFCC carries the client cert DER (base64) in a `Cert=` field (mesh convention); accept a raw b64 too.
            cert_b64 = xfcc.split("Cert=")[-1].strip('"; ').split(";")[0] if "Cert=" in xfcc else xfcc
            authenticated_sid = authenticate_peer(_b64.b64decode(cert_b64))
        except PermissionError as pe:
            _audit_a2a(method, peer_key, params, ok=False, error=f"mtls: {pe}")
            return JSONResponse(_err(rid, _INVALID_REQUEST, f"peer authentication failed: {pe}"), status_code=200)
        except Exception:  # noqa: BLE001 — malformed XFCC: treat as unauthenticated, don't crash the boundary
            authenticated_sid = None

    # Stage 24 (G-080): LIVE governance enforcement at the external boundary. Every A2A caller is an L0 external peer
    # (assume-breach) → function-scoped RBAC confines it to the `a2a_capability` category, and Bell-LaPadula no-read-up
    # clamps it to read responses at/below "internal" clearance. Composes with the mTLS gate above + the peer-key gate
    # + the ZeroTrustGateway (Stage 17). Allow/deny audited. An mTLS-AUTHENTICATED caller uses its SPIFFE ID as the
    # peer_id (R4/G-4 closed on that path); an unauthenticated caller is confined as `anonymous` (honestly weaker).
    peer_id = authenticated_sid or peer_key or "anonymous"
    try:
        from governance.rbac import AgentTier, check_function_access
        from governance.mac import SecurityLabel, can_read
        rbac = check_function_access(peer_id, AgentTier.L0_PEER, {"a2a_capability"}, "a2a_capability")
        if not rbac.allow:
            _audit_a2a(method, peer_key, params, ok=False, error=f"rbac: {rbac.reason}")
            return JSONResponse(_err(rid, _INVALID_REQUEST, f"governance/RBAC: {rbac.reason}"), status_code=200)
        if not can_read(SecurityLabel.of("internal"), SecurityLabel.of("internal"), actor=peer_id).allow:
            _audit_a2a(method, peer_key, params, ok=False, error="mac: no-read-up")
            return JSONResponse(_err(rid, _INVALID_REQUEST, "governance/MAC: response above peer clearance"), status_code=200)
    except ImportError:
        pass  # governance layer unavailable -> peer-key + method-allowlist gates still apply (honest degradation)

    # Stage 19 (G-074): the external trust boundary is now trace + audit visible — an `a2a.rpc.<method>` span +
    # an `audit_chain` row per capability invocation (the boundary was previously invisible to the evidence pipeline).
    from observability.otel_init import traced_span
    with traced_span(f"a2a.rpc.{method}", **{"a2a.method": method, "a2a.peer": peer_id}):
        try:
            result = handler(params)
            _audit_a2a(method, peer_key, params, ok=True)
            return JSONResponse({"jsonrpc": "2.0", "result": result, "id": rid}, status_code=200)
        except Exception as e:  # noqa: BLE001 - a skill error is a JSON-RPC internal error, never a 500 leak
            _audit_a2a(method, peer_key, params, ok=False, error=str(e))
            return JSONResponse(_err(rid, _INTERNAL, f"capability error: {e}"), status_code=200)


def _audit_a2a(method: str, peer_key: Optional[str], params: dict, *, ok: bool, error: str = "") -> None:
    """Append a signed audit_chain row for an external A2A capability invocation (KB_15 / EU AI Act Art-12 evidence).
    Best-effort + privacy-light: records the method + peer + a hash of params (not the raw params)."""
    try:
        import hashlib
        import json as _json
        from observability.evidence_sink import record
        record("a2a:peer", f"a2a.capability.{method}", {
            "method": method, "peer": peer_key or "anonymous", "ok": ok,
            "params_sha256": hashlib.sha256(_json.dumps(params, sort_keys=True, default=str).encode()).hexdigest(),
            **({"error": error[:200]} if error else {})})
    except Exception:  # noqa: BLE001 - audit is best-effort; never breaks the RPC path
        pass


__all__ = ["router", "build_agent_card"]
