"""Stage 15 — Sparkplug B v3.0 payload helpers over the real protobuf (`sparkplug_b_pb2`).

Build/parse spec-conformant payloads (NBIRTH/NDEATH/NDATA/DBIRTH/DDATA/NCMD/DCMD share the same `Payload` message;
the MSGTYPE lives in the MQTT topic, not the payload). Plus an HMAC-SHA-384 integrity tag (KB_13 / task AC) carried as
a dedicated metric, computed over the canonical payload with the tag cleared — so a receiver can re-derive + verify it.
"""
from __future__ import annotations

import enum
import time
from typing import Any, Optional

from . import sparkplug_b_pb2 as sp


class DataType(enum.IntEnum):
    """Sparkplug B metric datatypes (the subset we emit). Values are the spec's wire codes."""
    Int8 = 1
    Int16 = 2
    Int32 = 3
    Int64 = 4
    UInt8 = 5
    UInt16 = 6
    UInt32 = 7
    UInt64 = 8
    Float = 9
    Double = 10
    Boolean = 11
    String = 12
    DateTime = 13
    Text = 14
    Bytes = 17


# The metric that carries the HMAC-SHA-384 integrity tag (bytes). Cleared before MAC computation.
MAC_METRIC = "MAC/HMAC-SHA384"


def _now_ms() -> int:
    return int(time.time() * 1000)


def new_payload(seq: Optional[int] = None, timestamp: Optional[int] = None) -> "sp.Payload":
    p = sp.Payload()
    p.timestamp = timestamp if timestamp is not None else _now_ms()
    if seq is not None:
        p.seq = seq
    return p


def _infer_datatype(value: Any) -> DataType:
    if isinstance(value, bool):
        return DataType.Boolean
    if isinstance(value, int):
        return DataType.Int64
    if isinstance(value, float):
        return DataType.Double
    if isinstance(value, str):
        return DataType.String
    if isinstance(value, (bytes, bytearray)):
        return DataType.Bytes
    raise TypeError(f"unsupported Sparkplug metric value type: {type(value).__name__}")


def add_metric(payload: "sp.Payload", name: str, value: Any, *, datatype: Optional[DataType] = None,
               alias: Optional[int] = None, timestamp: Optional[int] = None) -> "sp.Payload.Metric":
    """Append a metric, setting the correct typed `value` oneof per the (inferred or given) datatype."""
    dt = DataType(datatype) if datatype is not None else _infer_datatype(value)
    m = payload.metrics.add()
    m.name = name
    m.datatype = int(dt)
    m.timestamp = timestamp if timestamp is not None else _now_ms()
    if alias is not None:
        m.alias = alias
    if dt in (DataType.Int8, DataType.Int16, DataType.Int32, DataType.UInt8, DataType.UInt16, DataType.UInt32):
        m.int_value = int(value)
    elif dt in (DataType.Int64, DataType.UInt64, DataType.DateTime):
        m.long_value = int(value)
    elif dt == DataType.Float:
        m.float_value = float(value)
    elif dt == DataType.Double:
        m.double_value = float(value)
    elif dt == DataType.Boolean:
        m.boolean_value = bool(value)
    elif dt in (DataType.String, DataType.Text):
        m.string_value = str(value)
    elif dt == DataType.Bytes:
        m.bytes_value = bytes(value)
    else:
        raise TypeError(f"unhandled datatype {dt}")
    return m


def get_metric_value(metric: "sp.Payload.Metric") -> Any:
    """Extract a metric's Python value from its set oneof field."""
    which = metric.WhichOneof("value")
    if which is None:
        return None
    return getattr(metric, which)


def metrics_dict(payload: "sp.Payload") -> dict[str, Any]:
    """{name: value} for all named metrics (excludes the MAC metric)."""
    return {m.name: get_metric_value(m) for m in payload.metrics if m.name and m.name != MAC_METRIC}


def encode(payload: "sp.Payload") -> bytes:
    return payload.SerializeToString()


def decode(data: bytes) -> "sp.Payload":
    p = sp.Payload()
    p.ParseFromString(data)
    return p


# ---- HMAC-SHA-384 integrity (task AC) --------------------------------------------------------------

def mac_payload(payload: "sp.Payload", key: bytes) -> "sp.Payload":
    """Attach an HMAC-SHA-384 tag (as the MAC_METRIC) computed over the payload with the tag cleared. In place."""
    from crypto.hmac_sha384 import mac as hmac_mac
    _strip_mac(payload)
    tag = hmac_mac(key, payload.SerializeToString())
    add_metric(payload, MAC_METRIC, tag, datatype=DataType.Bytes)
    return payload


def verify_payload_mac(payload: "sp.Payload", key: bytes) -> bool:
    """Verify the MAC_METRIC tag. Returns False if absent or mismatched (constant-time compare)."""
    from crypto.hmac_sha384 import verify_mac
    tag = None
    for m in payload.metrics:
        if m.name == MAC_METRIC:
            tag = m.bytes_value
            break
    if tag is None:
        return False
    probe = sp.Payload()
    probe.CopyFrom(payload)
    _strip_mac(probe)
    return verify_mac(key, probe.SerializeToString(), tag)


def _strip_mac(payload: "sp.Payload") -> None:
    keep = [m for m in payload.metrics if m.name != MAC_METRIC]
    del payload.metrics[:]
    payload.metrics.extend(keep)


__all__ = ["DataType", "MAC_METRIC", "new_payload", "add_metric", "get_metric_value", "metrics_dict",
           "encode", "decode", "mac_payload", "verify_payload_mac", "sp"]
