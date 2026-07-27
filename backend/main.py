"""
FastAPI Main Application for AI Embodied Agent
Multi-Domain Manufacturing Optimization Platform
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import make_asgi_app

from config import settings
from api.routes import router as api_router
from services.state_manager import StateManager
from services.decision_engine import DecisionEngine
from pipeline.mqtt_listener import MQTTListener
from pipeline.video_processor import VideoProcessor
from pipeline.api_integrations import ExternalAPIClient

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Import centralized Prometheus metrics to avoid duplicate registration
from monitoring.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    ACTIVE_CONNECTIONS,
    DECISION_COUNT,
)

# Global instances
state_manager: StateManager | None = None
decision_engine: DecisionEngine | None = None
agent_runtime = None  # Stage 11: compiled LangGraph self-healing runtime (built in lifespan)
mcp_tool_mount = None  # Stage 11.5: persistent MCP tool mount (env-gated MCP_MOUNT=1; spawns 5 stdio servers)
cdc_listener = None    # Stage 13: CDC listener (drains cdc_outbox → SimWorld injects; None if no DATABASE_URL)
mqtt_listener: MQTTListener | None = None
video_processor: VideoProcessor | None = None
api_client: ExternalAPIClient | None = None
websocket_clients: set[WebSocket] = set()

# Stage 3 — WebSocket incident broker (Redis pub/sub fan-out of simulator incidents).
from services.ws_broker import ConnectionManager, SimulatorEventBroker
connection_manager = ConnectionManager()


async def broadcast_state_update(state: dict) -> None:
    """Broadcast state updates to all connected WebSocket clients."""
    if not websocket_clients:
        return
    
    disconnected = set()
    for client in websocket_clients:
        try:
            await client.send_json(state)
        except Exception as e:
            logger.warning("Failed to send to WebSocket client", error=str(e))
            disconnected.add(client)
    
    # Clean up disconnected clients
    websocket_clients.difference_update(disconnected)
    ACTIVE_CONNECTIONS.set(len(websocket_clients))


async def state_broadcast_loop() -> None:
    """Background task to broadcast state updates periodically."""
    global state_manager
    
    while True:
        try:
            if state_manager and websocket_clients:
                state = await state_manager.get_current_state()
                await broadcast_state_update({
                    "type": "state_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": state
                })
            await asyncio.sleep(settings.state_update_interval_ms / 1000)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in state broadcast loop", error=str(e))
            await asyncio.sleep(1)


async def decision_loop() -> None:
    """Background task to trigger periodic AI decisions."""
    global decision_engine, state_manager
    
    while True:
        try:
            if decision_engine and state_manager:
                state = await state_manager.get_current_state()
                decision = await decision_engine.make_decision(state)
                
                if decision:
                    # Broadcast decision to clients
                    await broadcast_state_update({
                        "type": "decision",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": decision
                    })
                    
                    # Update metrics
                    confidence_level = "high" if decision.get("confidence", 0) > 0.8 else "medium" if decision.get("confidence", 0) > 0.5 else "low"
                    DECISION_COUNT.labels(
                        decision_type=decision.get("decision_type", "unknown"),
                        confidence_level=confidence_level
                    ).inc()
                    
            await asyncio.sleep(settings.decision_interval_seconds)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in decision loop", error=str(e))
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown."""
    global state_manager, decision_engine, mqtt_listener, video_processor, api_client
    
    logger.info("Starting AI Embodied Agent", version=settings.app_version)

    # Stage 12.5: OpenTelemetry — TracerProvider + (env-gated) OTLP exporter + FastAPI auto-instrumentation. Honest:
    # with no OTEL_EXPORTER_OTLP_ENDPOINT, spans are created but not exported to a fake sink (KB_15 / research §21).
    try:
        from observability.otel_init import init as otel_init
        logger.info("OpenTelemetry initialized", backend=otel_init(app))
    except Exception as e:
        logger.warning("OpenTelemetry init failed; running without traces", error=str(e))

    # Initialize services
    state_manager = StateManager()
    await state_manager.initialize()
    
    decision_engine = DecisionEngine(state_manager)
    await decision_engine.initialize()

    # Stage 11: build the durable LangGraph self-healing runtime once (Postgres checkpointer if DATABASE_URL is
    # reachable, else in-memory — named honestly) and report the active tracers. The runtime consumes the real
    # depth-hardened models; `EmbodiedAgent.coordinate(incident)` delegates to it.
    global agent_runtime
    try:
        from agents.runtime.graph import build_runtime
        from agents.runtime.tracing import tracing_status
        agent_runtime, _cp_backend = build_runtime()
        logger.info("LangGraph self-healing runtime ready",
                    checkpointer=_cp_backend, tracing=tracing_status())
    except Exception as e:
        agent_runtime = None
        logger.warning("LangGraph runtime init failed; coordinate() will build per-call", error=str(e))

    # Stage 11.5: optionally mount the MCP tool servers (spawns 5 persistent stdio subprocesses). Env-gated so dev /
    # tests don't pay the subprocess cost unless asked. `app.state.mcp_tools` is the mounted StructuredTool surface.
    global mcp_tool_mount
    if os.environ.get("MCP_MOUNT") == "1":
        try:
            from agents.runtime.mcp_mount import MCPToolMount
            mcp_tool_mount = MCPToolMount()
            await mcp_tool_mount.__aenter__()
            app.state.mcp_tools = mcp_tool_mount.tools
            logger.info("MCP tool servers mounted", n_tools=len(mcp_tool_mount.tools),
                        tools=[t.name for t in mcp_tool_mount.tools])
        except Exception as e:
            mcp_tool_mount = None
            logger.warning("MCP mount failed; tools unavailable this run", error=str(e))

    # Pre-load reference user for face recognition
    try:
        from api.auth_routes import preload_reference_user
        await preload_reference_user()
    except Exception as e:
        logger.warning("Failed to preload reference user", error=str(e))
    
    api_client = ExternalAPIClient()
    await api_client.initialize()
    from simulation.sim_world import SimWorld
    from api.simulation_routes import set_sim_world
    from simulation.persistence import append_incident
    import redis.asyncio as aioredis

    # Redis client used to PUBLISH simulator incidents. The broker (below) holds
    # its own dedicated connection for the blocking pub/sub SUBSCRIBE.
    main_loop = asyncio.get_running_loop()
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    try:
        redis_client = aioredis.from_url(redis_url)
    except Exception as e:
        logger.warning("Redis client init failed; incident fan-out degraded", error=str(e))
        redis_client = None

    def _on_incident(incident) -> None:
        # Runs inside the SimPy worker thread; bridge to the main loop and
        # publish to Redis so the WebSocket broker can fan the incident out.
        try:
            payload = incident.to_payload()
            asyncio.run_coroutine_threadsafe(
                append_incident(payload, redis_client=redis_client),
                main_loop,
            )
        except Exception:
            logger.exception("on_incident publish bridge failed")

    sim_world = SimWorld(seed=getattr(settings, "sim_seed", 20260524), on_incident=_on_incident)
    sim_world.start()
    set_sim_world(sim_world)

    # Stage 13: CDC listener — DB writes (INSERT incidents / UPDATE stages.status) drain from the transactional
    # outbox into the live SimWorld (KB_05 §97). Started AFTER the world is bound so injects have a target; honest
    # no-op if no DATABASE_URL.
    global cdc_listener
    try:
        from ingestion.cdc_listener import CDCListener
        cdc_listener = CDCListener()
        started = await cdc_listener.start()
        logger.info("CDC listener", started=started)
        if not started:
            cdc_listener = None
    except Exception as e:
        cdc_listener = None
        logger.warning("CDC listener init failed", error=str(e))

    # Start the WebSocket incident broker: subscribes to pubsub:simulator:events
    # and fans each incident out to connected clients via connection_manager.
    event_broker = SimulatorEventBroker(connection_manager, redis_url=redis_url)
    await event_broker.start()

    
    # Initialize MQTT listener (if not in simulation mode)
    if not settings.simulation_mode:
        mqtt_listener = MQTTListener(state_manager)
        await mqtt_listener.start()
        
        video_processor = VideoProcessor(state_manager)
        await video_processor.start()
    else:
        logger.info("Running in simulation mode - MQTT and video processing disabled")
        # Start simulation data generation
        await state_manager.start_simulation()
    
    # Start background tasks
    broadcast_task = asyncio.create_task(state_broadcast_loop())
    decision_task = asyncio.create_task(decision_loop())
    
    logger.info("AI Embodied Agent started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Embodied Agent")
    if cdc_listener is not None:
        try:
            await cdc_listener.stop()  # bounded cancellation of the LISTEN loop + close conns
        except Exception:
            logger.warning("cdc_listener stop failed", exc_info=True)
    try:
        await event_broker.stop()
    except Exception:
        logger.warning("event_broker stop failed", exc_info=True)
    sim_world.stop()
    set_sim_world(None)
    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception:
            try:
                await redis_client.close()
            except Exception:
                pass

    
    # Cancel background tasks
    broadcast_task.cancel()
    decision_task.cancel()
    
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    
    try:
        await decision_task
    except asyncio.CancelledError:
        pass
    
    # Stop services
    if mqtt_listener:
        await mqtt_listener.stop()
    
    if video_processor:
        await video_processor.stop()

    if mcp_tool_mount is not None:
        try:
            await mcp_tool_mount.__aexit__(None, None, None)  # stops the 5 MCP stdio subprocesses
        except Exception:
            logger.warning("MCP mount close failed", exc_info=True)

    if api_client:
        try:
            await api_client.close()  # cancels the weather/carbon update loops
        except Exception:
            logger.warning("api_client close failed", exc_info=True)

    if state_manager:
        await state_manager.shutdown()
    
    # Close all WebSocket connections
    for client in websocket_clients:
        try:
            await client.close()
        except Exception:
            pass
    
    logger.info("AI Embodied Agent shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Embodied Agent for Multi-Domain Manufacturing Optimization",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API routes
app.include_router(api_router, prefix="/api")

# Include Simulation routes
from api.simulation_routes import router as simulation_router
app.include_router(simulation_router)

# Include Voice routes
from api.voice_routes import router as voice_router
app.include_router(voice_router)

# Include Metrics routes
from api.metrics_routes import router as metrics_router
app.include_router(metrics_router)

# Include Auth routes
from api.auth_routes import router as auth_router
app.include_router(auth_router)

# Include Inventory routes
from api.inventory_routes import router as inventory_router
app.include_router(inventory_router)

# Stage 14: A2A external federation surface — signed agent card (/.well-known/agent.json) + JSON-RPC 2.0 (/a2a/v1/rpc).
# Exposes only the deliberate capability subset (a2a/skills), NOT the internal MCP tools (KB_16 trust boundary).
from a2a.server import router as a2a_router
app.include_router(a2a_router)

# Stage 25 (G-021 + Art-72): live ops — decision-cascade/latency view + post-market posture, read from the REAL
# signed audit_chain only (never the legacy demo state path — G-082). Honest-503 when the DB is down.
from api.ops_routes import router as ops_router
app.include_router(ops_router)

# Stage 28 (adoption UX): behavioural-science layer (trust calibration + progressive autonomy + WIIFM) served
# from REAL data (GraphRAG grounding, the Stage-6/26 A/B, the safety/HITL ladder). Honest-empty, no fabrication.
from api.adoption_routes import router as adoption_router
app.include_router(adoption_router)

# Stage 29 — Conversational Factory Intelligence: ask-the-factory (G-022) + NL problem injection (G-023) + active
# diagnosis (G-026). Grounded in real evidence (decision traces / GraphRAG / live sim); Hard Rule 3 preserved on inject.
from api.conversation_routes import router as conversation_router
app.include_router(conversation_router)

# Stage 38 — Facilities / Energy head-agent (G-018): the KB_25 loop extended to industrial energy management —
# peak-shaving / load-shifting as a real MILP (HiGHS) over the sim's real per-stage nominal_kw, validator-gated
# (Hard Rule 3) + audit-signed (Art-12).
from api.facilities_routes import router as facilities_router
app.include_router(facilities_router)


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint for container orchestration."""
    global state_manager, decision_engine
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "components": {
            "state_manager": state_manager is not None,
            "decision_engine": decision_engine is not None,
            "mqtt_listener": mqtt_listener is not None or settings.simulation_mode,
            "video_processor": video_processor is not None or settings.simulation_mode,
        },
        "simulation_mode": settings.simulation_mode,
        "websocket_clients": len(websocket_clients)
    }
    
    # Check if any critical component is down
    if not all([state_manager, decision_engine]):
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/ready", tags=["Health"])
async def readiness_check() -> dict:
    """Readiness check for load balancer."""
    global state_manager, decision_engine
    
    is_ready = all([
        state_manager is not None,
        decision_engine is not None,
        state_manager.is_initialized if state_manager else False,
        decision_engine.is_initialized if decision_engine else False
    ])
    
    return {
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    websocket_clients.add(websocket)
    connection_manager.connect(websocket)  # Stage 3: receive simulator incident fan-out
    ACTIVE_CONNECTIONS.set(len(websocket_clients))
    
    logger.info("WebSocket client connected", total_clients=len(websocket_clients))
    
    try:
        # Send initial state
        if state_manager:
            initial_state = await state_manager.get_current_state()
            await websocket.send_json({
                "type": "initial_state",
                "timestamp": datetime.utcnow().isoformat(),
                "data": initial_state
            })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                
                # Handle client messages (e.g., override requests)
                if data.get("type") == "override":
                    if decision_engine:
                        result = await decision_engine.apply_override(data.get("override", {}))
                        await websocket.send_json({
                            "type": "override_result",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": result
                        })
                
                elif data.get("type") == "set_weights":
                    if decision_engine:
                        await decision_engine.set_optimization_weights(data.get("weights", {}))
                        await websocket.send_json({
                            "type": "weights_updated",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning("WebSocket message error", error=str(e))
                
    except WebSocketDisconnect:
        pass
    finally:
        websocket_clients.discard(websocket)
        connection_manager.disconnect(websocket)
        ACTIVE_CONNECTIONS.set(len(websocket_clients))
        logger.info("WebSocket client disconnected", total_clients=len(websocket_clients))


# Export for uvicorn
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers,
        log_level=settings.log_level.lower()
    )
