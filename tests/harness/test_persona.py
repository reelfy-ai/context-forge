"""Tests for persona and behavior definitions."""

import pytest

from context_forge.harness.user_simulator.persona import (
    Behavior,
    CommunicationStyle,
    Goal,
    Persona,
    TechnicalLevel,
)


class TestGoal:
    """Tests for Goal model."""

    def test_create_goal(self):
        """Create a goal."""
        goal = Goal(
            description="Get EV charging advice",
            success_criteria="Agent provides specific time recommendation",
        )
        assert goal.description == "Get EV charging advice"
        assert goal.is_achieved is False
        assert goal.priority == 1

    def test_goal_with_priority(self):
        """Create goal with custom priority."""
        goal = Goal(
            description="Secondary goal",
            success_criteria="Something happens",
            priority=3,
        )
        assert goal.priority == 3


class TestBehavior:
    """Tests for Behavior model."""

    def test_default_behavior(self):
        """Create behavior with defaults."""
        behavior = Behavior()
        assert behavior.communication_style == CommunicationStyle.CASUAL
        assert behavior.technical_level == TechnicalLevel.INTERMEDIATE
        assert behavior.patience_level == 5
        assert behavior.asks_followup_questions is True

    def test_custom_behavior(self):
        """Create behavior with custom values."""
        behavior = Behavior(
            communication_style=CommunicationStyle.FORMAL,
            technical_level=TechnicalLevel.EXPERT,
            patience_level=2,
            asks_followup_questions=False,
        )
        assert behavior.communication_style == CommunicationStyle.FORMAL
        assert behavior.patience_level == 2


class TestPersona:
    """Tests for Persona model."""

    def test_create_persona(self):
        """Create a persona."""
        persona = Persona(
            persona_id="test-user",
            name="Sarah",
            background="Homeowner with solar panels",
            situation="Wants to reduce electricity bills",
        )
        assert persona.persona_id == "test-user"
        assert persona.name == "Sarah"
        assert len(persona.goals) == 0

    def test_persona_with_goals(self):
        """Create persona with goals."""
        persona = Persona(
            persona_id="test-user",
            name="Sarah",
            goals=[
                Goal(
                    description="Get EV charging advice",
                    success_criteria="Time recommendation given",
                ),
                Goal(
                    description="Understand solar production",
                    success_criteria="kWh estimate provided",
                ),
            ],
        )
        assert len(persona.goals) == 2
        assert persona.goals[0].description == "Get EV charging advice"

    def test_to_system_prompt(self):
        """Generate system prompt from persona."""
        persona = Persona(
            persona_id="test-user",
            name="Sarah",
            background="Homeowner with solar panels",
            situation="Wants to reduce electricity bills",
            behavior=Behavior(
                communication_style=CommunicationStyle.CASUAL,
                technical_level=TechnicalLevel.INTERMEDIATE,
            ),
            goals=[
                Goal(
                    description="Get EV charging advice",
                    success_criteria="Time given",
                ),
            ],
        )
        prompt = persona.to_system_prompt()

        assert "Sarah" in prompt
        assert "solar panels" in prompt
        assert "EV charging advice" in prompt
        assert "informal" in prompt.lower() or "casual" in prompt.lower()

    def test_mark_goal_achieved(self):
        """Mark a goal as achieved."""
        persona = Persona(
            persona_id="test-user",
            name="Sarah",
            goals=[
                Goal(description="Goal 1", success_criteria="Done"),
                Goal(description="Goal 2", success_criteria="Done"),
            ],
        )

        result = persona.mark_goal_achieved("Goal 1")
        assert result is True
        assert persona.goals[0].is_achieved is True
        assert persona.goals[1].is_achieved is False

    def test_mark_nonexistent_goal(self):
        """Try to mark nonexistent goal."""
        persona = Persona(
            persona_id="test-user",
            name="Sarah",
            goals=[Goal(description="Goal 1", success_criteria="Done")],
        )

        result = persona.mark_goal_achieved("Nonexistent")
        assert result is False

    def test_get_pending_goals(self):
        """Get pending goals."""
        persona = Persona(
            persona_id="test-user",
            name="Sarah",
            goals=[
                Goal(description="Goal 1", success_criteria="Done", is_achieved=True),
                Goal(description="Goal 2", success_criteria="Done"),
                Goal(description="Goal 3", success_criteria="Done"),
            ],
        )

        pending = persona.get_pending_goals()
        assert len(pending) == 2
        assert pending[0].description == "Goal 2"

    def test_reset_goals(self):
        """Reset all goals."""
        persona = Persona(
            persona_id="test-user",
            name="Sarah",
            goals=[
                Goal(description="Goal 1", success_criteria="Done", is_achieved=True),
                Goal(description="Goal 2", success_criteria="Done", is_achieved=True),
            ],
        )

        persona.reset_goals()
        assert all(not g.is_achieved for g in persona.goals)
