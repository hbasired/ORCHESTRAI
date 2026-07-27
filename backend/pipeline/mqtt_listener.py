"""
MQTT Listener for Factory Sensor Telemetry
Subscribes to robot and stage telemetry topics.
"""

import asyncio
import json
from typing import Optional, Callable
from datetime import datetime

import structlog

from config import settings

logger = structlog.get_logger(__name__)


class MQTTListener:
    """
    MQTT client for receiving factory sensor telemetry.
    
    Topics:
    - factory/robots/{robot_id}/telemetry (10Hz)
    - factory/stages/{stage_id}/metrics (1Hz)
    - factory/system/alerts
    """
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.client = None
        self.is_running = False
        
        # Configuration
        self.broker_host = settings.mqtt_broker_host
        self.broker_port = settings.mqtt_broker_port
        self.username = settings.mqtt_username
        self.password = settings.mqtt_password
        self.client_id = settings.mqtt_client_id
        
        # Topics
        self.topics = [
            ("factory/robots/+/telemetry", 1),
            ("factory/stages/+/metrics", 1),
            ("factory/system/alerts", 2)
        ]
        
        # Message handlers
        self._handlers: dict[str, Callable] = {}
        self._message_count = 0
        
        # Buffer for batch processing
        self._robot_buffer: dict[int, dict] = {}
        self._stage_buffer: dict[int, dict] = {}
        self._buffer_flush_interval = 0.5  # seconds
    
    async def start(self) -> None:
        """Start the MQTT listener."""
        try:
            import paho.mqtt.client as mqtt
            
            # Create client
            self.client = mqtt.Client(
                client_id=self.client_id,
                protocol=mqtt.MQTTv311
            )
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            # Authentication if configured
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Connect
            logger.info("Connecting to MQTT broker", host=self.broker_host, port=self.broker_port)
            
            try:
                self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            except Exception as e:
                logger.warning("MQTT broker not available, running without telemetry", error=str(e))
                return
            
            # Start network loop in background
            self.client.loop_start()
            self.is_running = True
            
            # Start buffer flush task
            asyncio.create_task(self._buffer_flush_loop())
            
            logger.info("MQTT listener started")
            
        except ImportError:
            logger.warning("paho-mqtt not installed, MQTT listener disabled")
        except Exception as e:
            logger.error("Failed to start MQTT listener", error=str(e))
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            
            # Subscribe to topics
            for topic, qos in self.topics:
                client.subscribe(topic, qos)
                logger.info("Subscribed to topic", topic=topic)
        else:
            logger.error("MQTT connection failed", rc=rc)
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received."""
        try:
            self._message_count += 1
            
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Route message based on topic
            if "/robots/" in topic:
                self._handle_robot_telemetry(topic, payload)
            elif "/stages/" in topic:
                self._handle_stage_metrics(topic, payload)
            elif "/alerts" in topic:
                self._handle_alert(payload)
            
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in MQTT message", topic=msg.topic, error=str(e))
        except Exception as e:
            logger.error("Error handling MQTT message", error=str(e))
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker."""
        if rc != 0:
            logger.warning("Unexpected MQTT disconnect", rc=rc)
            # Attempt reconnection
            asyncio.create_task(self._reconnect())
    
    async def _reconnect(self):
        """Attempt to reconnect to the broker."""
        if not self.is_running:
            return
        
        backoff = 1
        max_backoff = 60
        
        while self.is_running:
            try:
                logger.info("Attempting MQTT reconnection", backoff=backoff)
                self.client.reconnect()
                return
            except Exception as e:
                logger.warning("Reconnection failed", error=str(e))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
    
    def _handle_robot_telemetry(self, topic: str, payload: dict):
        """Handle robot telemetry message."""
        # Extract robot ID from topic: factory/robots/{id}/telemetry
        parts = topic.split("/")
        try:
            robot_id = int(parts[2])
        except (IndexError, ValueError):
            logger.warning("Invalid robot topic", topic=topic)
            return
        
        # Buffer the update
        self._robot_buffer[robot_id] = {
            "id": robot_id,
            "position": payload.get("position", {"x": 0, "y": 0}),
            "battery": payload.get("battery", 100),
            "speed": payload.get("speed", 0),
            "task": payload.get("task"),
            "status": payload.get("status", "idle"),
            "task_queue_length": payload.get("queue_length", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _handle_stage_metrics(self, topic: str, payload: dict):
        """Handle stage metrics message."""
        # Extract stage ID from topic: factory/stages/{id}/metrics
        parts = topic.split("/")
        try:
            stage_id = int(parts[2])
        except (IndexError, ValueError):
            logger.warning("Invalid stage topic", topic=topic)
            return
        
        # Buffer the update
        self._stage_buffer[stage_id] = {
            "id": stage_id,
            "queue_depth": payload.get("queue_depth", 0),
            "throughput": payload.get("throughput", 0),
            "cycle_time": payload.get("cycle_time", 0),
            "defect_rate": payload.get("defect_rate", 0),
            "energy_consumption": payload.get("energy", 0),
            "status": payload.get("status", "normal"),
            "utilization": payload.get("utilization", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _handle_alert(self, payload: dict):
        """Handle system alert message."""
        logger.info("Received alert", alert=payload)
        # Would add to state manager's alert list
    
    async def _buffer_flush_loop(self):
        """Periodically flush buffered updates to state manager."""
        while self.is_running:
            try:
                # Flush robot updates
                for robot_id, data in self._robot_buffer.items():
                    await self.state_manager.update_robot_state(robot_id, data)
                self._robot_buffer.clear()
                
                # Flush stage updates
                for stage_id, data in self._stage_buffer.items():
                    await self.state_manager.update_stage_state(stage_id, data)
                self._stage_buffer.clear()
                
                await asyncio.sleep(self._buffer_flush_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Buffer flush error", error=str(e))
                await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop the MQTT listener."""
        self.is_running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        
        logger.info("MQTT listener stopped", messages_received=self._message_count)
    
    def register_handler(self, topic_pattern: str, handler: Callable) -> None:
        """Register a custom message handler for a topic pattern."""
        self._handlers[topic_pattern] = handler
    
    @property
    def stats(self) -> dict:
        """Get listener statistics."""
        return {
            "is_running": self.is_running,
            "broker_host": self.broker_host,
            "broker_port": self.broker_port,
            "messages_received": self._message_count,
            "buffered_robots": len(self._robot_buffer),
            "buffered_stages": len(self._stage_buffer)
        }
