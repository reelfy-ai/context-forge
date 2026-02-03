"""Tests for simulation models."""

import pytest
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage

from context_forge.harness.user_simulator.models import (
    ConversationRole,
    SimulationResult,
    SimulationState,
    SimulationTurn,
)


class TestSimulationTurn:
    """Tests for SimulationTurn model."""

    def test_create_user_turn(self):
        """Create a user turn."""
        turn = SimulationTurn(
            turn_number=0,
            role=ConversationRole.USER,
            message=HumanMessage(content="Hello"),
        )
        assert turn.turn_number == 0
        assert turn.role == ConversationRole.USER
        assert turn.message.content == "Hello"
        assert isinstance(turn.timestamp, datetime)

    def test_create_agent_turn(self):
        """Create an agent turn."""
        turn = SimulationTurn(
            turn_number=1,
            role=ConversationRole.AGENT,
            message=AIMessage(content="Hi there!"),
        )
        assert turn.role == ConversationRole.AGENT
        assert turn.message.content == "Hi there!"


class TestSimulationState:
    """Tests for SimulationState model."""

    def test_create_state(self):
        """Create simulation state."""
        state = SimulationState(
            simulation_id="test-123",
            scenario_id="scenario-1",
            persona_id="persona-1",
        )
        assert state.simulation_id == "test-123"
        assert state.status == "running"
        assert state.current_turn == 0
        assert state.max_turns == 20
        assert len(state.turns) == 0

    def test_get_messages(self):
        """Get all messages from state."""
        state = SimulationState(
            simulation_id="test-123",
            scenario_id="scenario-1",
            persona_id="persona-1",
            turns=[
                SimulationTurn(
                    turn_number=0,
                    role=ConversationRole.USER,
                    message=HumanMessage(content="Hello"),
                ),
                SimulationTurn(
                    turn_number=0,
                    role=ConversationRole.AGENT,
                    message=AIMessage(content="Hi!"),
                ),
            ],
        )
        messages = state.get_messages()
        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi!"

    def test_get_last_agent_message(self):
        """Get last agent message."""
        state = SimulationState(
            simulation_id="test-123",
            scenario_id="scenario-1",
            persona_id="persona-1",
            turns=[
                SimulationTurn(
                    turn_number=0,
                    role=ConversationRole.USER,
                    message=HumanMessage(content="Hello"),
                ),
                SimulationTurn(
                    turn_number=0,
                    role=ConversationRole.AGENT,
                    message=AIMessage(content="First response"),
                ),
                SimulationTurn(
                    turn_number=1,
                    role=ConversationRole.USER,
                    message=HumanMessage(content="Follow up"),
                ),
                SimulationTurn(
                    turn_number=1,
                    role=ConversationRole.AGENT,
                    message=AIMessage(content="Second response"),
                ),
            ],
        )
        last = state.get_last_agent_message()
        assert last.content == "Second response"

    def test_get_last_agent_message_none(self):
        """Get last agent message when no agent messages exist."""
        state = SimulationState(
            simulation_id="test-123",
            scenario_id="scenario-1",
            persona_id="persona-1",
        )
        assert state.get_last_agent_message() is None


class TestSimulationResult:
    """Tests for SimulationResult model."""

    def test_create_result(self):
        """Create simulation result."""
        state = SimulationState(
            simulation_id="test-123",
            scenario_id="scenario-1",
            persona_id="persona-1",
        )
        result = SimulationResult(
            simulation_id="test-123",
            state=state,
            success=True,
            metrics={"total_turns": 5},
        )
        assert result.success is True
        assert result.metrics["total_turns"] == 5

    def test_to_dict(self):
        """Convert result to dictionary."""
        state = SimulationState(
            simulation_id="test-123",
            scenario_id="scenario-1",
            persona_id="persona-1",
            status="completed",
            turns=[
                SimulationTurn(
                    turn_number=0,
                    role=ConversationRole.USER,
                    message=HumanMessage(content="Hello"),
                ),
            ],
        )
        state.ended_at = datetime.now()

        result = SimulationResult(
            simulation_id="test-123",
            state=state,
            success=True,
        )

        data = result.to_dict()
        assert data["simulation_id"] == "test-123"
        assert data["scenario_id"] == "scenario-1"
        assert data["success"] is True
        assert len(data["conversation"]) == 1
        assert data["conversation"][0]["content"] == "Hello"
