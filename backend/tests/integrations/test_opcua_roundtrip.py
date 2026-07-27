"""Stage 15 — OPC UA ISA-95 server↔client roundtrip over the REAL OPC UA binary protocol (asyncua, loopback TCP).

No mocks: an actual asyncua server binds a loopback port, exposes the ISA-95 tree, and a real asyncua client browses,
reads, and receives a live data-change subscription notification.
"""
import asyncio

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.timeout(60)]

ENDPOINT = "opc.tcp://127.0.0.1:48401/aiagent/opcua/"


async def test_isa95_server_client_roundtrip_and_subscription():
    from integrations.opcua.client import OpcUaTelemetryClient
    from integrations.opcua.server import ISA95OpcUaServer

    server = ISA95OpcUaServer(endpoint=ENDPOINT)
    async with server:
        # interim policy is NOT armed without certs (honest capability report)
        assert server.secure_policy_enabled() is False
        async with OpcUaTelemetryClient(ENDPOINT) as client:
            # browse finds the ISA-95 telemetry variables
            variables = await client.browse_variables()
            assert "OEE" in variables and "Status" in variables and "UnitsProduced" in variables

            # set a value on the server, read it back through the client
            await server.set_telemetry("Stage0_Intake", "OEE", 0.77)
            await asyncio.sleep(0.2)
            oee_nid = server.variable_nodeids()["Stage0_Intake/OEE"]
            assert abs(await client.read(oee_nid) - 0.77) < 1e-6

            # subscribe and receive a live data-change notification. asyncua sends the CURRENT value as the
            # first notification, so only fire the event once we observe the NEW value we set after subscribing.
            got: dict = {}
            ev = asyncio.Event()

            def on_change(nodeid, value):
                got[nodeid] = value
                if abs(value - 0.91) < 1e-6:
                    ev.set()

            await client.subscribe([oee_nid], on_change)
            await asyncio.sleep(0.3)                       # drain the initial-value notification (0.77)
            await server.set_telemetry("Stage0_Intake", "OEE", 0.91)
            await asyncio.wait_for(ev.wait(), timeout=15)
            assert abs(got[oee_nid] - 0.91) < 1e-6
