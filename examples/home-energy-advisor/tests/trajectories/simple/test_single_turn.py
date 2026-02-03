"""Simple single-turn evaluation tests (Level 2).

These tests demonstrate the simplest way to evaluate your LangGraph agent
with ContextForge. No personas, scenarios, or simulation runners - just:

1. Build your agent
2. Call evaluate_agent()
3. Check the result

This is the recommended starting point for most users.
"""

import pytest

from context_forge.evaluation import evaluate_agent, evaluate_trace
from context_forge.graders.judges.backends import OllamaBackend

from src.memory.helpers import get_profile_from_store


def ollama_available() -> bool:
    """Check if Ollama is available."""
    try:
        backend = OllamaBackend(model="llama3.2")
        return backend.is_available()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Basic Evaluation Tests
# ---------------------------------------------------------------------------


class TestSimpleEvaluation:
    """Basic tests showing the simplest evaluation pattern."""

    @pytest.mark.integration
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    async def test_simple_question(self, advisor_graph, store_with_profile):
        """Evaluate a simple question - no memory updates expected.

        This is the simplest possible test: ask a question and check
        that the agent responds without any evaluation failures.
        """
        result = evaluate_agent(
            graph=advisor_graph,
            message="What time should I charge my EV tonight?",
            store=store_with_profile,
            user_id="test_user",
            print_result=True,  # Show the report
        )

        # Basic checks
        assert result.response is not None, "Agent should respond"
        assert result.trace is not None, "Trace should be captured"

        # The grader should pass (no memory issues with simple question)
        print(f"\nPassed: {result.passed}")
        print(f"Score: {result.score}")

    @pytest.mark.integration
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    async def test_memory_update(self, advisor_graph_stale, store_with_stale_profile):
        """Evaluate when user mentions new information.

        The profile has work_schedule="Office 9-5" (stale).
        User says they now work from home.
        Agent should update the profile.

        This tests the core memory hygiene scenario.
        """
        result = evaluate_agent(
            graph=advisor_graph_stale,
            message="I work from home now. When should I charge my EV?",
            store=store_with_stale_profile,
            user_id="stale_user",
            print_result=True,
        )

        # Check the trace captured memory operations
        from context_forge.core.trace import MemoryWriteStep
        memory_writes = [
            s for s in result.trace.steps
            if isinstance(s, MemoryWriteStep)
        ]

        print(f"\nMemory writes captured: {len(memory_writes)}")
        for write in memory_writes:
            if write.changes:
                for change in write.changes:
                    print(f"  {change.path}: {change.old_value} -> {change.new_value}")

        # Check if profile was updated in store
        updated_profile = get_profile_from_store(
            store_with_stale_profile,
            "stale_user",
        )
        print(f"\nFinal work_schedule: {updated_profile.household.work_schedule}")

        # If agent updated correctly, grader should pass
        # If agent missed the fact, LLM judge should catch it
        if not result.passed:
            print("\nEvaluation failed - checking errors:")
            for error in result.errors:
                print(f"  [{error.check_name}] {error.description}")


# ---------------------------------------------------------------------------
# Deterministic-Only Tests (No Ollama Required)
# ---------------------------------------------------------------------------


class TestDeterministicEvaluation:
    """Tests that run without Ollama (deterministic checks only)."""

    @pytest.mark.integration
    async def test_corruption_detection(self, advisor_graph, store_with_profile):
        """Test that data corruption is detected.

        Uses only the deterministic grader (no LLM needed).
        """
        result = evaluate_agent(
            graph=advisor_graph,
            message="What's my current solar capacity?",
            store=store_with_profile,
            user_id="test_user",
            graders=["memory_corruption"],  # Deterministic only
            print_result=True,
        )

        # Should pass - no corruption expected for read-only query
        print(f"\nCorruption check passed: {result.passed}")


# ---------------------------------------------------------------------------
# Trace-Only Evaluation (No Agent Run)
# ---------------------------------------------------------------------------


class TestTraceEvaluation:
    """Tests showing how to evaluate an existing trace."""

    @pytest.mark.integration
    def test_evaluate_existing_trace(self):
        """Evaluate a trace loaded from file or created manually.

        This is useful when:
        - You have traces from production
        - You want to re-evaluate old traces with new graders
        - You're debugging a specific trace
        """
        from datetime import datetime, timezone
        from context_forge.core.trace import (
            TraceRun,
            UserInputStep,
            MemoryReadStep,
            MemoryWriteStep,
            FinalOutputStep,
        )
        from context_forge.core.types import AgentInfo, FieldChange

        # Create a synthetic trace (or load from file)
        trace = TraceRun(
            run_id="test-trace-001",
            started_at=datetime.now(timezone.utc),
            agent_info=AgentInfo(name="test_agent", version="1.0.0"),
            steps=[
                UserInputStep(
                    step_id="step-1",
                    timestamp=datetime.now(timezone.utc),
                    content="I upgraded my solar to 12kW",
                ),
                MemoryReadStep(
                    step_id="step-2",
                    timestamp=datetime.now(timezone.utc),
                    query={"namespace": ["profiles", "user_123"], "key": "profile"},
                    results=[{"equipment": {"solar_capacity_kw": 7.5}}],
                    match_count=1,
                ),
                MemoryWriteStep(
                    step_id="step-3",
                    timestamp=datetime.now(timezone.utc),
                    namespace=["profiles", "user_123"],
                    key="profile",
                    operation="add",
                    data={"equipment": {"solar_capacity_kw": 12.0}},
                    changes=[
                        FieldChange(
                            path="$.equipment.solar_capacity_kw",
                            old_value=7.5,
                            new_value=12.0,
                        ),
                    ],
                ),
                FinalOutputStep(
                    step_id="step-4",
                    timestamp=datetime.now(timezone.utc),
                    content="Updated your solar capacity to 12kW!",
                ),
            ],
        )

        # Evaluate the trace
        result = evaluate_trace(
            trace=trace,
            graders=["memory_corruption"],  # No Ollama needed
            print_result=True,
        )

        # This should pass - correct update, no corruption
        assert result.passed, "Trace should pass corruption check"
        print(f"\nTrace evaluation passed: {result.passed}")
