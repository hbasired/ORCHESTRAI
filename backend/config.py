"""
Enhanced Configuration for AI Embodied Agent Platform
Version 2.0 - Multi-Domain with Knowledge Graph, LangChain, and Voice
"""

from functools import lru_cache
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # =========================================================================
    # APPLICATION
    # =========================================================================
    app_name: str = "AI Embodied Agent Platform"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # =========================================================================
    # SERVER
    # =========================================================================
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of workers")
    
    # =========================================================================
    # CORS
    # =========================================================================
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins"
    )
    
    # =========================================================================
    # NEO4J KNOWLEDGE GRAPH
    # =========================================================================
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4J Bolt URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4J username")
    # No default — must be supplied via env (NEO4J_PASSWORD). Hardcoded
    # default removed in Stage 1 (2026-05-11) secrets sweep.
    neo4j_password: str = Field(default="", description="Neo4J password — required, no default")
    
    # =========================================================================
    # REDIS
    # =========================================================================
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")
    
    # =========================================================================
    # DATABASE - SUPABASE
    # =========================================================================
    supabase_url: Optional[str] = Field(default=None, description="Supabase project URL")
    supabase_key: Optional[str] = Field(default=None, description="Supabase anon key")
    supabase_service_key: Optional[str] = Field(default=None, description="Supabase service key")
    database_url: Optional[str] = Field(default=None, description="PostgreSQL URL")
    
    # =========================================================================
    # LLM PROVIDERS
    # =========================================================================
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    
    default_llm_provider: Literal["groq", "gemini", "ollama"] = Field(
        default="groq",
        description="Default LLM provider"
    )
    default_llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Default LLM model"
    )
    
    # =========================================================================
    # VOICE INTERFACE (STT-LLM-TTS)
    # =========================================================================
    voice_enabled: bool = Field(default=True, description="Enable voice interface")
    whisper_model: str = Field(default="base", description="Whisper model size: tiny, base, small, medium, large")
    piper_voice: str = Field(default="en_US-lessac-medium", description="Piper TTS voice")
    piper_model_path: Optional[str] = Field(default="./models/piper", description="Piper TTS model path")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for Whisper API fallback")
    
    # =========================================================================
    # FIREBASE
    # =========================================================================
    firebase_credentials_path: Optional[str] = Field(
        default=None, 
        description="Path to Firebase service account JSON"
    )
    firebase_database_url: Optional[str] = Field(
        default=None,
        description="Firebase Realtime Database URL"
    )
    
    # =========================================================================
    # EXTERNAL APIs
    # =========================================================================
    openweather_api_key: Optional[str] = Field(default=None, description="OpenWeather API key")
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"
    
    # =========================================================================
    # MQTT
    # =========================================================================
    mqtt_broker_host: str = Field(default="localhost", description="MQTT broker host")
    mqtt_broker_port: int = Field(default=1883, description="MQTT broker port")
    mqtt_username: Optional[str] = Field(default=None, description="MQTT username")
    mqtt_password: Optional[str] = Field(default=None, description="MQTT password")
    
    # =========================================================================
    # VIDEO PROCESSING
    # =========================================================================
    video_source: str = Field(default="0", description="Video source")
    yolo_model_path: str = Field(default="yolov8n.pt", description="YOLO model path")
    yolo_confidence_threshold: float = Field(default=0.5, description="YOLO confidence")
    
    # =========================================================================
    # ML MODELS
    # =========================================================================
    world_model_path: Optional[str] = Field(default=None, description="LSTM world model path")
    rl_policy_path: Optional[str] = Field(default=None, description="PPO policy path")
    bert_model_path: Optional[str] = Field(default=None, description="BERT NLP model path")
    
    # =========================================================================
    # SIMULATION
    # =========================================================================
    simulation_mode: bool = Field(default=True, description="Run in simulation mode")
    simulation_speed: float = Field(default=1.0, description="Simulation speed multiplier")
    scenario_mode: Literal["problem", "solution"] = Field(
        default="problem",
        description="Simulation scenario mode"
    )
    mock_robot_count: int = Field(default=20, description="Number of simulated robots")
    mock_stage_count: int = Field(default=10, description="Number of simulated stages")
    
    # =========================================================================
    # OPTIMIZATION WEIGHTS
    # =========================================================================
    default_throughput_weight: float = Field(default=0.5)
    default_energy_weight: float = Field(default=0.2)
    default_carbon_weight: float = Field(default=0.2)
    default_quality_weight: float = Field(default=0.1)
    
    # =========================================================================
    # PERFORMANCE
    # =========================================================================
    inference_timeout_ms: int = Field(default=500)
    state_update_interval_ms: int = Field(default=100)
    decision_interval_seconds: int = Field(default=30)


class DomainConfig:
    """Configuration for domain-specific parameters."""
    
    # Robotics Domain
    class Robotics:
        MAX_ROBOTS: int = 50
        BATTERY_WARNING: float = 20.0
        BATTERY_CRITICAL: float = 10.0
        MAX_SPEED: float = 2.0  # m/s
        COLLISION_RADIUS: float = 0.5  # meters
        CHARGING_RATE: float = 0.5  # % per second
        DRAIN_RATE: float = 0.1  # % per meter
    
    # Manufacturing Domain
    class Manufacturing:
        MAX_STAGES: int = 100
        QUEUE_WARNING: int = 15
        QUEUE_CRITICAL: int = 25
        DEFECT_BASE_RATE: float = 0.02  # 2%
        ENERGY_PER_UNIT: float = 0.5  # kWh
    
    # Supply Chain Domain
    class SupplyChain:
        FORECAST_HORIZON_DAYS: int = 7
        REORDER_LEAD_TIME_DAYS: int = 3
        SAFETY_STOCK_DAYS: int = 5
        DEMAND_VARIANCE: float = 0.15  # 15% variance


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export for easy access
settings = get_settings()
