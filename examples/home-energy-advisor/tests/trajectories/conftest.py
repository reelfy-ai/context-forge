"""Simulation fixtures for trajectory testing.

These fixtures provide:
- Pre-configured simulation scenarios
- Adapter setup for the advisor graph
- Trace generation for grader evaluation
- ContextForge instrumentation for full trace capture
"""

from datetime import datetime

import pytest
from langgraph.store.memory import InMemoryStore

from context_forge.harness.user_simulator import (
    GenerativeScenario,
    LangGraphAdapter,
    Persona,
    SimulationResult,
    SimulationRunner,
)
from context_forge.instrumentation import LangGraphInstrumentor

from src.agents.advisor import build_advisor_graph
from src.core.models import Equipment, Household, Location, Preferences, UserProfile

from .scenarios import (
    ev_charging_persona,
    ev_charging_scenario,
    general_advice_persona,
    general_advice_scenario,
    solar_advice_persona,
    solar_advice_scenario,
    stale_work_schedule_scenario,
    stale_solar_scenario,
    multi_update_scenario,
)


# ---------------------------------------------------------------------------
# User Profile Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simulation_profile() -> UserProfile:
    """User profile for simulation tests."""
    return UserProfile(
        user_id="simulation_user",
        equipment=Equipment(
            solar_capacity_kw=7.5,
            ev_model="Tesla Model 3",
            ev_battery_kwh=75.0,
            heating_type="heat_pump",
            cooling_type="central_ac",
        ),
        household=Household(
            occupants=4,
            work_schedule="work_from_home",
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


# ---------------------------------------------------------------------------
# Instrumentation Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def trace_instrumentor():
    """ContextForge instrumentor for capturing full traces.

    Uses LangGraphInstrumentor to capture:
    - LLM calls (via LangChain callbacks)
    - Tool calls (via LangChain callbacks)
    - Memory operations (via BaseStore patching)

    All events go into a single unified trace.

    Set CONTEXTFORGE_TRACE_OUTPUT=./traces to save traces to disk for inspection.
    Example:
        CONTEXTFORGE_TRACE_OUTPUT=./traces pytest tests/trajectories/ -v
    """
    import os

    output_path = os.environ.get("CONTEXTFORGE_TRACE_OUTPUT")

    instrumentor = LangGraphInstrumentor(
        agent_name="home_energy_advisor",
        agent_version="0.1.0",
        output_path=output_path,  # None if not set, traces stay in memory
    )
    instrumentor.instrument()
    yield instrumentor
    instrumentor.uninstrument()


# ---------------------------------------------------------------------------
# Adapter Fixtures
# ---------------------------------------------------------------------------


def create_state_builder(profile: UserProfile):
    """Create a state builder function for the LangGraphAdapter."""

    def build_state(message, state):
        """Build the initial state for the advisor graph."""
        return {
            "user_id": "simulation_user",
            "session_id": f"sim_{state.simulation_id}",
            "message": message.content,
            "messages": [t.message for t in state.turns],
            "turn_count": state.current_turn,
            "user_profile": profile,
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "memory_operations": [],
        }

    return build_state


@pytest.fixture
def advisor_store() -> InMemoryStore:
    """Fresh InMemoryStore for simulation tests."""
    return InMemoryStore()


@pytest.fixture
def advisor_graph(advisor_store):
    """Build the advisor graph for simulation."""
    return build_advisor_graph(store=advisor_store)


@pytest.fixture
def advisor_adapter(advisor_graph, simulation_profile, trace_instrumentor) -> LangGraphAdapter:
    """LangGraph adapter configured for the advisor with instrumentation."""
    return LangGraphAdapter(
        graph=advisor_graph,
        input_key="message",
        output_key="response",
        agent_name="home_energy_advisor",
        state_builder=create_state_builder(simulation_profile),
        callbacks=[trace_instrumentor.get_callback_handler()],
    )


# ---------------------------------------------------------------------------
# Scenario Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ev_scenario() -> GenerativeScenario:
    """EV charging optimization scenario."""
    return ev_charging_scenario(max_turns=5)


@pytest.fixture
def solar_scenario() -> GenerativeScenario:
    """Solar production advice scenario."""
    return solar_advice_scenario(max_turns=5)


@pytest.fixture
def general_scenario() -> GenerativeScenario:
    """General energy advice scenario."""
    return general_advice_scenario(max_turns=5)


# ---------------------------------------------------------------------------
# Simulation Runner Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simulation_runner(advisor_adapter) -> SimulationRunner:
    """Configured simulation runner."""
    return SimulationRunner(
        adapter=advisor_adapter,
        trace_output_dir=None,  # Don't save traces to disk in tests
    )


# ---------------------------------------------------------------------------
# Trace Generation Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def ev_charging_trace(simulation_runner, ev_scenario) -> SimulationResult:
    """Run EV charging simulation and return result with trace.

    This fixture runs a full multi-turn simulation of the EV charging
    scenario and returns the result for grader evaluation.
    """
    result = await simulation_runner.run(ev_scenario)
    return result


@pytest.fixture
async def solar_advice_trace(simulation_runner, solar_scenario) -> SimulationResult:
    """Run solar advice simulation and return result with trace."""
    result = await simulation_runner.run(solar_scenario)
    return result


@pytest.fixture
async def general_advice_trace(simulation_runner, general_scenario) -> SimulationResult:
    """Run general advice simulation and return result with trace."""
    result = await simulation_runner.run(general_scenario)
    return result


# ---------------------------------------------------------------------------
# ContextForge Trace Fixtures (Full E2E Traces)
# ---------------------------------------------------------------------------


@pytest.fixture
async def ev_charging_contextforge_trace(simulation_runner, ev_scenario, trace_instrumentor):
    """Run EV charging simulation and return the full ContextForge trace.

    This captures all internal events: LLM calls, tool calls, retrieval, etc.
    Returns a tuple of (SimulationResult, list[TraceRun]).
    """
    result = await simulation_runner.run(ev_scenario)
    traces = trace_instrumentor.get_traces()
    return result, traces


@pytest.fixture
async def solar_advice_contextforge_trace(simulation_runner, solar_scenario, trace_instrumentor):
    """Run solar advice simulation and return the full ContextForge trace."""
    result = await simulation_runner.run(solar_scenario)
    traces = trace_instrumentor.get_traces()
    return result, traces


@pytest.fixture
async def general_advice_contextforge_trace(simulation_runner, general_scenario, trace_instrumentor):
    """Run general advice simulation and return the full ContextForge trace."""
    result = await simulation_runner.run(general_scenario)
    traces = trace_instrumentor.get_traces()
    return result, traces


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
    from datetime import timedelta, timezone

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
    from datetime import timedelta, timezone

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
    from datetime import timedelta, timezone

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
    from src.memory.helpers import save_profile_to_store

    store = InMemoryStore()
    save_profile_to_store(store, stale_work_schedule_profile)
    return store


@pytest.fixture
def stale_solar_store(stale_solar_profile) -> InMemoryStore:
    """Store pre-populated with stale solar capacity profile."""
    from src.memory.helpers import save_profile_to_store

    store = InMemoryStore()
    save_profile_to_store(store, stale_solar_profile)
    return store


@pytest.fixture
def multi_stale_store(multi_stale_profile) -> InMemoryStore:
    """Store pre-populated with multi-stale profile."""
    from src.memory.helpers import save_profile_to_store

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
