"""Trajectory tests for solar production advice scenario.

These tests simulate multi-turn conversations about solar production
and evaluate agent behavior using graders.
"""

import pytest

from context_forge.harness.user_simulator import SimulationResult


# ---------------------------------------------------------------------------
# Simulation Execution Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_solar_advice_simulation_runs(solar_advice_trace: SimulationResult):
    """Verify solar advice simulation completes successfully."""
    assert solar_advice_trace is not None
    assert solar_advice_trace.state.status in ["completed", "terminated"]
    assert len(solar_advice_trace.state.turns) > 0


@pytest.mark.integration
async def test_solar_advice_has_agent_responses(solar_advice_trace: SimulationResult):
    """Verify agent provides responses in the simulation."""
    agent_turns = [
        t for t in solar_advice_trace.state.turns if t.role.value == "agent"
    ]
    assert len(agent_turns) > 0, "Agent should provide at least one response"


# ---------------------------------------------------------------------------
# Grader Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_solar_advice_no_empty_responses(solar_advice_trace: SimulationResult):
    """Grader: Agent responses should not be empty."""
    for turn in solar_advice_trace.state.turns:
        if turn.role.value == "agent":
            assert turn.message.content, f"Agent response at turn {turn.turn_number} is empty"
            assert len(turn.message.content.strip()) > 10, "Agent response too short"


@pytest.mark.integration
async def test_solar_advice_response_relevance(solar_advice_trace: SimulationResult):
    """Grader: Agent responses should be relevant to solar production."""
    relevant_keywords = [
        "solar", "panel", "production", "kwh", "energy", "sun",
        "weather", "cloud", "generate", "power", "watt"
    ]

    agent_responses = [
        t.message.content.lower()
        for t in solar_advice_trace.state.turns
        if t.role.value == "agent"
    ]

    for response in agent_responses:
        has_relevant_content = any(kw in response for kw in relevant_keywords)
        assert has_relevant_content, f"Response doesn't seem relevant to solar: {response[:100]}..."


@pytest.mark.integration
async def test_solar_advice_provides_estimate(solar_advice_trace: SimulationResult):
    """Grader: Agent should provide production estimate when asked."""
    agent_responses = " ".join(
        t.message.content.lower()
        for t in solar_advice_trace.state.turns
        if t.role.value == "agent"
    )

    # Check for numeric estimates or mentions of kWh
    import re
    has_numbers = bool(re.search(r'\d+', agent_responses))
    has_kwh = "kwh" in agent_responses or "kilowatt" in agent_responses

    assert has_numbers or has_kwh, "Agent should provide numeric estimates for solar production"


# ---------------------------------------------------------------------------
# Future Grader Tests
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Requires ContextForge graders")
@pytest.mark.integration
async def test_solar_advice_explains_factors(solar_advice_trace: SimulationResult):
    """Grader: Agent should explain factors affecting production."""
    # TODO: Implement with ContextForge TrajectoryJudge
    pass
