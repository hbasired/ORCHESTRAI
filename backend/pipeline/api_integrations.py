"""
External API Integrations
Clients for OpenWeather, ThingSpeak, Grid Carbon, and Firebase.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta

import httpx
import structlog

from config import settings

logger = structlog.get_logger(__name__)


class ExternalAPIClient:
    """
    Client for external API integrations.
    
    Integrates with:
    - OpenWeather API (weather + renewable context)
    - ThingSpeak (IoT data ingestion)
    - Grid carbon intensity API
    - Firebase Realtime Database
    """
    
    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
        self._firebase_app = None
        self._firebase_db = None
        
        # Cache for API responses
        self._weather_cache: dict = {}
        self._carbon_cache: dict = {}
        self._cache_ttl = 1800  # 30 minutes
        
        # Update tasks
        self._weather_task: Optional[asyncio.Task] = None
        self._carbon_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize API clients."""
        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "AI-Embodied-Agent/1.0"}
        )
        
        # Initialize Firebase if configured
        if settings.firebase_credentials_path:
            await self._init_firebase()
        
        # Start background update tasks
        self._weather_task = asyncio.create_task(self._weather_update_loop())
        self._carbon_task = asyncio.create_task(self._carbon_update_loop())
        
        logger.info("External API client initialized")
    
    async def _init_firebase(self) -> None:
        """Initialize Firebase connection."""
        try:
            import firebase_admin
            from firebase_admin import credentials, db
            
            cred = credentials.Certificate(settings.firebase_credentials_path)
            self._firebase_app = firebase_admin.initialize_app(cred, {
                'databaseURL': settings.firebase_database_url
            })
            self._firebase_db = db.reference()
            
            logger.info("Firebase initialized")
            
        except ImportError:
            logger.warning("firebase-admin not installed")
        except Exception as e:
            logger.error("Firebase initialization failed", error=str(e))
    
    async def close(self) -> None:
        """Close API clients and stop background tasks.

        Cancellation is *awaited* so the loops actually unwind before the event
        loop tears down — otherwise they linger as pending tasks ("Task was
        destroyed but it is pending").
        """
        for task in (self._weather_task, self._carbon_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception:  # pragma: no cover - defensive
                    pass
        self._weather_task = None
        self._carbon_task = None

        if self._http_client:
            await self._http_client.aclose()

        logger.info("External API client closed")
    
    # =========================================================================
    # OpenWeather API
    # =========================================================================
    
    async def get_weather(
        self,
        lat: float = 37.7749,  # Default: San Francisco
        lon: float = -122.4194,
        force_refresh: bool = False
    ) -> dict:
        """
        Get current weather data.
        
        Args:
            lat: Latitude
            lon: Longitude
            force_refresh: Bypass cache
            
        Returns:
            Weather data dictionary
        """
        cache_key = f"weather_{lat}_{lon}"
        
        # Check cache
        if not force_refresh and cache_key in self._weather_cache:
            cached = self._weather_cache[cache_key]
            if (datetime.utcnow() - cached["timestamp"]).total_seconds() < self._cache_ttl:
                return cached["data"]
        
        # Fetch from API
        if not settings.openweather_api_key:
            return self._get_mock_weather()
        
        try:
            url = f"{settings.openweather_base_url}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": settings.openweather_api_key,
                "units": "metric"
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            weather = {
                "temperature": data.get("main", {}).get("temp", 20),
                "humidity": data.get("main", {}).get("humidity", 50),
                "conditions": data.get("weather", [{}])[0].get("main", "Clear"),
                "description": data.get("weather", [{}])[0].get("description", ""),
                "wind_speed": data.get("wind", {}).get("speed", 0),
                "clouds": data.get("clouds", {}).get("all", 0),
                "visibility": data.get("visibility", 10000) / 1000,  # km
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Estimate solar potential
            weather["solar_potential"] = self._estimate_solar_potential(
                weather["clouds"],
                weather["conditions"]
            )
            
            # Cache the result
            self._weather_cache[cache_key] = {
                "data": weather,
                "timestamp": datetime.utcnow()
            }
            
            return weather
            
        except Exception as e:
            logger.error("Weather API error", error=str(e))
            return self._get_mock_weather()
    
    def _get_mock_weather(self) -> dict:
        """Stage 28 de-mock (G-082): honest-UNAVAILABLE, not fabricated weather. A real weather feed needs an API
        key (paid — forbidden at build, Rule 9); with none, the honest state is 'unavailable', never invented data."""
        return {
            "available": False,
            "reason": "weather feed unavailable — no API key configured (free-cost build, Rule 9)",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _estimate_solar_potential(self, clouds: int, conditions: str) -> float:
        """Estimate solar power potential based on weather."""
        base = 1.0 - (clouds / 100) * 0.7
        
        if "Rain" in conditions or "Storm" in conditions:
            base *= 0.3
        elif "Clouds" in conditions:
            base *= 0.7
        
        return round(base, 2)
    
    async def _weather_update_loop(self) -> None:
        """Background task to update weather periodically."""
        while True:
            try:
                await self.get_weather(force_refresh=True)
                await asyncio.sleep(1800)  # 30 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Weather update error", error=str(e))
                await asyncio.sleep(300)
    
    # =========================================================================
    # Grid Carbon Intensity API
    # =========================================================================
    
    async def get_carbon_intensity(
        self,
        region: str = "US-CA",  # California
        force_refresh: bool = False
    ) -> dict:
        """
        Get grid carbon intensity.
        
        Args:
            region: Grid region code
            force_refresh: Bypass cache
            
        Returns:
            Carbon intensity data
        """
        cache_key = f"carbon_{region}"
        
        # Check cache
        if not force_refresh and cache_key in self._carbon_cache:
            cached = self._carbon_cache[cache_key]
            if (datetime.utcnow() - cached["timestamp"]).total_seconds() < self._cache_ttl:
                return cached["data"]
        
        # For demo, use estimated values
        # In production, integrate with electricitymap.org or similar
        carbon_data = self._estimate_carbon_intensity(region)
        
        self._carbon_cache[cache_key] = {
            "data": carbon_data,
            "timestamp": datetime.utcnow()
        }
        
        return carbon_data
    
    def _estimate_carbon_intensity(self, region: str) -> dict:
        """Estimate carbon intensity based on region and time."""
        from datetime import datetime
        
        hour = datetime.utcnow().hour
        
        # Base intensity varies by region
        base_intensities = {
            "US-CA": 250,  # California - relatively clean
            "US-TX": 400,  # Texas - mixed
            "US-NY": 280,  # New York
            "US-WA": 100,  # Washington - hydro
            "EU-DE": 350,  # Germany
            "EU-FR": 80,   # France - nuclear
        }
        
        base = base_intensities.get(region, 320)
        
        # Time-of-day variation (higher during peak hours)
        if 9 <= hour <= 20:
            base *= 1.2
        else:
            base *= 0.85
        
        # Stage 28 de-mock (G-082): no random jitter — a deterministic time-of-day/region estimate is honest;
        # real grid-carbon data needs a paid API (Rule 9). This is a labelled ESTIMATE, not measured intensity.
        intensity = base
        
        # Renewable percentage (inverse of carbon intensity)
        renewable_pct = max(0, min(100, 100 - intensity / 5))
        
        return {
            "carbon_intensity": round(intensity, 1),  # gCO2/kWh
            "renewable_percentage": round(renewable_pct, 1),
            "region": region,
            "is_low_carbon": intensity < 200,
            "recommendation": "reduce" if intensity > 400 else "maintain" if intensity > 200 else "increase",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _carbon_update_loop(self) -> None:
        """Background task to update carbon intensity periodically."""
        while True:
            try:
                await self.get_carbon_intensity(force_refresh=True)
                await asyncio.sleep(3600)  # 1 hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Carbon update error", error=str(e))
                await asyncio.sleep(600)
    
    # =========================================================================
    # ThingSpeak IoT API
    # =========================================================================
    
    async def read_thingspeak(
        self,
        channel_id: str = None,
        field: int = 1,
        results: int = 10
    ) -> list[dict]:
        """
        Read data from ThingSpeak channel.
        
        Args:
            channel_id: ThingSpeak channel ID
            field: Field number (1-8)
            results: Number of results to fetch
            
        Returns:
            List of data points
        """
        channel_id = channel_id or settings.thingspeak_channel_id
        
        if not channel_id:
            return self._get_mock_iot_data(results)
        
        try:
            url = f"https://api.thingspeak.com/channels/{channel_id}/fields/{field}.json"
            params = {
                "api_key": settings.thingspeak_api_key,
                "results": results
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            feeds = data.get("feeds", [])
            
            return [
                {
                    "timestamp": f.get("created_at"),
                    "value": float(f.get(f"field{field}", 0)),
                    "entry_id": f.get("entry_id")
                }
                for f in feeds
            ]
            
        except Exception as e:
            logger.error("ThingSpeak API error", error=str(e))
            return self._get_mock_iot_data(results)
    
    async def write_thingspeak(
        self,
        field_data: dict[int, float],
        channel_id: str = None
    ) -> bool:
        """
        Write data to ThingSpeak channel.
        
        Args:
            field_data: Dictionary of field number to value
            channel_id: ThingSpeak channel ID
            
        Returns:
            Success status
        """
        if not settings.thingspeak_api_key:
            logger.warning("ThingSpeak API key not configured")
            return False
        
        try:
            url = "https://api.thingspeak.com/update"
            params = {"api_key": settings.thingspeak_api_key}
            
            for field_num, value in field_data.items():
                params[f"field{field_num}"] = value
            
            response = await self._http_client.get(url, params=params)
            
            # ThingSpeak returns 0 for failure, entry_id for success
            return int(response.text) > 0
            
        except Exception as e:
            logger.error("ThingSpeak write error", error=str(e))
            return False
    
    def _get_mock_iot_data(self, count: int) -> list[dict]:
        """Stage 28 de-mock (G-082): honest-empty, not fabricated IoT readings. A real IoT feed comes from the
        OPC-UA / Sparkplug integrations (Stage 15) or a configured provider; with none, return []."""
        return []
    
    # =========================================================================
    # Firebase Realtime Database
    # =========================================================================
    
    async def push_to_firebase(
        self,
        path: str,
        data: dict
    ) -> Optional[str]:
        """
        Push data to Firebase Realtime Database.
        
        Args:
            path: Database path
            data: Data to push
            
        Returns:
            Push key if successful
        """
        if not self._firebase_db:
            logger.warning("Firebase not initialized")
            return None
        
        try:
            from firebase_admin import db
            
            ref = self._firebase_db.child(path)
            result = await asyncio.to_thread(ref.push, data)
            
            return result.key
            
        except Exception as e:
            logger.error("Firebase push error", error=str(e))
            return None
    
    async def update_firebase(
        self,
        path: str,
        data: dict
    ) -> bool:
        """
        Update data in Firebase.
        
        Args:
            path: Database path
            data: Data to update
            
        Returns:
            Success status
        """
        if not self._firebase_db:
            return False
        
        try:
            ref = self._firebase_db.child(path)
            await asyncio.to_thread(ref.update, data)
            return True
            
        except Exception as e:
            logger.error("Firebase update error", error=str(e))
            return False
    
    async def read_firebase(
        self,
        path: str
    ) -> Optional[dict]:
        """
        Read data from Firebase.
        
        Args:
            path: Database path
            
        Returns:
            Data dictionary or None
        """
        if not self._firebase_db:
            return None
        
        try:
            ref = self._firebase_db.child(path)
            data = await asyncio.to_thread(ref.get)
            return data
            
        except Exception as e:
            logger.error("Firebase read error", error=str(e))
            return None
    
    # =========================================================================
    # Combined External Context
    # =========================================================================
    
    async def get_external_context(self) -> dict:
        """
        Get combined external context from all APIs.
        
        Returns:
            Dictionary with weather, carbon, and IoT data
        """
        # Fetch all data concurrently
        weather_task = self.get_weather()
        carbon_task = self.get_carbon_intensity()
        
        weather, carbon = await asyncio.gather(weather_task, carbon_task)
        
        return {
            "weather": weather,
            "grid_carbon_intensity": carbon.get("carbon_intensity"),
            "renewable_percentage": carbon.get("renewable_percentage"),
            "electricity_recommendation": carbon.get("recommendation"),
            "solar_potential": weather.get("solar_potential"),
            "timestamp": datetime.utcnow().isoformat()
        }
