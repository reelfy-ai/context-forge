"""Simulation fixtures for trajectory testing.

These fixtures provide:
- Pre-configured simulation scenarios
- Adapter setup for the advisor graph
- Trace generation for grader evaluation
"""

import pytest
from langgraph.store.memory import InMemoryStore

from context_forge.harness.user_simulator import (
    GenerativeScenario,
    LangGraphAdapter,
    Persona,
    SimulationResult,
    SimulationRunner,
)

from src.agents.advisor import build_advisor_graph
from src.core.models import Equipment, Household, Location, Preferences, UserProfile

from .scenarios import (
    ev_charging_persona,
    ev_charging_scenario,
    general_advice_persona,
    general_advice_scenario,
    solar_advice_persona,
    solar_advice_scenario,
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
            typical_wake_time="07:00",
            typical_sleep_time="22:00",
        ),
        location=Location(
            zip_code="94102",
            utility="PG&E",
            rate_schedule="E-TOU-C",
            climate_zone="3C",
        ),
        preferences=Preferences(
            comfort_priority=7,
            cost_priority=8,
            eco_priority=6,
        ),
    )


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
            "should_memorize": False,
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
def advisor_adapter(advisor_graph, simulation_profile) -> LangGraphAdapter:
    """LangGraph adapter configured for the advisor."""
    return LangGraphAdapter(
        graph=advisor_graph,
        input_key="message",
        output_key="response",
        agent_name="home_energy_advisor",
        state_builder=create_state_builder(simulation_profile),
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
