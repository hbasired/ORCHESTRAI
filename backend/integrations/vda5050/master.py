"""Stage 16 — VDA 5050 v2.1.0 master controller (multi-vendor AGV/AMR fleet over MQTT).

Subscribes to AGV→master topics (state/connection/factsheet/visualization), maintains a per-AGV registry, and
dispatches `order`/`instantActions` — but ONLY after (1) the AGV `connection` is verified **fresh + ONLINE**
(anti-spoof, risk register) and (2) the order passes `backend/safety/validator.py` (`safety.validate` span; KB_17).
Hand-rolled on paho-mqtt (no mature free Python VDA-5050 *master* lib; research §26.5). Messages validate against the
real upstream schemas (`models/`, `schemas/`).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import paho.mqtt.client as mqtt

from . import topics as T

VDA_VERSION = "2.1.0"


@dataclass
class AgvRecord:
    manufacturer: str
    serial_number: str
    connection_state: Optional[str] = None          # ONLINE / OFFLINE / CONNECTIONBROKEN
    connection_ts: float = 0.0                       # monotonic time of last connection msg
    last_state: Optional[dict] = None
    factsheet: Optional[dict] = None
    order_id_counter: int = 0
    header_counters: dict[str, int] = field(default_factory=dict)


class Vda5050Master:
    def __init__(self, *, broker_host: str = "localhost", broker_port: int = 1883,
                 connection_freshness_s: float = 30.0, client_id: str = "vda5050-master") -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.connection_freshness_s = connection_freshness_s
        self._agvs: dict[tuple[str, str], AgvRecord] = {}
        self._lock = threading.Lock()
        self._connected = threading.Event()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    # ---- lifecycle ----------------------------------------------------------
    def connect(self, timeout: float = 5.0) -> bool:
        self._client.connect(self.broker_host, self.broker_port, keepalive=30)
        self._client.loop_start()
        return self._connected.wait(timeout)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if getattr(reason_code, "is_failure", False):
            return
        for tname in T.AGV_TO_MASTER:
            client.subscribe(T.subscribe_filter(tname))
        self._connected.set()

    def disconnect(self) -> None:
        self._client.loop_stop()
        try:
            self._client.disconnect()
        except Exception:  # noqa: BLE001
            pass
        self._connected.clear()

    # ---- inbound ------------------------------------------------------------
    def _on_message(self, client, userdata, msg) -> None:
        import json
        parsed = T.parse_topic(msg.topic)
        if parsed is None:
            return
        try:
            payload = json.loads(msg.payload)
        except Exception:  # noqa: BLE001
            return
        key = (parsed.manufacturer, parsed.serial_number)
        with self._lock:
            rec = self._agvs.setdefault(key, AgvRecord(parsed.manufacturer, parsed.serial_number))
            if parsed.topic == "connection":
                rec.connection_state = payload.get("connectionState")
                rec.connection_ts = time.monotonic()
            elif parsed.topic == "state":
                rec.last_state = payload
            elif parsed.topic == "factsheet":
                rec.factsheet = payload

    # ---- freshness / registry ----------------------------------------------
    def connection_is_fresh(self, manufacturer: str, serial_number: str) -> bool:
        """ONLINE + received within the freshness window. Anti-spoof gate before any order dispatch."""
        with self._lock:
            rec = self._agvs.get((manufacturer, serial_number))
            if rec is None or rec.connection_state != "ONLINE":
                return False
            return (time.monotonic() - rec.connection_ts) <= self.connection_freshness_s

    def get_state(self, manufacturer: str, serial_number: str) -> Optional[dict]:
        with self._lock:
            rec = self._agvs.get((manufacturer, serial_number))
            return rec.last_state if rec else None

    def known_agvs(self) -> list[tuple[str, str]]:
        with self._lock:
            return list(self._agvs.keys())

    # ---- outbound -----------------------------------------------------------
    def _header(self, manufacturer: str, serial_number: str, topic_name: str) -> dict:
        with self._lock:
            rec = self._agvs.setdefault((manufacturer, serial_number),
                                        AgvRecord(manufacturer, serial_number))
            hid = rec.header_counters.get(topic_name, 0)
            rec.header_counters[topic_name] = hid + 1
        return {"headerId": hid, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "version": VDA_VERSION, "manufacturer": manufacturer, "serialNumber": serial_number}

    def build_order(self, manufacturer: str, serial_number: str, nodes: list[dict], edges: list[dict],
                    order_update_id: int = 0) -> dict:
        """Build a schema-valid VDA 5050 order (header + monotonic orderId + nodes/edges)."""
        with self._lock:
            rec = self._agvs.setdefault((manufacturer, serial_number),
                                        AgvRecord(manufacturer, serial_number))
            rec.order_id_counter += 1
            order_id = f"order-{rec.order_id_counter}"
        order = self._header(manufacturer, serial_number, "order")
        order.update({"orderId": order_id, "orderUpdateId": order_update_id, "nodes": nodes, "edges": edges})
        return order

    def dispatch_order(self, manufacturer: str, serial_number: str, order: dict) -> dict:
        """Verify connection freshness → safety.validate → publish to the `order` topic. Returns a dispatch result;
        REFUSES (no publish) if the connection is stale/offline or the safety gate blocks (anti-spoof + KB_17)."""
        import json

        from safety.validator import validate_order

        fresh = self.connection_is_fresh(manufacturer, serial_number)
        result = validate_order(order, connection_fresh=fresh)   # emits the safety.validate span
        if not result.allowed:
            return {"dispatched": False, "reason": result.reason, "checks": result.checks}
        # The publish is the actuation — emit an actuator.* span (KB_17 trace-pairing invariant: it is preceded by the
        # safety.validate span above; CI `check-safety-trace-pairing.py` enforces the ordering).
        from observability.otel_init import traced_span
        topic = T.topic(manufacturer, serial_number, "order")
        with traced_span("actuator.vda5050.order",
                         **{"actuator": "vda5050.order", "actuator.target": serial_number,
                            "vda5050.order_id": order.get("orderId", "")}):
            self._client.publish(topic, json.dumps(order), qos=0, retain=False)
        return {"dispatched": True, "order_id": order.get("orderId"), "topic": topic}

    def send_instant_action(self, manufacturer: str, serial_number: str, actions: list[dict]) -> dict:
        """Publish an instantActions message (immediate, e.g. cancelOrder/startPause). Requires a fresh connection."""
        import json
        if not self.connection_is_fresh(manufacturer, serial_number):
            return {"dispatched": False, "reason": "connection not fresh/ONLINE"}
        msg = self._header(manufacturer, serial_number, "instantActions")
        msg["actions"] = actions
        topic = T.topic(manufacturer, serial_number, "instantActions")
        self._client.publish(topic, json.dumps(msg), qos=0, retain=False)
        return {"dispatched": True, "topic": topic, "n_actions": len(actions)}


__all__ = ["Vda5050Master", "AgvRecord", "VDA_VERSION"]
