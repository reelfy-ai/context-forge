"""Weather forecast tool using OpenWeatherMap API."""

import logging
import time

from langchain_core.tools import tool

from src.config import get_config
from src.core.models import CurrentWeather, WeatherForecast, WeatherLocation
from src.tools.mock import mock_weather_forecast

logger = logging.getLogger(__name__)


def _get_mode() -> str:
    """Get the current tools mode (live or mock)."""
    return get_config().tools_mode


def _call_api(lat: float, lon: float) -> dict:
    """Call OpenWeatherMap current weather API."""
    import httpx

    config = get_config()
    api_key = config.settings.OPENWEATHER_API_KEY
    endpoint = config.tools.get("weather", {}).get(
        "endpoint", "https://api.openweathermap.org/data/2.5"
    )

    url = f"{endpoint}/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}

    response = httpx.get(url, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


@tool
def get_weather_forecast(lat: float, lon: float, days: int = 1) -> str:
    """Get weather forecast for a location including solar hours estimate.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        days: Number of days to forecast (1-5)

    Returns:
        JSON string with weather data including solar_hours estimate.
    """
    start = time.time()
    mode = _get_mode()

    if mode == "mock":
        logger.info("weather tool: using mock mode")
        result = mock_weather_forecast(lat=lat, lon=lon, days=days)
        return result.model_dump_json()

    # Live mode: call real API with fallback
    try:
        data = _call_api(lat, lon)
        cloud_cover = data.get("clouds", {}).get("all", 50)
        temp_c = data.get("main", {}).get("temp", 20)
        conditions = data.get("weather", [{}])[0].get("description", "unknown")
        solar_hours = round((1 - cloud_cover / 100) * 8.5, 1)

        result = WeatherForecast(
            location=WeatherLocation(lat=lat, lon=lon, city=data.get("name", "Unknown")),
            current=CurrentWeather(temp=temp_c, cloud_cover=cloud_cover, conditions=conditions),
            forecast=[],
            solar_hours=solar_hours,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            is_fallback=False,
        )

        elapsed = time.time() - start
        logger.info(f"weather tool: success in {elapsed:.2f}s")
        return result.model_dump_json()

    except Exception as e:
        elapsed = time.time() - start
        logger.warning(f"weather tool: API failed ({e}), using fallback. Elapsed: {elapsed:.2f}s")
        result = mock_weather_forecast(lat=lat, lon=lon, days=days)
        result.is_fallback = True
        return result.model_dump_json()
