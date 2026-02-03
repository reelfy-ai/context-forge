"""Fixtures for simple trajectory tests.

These fixtures are minimal - just what you need to run evaluate_agent().
"""

from datetime import datetime, timedelta, timezone

import pytest
from langgraph.store.memory import InMemoryStore

from src.agents.advisor import build_advisor_graph
from src.core.models import Equipment, Household, Location, Preferences, UserProfile
from src.memory.helpers import save_profile_to_store


# ---------------------------------------------------------------------------
# Profile Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_profile() -> UserProfile:
    """A basic user profile for testing."""
    return UserProfile(
        user_id="test_user",
        equipment=Equipment(
            solar_capacity_kw=7.5,
            ev_model="Tesla Model 3",
            ev_battery_kwh=75.0,
            heating_type="heat_pump",
            cooling_type="central_ac",
        ),
        household=Household(
            occupants=2,
            work_schedule="Office 9-5",
            typical_usage_pattern="evening_heavy",
        ),
        location=Location(
            zip_code="94102",
            utility_provider="PG&E",
            rate_schedule="E-TOU-C",
        ),
        preferences=Preferences(
            comfort_priority="medium",
            budget_priority="high",
            green_priority="medium",
        ),
    )


@pytest.fixture
def stale_profile() -> UserProfile:
    """A profile with stale work_schedule (120 days old).

    This profile says "Office 9-5" but the user now works from home.
    Use this to test if the agent updates the profile when the user
    mentions their new work situation.
    """
    old_date = datetime.now(timezone.utc) - timedelta(days=120)

    return UserProfile(
        user_id="stale_user",
        equipment=Equipment(
            solar_capacity_kw=7.5,
            ev_model="Tesla Model 3",
            ev_battery_kwh=75.0,
        ),
        household=Household(
            occupants=2,
            work_schedule="Office 9-5",  # STALE - user is now WFH
            typical_usage_pattern="evening_heavy",
            updated_at=old_date,
        ),
        location=Location(
            zip_code="94102",
            utility_provider="PG&E",
            rate_schedule="E-TOU-C",
        ),
        preferences=Preferences(
            comfort_priority="medium",
            budget_priority="high",
            green_priority="medium",
        ),
    )


# ---------------------------------------------------------------------------
# Store Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store_with_profile(user_profile) -> InMemoryStore:
    """Store pre-populated with a user profile."""
    store = InMemoryStore()
    save_profile_to_store(store, user_profile)
    return store


@pytest.fixture
def store_with_stale_profile(stale_profile) -> InMemoryStore:
    """Store pre-populated with a stale profile."""
    store = InMemoryStore()
    save_profile_to_store(store, stale_profile)
    return store


# ---------------------------------------------------------------------------
# Graph Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def advisor_graph(store_with_profile):
    """Build the advisor graph with a pre-populated store."""
    return build_advisor_graph(store=store_with_profile)


@pytest.fixture
def advisor_graph_stale(store_with_stale_profile):
    """Build the advisor graph with a stale profile in store."""
    return build_advisor_graph(store=store_with_stale_profile)
