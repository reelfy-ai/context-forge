"""Trajectory tests for general energy advice scenario.

These tests simulate multi-turn conversations about energy saving
and evaluate agent behavior using graders.
"""

import pytest

from context_forge.harness.user_simulator import SimulationResult


# ---------------------------------------------------------------------------
# Simulation Execution Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_general_advice_simulation_runs(general_advice_trace: SimulationResult):
    """Verify general advice simulation completes successfully."""
    assert general_advice_trace is not None
    assert general_advice_trace.state.status in ["completed", "terminated"]
    assert len(general_advice_trace.state.turns) > 0


@pytest.mark.integration
async def test_general_advice_has_agent_responses(general_advice_trace: SimulationResult):
    """Verify agent provides responses in the simulation."""
    agent_turns = [
        t for t in general_advice_trace.state.turns if t.role.value == "agent"
    ]
    assert len(agent_turns) > 0, "Agent should provide at least one response"


# ---------------------------------------------------------------------------
# Grader Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_general_advice_no_empty_responses(general_advice_trace: SimulationResult):
    """Grader: Agent responses should not be empty."""
    for turn in general_advice_trace.state.turns:
        if turn.role.value == "agent":
            assert turn.message.content, f"Agent response at turn {turn.turn_number} is empty"
            assert len(turn.message.content.strip()) > 10, "Agent response too short"


@pytest.mark.integration
async def test_general_advice_response_relevance(general_advice_trace: SimulationResult):
    """Grader: Agent responses should be relevant to energy saving."""
    relevant_keywords = [
        "energy", "electricity", "bill", "save", "reduce", "cost",
        "efficient", "usage", "power", "consumption", "tip", "advice"
    ]

    agent_responses = [
        t.message.content.lower()
        for t in general_advice_trace.state.turns
        if t.role.value == "agent"
    ]

    for response in agent_responses:
        has_relevant_content = any(kw in response for kw in relevant_keywords)
        assert has_relevant_content, f"Response doesn't seem relevant to energy: {response[:100]}..."


@pytest.mark.integration
async def test_general_advice_provides_actionable_tips(general_advice_trace: SimulationResult):
    """Grader: Agent should provide actionable energy saving tips."""
    agent_responses = " ".join(
        t.message.content.lower()
        for t in general_advice_trace.state.turns
        if t.role.value == "agent"
    )

    # Check for actionable language
    actionable_patterns = [
        "you can", "try", "consider", "recommend", "suggest",
        "should", "turn off", "reduce", "switch", "use"
    ]

    has_actionable = any(pattern in agent_responses for pattern in actionable_patterns)
    assert has_actionable, "Agent should provide actionable advice"


@pytest.mark.integration
async def test_general_advice_turn_limit(general_advice_trace: SimulationResult):
    """Grader: Simulation should respect turn limits."""
    max_expected_turns = 10
    assert len(general_advice_trace.state.turns) <= max_expected_turns


# ---------------------------------------------------------------------------
# Future Grader Tests
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Requires ContextForge graders")
@pytest.mark.integration
async def test_general_advice_personalization(general_advice_trace: SimulationResult):
    """Grader: Agent should personalize advice based on user profile."""
    # TODO: Check if agent mentions user's specific equipment/situation
    pass
