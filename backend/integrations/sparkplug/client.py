"""Stage 15 — Sparkplug B v3.0 edge-node client (paho-mqtt 2.x) with correct lifecycle + seq/bdSeq accounting.

Implements the spec's operational behaviour (research §25.1):
- **NDEATH registered as the MQTT Last-Will** at CONNECT, carrying a `bdSeq` metric.
- **NBIRTH** published immediately after CONNECT: `seq=0`, same `bdSeq`, a `Node Control/Rebirth` metric, + node metrics.
- **`seq`** (0–255, wraps) increments on every subsequent message (NDATA/DBIRTH/DDATA); **`bdSeq`** (per MQTT session)
  correlates the NDEATH to its NBIRTH.
- Inbound **NCMD `Node Control/Rebirth=true`** → republish NBIRTH (full re-sync).
- Every payload is HMAC-SHA-384 MAC'd (when a key is set); inbound payloads are MAC-verified.

Telemetry-direction only: inbound DCMD/NCMD are parsed + dispatched to a callback, NOT used to drive real actuators
(that path is the Stage-16/17 safety wrapper, KB_17).
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import paho.mqtt.client as mqtt

from . import payload as spb

SPB_NAMESPACE = "spBv1.0"


class SparkplugEdgeNode:
    def __init__(self, group_id: str, edge_node_id: str, *, broker_host: str = "localhost",
                 broker_port: int = 1883, mac_key: Optional[bytes] = None,
                 on_command: Optional[Callable[[str, "spb.sp.Payload"], None]] = None,
                 client_id: Optional[str] = None) -> None:
        self.group_id = group_id
        self.edge_node_id = edge_node_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.mac_key = mac_key
        self.on_command = on_command
        self._seq = 0
        self._bd_seq = 0
        self._lock = threading.Lock()
        self._connected = threading.Event()
        self._node_metrics: dict[str, Any] = {}
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                   client_id=client_id or f"{group_id}-{edge_node_id}")
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    # ---- topics -------------------------------------------------------------
    def _topic(self, msgtype: str, device: Optional[str] = None) -> str:
        t = f"{SPB_NAMESPACE}/{self.group_id}/{msgtype}/{self.edge_node_id}"
        return f"{t}/{device}" if device else t

    # ---- seq / bdSeq --------------------------------------------------------
    def _next_seq(self) -> int:
        """Return the current seq then advance (wraps 255→0). Caller holds the publish ordering."""
        with self._lock:
            s = self._seq
            self._seq = (self._seq + 1) % 256
            return s

    def _build_payload(self, metrics: dict[str, Any], *, seq: int,
                       extra: Optional[list[tuple[str, Any, spb.DataType]]] = None) -> "spb.sp.Payload":
        p = spb.new_payload(seq=seq)
        for name, value in metrics.items():
            spb.add_metric(p, name, value)
        for name, value, dt in (extra or []):
            spb.add_metric(p, name, value, datatype=dt)
        if self.mac_key is not None:
            spb.mac_payload(p, self.mac_key)
        return p

    def _publish(self, topic: str, payload: "spb.sp.Payload") -> None:
        self._client.publish(topic, spb.encode(payload), qos=0, retain=False)

    # ---- lifecycle ----------------------------------------------------------
    def connect(self, timeout: float = 5.0) -> bool:
        """Register the NDEATH LWT, connect, and let on_connect publish NBIRTH. Returns True on connect."""
        with self._lock:
            self._bd_seq = (self._bd_seq + 1) % (2 ** 64)
            bd = self._bd_seq
            self._seq = 0
        # NDEATH (the will): carries the bdSeq so the host can correlate the dead session
        ndeath = spb.new_payload()
        spb.add_metric(ndeath, "bdSeq", bd, datatype=spb.DataType.UInt64)
        if self.mac_key is not None:
            spb.mac_payload(ndeath, self.mac_key)
        self._client.will_set(self._topic("NDEATH"), spb.encode(ndeath), qos=0, retain=False)
        self._client.connect(self.broker_host, self.broker_port, keepalive=30)
        self._client.loop_start()
        return self._connected.wait(timeout)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if getattr(reason_code, "is_failure", False):
            return
        self._publish_nbirth()
        client.subscribe(self._topic("NCMD"))
        client.subscribe(self._topic("DCMD", "+"))
        self._connected.set()

    def _publish_nbirth(self) -> None:
        """NBIRTH: seq reset to 0, bdSeq + Node Control/Rebirth + node metrics."""
        with self._lock:
            self._seq = 0
            bd = self._bd_seq
        p = self._build_payload(
            self._node_metrics, seq=self._next_seq(),
            extra=[("bdSeq", bd, spb.DataType.UInt64),
                   ("Node Control/Rebirth", False, spb.DataType.Boolean)])
        self._publish(self._topic("NBIRTH"), p)

    def set_node_metrics(self, metrics: dict[str, Any]) -> None:
        """Set/replace the node's metric set advertised at NBIRTH."""
        self._node_metrics.update(metrics)

    def publish_node_data(self, metrics: dict[str, Any]) -> int:
        """NDATA — a node metric change. Returns the seq used."""
        seq = self._next_seq()
        self._publish(self._topic("NDATA"), self._build_payload(metrics, seq=seq))
        return seq

    def publish_device_birth(self, device_id: str, metrics: dict[str, Any]) -> int:
        seq = self._next_seq()
        self._publish(self._topic("DBIRTH", device_id), self._build_payload(metrics, seq=seq))
        return seq

    def publish_device_data(self, device_id: str, metrics: dict[str, Any]) -> int:
        seq = self._next_seq()
        self._publish(self._topic("DDATA", device_id), self._build_payload(metrics, seq=seq))
        return seq

    # ---- inbound ------------------------------------------------------------
    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = spb.decode(msg.payload)
        except Exception:  # noqa: BLE001 - malformed inbound is dropped, never crashes the loop
            return
        if self.mac_key is not None and not spb.verify_payload_mac(payload, self.mac_key):
            return  # integrity failure → ignore (honest: a bad MAC is an untrusted message)
        parts = msg.topic.split("/")
        msgtype = parts[2] if len(parts) > 2 else ""
        if msgtype == "NCMD":
            for m in payload.metrics:
                if m.name == "Node Control/Rebirth" and spb.get_metric_value(m):
                    self._publish_nbirth()
        if self.on_command is not None:
            self.on_command(msgtype, payload)

    def disconnect(self) -> None:
        """Graceful stop: publish an explicit NDEATH (with the current bdSeq), then disconnect."""
        try:
            with self._lock:
                bd = self._bd_seq
            ndeath = spb.new_payload()
            spb.add_metric(ndeath, "bdSeq", bd, datatype=spb.DataType.UInt64)
            if self.mac_key is not None:
                spb.mac_payload(ndeath, self.mac_key)
            self._publish(self._topic("NDEATH"), ndeath)
        finally:
            self._client.loop_stop()
            try:
                self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._connected.clear()

    @property
    def bd_seq(self) -> int:
        return self._bd_seq

    @property
    def seq(self) -> int:
        return self._seq


__all__ = ["SparkplugEdgeNode", "SPB_NAMESPACE"]
