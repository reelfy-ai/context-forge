# API Contract: Tools

**Feature**: 001-langgraph-agent | **Date**: 2026-01-21

## Overview

This document defines the tool function signatures for the Home Energy Advisor agent. Tools use the `@tool` decorator from `langchain_core.tools` and are passed directly to `create_agent()` from `langchain.agents` (LangGraph v1). The `@tool` decorator provides both the JSON schema for LLM tool binding and automatic trace capture via `LangGraphInstrumentor`.

---

## Weather Tool

### `get_weather_forecast`

Retrieves weather forecast including cloud cover for solar estimation.

```python
@tool
async def get_weather_forecast(
    lat: float,
    lon: float,
    days: int = 1
) -> WeatherForecast:
    """
    Get weather forecast for a location.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        days: Number of days to forecast (1-5)

    Returns:
        WeatherForecast with current conditions, forecast, and solar hours estimate

    Raises:
        ToolError: If API call fails or rate limited
    """
```

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "lat": {"type": "number", "minimum": -90, "maximum": 90},
    "lon": {"type": "number", "minimum": -180, "maximum": 180},
    "days": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1}
  },
  "required": ["lat", "lon"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "location": {
      "type": "object",
      "properties": {
        "lat": {"type": "number"},
        "lon": {"type": "number"},
        "city": {"type": "string"}
      }
    },
    "current": {
      "type": "object",
      "properties": {
        "temp": {"type": "number"},
        "cloud_cover": {"type": "integer", "minimum": 0, "maximum": 100},
        "conditions": {"type": "string"}
      }
    },
    "forecast": {
      "type": "array",
      "items": {"type": "object"}
    },
    "solar_hours": {"type": "number"},
    "timestamp": {"type": "string", "format": "date-time"}
  }
}
```

**Mock Response**:
```json
{
  "location": {"lat": 37.7749, "lon": -122.4194, "city": "San Francisco"},
  "current": {"temp": 18.5, "cloud_cover": 20, "conditions": "partly cloudy"},
  "forecast": [...],
  "solar_hours": 6.5,
  "timestamp": "2026-01-21T10:00:00Z"
}
```

---

## Utility Rates Tool

### `get_utility_rates`

Retrieves time-of-use electricity rates for a utility/schedule.

```python
@tool
async def get_utility_rates(
    utility: str,
    schedule: str | None = None
) -> RateSchedule:
    """
    Get electricity rate schedule for a utility.

    Args:
        utility: Utility provider name (e.g., "PG&E", "SCE", "SDG&E")
        schedule: Specific rate schedule (e.g., "EV-TOU-5"). If None, returns default residential.

    Returns:
        RateSchedule with TOU periods and rates

    Raises:
        ToolError: If utility not found or API fails
    """
```

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "utility": {"type": "string"},
    "schedule": {"type": "string", "nullable": true}
  },
  "required": ["utility"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "utility_name": {"type": "string"},
    "schedule_name": {"type": "string"},
    "periods": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string", "enum": ["off_peak", "peak", "partial_peak"]},
          "start_hour": {"type": "integer", "minimum": 0, "maximum": 23},
          "end_hour": {"type": "integer", "minimum": 0, "maximum": 23},
          "rate_kwh": {"type": "number"},
          "days": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "effective_date": {"type": "string", "format": "date"}
  }
}
```

**Mock Response (PG&E EV-TOU-5)**:
```json
{
  "utility_name": "PG&E",
  "schedule_name": "EV-TOU-5",
  "periods": [
    {
      "name": "off_peak",
      "start_hour": 21,
      "end_hour": 9,
      "rate_kwh": 0.18,
      "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    },
    {
      "name": "peak",
      "start_hour": 16,
      "end_hour": 21,
      "rate_kwh": 0.45,
      "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]
    },
    {
      "name": "partial_peak",
      "start_hour": 9,
      "end_hour": 16,
      "rate_kwh": 0.28,
      "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]
    }
  ],
  "effective_date": "2026-01-01"
}
```

---

## Solar Estimation Tool

### `get_solar_estimate`

Calculates expected solar production using NREL PVWatts.

```python
@tool
async def get_solar_estimate(
    lat: float,
    lon: float,
    system_capacity_kw: float,
    tilt: float = 20.0,
    azimuth: float = 180.0
) -> SolarEstimate:
    """
    Estimate solar production for a PV system.

    Args:
        lat: Latitude
        lon: Longitude
        system_capacity_kw: System size in kW
        tilt: Panel tilt angle (default 20 for rooftop)
        azimuth: Panel orientation (180 = south-facing)

    Returns:
        SolarEstimate with annual and monthly production

    Raises:
        ToolError: If API fails or invalid parameters
    """
```

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "lat": {"type": "number", "minimum": -90, "maximum": 90},
    "lon": {"type": "number", "minimum": -180, "maximum": 180},
    "system_capacity_kw": {"type": "number", "minimum": 0.1, "maximum": 100},
    "tilt": {"type": "number", "minimum": 0, "maximum": 90, "default": 20},
    "azimuth": {"type": "number", "minimum": 0, "maximum": 360, "default": 180}
  },
  "required": ["lat", "lon", "system_capacity_kw"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "system_capacity_kw": {"type": "number"},
    "ac_annual_kwh": {"type": "number"},
    "monthly_kwh": {
      "type": "array",
      "items": {"type": "number"},
      "minItems": 12,
      "maxItems": 12
    },
    "solrad_annual": {"type": "number"},
    "capacity_factor": {"type": "number"}
  }
}
```

**Mock Response (6kW system in SF)**:
```json
{
  "system_capacity_kw": 6.0,
  "ac_annual_kwh": 8547.0,
  "monthly_kwh": [520, 580, 720, 780, 850, 900, 920, 880, 760, 640, 510, 487],
  "solrad_annual": 5.2,
  "capacity_factor": 0.163
}
```

---

## Tool Registration

All tools are passed to `create_agent()` which handles LLM tool binding internally:

```python
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

# @tool-decorated functions (defined in src/tools/)
tools = [
    get_weather_forecast,
    get_utility_rates,
    get_solar_estimate,
]

# create_agent handles tool binding, ReAct loop, and trace capture
analyzer = create_agent(
    model=ChatOllama(model="llama3.1:8b", temperature=0.3),
    tools=tools,
    system_prompt="You are an energy data analyst...",
    name="analyzer",
)
```

**Note**: No manual `llm.bind_tools()` call is needed — `create_agent()` handles this internally. The `@tool` decorator provides the JSON schema that the LLM uses for structured tool calling.

---

## Error Handling

All tools follow a consistent error pattern:

```python
class ToolError(Exception):
    """Base exception for tool errors."""
    def __init__(self, tool_name: str, message: str, retry_after: int | None = None):
        self.tool_name = tool_name
        self.message = message
        self.retry_after = retry_after  # Seconds, if rate limited

# Usage
try:
    result = await get_weather_forecast(lat, lon)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        raise ToolError("get_weather_forecast", "Rate limited", retry_after=60)
    raise ToolError("get_weather_forecast", f"API error: {e.response.status_code}")
```

---

## Mock Mode

For testing and offline demos, all tools support a mock mode:

```python
# config.py
class Settings(BaseSettings):
    USE_MOCK_TOOLS: bool = False  # Set via env: USE_MOCK_TOOLS=true

# In each tool
async def get_weather_forecast(lat: float, lon: float, days: int = 1) -> WeatherForecast:
    if settings.USE_MOCK_TOOLS:
        return _mock_weather_forecast(lat, lon, days)
    # ... real implementation
```