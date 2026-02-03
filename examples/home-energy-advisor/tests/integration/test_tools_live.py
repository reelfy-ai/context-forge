"""Integration tests for tools with real API calls.

Tests each tool in live mode (not mock) to verify API connectivity
and response structure. Also includes an E2E test with the full
advisor using live tools.

Requires:
- Ollama running at localhost:11434 with llama3.2 pulled
- OPENWEATHER_API_KEY environment variable set
- NREL_API_KEY environment variable set

Skip if keys not available: tests auto-skip via markers.
"""

import json

import pytest

from .conftest import api_keys_available, model_required, ollama_required

pytestmark = [ollama_required, model_required, api_keys_available]


class TestLiveWeatherTool:
    """Tests for the weather tool with real OpenWeatherMap API."""

    def test_weather_returns_temperature(self, live_config):
        """Weather tool returns temperature data from real API."""
        from src.tools.weather import get_weather_forecast

        result = get_weather_forecast.invoke({"lat": 37.7749, "lon": -122.4194})
        data = json.loads(result)

        assert "current" in data
        assert "temp" in data["current"]
        assert isinstance(data["current"]["temp"], (int, float))
        assert data.get("is_fallback") is not True

    def test_weather_returns_conditions(self, live_config):
        """Weather tool returns condition description."""
        from src.tools.weather import get_weather_forecast

        result = get_weather_forecast.invoke({"lat": 37.7749, "lon": -122.4194})
        data = json.loads(result)

        assert "current" in data
        assert "conditions" in data["current"]
        assert len(data["current"]["conditions"]) > 0


class TestLiveRatesTool:
    """Tests for the rates tool with real rate data."""

    def test_rates_returns_periods(self, live_config):
        """Rates tool returns TOU period information."""
        from src.tools.rates import get_utility_rates

        result = get_utility_rates.invoke({
            "utility": "PG&E",
            "rate_schedule": "E-TOU-C",
        })
        data = json.loads(result)

        assert "periods" in data
        assert len(data["periods"]) > 0
        assert data.get("is_fallback") is not True

    def test_rates_include_prices(self, live_config):
        """Each rate period has a rate."""
        from src.tools.rates import get_utility_rates

        result = get_utility_rates.invoke({
            "utility": "PG&E",
            "rate_schedule": "E-TOU-C",
        })
        data = json.loads(result)

        for period in data["periods"]:
            assert "rate_kwh" in period
            assert period["rate_kwh"] > 0


class TestLiveSolarTool:
    """Tests for the solar tool with real NREL PVWatts API."""

    def test_solar_returns_annual_kwh(self, live_config):
        """Solar tool returns annual production estimate."""
        from src.tools.solar import get_solar_estimate

        result = get_solar_estimate.invoke({
            "lat": 37.7749,
            "lon": -122.4194,
            "system_capacity_kw": 7.5,
        })
        data = json.loads(result)

        assert "ac_annual_kwh" in data
        assert data["ac_annual_kwh"] > 0
        assert data.get("is_fallback") is not True

    def test_solar_scales_with_capacity(self, live_config):
        """Larger systems produce more energy."""
        from src.tools.solar import get_solar_estimate

        small = json.loads(get_solar_estimate.invoke({
            "lat": 37.7749, "lon": -122.4194, "system_capacity_kw": 5.0,
        }))
        large = json.loads(get_solar_estimate.invoke({
            "lat": 37.7749, "lon": -122.4194, "system_capacity_kw": 10.0,
        }))

        assert large["ac_annual_kwh"] > small["ac_annual_kwh"]


class TestLiveAdvisorFlow:
    """E2E test with the full advisor using live tools (real APIs)."""

    def test_ev_charging_with_live_tools(self, live_config, demo_profile):
        """Full advisor flow with live tool calls produces a response."""
        from langgraph.store.memory import InMemoryStore

        from src.agents.advisor import build_advisor_graph

        store = InMemoryStore()
        graph = build_advisor_graph(store=store)
        result = graph.invoke({
            "user_id": "live_test_user",
            "session_id": "live_e2e_session",
            "message": "When should I charge my EV tonight to minimize cost?",
            "messages": [],
            "turn_count": 0,
            "user_profile": demo_profile,
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "should_memorize": False,
        })

        assert result["response"] is not None
        assert len(result["response"]) > 20
        # Verify tools were called with real data (not fallback)
        for obs in result.get("tool_observations", []):
            data = json.loads(obs["result"])
            assert data.get("is_fallback") is not True
