"""Tests for explicit Tracer API.

Tests T075-T079, T088-T091:
- Tracer context manager
- All step recording methods
- Async Tracer.run_async()
- to_json() and save() methods
- parent_step_id nesting
"""

import json
import tempfile
from pathlib import Path

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
from context_forge.core.types import AgentInfo
from context_forge.exceptions import TracerNotActiveError
from context_forge.instrumentation.tracer import Tracer


class TestTracerContextManager:
    """Tests for Tracer.run() context manager (T075)."""

    def test_tracer_run_creates_trace(self):
        """Tracer.run() creates a trace with agent info."""
        with Tracer.run(agent_info={"name": "test-agent"}) as t:
            assert t.is_active
            assert t.trace.agent_info.name == "test-agent"
            assert t.trace.started_at is not None

        assert not t.is_active
        assert t.trace.ended_at is not None

    def test_tracer_with_full_agent_info(self):
        """Tracer accepts full AgentInfo."""
        agent_info = AgentInfo(
            name="my-agent",
            version="1.0.0",
            framework="custom",
            framework_version="0.1.0",
        )
        with Tracer.run(agent_info=agent_info) as t:
            assert t.trace.agent_info.version == "1.0.0"
            assert t.trace.agent_info.framework == "custom"

    def test_tracer_with_task_info(self):
        """Tracer accepts task info."""
        with Tracer.run(
            agent_info={"name": "test"},
            task_info={"description": "Test task", "goal": "Complete test"},
        ) as t:
            assert t.trace.task_info.description == "Test task"
            assert t.trace.task_info.goal == "Complete test"

    def test_tracer_with_custom_run_id(self):
        """Tracer accepts custom run ID."""
        with Tracer.run(agent_info={"name": "test"}, run_id="custom-123") as t:
            assert t.trace.run_id == "custom-123"

    def test_tracer_inactive_raises(self):
        """Recording steps without context raises error."""
        tracer = Tracer(agent_info={"name": "test"})
        with pytest.raises(TracerNotActiveError):
            tracer.llm_call(model="gpt-4", input="hi", output="hello")


class TestAsyncTracer:
    """Tests for Tracer.run_async() (T077)."""

    @pytest.mark.asyncio
    async def test_async_tracer_creates_trace(self):
        """Async tracer creates trace correctly."""
        async with Tracer.run_async(agent_info={"name": "async-agent"}) as t:
            assert t.is_active
            t.llm_call(model="gpt-4", input="hello", output="hi")

        assert not t.is_active
        assert len(t.trace.steps) == 1


class TestStepRecording:
    """Tests for all step recording methods (T076)."""

    def test_user_input(self):
        """Record user input step."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            step_id = t.user_input(content="Hello, how are you?")
            assert step_id is not None

        step = t.trace.steps[0]
        assert isinstance(step, UserInputStep)
        assert step.content == "Hello, how are you?"

    def test_user_input_with_type(self):
        """Record user input with type."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.user_input(content="file.pdf", input_type="file")

        assert t.trace.steps[0].input_type == "file"

    def test_llm_call_minimal(self):
        """Record minimal LLM call."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.llm_call(model="gpt-4", input="Hello", output="Hi there!")

        step = t.trace.steps[0]
        assert isinstance(step, LLMCallStep)
        assert step.model == "gpt-4"
        assert step.input == "Hello"
        assert step.output == "Hi there!"

    def test_llm_call_with_tokens(self):
        """Record LLM call with token counts."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.llm_call(
                model="gpt-4",
                input="Hello",
                output="Hi!",
                tokens_in=5,
                tokens_out=3,
                tokens_total=8,
            )

        step = t.trace.steps[0]
        assert step.tokens_in == 5
        assert step.tokens_out == 3
        assert step.tokens_total == 8

    def test_llm_call_with_messages(self):
        """Record LLM call with message list."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.llm_call(
                model="gpt-4",
                input=[
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"},
                ],
                output="Hi there!",
            )

        step = t.trace.steps[0]
        assert isinstance(step.input, list)
        assert len(step.input) == 2

    def test_tool_call(self):
        """Record tool call step."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.tool_call(
                tool_name="calculator",
                arguments={"expression": "2+2"},
                result=4,
            )

        step = t.trace.steps[0]
        assert isinstance(step, ToolCallStep)
        assert step.tool_name == "calculator"
        assert step.result == 4

    def test_tool_call_with_error(self):
        """Record failed tool call."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.tool_call(
                tool_name="api",
                arguments={"url": "http://example.com"},
                result=None,
                success=False,
                error="Connection timeout",
            )

        step = t.trace.steps[0]
        assert step.success is False
        assert step.error == "Connection timeout"

    def test_tool_call_with_resource_impact(self):
        """Record tool call with resource impact."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.tool_call(
                tool_name="expensive_api",
                arguments={},
                result={},
                resource_impact={"amount": 0.05, "unit": "USD"},
            )

        step = t.trace.steps[0]
        assert step.resource_impact.amount == 0.05
        assert step.resource_impact.unit == "USD"

    def test_retrieval(self):
        """Record retrieval step."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.retrieval(
                query="python best practices",
                results=[
                    {"content": "Use type hints", "score": 0.95},
                    {"content": "Write tests", "score": 0.90},
                ],
            )

        step = t.trace.steps[0]
        assert isinstance(step, RetrievalStep)
        assert step.query == "python best practices"
        assert len(step.results) == 2
        assert step.match_count == 2

    def test_memory_read(self):
        """Record memory read step."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.memory_read(
                query="user preferences",
                results=["dark mode", "large font"],
            )

        step = t.trace.steps[0]
        assert isinstance(step, MemoryReadStep)
        assert step.query == "user preferences"
        assert len(step.results) == 2

    def test_memory_write(self):
        """Record memory write step."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.memory_write(
                entity_type="user_fact",
                operation="add",
                data={"fact": "User prefers dark mode"},
            )

        step = t.trace.steps[0]
        assert isinstance(step, MemoryWriteStep)
        assert step.entity_type == "user_fact"
        assert step.operation == "add"

    def test_interrupt(self):
        """Record interrupt step."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.interrupt(
                prompt="Do you want to proceed?",
                response="Yes",
                wait_duration_ms=5000,
            )

        step = t.trace.steps[0]
        assert isinstance(step, InterruptStep)
        assert step.prompt == "Do you want to proceed?"
        assert step.wait_duration_ms == 5000

    def test_state_change(self):
        """Record state change step."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.state_change(
                state_key="mode",
                old_value="idle",
                new_value="processing",
                reason="User request received",
            )

        step = t.trace.steps[0]
        assert isinstance(step, StateChangeStep)
        assert step.state_key == "mode"
        assert step.old_value == "idle"
        assert step.new_value == "processing"

    def test_final_output(self):
        """Record final output step."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.final_output(content="Here is your answer: 42")

        step = t.trace.steps[0]
        assert isinstance(step, FinalOutputStep)
        assert step.content == "Here is your answer: 42"

    def test_final_output_with_format(self):
        """Record final output with format."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.final_output(
                content={"result": 42},
                format="json",
            )

        step = t.trace.steps[0]
        assert step.format == "json"


class TestParentStepNesting:
    """Tests for parent_step_id nesting (T079)."""

    def test_explicit_parent_step_id(self):
        """Steps can have explicit parent_step_id."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            llm_id = t.llm_call(model="gpt-4", input="hi", output="hello")
            t.tool_call(
                tool_name="search",
                arguments={},
                result={},
                parent_step_id=llm_id,
            )

        assert t.trace.steps[1].parent_step_id == llm_id

    def test_nested_context_manager(self):
        """nested() context sets parent_step_id automatically."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            llm_id = t.llm_call(model="gpt-4", input="hi", output="hello")

            with t.nested(llm_id):
                t.tool_call(tool_name="a", arguments={}, result={})
                t.tool_call(tool_name="b", arguments={}, result={})

            # After nested context, steps have no parent
            t.final_output(content="done")

        # Steps 1 and 2 (tools) should have llm_id as parent
        assert t.trace.steps[1].parent_step_id == llm_id
        assert t.trace.steps[2].parent_step_id == llm_id
        # Step 3 (final) should have no parent
        assert t.trace.steps[3].parent_step_id is None


class TestJsonSerialization:
    """Tests for to_json() and save() (T078)."""

    def test_to_json(self):
        """to_json() produces valid JSON."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.llm_call(model="gpt-4", input="hi", output="hello")

        json_str = t.to_json()
        parsed = json.loads(json_str)
        assert parsed["agent_info"]["name"] == "test"
        assert len(parsed["steps"]) == 1

    def test_to_json_with_indent(self):
        """to_json() supports indentation."""
        with Tracer.run(agent_info={"name": "test"}) as t:
            t.llm_call(model="gpt-4", input="hi", output="hello")

        json_str = t.to_json(indent=2)
        assert "\n" in json_str  # Indented output has newlines

    def test_save(self):
        """save() writes trace to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with Tracer.run(agent_info={"name": "test"}) as t:
                t.llm_call(model="gpt-4", input="hi", output="hello")

            path = t.save(Path(tmpdir) / "trace.json")
            assert path.exists()

            with open(path) as f:
                data = json.load(f)
            assert data["agent_info"]["name"] == "test"

    def test_save_creates_directories(self):
        """save() creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with Tracer.run(agent_info={"name": "test"}) as t:
                t.llm_call(model="gpt-4", input="hi", output="hello")

            nested_path = Path(tmpdir) / "a" / "b" / "c" / "trace.json"
            path = t.save(nested_path)
            assert path.exists()


class TestFullTrace:
    """Integration tests for complete trace scenarios."""

    def test_complete_agent_trace(self):
        """Record a complete agent conversation."""
        with Tracer.run(
            agent_info={"name": "assistant", "version": "1.0"},
            task_info={"goal": "Answer user question"},
        ) as t:
            t.user_input(content="What is 2+2?")

            llm_id = t.llm_call(
                model="gpt-4",
                input="What is 2+2?",
                output="Let me calculate that for you.",
                tokens_in=10,
                tokens_out=8,
            )

            with t.nested(llm_id):
                t.tool_call(
                    tool_name="calculator",
                    arguments={"expression": "2+2"},
                    result=4,
                    latency_ms=5,
                )

            t.llm_call(
                model="gpt-4",
                input="Calculator returned 4",
                output="2+2 equals 4.",
                tokens_in=8,
                tokens_out=6,
            )

            t.final_output(content="2+2 equals 4.")

        trace = t.get_trace()
        assert len(trace.steps) == 5
        assert trace.total_tokens() == 32
        assert trace.total_tool_calls() == 1

        # Verify step types
        assert isinstance(trace.steps[0], UserInputStep)
        assert isinstance(trace.steps[1], LLMCallStep)
        assert isinstance(trace.steps[2], ToolCallStep)
        assert isinstance(trace.steps[3], LLMCallStep)
        assert isinstance(trace.steps[4], FinalOutputStep)

        # Verify nesting
        assert trace.steps[2].parent_step_id == llm_id
