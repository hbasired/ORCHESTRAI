"""
Prometheus Metrics Module

Centralized metrics registration to avoid duplicate registration errors.
Metrics are registered once at module import time.
"""

from prometheus_client import Counter, Histogram, Gauge, REGISTRY
import structlog

logger = structlog.get_logger(__name__)


def _get_or_create_counter(name: str, description: str, labels: list) -> Counter:
    """Get existing counter or create new one."""
    full_name = name + "_total"
    for collector in REGISTRY._names_to_collectors.values():
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    return Counter(name, description, labels)


def _get_or_create_histogram(name: str, description: str, labels: list = None) -> Histogram:
    """Get existing histogram or create new one."""
    for collector in REGISTRY._names_to_collectors.values():
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    if labels:
        return Histogram(name, description, labels)
    return Histogram(name, description)


def _get_or_create_gauge(name: str, description: str) -> Gauge:
    """Get existing gauge or create new one."""
    for collector in REGISTRY._names_to_collectors.values():
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    return Gauge(name, description)


# HTTP Request metrics
REQUEST_COUNT = _get_or_create_counter(
    "http_requests",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = _get_or_create_histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

# WebSocket metrics
ACTIVE_CONNECTIONS = _get_or_create_gauge(
    "websocket_connections_active",
    "Number of active WebSocket connections"
)

# AI Decision metrics
DECISION_COUNT = _get_or_create_counter(
    "ai_decisions",
    "Total AI decisions made",
    ["decision_type", "confidence_level"]
)

# Simulation metrics
SIMULATION_EVENTS = _get_or_create_counter(
    "simulation_events",
    "Simulation events by type",
    ["event_type", "domain", "severity"]
)

# Domain-specific metrics
ROBOT_COLLISIONS = _get_or_create_counter(
    "robot_collisions",
    "Total robot collisions",
    ["mode"]
)

PRODUCTION_BOTTLENECKS = _get_or_create_counter(
    "production_bottlenecks",
    "Production bottleneck events",
    ["stage", "mode"]
)

INVENTORY_STOCKOUTS = _get_or_create_counter(
    "inventory_stockouts",
    "Inventory stockout events",
    ["item", "mode"]
)

# Model metrics
MODEL_INFERENCE_TIME = _get_or_create_histogram(
    "model_inference_seconds",
    "ML model inference time",
    ["model_name", "model_type"]
)

logger.debug("Prometheus metrics module loaded")

