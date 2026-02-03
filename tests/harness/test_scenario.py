"""Tests for scenario definitions."""

import pytest

from context_forge.harness.user_simulator.persona import Goal, Persona
from context_forge.harness.user_simulator.scenario import (
    GenerativeScenario,
    ScriptedScenario,
    ScriptedTurn,
    TerminationCondition,
)


@pytest.fixture
def test_persona():
    """Create a test persona."""
    return Persona(
        persona_id="test-user",
        name="Test User",
        background="Test background",
    )


class TestScriptedScenario:
    """Tests for ScriptedScenario."""

    def test_create_scripted_scenario(self, test_persona):
        """Create a scripted scenario."""
        scenario = ScriptedScenario(
            scenario_id="test-scenario",
            name="Test Scenario",
            persona=test_persona,
            turns=[
                ScriptedTurn(turn_number=0, user_message="Hello"),
                ScriptedTurn(turn_number=1, user_message="How are you?"),
            ],
        )
        assert scenario.scenario_id == "test-scenario"
        assert len(scenario.turns) == 2
        assert scenario.fallback == "terminate"

    def test_get_turn_message(self, test_persona):
        """Get message for specific turn."""
        scenario = ScriptedScenario(
            scenario_id="test",
            name="Test",
            persona=test_persona,
            turns=[
                ScriptedTurn(turn_number=0, user_message="First"),
                ScriptedTurn(turn_number=1, user_message="Second"),
                ScriptedTurn(turn_number=2, user_message="Third"),
            ],
        )

        assert scenario.get_turn_message(0) == "First"
        assert scenario.get_turn_message(1) == "Second"
        assert scenario.get_turn_message(2) == "Third"
        assert scenario.get_turn_message(99) is None

    def test_get_initial_message(self, test_persona):
        """Get initial message."""
        scenario = ScriptedScenario(
            scenario_id="test",
            name="Test",
            persona=test_persona,
            turns=[
                ScriptedTurn(turn_number=0, user_message="Hello!"),
            ],
        )

        assert scenario.get_initial_message() == "Hello!"

    def test_get_initial_message_empty(self, test_persona):
        """Get initial message when no turns defined."""
        scenario = ScriptedScenario(
            scenario_id="test",
            name="Test",
            persona=test_persona,
            turns=[],
        )

        with pytest.raises(ValueError, match="no turns"):
            scenario.get_initial_message()

    def test_termination_conditions(self, test_persona):
        """Create scenario with termination conditions."""
        scenario = ScriptedScenario(
            scenario_id="test",
            name="Test",
            persona=test_persona,
            turns=[ScriptedTurn(turn_number=0, user_message="Hi")],
            termination_conditions=[
                TerminationCondition(
                    condition_type="keyword",
                    value="FINISHED",
                    description="End when user says FINISHED",
                ),
            ],
        )

        assert len(scenario.termination_conditions) == 1


class TestGenerativeScenario:
    """Tests for GenerativeScenario."""

    def test_create_generative_scenario(self, test_persona):
        """Create a generative scenario."""
        scenario = GenerativeScenario(
            scenario_id="test-scenario",
            name="Test Scenario",
            persona=test_persona,
            initial_message="When should I charge my EV?",
            max_turns=10,
        )
        assert scenario.scenario_id == "test-scenario"
        assert scenario.initial_message == "When should I charge my EV?"
        assert scenario.max_turns == 10

    def test_get_initial_message(self, test_persona):
        """Get initial message."""
        scenario = GenerativeScenario(
            scenario_id="test",
            name="Test",
            persona=test_persona,
            initial_message="Hello!",
        )

        assert scenario.get_initial_message() == "Hello!"

    def test_default_parameters(self, test_persona):
        """Check default parameters."""
        scenario = GenerativeScenario(
            scenario_id="test",
            name="Test",
            persona=test_persona,
            initial_message="Hi",
        )

        assert scenario.max_turns == 20
        assert scenario.temperature == 0.7
        assert scenario.max_response_tokens == 500

    def test_topic_boundaries(self, test_persona):
        """Create scenario with topic boundaries."""
        scenario = GenerativeScenario(
            scenario_id="test",
            name="Test",
            persona=test_persona,
            initial_message="Hi",
            allowed_topics=["energy", "solar", "EV"],
            forbidden_topics=["politics", "religion"],
        )

        assert "energy" in scenario.allowed_topics
        assert "politics" in scenario.forbidden_topics
