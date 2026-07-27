"""Stage 17 — MCP tool authorization: least-privilege capability grants + argument sanitisation + rate-limiting
(CTO #3 G-063; NIST SP 800-207 "Application/Workload" pillar; OWASP NHI / CSA MAESTRO tool-abuse mitigations).

An agent identity may invoke ONLY the tools its identity is granted (least privilege, continuous authorization — not
static roles), its arguments are sanitised (injection / oversize / depth), and calls are rate-limited per (agent, tool).
This is the authz layer a real MCP gateway enforces before dispatching to a tool server (KB_16 trust model).
"""
from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Optional

# Conservative injection signatures for string arguments (defence-in-depth; tools should also parameterise).
_INJECTION_PATTERNS = [
    re.compile(r"(?:^|[;&|`$])\s*(?:rm|del|drop\s+table|shutdown|reboot)\b", re.I),
    re.compile(r"\.\./|\.\.\\"),                       # path traversal
    re.compile(r"<script\b", re.I),                    # xss-ish
    re.compile(r"\$\{.*\}|\$\(.*\)|`.*`"),            # shell / template substitution
    re.compile(r"\b(?:UNION\s+SELECT|;\s*DROP\b|--\s)", re.I),  # sql-ish
]
_MAX_STR_LEN = 8192
_MAX_DEPTH = 6


@dataclass
class AuthzDecision:
    allowed: bool
    reason: str
    agent_id: str = ""
    tool: str = ""


def sanitize_args(args: Any, _depth: int = 0) -> tuple[bool, str]:
    """Reject obviously-malicious / abusive arguments. Returns (ok, reason)."""
    if _depth > _MAX_DEPTH:
        return False, "args nested too deep"
    if isinstance(args, str):
        if len(args) > _MAX_STR_LEN:
            return False, "string argument too long"
        for pat in _INJECTION_PATTERNS:
            if pat.search(args):
                return False, f"argument matched injection pattern {pat.pattern!r}"
        return True, "ok"
    if isinstance(args, dict):
        for k, v in args.items():
            ok, reason = sanitize_args(k, _depth + 1)
            if not ok:
                return ok, reason
            ok, reason = sanitize_args(v, _depth + 1)
            if not ok:
                return ok, reason
        return True, "ok"
    if isinstance(args, (list, tuple)):
        for v in args:
            ok, reason = sanitize_args(v, _depth + 1)
            if not ok:
                return ok, reason
        return True, "ok"
    return True, "ok"   # numbers/bools/None are fine


class MCPToolAuthz:
    """Per-agent capability grants + rate-limiting. `grants`: agent_id -> set of allowed tool names (or {'*'})."""

    def __init__(self, grants: Optional[dict[str, set[str]]] = None, *, rate_limit_per_min: int = 60) -> None:
        self._grants: dict[str, set[str]] = {a: set(t) for a, t in (grants or {}).items()}
        self._rpm = rate_limit_per_min
        self._calls: dict[tuple[str, str], deque] = defaultdict(deque)

    def grant(self, agent_id: str, tools: list[str]) -> None:
        self._grants.setdefault(agent_id, set()).update(tools)

    def authorize(self, agent_id: str, tool: str, args: Any) -> AuthzDecision:
        allowed_tools = self._grants.get(agent_id, set())
        if "*" not in allowed_tools and tool not in allowed_tools:
            return AuthzDecision(False, f"capability_denied: {agent_id} not granted {tool!r}", agent_id, tool)
        ok, reason = sanitize_args(args)
        if not ok:
            return AuthzDecision(False, f"arg_rejected: {reason}", agent_id, tool)
        if not self._rate_ok(agent_id, tool):
            return AuthzDecision(False, f"rate_limited: > {self._rpm}/min", agent_id, tool)
        return AuthzDecision(True, "ok", agent_id, tool)

    def _rate_ok(self, agent_id: str, tool: str) -> bool:
        now = time.monotonic()
        q = self._calls[(agent_id, tool)]
        while q and now - q[0] > 60.0:
            q.popleft()
        if len(q) >= self._rpm:
            return False
        q.append(now)
        return True


__all__ = ["AuthzDecision", "MCPToolAuthz", "sanitize_args"]
