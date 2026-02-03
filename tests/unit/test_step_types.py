"""Tests for all step type models.

Tests T009: All step type models (LLMCallStep, ToolCallStep, etc.)
"""

from datetime import datetime, timezone

import pytest

from context_forge.core.trace import (
    FinalOutputStep,
    InterruptStep,
    LLMCallStep,
    MemoryReadStep,
    MemoryWriteStep,
    RetrievalStep,
    StateChangeStep,
    ToolCallStep,
    UserInputStep,
)
from context_forge.core.types import ResourceImpact, RetrievalResult, StepType


@pytest.fixture
def now():
    """Current timestamp for tests."""
    return datetime.now(timezone.utc)


class TestLLMCallStep:
    """Tests for LLMCallStep model."""

    def test_minimal_llm_call(self, now):
        """LLMCallStep requires model, input, output."""
        step = LLMCallStep(
            step_id="llm-1",
            timestamp=now,
            model="gpt-4",
            input="Hello",
            output="Hi there!",
        )
        assert step.step_type == StepType.LLM_CALL
        assert step.model == "gpt-4"
        assert step.input == "Hello"
        assert step.output == "Hi there!"

    def test_llm_call_with_messages(self, now):
        """LLMCallStep accepts message list as input."""
        step = LLMCallStep(
            step_id="llm-1",
            timestamp=now,
            model="gpt-4",
            input=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ],
            output="Hi!",
        )
        assert isinstance(step.input, list)
        assert len(step.input) == 2

    def test_llm_call_with_tokens(self, now):
        """LLMCallStep accepts token counts."""
        step = LLMCallStep(
            step_id="llm-1",
            timestamp=now,
            model="gpt-4",
            input="Hello",
            output="Hi",
            tokens_in=5,
            tokens_out=2,
            tokens_total=7,
        )
        assert step.tokens_in == 5
        assert step.tokens_out == 2
        assert step.tokens_total == 7

    def test_llm_call_with_latency_and_cost(self, now):
        """LLMCallStep accepts latency and cost."""
        step = LLMCallStep(
            step_id="llm-1",
            timestamp=now,
            model="gpt-4",
            input="Hello",
            output="Hi",
            latency_ms=150,
            cost_estimate=0.003,
            provider="openai",
        )
        assert step.latency_ms == 150
        assert step.cost_estimate == 0.003
        assert step.provider == "openai"


class TestToolCallStep:
    """Tests for ToolCallStep model."""

    def test_minimal_tool_call(self, now):
        """ToolCallStep requires tool_name, arguments, result."""
        step = ToolCallStep(
            step_id="tool-1",
            timestamp=now,
            tool_name="calculator",
            arguments={"expression": "2+2"},
            result=4,
        )
        assert step.step_type == StepType.TOOL_CALL
        assert step.tool_name == "calculator"
        assert step.arguments == {"expression": "2+2"}
        assert step.result == 4

    def test_tool_call_with_success(self, now):
        """ToolCallStep accepts success flag."""
        step = ToolCallStep(
            step_id="tool-1",
            timestamp=now,
            tool_name="api",
            arguments={},
            result={"data": "ok"},
            success=True,
            latency_ms=50,
        )
        assert step.success is True
        assert step.latency_ms == 50

    def test_tool_call_with_error(self, now):
        """ToolCallStep accepts error message."""
        step = ToolCallStep(
            step_id="tool-1",
            timestamp=now,
            tool_name="api",
            arguments={},
            result=None,
            success=False,
            error="Connection timeout",
        )
        assert step.success is False
        assert step.error == "Connection timeout"

    def test_tool_call_with_resource_impact(self, now):
        """ToolCallStep accepts resource impact."""
        step = ToolCallStep(
            step_id="tool-1",
            timestamp=now,
            tool_name="expensive_api",
            arguments={},
            result={},
            resource_impact=ResourceImpact(amount=0.10, unit="USD"),
        )
        assert step.resource_impact.amount == 0.10
        assert step.resource_impact.unit == "USD"


class TestRetrievalStep:
    """Tests for RetrievalStep model."""

    def test_minimal_retrieval(self, now):
        """RetrievalStep requires query, results, match_count."""
        step = RetrievalStep(
            step_id="ret-1",
            timestamp=now,
            query="python best practices",
            results=[RetrievalResult(content="Use type hints")],
            match_count=1,
        )
        assert step.step_type == StepType.RETRIEVAL
        assert step.query == "python best practices"
        assert len(step.results) == 1
        assert step.match_count == 1

    def test_retrieval_with_scores(self, now):
        """RetrievalStep results can have scores."""
        step = RetrievalStep(
            step_id="ret-1",
            timestamp=now,
            query="test",
            results=[
                RetrievalResult(content="doc1", score=0.95),
                RetrievalResult(content="doc2", score=0.80),
            ],
            match_count=2,
            latency_ms=25,
        )
        assert step.results[0].score == 0.95
        assert step.latency_ms == 25


class TestMemoryReadStep:
    """Tests for MemoryReadStep model."""

    def test_minimal_memory_read(self, now):
        """MemoryReadStep requires query, results, match_count."""
        step = MemoryReadStep(
            step_id="mem-1",
            timestamp=now,
            query="user preferences",
            results=["preference1", "preference2"],
            match_count=2,
        )
        assert step.step_type == StepType.MEMORY_READ
        assert step.query == "user preferences"
        assert len(step.results) == 2
        assert step.match_count == 2

    def test_memory_read_with_dict_query(self, now):
        """MemoryReadStep accepts dict query."""
        step = MemoryReadStep(
            step_id="mem-1",
            timestamp=now,
            query={"namespace": "user", "key": "settings"},
            results=[{"theme": "dark"}],
            match_count=1,
        )
        assert step.query == {"namespace": "user", "key": "settings"}

    def test_memory_read_with_scores(self, now):
        """MemoryReadStep accepts relevance scores."""
        step = MemoryReadStep(
            step_id="mem-1",
            timestamp=now,
            query="test",
            results=["r1", "r2"],
            match_count=2,
            relevance_scores=[0.9, 0.7],
            total_available=100,
        )
        assert step.relevance_scores == [0.9, 0.7]
        assert step.total_available == 100


class TestMemoryWriteStep:
    """Tests for MemoryWriteStep model."""

    def test_memory_write_add(self, now):
        """MemoryWriteStep add operation."""
        step = MemoryWriteStep(
            step_id="mem-1",
            timestamp=now,
            entity_type="user_fact",
            operation="add",
            data={"fact": "User likes Python"},
        )
        assert step.step_type == StepType.MEMORY_WRITE
        assert step.operation == "add"

    def test_memory_write_update(self, now):
        """MemoryWriteStep update operation."""
        step = MemoryWriteStep(
            step_id="mem-1",
            timestamp=now,
            entity_type="user_profile",
            operation="update",
            data={"name": "Updated Name"},
            entity_id="user-123",
        )
        assert step.operation == "update"
        assert step.entity_id == "user-123"

    def test_memory_write_delete(self, now):
        """MemoryWriteStep delete operation."""
        step = MemoryWriteStep(
            step_id="mem-1",
            timestamp=now,
            entity_type="session",
            operation="delete",
            data={},
            entity_id="session-456",
        )
        assert step.operation == "delete"


class TestInterruptStep:
    """Tests for InterruptStep model."""

    def test_interrupt_step(self, now):
        """InterruptStep requires prompt, response, wait_duration_ms."""
        step = InterruptStep(
            step_id="int-1",
            timestamp=now,
            prompt="Please confirm this action",
            response="Yes, proceed",
            wait_duration_ms=5000,
        )
        assert step.step_type == StepType.INTERRUPT
        assert step.prompt == "Please confirm this action"
        assert step.response == "Yes, proceed"
        assert step.wait_duration_ms == 5000

    def test_interrupt_with_dict_response(self, now):
        """InterruptStep accepts dict response."""
        step = InterruptStep(
            step_id="int-1",
            timestamp=now,
            prompt="Select options",
            response={"choice": "A", "confirm": True},
            wait_duration_ms=3000,
        )
        assert step.response == {"choice": "A", "confirm": True}


class TestStateChangeStep:
    """Tests for StateChangeStep model."""

    def test_minimal_state_change(self, now):
        """StateChangeStep requires state_key and new_value."""
        step = StateChangeStep(
            step_id="state-1",
            timestamp=now,
            state_key="mode",
            new_value="processing",
        )
        assert step.step_type == StepType.STATE_CHANGE
        assert step.state_key == "mode"
        assert step.new_value == "processing"

    def test_state_change_with_old_value(self, now):
        """StateChangeStep accepts old_value."""
        step = StateChangeStep(
            step_id="state-1",
            timestamp=now,
            state_key="count",
            old_value=5,
            new_value=6,
            reason="Incremented counter",
        )
        assert step.old_value == 5
        assert step.new_value == 6
        assert step.reason == "Incremented counter"


class TestUserInputStep:
    """Tests for UserInputStep model."""

    def test_minimal_user_input(self, now):
        """UserInputStep requires content."""
        step = UserInputStep(
            step_id="user-1",
            timestamp=now,
            content="Hello, how are you?",
        )
        assert step.step_type == StepType.USER_INPUT
        assert step.content == "Hello, how are you?"

    def test_user_input_with_type(self, now):
        """UserInputStep accepts input_type."""
        step = UserInputStep(
            step_id="user-1",
            timestamp=now,
            content="/path/to/file.pdf",
            input_type="file",
        )
        assert step.input_type == "file"


class TestFinalOutputStep:
    """Tests for FinalOutputStep model."""

    def test_minimal_final_output(self, now):
        """FinalOutputStep requires content."""
        step = FinalOutputStep(
            step_id="out-1",
            timestamp=now,
            content="Here is your answer: 42",
        )
        assert step.step_type == StepType.FINAL_OUTPUT
        assert step.content == "Here is your answer: 42"

    def test_final_output_with_format(self, now):
        """FinalOutputStep accepts format."""
        step = FinalOutputStep(
            step_id="out-1",
            timestamp=now,
            content={"result": 42, "unit": "answer"},
            format="json",
        )
        assert step.format == "json"
        assert step.content == {"result": 42, "unit": "answer"}
