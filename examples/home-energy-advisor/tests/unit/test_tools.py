"""Tests for tool implementations (weather, rates, solar)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.mock import mock_solar_estimate, mock_utility_rates, mock_weather_forecast


class TestMockTools:
    """Tests for mock tool implementations."""

    def test_mock_weather_returns_valid_structure(self):
        """Mock weather has required fields."""
        result = mock_weather_forecast(lat=37.7749, lon=-122.4194)
        assert result.location is not None
        assert result.current is not None
        assert result.forecast is not None
        assert result.solar_hours is not None
        assert result.location.lat == 37.7749
        assert 0 <= result.current.cloud_cover <= 100
        assert result.solar_hours > 0

    def test_mock_weather_multi_day(self):
        """Mock weather returns multiple forecast days."""
        result = mock_weather_forecast(days=3)
        assert len(result.forecast) == 3

    def test_mock_rates_pge(self):
        """Mock rates returns PG&E E-TOU-C data."""
        result = mock_utility_rates(utility="PG&E", schedule="E-TOU-C")
        assert result.utility_name == "PG&E"
        assert result.schedule_name == "E-TOU-C"
        assert len(result.periods) >= 2
        # Check peak is more expensive than off-peak
        rates = {p.name: p.rate_kwh for p in result.periods}
        assert rates["peak"] > rates["off_peak"]

    def test_mock_rates_sce(self):
        """Mock rates returns SCE data."""
        result = mock_utility_rates(utility="SCE", schedule="TOU-D-PRIME")
        assert result.utility_name == "SCE"

    def test_mock_rates_ev_schedule(self):
        """Mock rates returns EV-specific schedule."""
        result = mock_utility_rates(utility="PG&E", schedule="EV-TOU-5")
        assert result.schedule_name == "EV-TOU-5"
        rates = {p.name: p.rate_kwh for p in result.periods}
        assert rates["off_peak"] < rates["peak"]

    def test_mock_rates_unknown_utility_fallback(self):
        """Mock rates returns default for unknown utility."""
        result = mock_utility_rates(utility="Unknown Electric Co")
        assert result.utility_name == "PG&E"  # fallback

    def test_mock_solar_estimate_valid(self):
        """Mock solar returns valid production estimate."""
        result = mock_solar_estimate(system_capacity_kw=7.5)
        assert result.system_capacity_kw == 7.5
        assert result.ac_annual_kwh > 0
        assert len(result.monthly_kwh) == 12
        assert result.solrad_annual > 0
        assert 0 < result.capacity_factor < 1

    def test_mock_solar_scales_with_capacity(self):
        """Larger systems produce proportionally more energy."""
        small = mock_solar_estimate(system_capacity_kw=3.0)
        large = mock_solar_estimate(system_capacity_kw=9.0)
        assert large.ac_annual_kwh > small.ac_annual_kwh


class TestToolFunctions:
    """Tests for the actual @tool decorated functions."""

    @patch("src.tools.weather._call_api")
    def test_weather_tool_mock_mode(self, mock_api):
        """Weather tool uses mock data in mock mode."""
        from src.tools.weather import get_weather_forecast

        with patch("src.tools.weather._get_mode", return_value="mock"):
            result = get_weather_forecast.invoke({"lat": 37.7749, "lon": -122.4194, "days": 1})

        data = json.loads(result)
        assert "location" in data
        assert "solar_hours" in data
        mock_api.assert_not_called()

    @patch("src.tools.rates._get_mode", return_value="mock")
    def test_rates_tool_mock_mode(self, mock_mode):
        """Rates tool uses mock data in mock mode."""
        from src.tools.rates import get_utility_rates

        result = get_utility_rates.invoke({"utility": "PG&E", "schedule": "E-TOU-C"})
        data = json.loads(result)
        assert data["utility_name"] == "PG&E"
        assert len(data["periods"]) >= 2

    @patch("src.tools.solar._get_mode", return_value="mock")
    def test_solar_tool_mock_mode(self, mock_mode):
        """Solar tool uses mock data in mock mode."""
        from src.tools.solar import get_solar_estimate

        result = get_solar_estimate.invoke({"lat": 37.7749, "lon": -122.4194, "system_capacity_kw": 7.5})
        data = json.loads(result)
        assert data["system_capacity_kw"] == 7.5
        assert data["ac_annual_kwh"] > 0

    @patch("src.tools.weather._call_api")
    def test_weather_tool_live_mode(self, mock_api):
        """Weather tool calls real API in live mode."""
        from src.tools.weather import get_weather_forecast

        mock_api.return_value = {
            "coord": {"lat": 37.77, "lon": -122.42},
            "main": {"temp": 290},
            "clouds": {"all": 30},
            "weather": [{"description": "scattered clouds"}],
        }

        with patch("src.tools.weather._get_mode", return_value="live"):
            result = get_weather_forecast.invoke({"lat": 37.7749, "lon": -122.4194, "days": 1})

        data = json.loads(result)
        assert "location" in data
        mock_api.assert_called_once()

    @patch("src.tools.weather._call_api")
    def test_weather_tool_api_failure_fallback(self, mock_api):
        """Weather tool falls back to mock on API error."""
        from src.tools.weather import get_weather_forecast

        mock_api.side_effect = Exception("API timeout")

        with patch("src.tools.weather._get_mode", return_value="live"):
            result = get_weather_forecast.invoke({"lat": 37.7749, "lon": -122.4194, "days": 1})

        data = json.loads(result)
        assert data["is_fallback"] is True
        assert "solar_hours" in data
