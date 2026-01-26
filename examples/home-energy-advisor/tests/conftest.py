"""Shared test fixtures for the Home Energy Advisor."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.store.memory import InMemoryStore

from src.config import reset_config
from src.core.models import (
    Equipment,
    ExtractedFact,
    Household,
    Location,
    Preferences,
    RatePeriod,
    RateSchedule,
    RetrievedDocument,
    SolarEstimate,
    UserProfile,
    WeatherForecast,
)
from src.core.state import AdvisorState


@pytest.fixture(autouse=True)
def _reset_config():
    """Reset config singleton between tests."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def mock_profile() -> UserProfile:
    """A complete user profile for testing."""
    return UserProfile(
        user_id="test_user_123",
        equipment=Equipment(
            solar_capacity_kw=7.5,
            ev_model="Tesla Model 3",
            ev_battery_kwh=75.0,
            has_battery_storage=True,
            battery_capacity_kwh=13.5,
            heating_type="heat_pump",
            cooling_type="mini_split",
            updated_at=datetime(2024, 6, 15, 10, 0, 0),
        ),
        preferences=Preferences(
            budget_priority="high",
            comfort_priority="medium",
            green_priority="high",
            updated_at=datetime(2024, 6, 15, 10, 0, 0),
        ),
        household=Household(
            work_schedule="9-5 weekdays",
            occupants=4,
            typical_usage_pattern="evening_heavy",
            updated_at=datetime(2024, 6, 15, 10, 0, 0),
        ),
        location=Location(
            lat=37.7749,
            lon=-122.4194,
            zip_code="94102",
            utility_provider="PG&E",
            rate_schedule="E-TOU-C",
        ),
        created_at=datetime(2024, 1, 1, 0, 0, 0),
        updated_at=datetime(2024, 6, 15, 10, 0, 0),
    )


@pytest.fixture
def mock_weather_response() -> dict:
    """Mock weather forecast data as returned by the weather tool."""
    return {
        "location": {"lat": 37.7749, "lon": -122.4194},
        "current": {"temp_f": 72, "cloud_cover": 25, "description": "partly cloudy"},
        "forecast": [
            {"date": "2024-07-01", "high_f": 78, "low_f": 58, "cloud_cover": 20},
            {"date": "2024-07-02", "high_f": 75, "low_f": 56, "cloud_cover": 40},
        ],
        "solar_hours": 6.5,
        "timestamp": "2024-07-01T10:00:00",
    }


@pytest.fixture
def mock_rate_response() -> dict:
    """Mock utility rate data."""
    return {
        "utility_name": "PG&E",
        "schedule_name": "E-TOU-C",
        "periods": [
            {
                "name": "off_peak",
                "start_hour": 0,
                "end_hour": 16,
                "rate_kwh": 0.30,
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            },
            {
                "name": "peak",
                "start_hour": 16,
                "end_hour": 21,
                "rate_kwh": 0.49,
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            },
            {
                "name": "off_peak",
                "start_hour": 21,
                "end_hour": 0,
                "rate_kwh": 0.30,
                "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            },
        ],
        "effective_date": "2024-01-01",
    }


@pytest.fixture
def mock_solar_response() -> dict:
    """Mock solar estimate data."""
    return {
        "system_capacity_kw": 7.5,
        "ac_annual_kwh": 11250.0,
        "monthly_kwh": [750, 800, 950, 1000, 1100, 1150, 1100, 1050, 950, 850, 750, 700],
        "solrad_annual": 5.5,
        "capacity_factor": 0.17,
    }


@pytest.fixture
def initial_advisor_state(mock_profile) -> AdvisorState:
    """A pre-populated AdvisorState for integration tests."""
    return AdvisorState(
        user_id="test_user_123",
        session_id="session_001",
        message="When should I charge my EV tonight?",
        messages=[HumanMessage(content="When should I charge my EV tonight?")],
        turn_count=1,
        user_profile=mock_profile,
        weather_data=None,
        rate_data=None,
        solar_estimate=None,
        retrieved_docs=[],
        tool_observations=[],
        response=None,
        extracted_facts=[],
        should_memorize=False,
    )


@pytest.fixture
def mock_llm_response():
    """Factory for mock LLM responses."""
    def _make(content: str) -> AIMessage:
        return AIMessage(content=content)
    return _make


@pytest.fixture
def mock_llm():
    """Mock ChatOllama that returns configurable responses."""
    llm = MagicMock()
    llm.invoke = MagicMock(return_value=AIMessage(content="Based on your PG&E E-TOU-C rate schedule, charge your EV after 9 PM for the lowest off-peak rate of $0.30/kWh."))
    llm.bind_tools = MagicMock(return_value=llm)
    return llm


@pytest.fixture
def memory_store():
    """Fresh InMemoryStore for each test."""
    return InMemoryStore()


@pytest.fixture
def memory_store_with_profile(memory_store, mock_profile):
    """InMemoryStore pre-populated with mock_profile."""
    from src.memory.helpers import save_profile_to_store
    save_profile_to_store(memory_store, mock_profile)
    return memory_store
