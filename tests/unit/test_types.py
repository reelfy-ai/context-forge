"""Tests for core type definitions.

Tests T007: StepType enum
"""

import pytest

from context_forge.core.types import (
    AgentInfo,
    ResourceImpact,
    RetrievalResult,
    StepType,
    TaskInfo,
)


class TestStepType:
    """Tests for StepType enum."""

    def test_step_type_values(self):
        """StepType has all required values."""
        assert StepType.USER_INPUT == "user_input"
        assert StepType.LLM_CALL == "llm_call"
        assert StepType.TOOL_CALL == "tool_call"
        assert StepType.RETRIEVAL == "retrieval"
        assert StepType.MEMORY_READ == "memory_read"
        assert StepType.MEMORY_WRITE == "memory_write"
        assert StepType.STATE_CHANGE == "state_change"
        assert StepType.INTERRUPT == "interrupt"
        assert StepType.FINAL_OUTPUT == "final_output"

    def test_step_type_is_string_enum(self):
        """StepType values are strings."""
        for step_type in StepType:
            assert isinstance(step_type.value, str)

    def test_step_type_count(self):
        """StepType has exactly 9 members."""
        assert len(StepType) == 9


class TestAgentInfo:
    """Tests for AgentInfo model."""

    def test_minimal_agent_info(self):
        """AgentInfo requires only name."""
        info = AgentInfo(name="test-agent")
        assert info.name == "test-agent"
        assert info.version is None
        assert info.framework is None

    def test_full_agent_info(self):
        """AgentInfo accepts all fields."""
        info = AgentInfo(
            name="my-agent",
            version="1.0.0",
            framework="langchain",
            framework_version="0.1.0",
        )
        assert info.name == "my-agent"
        assert info.version == "1.0.0"
        assert info.framework == "langchain"
        assert info.framework_version == "0.1.0"

    def test_agent_info_ignores_extra_fields(self):
        """AgentInfo ignores unknown fields."""
        info = AgentInfo(name="test", unknown_field="ignored")
        assert info.name == "test"
        assert not hasattr(info, "unknown_field")


class TestTaskInfo:
    """Tests for TaskInfo model."""

    def test_empty_task_info(self):
        """TaskInfo allows all optional fields."""
        info = TaskInfo()
        assert info.description is None
        assert info.goal is None
        assert info.input is None

    def test_full_task_info(self):
        """TaskInfo accepts all fields."""
        info = TaskInfo(
            description="Process user request",
            goal="Provide helpful response",
            input={"query": "hello"},
        )
        assert info.description == "Process user request"
        assert info.goal == "Provide helpful response"
        assert info.input == {"query": "hello"}


class TestResourceImpact:
    """Tests for ResourceImpact model."""

    def test_minimal_resource_impact(self):
        """ResourceImpact requires amount and unit."""
        impact = ResourceImpact(amount=0.05, unit="USD")
        assert impact.amount == 0.05
        assert impact.unit == "USD"
        assert impact.breakdown is None

    def test_resource_impact_with_breakdown(self):
        """ResourceImpact accepts breakdown."""
        impact = ResourceImpact(
            amount=100,
            unit="credits",
            breakdown={"compute": 80, "storage": 20},
        )
        assert impact.amount == 100
        assert impact.breakdown == {"compute": 80, "storage": 20}


class TestRetrievalResult:
    """Tests for RetrievalResult model."""

    def test_minimal_retrieval_result(self):
        """RetrievalResult requires only content."""
        result = RetrievalResult(content="Document text here")
        assert result.content == "Document text here"
        assert result.score is None
        assert result.metadata is None

    def test_full_retrieval_result(self):
        """RetrievalResult accepts all fields."""
        result = RetrievalResult(
            content="Relevant document",
            score=0.95,
            metadata={"source": "wiki", "page": 42},
        )
        assert result.content == "Relevant document"
        assert result.score == 0.95
        assert result.metadata == {"source": "wiki", "page": 42}

    def test_score_validation(self):
        """Score can be any float (no strict 0-1 validation)."""
        # Pydantic doesn't enforce range by default
        result = RetrievalResult(content="test", score=1.5)
        assert result.score == 1.5
