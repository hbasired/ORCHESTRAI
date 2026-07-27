"""Stage 17 — agentic zero-trust (CTO #3 G-063/G-064): per-agent ML-DSA-65 identity + MCP tool authz + signed manifest."""
from security.agent_identity import issue_identity, sign_statement, verify_statement
from security.mcp_authz import MCPToolAuthz, sanitize_args
from security.tool_manifest import build_manifest, diff_against_live, sign_manifest, verify_manifest
from security.zero_trust import FRAMEWORK, describe_framework, ZeroTrustGateway

_LIVE = [{"server": "model_inference_server", "name": "predict_failure"},
         {"server": "kpi_query_server", "name": "queue_depth"}]


def test_named_framework_is_nist_800_207():
    assert "NIST SP 800-207" in FRAMEWORK
    pillars = describe_framework()["pillars"]
    assert set(pillars) == {"Identity", "Device", "Network", "Application/Workload", "Data"}


def test_per_agent_identities_are_distinct_real_mldsa65():
    a = issue_identity("embodied", owner="ops", purpose="runtime", capabilities=["x"])
    b = issue_identity("supply_chain", owner="ops", purpose="logistics", capabilities=["y"])
    assert a.algorithm == "ML-DSA-65" and b.algorithm == "ML-DSA-65"
    assert a.public_key_b64 and a.public_key_b64 != b.public_key_b64   # distinct non-human identities


def test_agent_statement_signed_and_verified():
    a = issue_identity("embodied", owner="ops", purpose="runtime")
    b = issue_identity("supply_chain", owner="ops", purpose="logistics")
    stmt = {"action": "predict", "ts": 1}
    sig = sign_statement("embodied", stmt)
    assert verify_statement(a.public_key_b64, stmt, sig) is True            # own key verifies
    assert verify_statement(b.public_key_b64, stmt, sig) is False           # another agent's key does NOT
    assert verify_statement(a.public_key_b64, {**stmt, "ts": 2}, sig) is False  # tampered payload


def test_tool_manifest_signed_verified_and_rogue_detected():
    m = sign_manifest(build_manifest(_LIVE))
    assert verify_manifest(m) is True
    tampered = {**m, "tools": m["tools"] + [{"server": "evil", "name": "exfiltrate"}]}
    assert verify_manifest(tampered) is False                               # signature breaks on tamper
    drift = diff_against_live(m, _LIVE + [{"server": "evil", "name": "exfiltrate"}])
    assert ("evil", "exfiltrate") in drift["rogue"] and drift["ok"] is False


def test_mcp_authz_capability_and_sanitisation():
    authz = MCPToolAuthz({"embodied": {"model_inference_server.predict_failure"}})
    assert authz.authorize("embodied", "model_inference_server.predict_failure", {"air_temp_k": 300.0}).allowed is True
    assert authz.authorize("embodied", "kpi_query_server.queue_depth", {}).allowed is False   # not granted
    assert authz.authorize("embodied", "model_inference_server.predict_failure", {"p": "; rm -rf /"}).allowed is False
    ok, _ = sanitize_args({"path": "../../etc/passwd"})
    assert ok is False                                                       # path traversal rejected


def test_mcp_authz_rate_limiting():
    authz = MCPToolAuthz({"a": {"t"}}, rate_limit_per_min=3)
    assert sum(1 for _ in range(3) if authz.authorize("a", "t", {}).allowed) == 3
    assert authz.authorize("a", "t", {}).allowed is False                   # 4th within the window → limited


def test_zero_trust_gateway_blocks_rogue_tool_and_ungranted():
    authz = MCPToolAuthz({"embodied": {"model_inference_server.predict_failure"}})
    gw = ZeroTrustGateway(authz, sign_manifest(build_manifest(_LIVE)))
    assert gw.authorize_tool_call("embodied", "model_inference_server.predict_failure", {}, _LIVE)["allowed"] is True
    rogue_live = _LIVE + [{"server": "evil", "name": "exfiltrate"}]
    assert gw.authorize_tool_call("embodied", "exfiltrate", {}, rogue_live)["allowed"] is False   # rogue → blocked


def test_zero_trust_gateway_refuses_tampered_manifest():
    authz = MCPToolAuthz({"embodied": {"model_inference_server.predict_failure"}})
    m = sign_manifest(build_manifest(_LIVE))
    m["tools"] = m["tools"] + [{"server": "evil", "name": "x"}]   # tamper after signing
    gw = ZeroTrustGateway(authz, m)
    out = gw.authorize_tool_call("embodied", "model_inference_server.predict_failure", {}, _LIVE)
    assert out["allowed"] is False and "manifest" in out["reason"]
