"""Tests for trace schema models.

Tests:
- T008: BaseStep model
- T010: TraceRun model
- T011: Discriminated union validation
- T012: JSON serialization performance
"""

import json
import time
from datetime import datetime, timezone

import pytest

from context_forge.core.trace import (
    BaseStep,
    FinalOutputStep,
    LLMCallStep,
    MemoryReadStep,
    MemoryWriteStep,
    RetrievalStep,
    StateChangeStep,
    ToolCallStep,
    TraceRun,
    TraceStep,
    UserInputStep,
)
from context_forge.core.types import AgentInfo, RetrievalResult, StepType


class TestBaseStep:
    """Tests for BaseStep model (T008)."""

    def test_base_step_required_fields(self):
        """BaseStep requires step_id and timestamp."""
        # Can't instantiate BaseStep directly for step_type, but we can test via subclass
        step = UserInputStep(
            step_id="step-001",
            timestamp=datetime.now(timezone.utc),
            content="Hello",
        )
        assert step.step_id == "step-001"
        assert step.timestamp is not None

    def test_base_step_optional_fields(self):
        """BaseStep has optional parent_step_id and metadata."""
        step = UserInputStep(
            step_id="step-002",
            timestamp=datetime.now(timezone.utc),
            content="Hello",
            parent_step_id="step-001",
            metadata={"source": "test"},
        )
        assert step.parent_step_id == "step-001"
        assert step.metadata == {"source": "test"}


class TestTraceRun:
    """Tests for TraceRun model (T010)."""

    def test_minimal_trace_run(self):
        """TraceRun requires run_id, started_at, and agent_info."""
        trace = TraceRun(
            run_id="run-123",
            started_at=datetime.now(timezone.utc),
            agent_info=AgentInfo(name="test-agent"),
        )
        assert trace.run_id == "run-123"
        assert trace.started_at is not None
        assert trace.agent_info.name == "test-agent"
        assert trace.steps == []
        assert trace.ended_at is None

    def test_trace_run_with_steps(self):
        """TraceRun can contain steps."""
        now = datetime.now(timezone.utc)
        trace = TraceRun(
            run_id="run-123",
            started_at=now,
            agent_info=AgentInfo(name="test-agent"),
            steps=[
                UserInputStep(
                    step_id="step-1",
                    timestamp=now,
                    content="Hello",
                ),
                LLMCallStep(
                    step_id="step-2",
                    timestamp=now,
                    model="gpt-4",
                    input="Hello",
                    output="Hi there!",
                ),
            ],
        )
        assert len(trace.steps) == 2

    def test_add_step(self):
        """TraceRun.add_step appends steps."""
        trace = TraceRun(
            run_id="run-123",
            started_at=datetime.now(timezone.utc),
            agent_info=AgentInfo(name="test-agent"),
        )
        trace.add_step(
            UserInputStep(
                step_id="step-1",
                timestamp=datetime.now(timezone.utc),
                content="Hello",
            )
        )
        assert len(trace.steps) == 1

    def test_get_steps_by_type(self):
        """TraceRun.get_steps_by_type filters correctly."""
        now = datetime.now(timezone.utc)
        trace = TraceRun(
            run_id="run-123",
            started_at=now,
            agent_info=AgentInfo(name="test-agent"),
            steps=[
                UserInputStep(step_id="s1", timestamp=now, content="Hello"),
                LLMCallStep(step_id="s2", timestamp=now, model="gpt-4", input="Hi", output="Hey"),
                ToolCallStep(step_id="s3", timestamp=now, tool_name="calc", arguments={}, result=42),
                LLMCallStep(step_id="s4", timestamp=now, model="gpt-4", input="X", output="Y"),
            ],
        )
        llm_steps = trace.get_steps_by_type(StepType.LLM_CALL)
        assert len(llm_steps) == 2

    def test_total_tokens(self):
        """TraceRun.total_tokens sums correctly."""
        now = datetime.now(timezone.utc)
        trace = TraceRun(
            run_id="run-123",
            started_at=now,
            agent_info=AgentInfo(name="test-agent"),
            steps=[
                LLMCallStep(
                    step_id="s1", timestamp=now, model="gpt-4",
                    input="Hi", output="Hey", tokens_total=100,
                ),
                LLMCallStep(
                    step_id="s2", timestamp=now, model="gpt-4",
                    input="X", output="Y", tokens_in=50, tokens_out=50,
                ),
            ],
        )
        assert trace.total_tokens() == 200

    def test_total_tool_calls(self):
        """TraceRun.total_tool_calls counts correctly."""
        now = datetime.now(timezone.utc)
        trace = TraceRun(
            run_id="run-123",
            started_at=now,
            agent_info=AgentInfo(name="test-agent"),
            steps=[
                ToolCallStep(step_id="t1", timestamp=now, tool_name="a", arguments={}, result=1),
                ToolCallStep(step_id="t2", timestamp=now, tool_name="b", arguments={}, result=2),
                LLMCallStep(step_id="l1", timestamp=now, model="gpt-4", input="x", output="y"),
            ],
        )
        assert trace.total_tool_calls() == 2


class TestDiscriminatedUnion:
    """Tests for TraceStep discriminated union (T011)."""

    def test_llm_call_discriminator(self):
        """LLMCallStep has correct step_type."""
        step = LLMCallStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            model="gpt-4",
            input="Hello",
            output="Hi",
        )
        assert step.step_type == StepType.LLM_CALL

    def test_tool_call_discriminator(self):
        """ToolCallStep has correct step_type."""
        step = ToolCallStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            tool_name="calculator",
            arguments={"x": 1},
            result=42,
        )
        assert step.step_type == StepType.TOOL_CALL

    def test_retrieval_discriminator(self):
        """RetrievalStep has correct step_type."""
        step = RetrievalStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            query="search term",
            results=[RetrievalResult(content="doc")],
            match_count=1,
        )
        assert step.step_type == StepType.RETRIEVAL

    def test_memory_read_discriminator(self):
        """MemoryReadStep has correct step_type."""
        step = MemoryReadStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            query="user preferences",
            results=["pref1"],
            match_count=1,
        )
        assert step.step_type == StepType.MEMORY_READ

    def test_memory_write_discriminator(self):
        """MemoryWriteStep has correct step_type."""
        step = MemoryWriteStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            entity_type="user",
            operation="update",
            data={"name": "test"},
        )
        assert step.step_type == StepType.MEMORY_WRITE

    def test_state_change_discriminator(self):
        """StateChangeStep has correct step_type."""
        step = StateChangeStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            state_key="mode",
            new_value="active",
        )
        assert step.step_type == StepType.STATE_CHANGE

    def test_user_input_discriminator(self):
        """UserInputStep has correct step_type."""
        step = UserInputStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            content="Hello",
        )
        assert step.step_type == StepType.USER_INPUT

    def test_final_output_discriminator(self):
        """FinalOutputStep has correct step_type."""
        step = FinalOutputStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            content="Goodbye",
        )
        assert step.step_type == StepType.FINAL_OUTPUT

    def test_parse_mixed_steps_from_json(self):
        """Parse trace with mixed step types from JSON."""
        now = datetime.now(timezone.utc)
        trace = TraceRun(
            run_id="test",
            started_at=now,
            agent_info=AgentInfo(name="test"),
            steps=[
                UserInputStep(step_id="s1", timestamp=now, content="Hi"),
                LLMCallStep(step_id="s2", timestamp=now, model="gpt-4", input="Hi", output="Hello"),
                ToolCallStep(step_id="s3", timestamp=now, tool_name="calc", arguments={}, result=1),
            ],
        )
        json_str = trace.to_json()
        parsed = TraceRun.model_validate_json(json_str)
        assert len(parsed.steps) == 3
        assert isinstance(parsed.steps[0], UserInputStep)
        assert isinstance(parsed.steps[1], LLMCallStep)
        assert isinstance(parsed.steps[2], ToolCallStep)


class TestJsonSerialization:
    """Tests for JSON serialization performance (T012)."""

    def test_simple_trace_serialization(self):
        """Simple trace serializes to valid JSON."""
        trace = TraceRun(
            run_id="test-123",
            started_at=datetime.now(timezone.utc),
            agent_info=AgentInfo(name="test"),
        )
        json_str = trace.to_json()
        parsed = json.loads(json_str)
        assert parsed["run_id"] == "test-123"

    def test_serialization_excludes_none(self):
        """Serialization excludes None values."""
        trace = TraceRun(
            run_id="test-123",
            started_at=datetime.now(timezone.utc),
            agent_info=AgentInfo(name="test"),
        )
        json_str = trace.to_json()
        parsed = json.loads(json_str)
        assert "ended_at" not in parsed
        assert "task_info" not in parsed

    def test_1000_steps_under_100ms(self):
        """Serialization of 1000 steps completes in under 100ms (SC-003)."""
        now = datetime.now(timezone.utc)
        steps = []
        for i in range(1000):
            if i % 3 == 0:
                steps.append(UserInputStep(step_id=f"s{i}", timestamp=now, content=f"msg{i}"))
            elif i % 3 == 1:
                steps.append(LLMCallStep(
                    step_id=f"s{i}", timestamp=now, model="gpt-4",
                    input=f"in{i}", output=f"out{i}", tokens_total=100,
                ))
            else:
                steps.append(ToolCallStep(
                    step_id=f"s{i}", timestamp=now, tool_name=f"tool{i}",
                    arguments={"x": i}, result={"y": i * 2},
                ))

        trace = TraceRun(
            run_id="perf-test",
            started_at=now,
            agent_info=AgentInfo(name="perf-agent"),
            steps=steps,
        )

        start = time.perf_counter()
        json_str = trace.to_json()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"Serialization took {elapsed_ms:.2f}ms, expected < 100ms"
        assert len(json_str) > 0
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert len(parsed["steps"]) == 1000
