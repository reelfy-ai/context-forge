"""Fixtures for multi-turn simulation tests (Level 3).

These fixtures provide the full simulation infrastructure:
- Personas and Scenarios for multi-turn conversations
- LangGraphAdapter for bridging agent and simulator
- SimulationRunner for orchestrating conversations
- Pre-configured stores with stale profiles

For simpler fixtures, see tests/trajectories/simple/conftest.py
"""

from datetime import datetime, timedelta, timezone

import pytest
from langgraph.store.memory import InMemoryStore

from context_forge.harness.user_simulator import (
    GenerativeScenario,
    LangGraphAdapter,
    Persona,
    SimulationRunner,
)
from context_forge.instrumentation import LangGraphInstrumentor

from src.agents.advisor import build_advisor_graph
from src.core.models import Equipment, Household, Location, Preferences, UserProfile
from src.memory.helpers import save_profile_to_store

from .scenarios import (
    stale_work_schedule_scenario,
    stale_solar_scenario,
    multi_update_scenario,
)


# ---------------------------------------------------------------------------
# Stale Memory Profile Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stale_work_schedule_profile() -> UserProfile:
    """User profile where household.work_schedule is 120+ days old.

    Profile has:
    - work_schedule = "Office 9-5" (STALE - user now works from home)
    - household.updated_at = 120 days ago
    """
    old_date = datetime.now(timezone.utc) - timedelta(days=120)

    return UserProfile(
        user_id="stale_wfh_user",
        equipment=Equipment(
            solar_capacity_kw=7.5,
            ev_model="Tesla Model 3",
            ev_battery_kwh=75.0,
            heating_type="heat_pump",
            cooling_type="central_ac",
        ),
        household=Household(
            occupants=2,
            work_schedule="Office 9-5",  # STALE - user is now WFH
            typical_usage_pattern="evening_heavy",
            updated_at=old_date,  # 120 days old!
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
def stale_solar_profile() -> UserProfile:
    """User profile where equipment.solar_capacity_kw is outdated.

    Profile has:
    - solar_capacity_kw = 7.5 (STALE - user upgraded to 12kW)
    - equipment.updated_at = 100 days ago
    """
    old_date = datetime.now(timezone.utc) - timedelta(days=100)

    return UserProfile(
        user_id="stale_solar_user",
        equipment=Equipment(
            solar_capacity_kw=7.5,  # STALE - user upgraded to 12kW
            ev_model="Tesla Model 3",
            ev_battery_kwh=75.0,
            heating_type="heat_pump",
            cooling_type="central_ac",
            updated_at=old_date,  # 100 days old!
        ),
        household=Household(
            occupants=2,
            work_schedule="work_from_home",
            typical_usage_pattern="constant",
        ),
        location=Location(
            zip_code="94102",
            utility_provider="PG&E",
            rate_schedule="E-TOU-C",
        ),
        preferences=Preferences(
            comfort_priority="medium",
            budget_priority="high",
            green_priority="high",
        ),
    )


@pytest.fixture
def multi_stale_profile() -> UserProfile:
    """User profile where multiple fields are outdated.

    Profile has (all STALE):
    - solar_capacity_kw = 7.5 (now 15kW)
    - ev_model = "Tesla Model 3" (now "Rivian R1T")
    - occupants = 2 (now 3)
    """
    old_date = datetime.now(timezone.utc) - timedelta(days=150)

    return UserProfile(
        user_id="multi_stale_user",
        equipment=Equipment(
            solar_capacity_kw=7.5,  # STALE - now 15kW
            ev_model="Tesla Model 3",  # STALE - now Rivian R1T
            ev_battery_kwh=75.0,
            heating_type="heat_pump",
            cooling_type="central_ac",
            updated_at=old_date,
        ),
        household=Household(
            occupants=2,  # STALE - now 3
            work_schedule="work_from_home",
            typical_usage_pattern="constant",
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
            green_priority="high",
        ),
    )


# ---------------------------------------------------------------------------
# Stale Memory Store Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stale_work_schedule_store(stale_work_schedule_profile) -> InMemoryStore:
    """Store pre-populated with stale work schedule profile."""
    store = InMemoryStore()
    save_profile_to_store(store, stale_work_schedule_profile)
    return store


@pytest.fixture
def stale_solar_store(stale_solar_profile) -> InMemoryStore:
    """Store pre-populated with stale solar capacity profile."""
    store = InMemoryStore()
    save_profile_to_store(store, stale_solar_profile)
    return store


@pytest.fixture
def multi_stale_store(multi_stale_profile) -> InMemoryStore:
    """Store pre-populated with multi-stale profile."""
    store = InMemoryStore()
    save_profile_to_store(store, multi_stale_profile)
    return store


# ---------------------------------------------------------------------------
# Stale Memory Scenario Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stale_work_scenario():
    """Scenario for stale work schedule test."""
    return stale_work_schedule_scenario()


@pytest.fixture
def stale_solar_scenario_fixture():
    """Scenario for stale solar capacity test."""
    return stale_solar_scenario()


@pytest.fixture
def multi_stale_scenario():
    """Scenario for multi-stale field test."""
    return multi_update_scenario()
