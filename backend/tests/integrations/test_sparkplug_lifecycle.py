"""Stage 15 — Sparkplug B v3.0: payload + seq/bdSeq accounting (unit) and the full edge-node lifecycle over a REAL
Mosquitto broker (skipif the broker is down).
"""
import socket
import time

import pytest

from integrations.sparkplug import payload as spb
from integrations.sparkplug.client import SPB_NAMESPACE, SparkplugEdgeNode

MAC_KEY = b"sparkplug-test-key-0123456789abcd"


# ---- unit: payload + accounting (no broker) ---------------------------------

def test_seq_wraps_0_to_255():
    n = SparkplugEdgeNode("g", "e")
    n._seq = 254
    assert [n._next_seq() for _ in range(4)] == [254, 255, 0, 1]  # wraps 255 -> 0


def test_payload_datatypes_roundtrip():
    p = spb.new_payload(seq=0)
    spb.add_metric(p, "OEE", 0.83)
    spb.add_metric(p, "Running", True)
    spb.add_metric(p, "Units", 42)
    spb.add_metric(p, "Recipe", "weld-A")
    q = spb.decode(spb.encode(p))
    d = spb.metrics_dict(q)
    assert d == {"OEE": pytest.approx(0.83), "Running": True, "Units": 42, "Recipe": "weld-A"}


def test_hmac_sha384_mac_detects_tamper_and_wrong_key():
    p = spb.new_payload(seq=0)
    spb.add_metric(p, "OEE", 0.5)
    spb.mac_payload(p, MAC_KEY)
    assert spb.verify_payload_mac(p, MAC_KEY) is True
    p.metrics[0].double_value = 0.6                       # tamper
    assert spb.verify_payload_mac(p, MAC_KEY) is False
    p2 = spb.new_payload(seq=1); spb.add_metric(p2, "X", 1.0); spb.mac_payload(p2, MAC_KEY)
    assert spb.verify_payload_mac(p2, b"wrong-key") is False


# ---- integration: real Mosquitto broker -------------------------------------

def _broker_up(host="localhost", port=1883) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


_BROKER = _broker_up()


@pytest.mark.timeout(40)
@pytest.mark.skipif(not _BROKER, reason="Mosquitto broker not reachable on localhost:1883")
def test_full_lifecycle_over_real_broker():
    """NBIRTH(seq=0,bdSeq) → NDATA(seq=1) → NCMD Rebirth → NBIRTH(seq=0) → NDEATH — captured by a real subscriber."""
    import paho.mqtt.client as mqtt

    captured: list[tuple[str, "spb.sp.Payload"]] = []

    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="spb-test-subscriber")
    sub.on_message = lambda c, u, msg: captured.append((msg.topic, spb.decode(msg.payload)))
    sub.connect("localhost", 1883, 30)
    sub.subscribe(f"{SPB_NAMESPACE}/TestGroup/#")
    sub.loop_start()
    time.sleep(0.5)

    node = SparkplugEdgeNode("TestGroup", "EdgeNode1", mac_key=MAC_KEY)
    node.set_node_metrics({"Node/Uptime": 0})
    try:
        assert node.connect(timeout=5) is True
        first_bdseq = node.bd_seq
        time.sleep(0.5)
        node.publish_node_data({"Node/Uptime": 10})        # NDATA
        node.publish_device_birth("Robot1", {"OEE": 0.8})  # DBIRTH
        node.publish_device_data("Robot1", {"OEE": 0.85})  # DDATA
        time.sleep(0.5)

        topics = [t.split("/")[2] for t, _ in captured]
        assert "NBIRTH" in topics and "NDATA" in topics and "DBIRTH" in topics

        # NBIRTH: seq 0, carries bdSeq + Node Control/Rebirth, MAC valid
        nbirth = next(p for t, p in captured if t.split("/")[2] == "NBIRTH")
        assert nbirth.seq == 0
        names = {m.name for m in nbirth.metrics}
        assert "bdSeq" in names and "Node Control/Rebirth" in names
        assert spb.verify_payload_mac(nbirth, MAC_KEY) is True

        # the first NDATA seq == 1 (NBIRTH was 0)
        ndata = next(p for t, p in captured if t.split("/")[2] == "NDATA")
        assert ndata.seq == 1

        # trigger a Rebirth via NCMD → a fresh NBIRTH (seq reset to 0) is published
        captured.clear()
        rebirth = spb.new_payload(seq=0)
        spb.add_metric(rebirth, "Node Control/Rebirth", True, datatype=spb.DataType.Boolean)
        spb.mac_payload(rebirth, MAC_KEY)
        sub_pub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="spb-test-ncmd")
        sub_pub.connect("localhost", 1883, 30)
        sub_pub.publish(f"{SPB_NAMESPACE}/TestGroup/NCMD/EdgeNode1", spb.encode(rebirth))
        sub_pub.disconnect()
        time.sleep(0.8)
        assert any(t.split("/")[2] == "NBIRTH" and p.seq == 0 for t, p in captured), "Rebirth must re-emit NBIRTH"
    finally:
        node.disconnect()         # publishes an explicit NDEATH
        time.sleep(0.3)
        assert node.bd_seq == first_bdseq  # bdSeq stable within a session
        sub.loop_stop()
        sub.disconnect()
