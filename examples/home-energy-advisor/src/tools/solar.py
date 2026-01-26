"""Solar production estimation tool using NREL PVWatts API."""

import logging
import time

from langchain_core.tools import tool

from src.config import get_config
from src.core.models import SolarEstimate
from src.tools.mock import mock_solar_estimate

logger = logging.getLogger(__name__)


def _get_mode() -> str:
    """Get the current tools mode (live or mock)."""
    return get_config().tools_mode


def _call_pvwatts_api(
    lat: float, lon: float, system_capacity_kw: float, tilt: float, azimuth: float
) -> dict:
    """Call NREL PVWatts API."""
    import httpx

    config = get_config()
    api_key = config.settings.NREL_API_KEY
    endpoint = config.tools.get("solar", {}).get(
        "endpoint", "https://developer.nrel.gov/api/pvwatts/v8"
    )

    url = f"{endpoint}.json"
    params = {
        "api_key": api_key,
        "lat": lat,
        "lon": lon,
        "system_capacity": system_capacity_kw,
        "module_type": 0,
        "losses": 14,
        "array_type": 1,
        "tilt": tilt,
        "azimuth": azimuth,
    }

    response = httpx.get(url, params=params, timeout=15.0)
    response.raise_for_status()
    return response.json()


@tool
def get_solar_estimate(
    lat: float, lon: float, system_capacity_kw: float, tilt: float = 20.0, azimuth: float = 180.0
) -> str:
    """Estimate solar production for a PV system at a given location.

    Args:
        lat: Latitude
        lon: Longitude
        system_capacity_kw: System size in kW
        tilt: Panel tilt angle in degrees (default 20 for rooftop)
        azimuth: Panel orientation in degrees (180 = south-facing)

    Returns:
        JSON string with annual and monthly production estimates.
    """
    start = time.time()
    mode = _get_mode()

    if mode == "mock":
        logger.info("solar tool: using mock mode")
        result = mock_solar_estimate(
            lat=lat, lon=lon, system_capacity_kw=system_capacity_kw, tilt=tilt, azimuth=azimuth
        )
        return result.model_dump_json()

    # Live mode: call PVWatts API with fallback
    try:
        data = _call_pvwatts_api(lat, lon, system_capacity_kw, tilt, azimuth)
        outputs = data.get("outputs", {})

        monthly_kwh = outputs.get("ac_monthly", [0] * 12)
        annual_kwh = outputs.get("ac_annual", sum(monthly_kwh))
        solrad = outputs.get("solrad_annual", 0)
        capacity_factor = outputs.get("capacity_factor", 0) / 100 if outputs.get("capacity_factor") else None

        result = SolarEstimate(
            system_capacity_kw=system_capacity_kw,
            ac_annual_kwh=round(annual_kwh, 1),
            monthly_kwh=[round(m, 1) for m in monthly_kwh],
            solrad_annual=round(solrad, 2),
            capacity_factor=round(capacity_factor, 3) if capacity_factor else None,
            is_fallback=False,
        )

        elapsed = time.time() - start
        logger.info(f"solar tool: success in {elapsed:.2f}s")
        return result.model_dump_json()

    except Exception as e:
        elapsed = time.time() - start
        logger.warning(f"solar tool: API failed ({e}), using fallback. Elapsed: {elapsed:.2f}s")
        result = mock_solar_estimate(
            lat=lat, lon=lon, system_capacity_kw=system_capacity_kw, tilt=tilt, azimuth=azimuth
        )
        result.is_fallback = True
        return result.model_dump_json()
