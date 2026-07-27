"""Stage 16 — VDA 5050 MQTT topic namespace (v2.1.0 §"MQTT topics").

`<interfaceName>/<majorVersion>/<manufacturer>/<serialNumber>/<topic>` — default interface `uagv`, major `v2`.
Master→AGV: `order`, `instantActions`. AGV→master: `state`, `connection`, `factsheet`, `visualization`.
`connection` is published MQTT-**retained** (it is the AGV's online/offline LWT).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

INTERFACE_NAME = "uagv"
MAJOR_VERSION = "v2"

# direction matters for the master controller's subscribe/publish split
MASTER_TO_AGV = ("order", "instantActions")
AGV_TO_MASTER = ("state", "connection", "factsheet", "visualization")
ALL_TOPICS = MASTER_TO_AGV + AGV_TO_MASTER
RETAINED_TOPICS = ("connection",)  # the AGV's online/offline state is retained


def topic(manufacturer: str, serial_number: str, topic_name: str,
          interface: str = INTERFACE_NAME, major: str = MAJOR_VERSION) -> str:
    if topic_name not in ALL_TOPICS:
        raise ValueError(f"unknown VDA 5050 topic {topic_name!r}")
    return f"{interface}/{major}/{manufacturer}/{serial_number}/{topic_name}"


def subscribe_filter(topic_name: str, interface: str = INTERFACE_NAME, major: str = MAJOR_VERSION) -> str:
    """A wildcard filter for one topic across all AGVs: `uagv/v2/+/+/<topic>`."""
    return f"{interface}/{major}/+/+/{topic_name}"


@dataclass(frozen=True)
class ParsedTopic:
    interface: str
    major: str
    manufacturer: str
    serial_number: str
    topic: str


def parse_topic(full_topic: str) -> Optional[ParsedTopic]:
    """Parse `uagv/v2/<mfr>/<sn>/<topic>` → ParsedTopic, or None if it doesn't match the VDA 5050 shape."""
    parts = full_topic.split("/")
    if len(parts) != 5 or parts[4] not in ALL_TOPICS:
        return None
    return ParsedTopic(interface=parts[0], major=parts[1], manufacturer=parts[2],
                       serial_number=parts[3], topic=parts[4])


__all__ = ["INTERFACE_NAME", "MAJOR_VERSION", "MASTER_TO_AGV", "AGV_TO_MASTER", "ALL_TOPICS", "RETAINED_TOPICS",
           "topic", "subscribe_filter", "ParsedTopic", "parse_topic"]
