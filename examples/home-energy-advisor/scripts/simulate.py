#!/usr/bin/env python3
"""Manual exploration script for user simulation.

This script is for interactive exploration and debugging of the
Home Energy Advisor using simulated user conversations.

For automated testing, use: pytest tests/trajectories/ -m integration

Usage:
    python scripts/simulate.py
    python scripts/simulate.py --scenario solar_advice
    python scripts/simulate.py --max-turns 10
    python scripts/simulate.py --output-dir ./traces
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src and tests to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "trajectories"))

from langgraph.store.memory import InMemoryStore

from context_forge.harness.user_simulator import (
    LangGraphAdapter,
    SimulationRunner,
)

from src.agents.advisor import build_advisor_graph
from src.core.models import Equipment, Household, Location, Preferences, UserProfile

# Import scenarios from test definitions
from scenarios import (
    ev_charging_scenario,
    general_advice_scenario,
    solar_advice_scenario,
)


def create_demo_profile() -> UserProfile:
    """Create a demo user profile for simulation."""
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


SCENARIOS = {
    "ev_charging": ev_charging_scenario,
    "solar_advice": solar_advice_scenario,
    "general_advice": general_advice_scenario,
}


async def run_simulation(
    scenario_name: str = "ev_charging",
    max_turns: int = 5,
    output_dir: str | None = None,
) -> None:
    """Run a simulation with the advisor.

    Args:
        scenario_name: Name of the scenario to run
        max_turns: Maximum number of conversation turns
        output_dir: Directory to save trace files
    """
    print(f"\n{'='*60}")
    print(f"Running simulation: {scenario_name}")
    print(f"Max turns: {max_turns}")
    print(f"{'='*60}\n")

    # Create advisor graph with store
    store = InMemoryStore()
    graph = build_advisor_graph(store=store)

    # Create demo profile
    profile = create_demo_profile()

    # Create adapter with custom state builder
    adapter = LangGraphAdapter(
        graph=graph,
        input_key="message",
        output_key="response",
        agent_name="home_energy_advisor",
        state_builder=create_state_builder(profile),
    )

    # Get scenario factory
    scenario_factory = SCENARIOS.get(scenario_name)
    if not scenario_factory:
        print(f"Unknown scenario: {scenario_name}")
        print(f"Available scenarios: {list(SCENARIOS.keys())}")
        return

    scenario = scenario_factory(max_turns=max_turns)

    # Create runner
    runner = SimulationRunner(
        adapter=adapter,
        trace_output_dir=output_dir,
    )

    # Run simulation
    print("Starting simulation...\n")
    print(f"Persona: {scenario.persona.name}")
    print(f"Background: {scenario.persona.background}")
    print(f"Initial message: {scenario.initial_message}\n")

    result = await runner.run(scenario)

    # Print results
    print(f"\n{'='*60}")
    print("SIMULATION RESULTS")
    print(f"{'='*60}")
    print(f"Success: {result.success}")
    print(f"Total turns: {result.metrics.get('total_turns', 0)}")
    print(f"Duration: {result.metrics.get('duration_seconds', 0):.2f}s")
    print(f"Termination: {result.state.termination_reason}")

    if result.trace_path:
        print(f"Trace saved to: {result.trace_path}")

    print(f"\n{'='*60}")
    print("CONVERSATION")
    print(f"{'='*60}")

    for turn in result.state.turns:
        role = "USER" if turn.role.value == "user" else "ADVISOR"
        content = turn.message.content
        if len(content) > 500:
            content = content[:500] + "..."
        print(f"\n[{role}]:")
        print(content)

    if result.error:
        print(f"\nError: {result.error}")

    # Print goals status
    print(f"\n{'='*60}")
    print("GOALS STATUS")
    print(f"{'='*60}")
    for goal in scenario.persona.goals:
        status = "ACHIEVED" if goal.is_achieved else "PENDING"
        print(f"  [{status}] {goal.description}")


def main():
    parser = argparse.ArgumentParser(
        description="Run user simulation with Home Energy Advisor (manual exploration)",
        epilog="For automated testing, use: pytest tests/trajectories/ -m integration",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="ev_charging",
        choices=list(SCENARIOS.keys()),
        help="Scenario to run",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=5,
        help="Maximum conversation turns",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save trace files",
    )

    args = parser.parse_args()

    asyncio.run(run_simulation(
        scenario_name=args.scenario,
        max_turns=args.max_turns,
        output_dir=args.output_dir,
    ))


if __name__ == "__main__":
    main()
