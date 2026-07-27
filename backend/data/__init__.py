"""Data ingestion and persistence module."""

from .realtime_ingestion import RealTimeDataAdapter, DataMode, get_data_adapter
from .supabase_service import SupabaseService, get_supabase_service

__all__ = [
    "RealTimeDataAdapter",
    "DataMode",
    "get_data_adapter",
    "SupabaseService",
    "get_supabase_service"
]
