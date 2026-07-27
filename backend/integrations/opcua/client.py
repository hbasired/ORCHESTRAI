"""Stage 15 — OPC UA telemetry client (asyncua): browse + read + subscribe to external OPC UA servers.

Connects to an external (or our own) OPC UA server, reads ISA-95 telemetry, and subscribes to data changes — each
change is forwarded to an `on_datachange(nodeid, value)` callback and (optionally) mirrored into the ISA-95 Neo4j
graph. Subscribe-only this stage (no writes to external servers — the actuator/write path is the Stage-17 safety
wrapper, KB_17).
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from asyncua import Client, ua


class _SubHandler:
    """asyncua subscription handler — fans datachange notifications out to the user callback."""

    def __init__(self, on_datachange: Callable[[str, Any], None]) -> None:
        self._cb = on_datachange

    def datachange_notification(self, node, val, data) -> None:  # asyncua calls this
        try:
            self._cb(node.nodeid.to_string(), val)
        except Exception:  # noqa: BLE001 - a callback error must not kill the subscription
            pass


class OpcUaTelemetryClient:
    def __init__(self, url: str, *, security_string: Optional[str] = None) -> None:
        """`security_string` e.g. 'Aes256Sha256RsaPss,SignAndEncrypt,<client_cert.der>,<client_key.pem>' (interim
        classical policy; PQC overlay @18). None → NoSecurity (certless, for the in-process roundtrip)."""
        self.url = url
        self.security_string = security_string
        self._client: Optional[Client] = None
        self._sub = None

    async def __aenter__(self) -> "OpcUaTelemetryClient":
        self._client = Client(url=self.url)
        if self.security_string:
            await self._client.set_security_string(self.security_string)
        await self._client.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._sub is not None:
            try:
                await self._sub.delete()
            except Exception:  # noqa: BLE001
                pass
        if self._client is not None:
            await self._client.disconnect()

    async def read(self, nodeid: str) -> Any:
        """Read a single node's value by NodeId string."""
        assert self._client is not None
        return await self._client.get_node(nodeid).read_value()

    async def browse_variables(self, root_nodeid: Optional[str] = None) -> dict[str, str]:
        """Recursively browse for Variable nodes → {browse_name: nodeid}. Defaults to the Objects folder."""
        assert self._client is not None
        root = self._client.get_node(root_nodeid) if root_nodeid else self._client.nodes.objects
        found: dict[str, str] = {}

        async def _walk(node) -> None:
            for child in await node.get_children():
                ncls = await child.read_node_class()
                if ncls == ua.NodeClass.Variable:
                    name = (await child.read_browse_name()).Name
                    found[name] = child.nodeid.to_string()
                elif ncls == ua.NodeClass.Object:
                    await _walk(child)

        await _walk(root)
        return found

    async def subscribe(self, nodeids: list[str], on_datachange: Callable[[str, Any], None],
                        period_ms: int = 200) -> None:
        """Subscribe to data changes on the given nodes; each change → on_datachange(nodeid, value)."""
        assert self._client is not None
        self._sub = await self._client.create_subscription(period_ms, _SubHandler(on_datachange))
        for nid in nodeids:
            await self._sub.subscribe_data_change(self._client.get_node(nid))


__all__ = ["OpcUaTelemetryClient"]
