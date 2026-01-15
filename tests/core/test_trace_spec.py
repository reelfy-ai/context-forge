"""
Tests for the canonical trace specification.

These tests verify the TraceRun and TraceStep data structures
conform to Spec 001: Trace Schema.
"""

import pytest
from datetime import datetime


class TestTraceRunCreation:
    """Tests for TraceRun initialization and required fields."""

    def test_minimal_trace_has_required_fields(self, minimal_trace):
        """Minimal trace contains all required fields."""
        assert minimal_trace.trace_version is not None
        assert minimal_trace.run_id is not None
        assert minimal_trace.started_at is not None
        assert isinstance(minimal_trace.steps, list)

    def test_trace_version_is_semver(self, minimal_trace):
        """trace_version follows semver format."""
        version = minimal_trace.trace_version
        parts = version.split(".")
        assert len(parts) == 3, "Version should have 3 parts"
        assert all(p.isdigit() for p in parts), "All parts should be numeric"

    def test_run_id_is_string(self, minimal_trace):
        """run_id is a non-empty string."""
        assert isinstance(minimal_trace.run_id, str)
        assert len(minimal_trace.run_id) > 0


class TestTraceSteps:
    """Tests for TraceStep structure and ordering."""

    def test_steps_have_unique_ids(self, trace_with_tools):
        """All step_ids in a trace are unique."""
        step_ids = [s.step_id for s in trace_with_tools.steps]
        assert len(step_ids) == len(set(step_ids)), "Duplicate step IDs found"

    def test_steps_have_required_fields(self, simple_trace):
        """Each step has required fields."""
        for step in simple_trace.steps:
            assert step.step_id is not None
            assert step.step_type is not None
            assert step.timestamp is not None

    def test_step_ids_are_monotonic(self, trace_with_llm_calls):
        """step_ids should be monotonically increasing."""
        step_ids = [s.step_id for s in trace_with_llm_calls.steps]
        for i in range(1, len(step_ids)):
            assert step_ids[i] > step_ids[i-1], "step_ids should increase"


class TestTraceBudgets:
    """Tests for budget aggregation."""

    def test_budgets_initialized_to_zero(self, minimal_trace):
        """Budgets start at zero for empty trace."""
        budgets = minimal_trace.budgets
        assert budgets.tokens_total == 0
        assert budgets.tool_calls_total == 0

    def test_budgets_reflect_llm_calls(self, trace_with_llm_calls):
        """Budgets correctly sum token usage."""
        budgets = trace_with_llm_calls.budgets
        assert budgets.tokens_total == 18
        assert budgets.tokens_input == 10
        assert budgets.tokens_output == 8

    def test_budgets_count_tool_calls(self, trace_with_tools):
        """Budgets correctly count tool calls."""
        assert trace_with_tools.budgets.tool_calls_total == 1


class TestTraceCapabilities:
    """Tests for capability flag detection."""

    def test_minimal_trace_has_no_capabilities(self, minimal_trace):
        """Empty trace has all capabilities false."""
        for cap in minimal_trace.capabilities.values():
            assert cap is False

    def test_llm_trace_has_llm_capability(self, trace_with_llm_calls):
        """Trace with LLM calls has llm_calls capability."""
        assert trace_with_llm_calls.capabilities["llm_calls"] is True

    def test_tool_trace_has_tool_capability(self, trace_with_tools):
        """Trace with tool calls has tool_calls capability."""
        assert trace_with_tools.capabilities["tool_calls"] is True

    def test_multi_agent_trace_has_multi_agent_capability(self, multi_agent_trace):
        """Trace with actors has multi_agent capability."""
        assert multi_agent_trace.capabilities["multi_agent"] is True


class TestTraceOutcome:
    """Tests for trace outcome status."""

    def test_successful_trace_has_success_status(self, simple_trace):
        """Completed trace has success status."""
        assert simple_trace.outcome.status == "success"

    def test_failing_trace_has_error_status(self, failing_trace):
        """Failed trace has error status."""
        assert failing_trace.outcome.status == "error"
        assert failing_trace.outcome.reason is not None


class TestStepData:
    """Tests for step-specific data fields."""

    def test_llm_call_has_model(self, trace_with_llm_calls):
        """LLM call steps include model identifier."""
        llm_steps = [s for s in trace_with_llm_calls.steps
                     if s.step_type == "llm_call"]
        assert len(llm_steps) > 0
        assert "model" in llm_steps[0].data

    def test_tool_call_has_tool_name(self, trace_with_tools):
        """Tool call steps include tool name."""
        tool_steps = [s for s in trace_with_tools.steps
                      if s.step_type == "tool_call"]
        assert len(tool_steps) > 0
        assert "tool" in tool_steps[0].data

    def test_tool_call_has_args_and_result(self, trace_with_tools):
        """Tool call steps include args and result."""
        tool_steps = [s for s in trace_with_tools.steps
                      if s.step_type == "tool_call"]
        tool_step = tool_steps[0]
        assert "args" in tool_step.data
        assert "result" in tool_step.data


class TestMultiAgentSteps:
    """Tests for multi-agent trace features."""

    def test_steps_can_have_actor(self, multi_agent_trace):
        """Steps can specify an actor."""
        actors = [s.actor for s in multi_agent_trace.steps if s.actor]
        assert len(actors) > 0
        assert "planner" in actors
        assert "executor" in actors

    def test_different_actors_in_same_trace(self, multi_agent_trace):
        """Multiple different actors can exist in one trace."""
        unique_actors = set(s.actor for s in multi_agent_trace.steps if s.actor)
        assert len(unique_actors) >= 2
