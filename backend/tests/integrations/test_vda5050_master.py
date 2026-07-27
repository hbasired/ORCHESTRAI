"""Stage 16 — VDA 5050 master controller over a REAL Mosquitto broker: connection-freshness anti-spoof gate, the
safety validator gate, and a full dispatch→state roundtrip with a simulated AGV. Plus infra-free gate-logic tests.
"""
import json
import socket
import time

import pytest

from integrations.vda5050 import topics as T
from integrations.vda5050.master import VDA_VERSION, Vda5050Master


# ---- infra-free: the safety + freshness gates -------------------------------

def test_safety_gate_blocks_stale_connection():
    """dispatch_order must REFUSE (no publish) when the AGV connection is not fresh — anti-spoof (risk register)."""
    m = Vda5050Master()  # no broker connect; registry empty → connection not fresh
    order = m.build_order("ACME", "AGV-1",
                          [{"nodeId": "n1", "sequenceId": 0, "released": True, "actions": []}], [])
    res = m.dispatch_order("ACME", "AGV-1", order)
    assert res["dispatched"] is False and "connection_fresh" in res["reason"]


def test_safety_gate_blocks_malformed_order():
    """A structurally invalid order is blocked even if the connection were fresh (the safety validator gate)."""
    from safety.validator import validate_order
    bad = {"orderId": "", "nodes": []}  # no orderId, no nodes
    res = validate_order(bad, connection_fresh=True)
    assert res.allowed is False


# ---- integration: real Mosquitto broker -------------------------------------

def _broker_up(host="localhost", port=1883) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


_BROKER = _broker_up()
pytestmark_broker = pytest.mark.skipif(not _BROKER, reason="Mosquitto broker not reachable on localhost:1883")


class _SimulatedAgv:
    """A minimal VDA 5050 AGV: announces ONLINE, and on receiving an order publishes a state referencing it."""

    def __init__(self, manufacturer="SIM", serial="AGV-1"):
        import paho.mqtt.client as mqtt
        self.mfr, self.sn = manufacturer, serial
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-agv-{serial}")
        self.c.on_message = self._on_msg
        self.received_orders = []

    def start(self):
        self.c.connect("localhost", 1883, 30)
        self.c.subscribe(T.topic(self.mfr, self.sn, "order"))
        self.c.loop_start()
        time.sleep(0.3)
        # announce ONLINE (retained, like a real AGV's connection)
        self.c.publish(T.topic(self.mfr, self.sn, "connection"),
                       json.dumps({"headerId": 0, "timestamp": "2026-06-20T00:00:00Z", "version": VDA_VERSION,
                                   "manufacturer": self.mfr, "serialNumber": self.sn, "connectionState": "ONLINE"}),
                       qos=0, retain=True)

    def _on_msg(self, client, userdata, msg):
        order = json.loads(msg.payload)
        self.received_orders.append(order)
        # respond with a state referencing the order
        client.publish(T.topic(self.mfr, self.sn, "state"),
                       json.dumps({"headerId": 1, "timestamp": "2026-06-20T00:00:01Z", "version": VDA_VERSION,
                                   "manufacturer": self.mfr, "serialNumber": self.sn,
                                   "orderId": order["orderId"], "orderUpdateId": order.get("orderUpdateId", 0),
                                   "lastNodeId": "n1", "lastNodeSequenceId": 0, "nodeStates": [], "edgeStates": [],
                                   "driving": True, "actionStates": [],
                                   "batteryState": {"batteryCharge": 90.0, "charging": False},
                                   "operatingMode": "AUTOMATIC", "errors": [],
                                   "safetyState": {"eStop": "NONE", "fieldViolation": False}}))

    def stop(self):
        self.c.loop_stop()
        self.c.disconnect()


@pytestmark_broker
def test_master_dispatch_roundtrip_with_simulated_agv():
    agv = _SimulatedAgv()
    master = Vda5050Master()
    try:
        agv.start()
        assert master.connect(timeout=5) is True
        # let the retained connection + announcement reach the master
        for _ in range(20):
            if master.connection_is_fresh("SIM", "AGV-1"):
                break
            time.sleep(0.2)
        assert master.connection_is_fresh("SIM", "AGV-1") is True

        order = master.build_order("SIM", "AGV-1",
                                   [{"nodeId": "n1", "sequenceId": 0, "released": True, "actions": []},
                                    {"nodeId": "n2", "sequenceId": 2, "released": True, "actions": []}],
                                   [{"edgeId": "e1", "sequenceId": 1, "released": True,
                                     "startNodeId": "n1", "endNodeId": "n2", "actions": []}])
        res = master.dispatch_order("SIM", "AGV-1", order)
        assert res["dispatched"] is True

        # the AGV received the order and the master saw the resulting state
        deadline = time.time() + 5
        while time.time() < deadline and not master.get_state("SIM", "AGV-1"):
            time.sleep(0.2)
        assert agv.received_orders and agv.received_orders[0]["orderId"] == order["orderId"]
        st = master.get_state("SIM", "AGV-1")
        assert st is not None and st["orderId"] == order["orderId"]
    finally:
        master.disconnect()
        agv.stop()


@pytestmark_broker
def test_master_refuses_order_to_offline_agv():
    """No connection announced → the master refuses to dispatch (anti-spoof over the real broker)."""
    master = Vda5050Master()
    try:
        assert master.connect(timeout=5) is True
        order = master.build_order("GHOST", "AGV-9",
                                   [{"nodeId": "n1", "sequenceId": 0, "released": True, "actions": []}], [])
        res = master.dispatch_order("GHOST", "AGV-9", order)
        assert res["dispatched"] is False
    finally:
        master.disconnect()
