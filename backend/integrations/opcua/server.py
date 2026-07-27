"""Stage 15 — OPC UA server exposing the ISA-95 equipment hierarchy (asyncua).

Builds an ISA-95 Part-2 object tree (Enterprise → Site → Area → WorkCenter → WorkUnit/Equipment) in our own
namespace, each WorkUnit carrying live telemetry variables (Status, OEE, Temperature, UnitsProduced). External OT
clients browse + subscribe to it; our own `client.py` reads it back in the roundtrip test.

Security: the interim classical policy is **Aes256Sha256RsaPss** (task AC; the PQC overlay is Stage 18, KB_13). It
requires a server certificate + private key (`load_certs`); without certs the server permits `NoSecurity` so the
certless in-process roundtrip test can run. Honest: `secure_policy_enabled()` reports whether the strong policy is
actually armed (it is only when certs are loaded).
"""
from __future__ import annotations

from typing import Optional

from asyncua import Server, ua

ISA95_NS = "http://aiagent.io/isa95"

# A small but real ISA-95 hierarchy: Enterprise/Site/Area/WorkCenter + two WorkUnits with telemetry.
_DEFAULT_TREE = {
    "enterprise": "AcmeManufacturing",
    "site": "Plant1",
    "area": "AssemblyArea",
    "work_center": "Line1",
    "work_units": ["Stage0_Intake", "Stage1_Weld"],
}
_TELEMETRY = {"Status": ("string", "idle"), "OEE": ("double", 0.0),
              "Temperature": ("double", 20.0), "UnitsProduced": ("int64", 0)}


class ISA95OpcUaServer:
    def __init__(self, endpoint: str = "opc.tcp://0.0.0.0:4840/aiagent/opcua/",
                 tree: Optional[dict] = None) -> None:
        self.endpoint = endpoint
        self.tree = tree or _DEFAULT_TREE
        self._server: Optional[Server] = None
        self._idx: Optional[int] = None
        self._vars: dict[str, "ua.Node"] = {}     # "WorkUnit/Var" -> Variable node
        self._secure = False

    async def init(self) -> None:
        self._server = Server()
        await self._server.init()
        self._server.set_endpoint(self.endpoint)
        self._server.set_server_name("AI-Agent ISA-95 OPC UA Server")
        self._idx = await self._server.register_namespace(ISA95_NS)
        await self._build_isa95_tree()

    async def load_certs(self, cert_path: str, key_path: str) -> None:
        """Arm the interim Aes256Sha256RsaPss security policy (requires a cert + key)."""
        assert self._server is not None
        await self._server.load_certificate(cert_path)
        await self._server.load_private_key(key_path)
        self._server.set_security_policy([ua.SecurityPolicyType.Aes256Sha256RsaPss_SignAndEncrypt,
                                          ua.SecurityPolicyType.Aes256Sha256RsaPss_Sign])
        self._secure = True

    def secure_policy_enabled(self) -> bool:
        """True only when the Aes256Sha256RsaPss policy is actually armed (certs loaded). Honest capability report."""
        return self._secure

    async def _build_isa95_tree(self) -> None:
        assert self._server is not None and self._idx is not None
        idx = self._idx
        objects = self._server.nodes.objects
        enterprise = await objects.add_object(idx, self.tree["enterprise"])
        site = await enterprise.add_object(idx, self.tree["site"])
        area = await site.add_object(idx, self.tree["area"])
        wc = await area.add_object(idx, self.tree["work_center"])
        for wu_name in self.tree["work_units"]:
            wu = await wc.add_object(idx, wu_name)
            for var_name, (vtype, default) in _TELEMETRY.items():
                varianttype = {"string": ua.VariantType.String, "double": ua.VariantType.Double,
                               "int64": ua.VariantType.Int64}[vtype]
                node = await wu.add_variable(idx, var_name, default, varianttype=varianttype)
                await node.set_writable()
                self._vars[f"{wu_name}/{var_name}"] = node

    async def set_telemetry(self, work_unit: str, var: str, value) -> None:
        """Update a WorkUnit telemetry variable (drives a datachange to subscribers)."""
        node = self._vars[f"{work_unit}/{var}"]
        await node.write_value(value)

    def variable_nodeids(self) -> dict[str, str]:
        """{‘WorkUnit/Var’: nodeid-string} — what a client browses/subscribes to."""
        return {k: v.nodeid.to_string() for k, v in self._vars.items()}

    async def __aenter__(self) -> "ISA95OpcUaServer":
        if self._server is None:
            await self.init()
        await self._server.start()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._server is not None:
            await self._server.stop()


__all__ = ["ISA95OpcUaServer", "ISA95_NS"]
