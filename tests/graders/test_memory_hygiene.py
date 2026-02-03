"""Tests for Memory Hygiene evaluation.

Tests both:
- MemoryCorruptionGrader: Deterministic invariant checks (data corruption)
- MemoryHygieneJudge: LLM-based semantic evaluation (via HybridMemoryHygieneGrader)
"""

import pytest
from datetime import datetime, timezone

from context_forge.core.trace import (
    LLMCallStep,
    MemoryReadStep,
    MemoryWriteStep,
    TraceRun,
    UserInputStep,
    FinalOutputStep,
)
from context_forge.core.types import AgentInfo, FieldChange
from context_forge.graders import (
    HybridMemoryHygieneGrader,
    MemoryCorruptionGrader,
)
from context_forge.graders.base import Severity


# =============================================================================
# Test Fixtures
# =============================================================================


def create_base_trace(run_id: str = "test-trace") -> TraceRun:
    """Create a base trace with common metadata."""
    return TraceRun(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        agent_info=AgentInfo(name="test_agent", version="1.0.0"),
        steps=[],
    )


@pytest.fixture
def good_trace() -> TraceRun:
    """A trace where everything works correctly.

    User says they upgraded solar, and it gets saved properly.
    """
    trace = create_base_trace("good-trace")
    trace.steps = [
        # User input
        UserInputStep(
            step_id="step-1",
            timestamp=datetime.now(timezone.utc),
            content="I just upgraded my solar panels to 10kW.",
        ),
        # Memory read (existing profile)
        MemoryReadStep(
            step_id="step-2",
            timestamp=datetime.now(timezone.utc),
            query={"namespace": ["profiles", "user_123"], "key": "profile"},
            results=[{
                "equipment": {"solar_capacity_kw": 7.5, "ev_model": "Tesla Model 3"},
                "household": {"work_schedule": "Office 9-5"},
            }],
            match_count=1,
        ),
        # Memory write (correctly updates solar)
        MemoryWriteStep(
            step_id="step-3",
            timestamp=datetime.now(timezone.utc),
            namespace=["profiles", "user_123"],
            key="profile",
            operation="put",
            data={"equipment": {"solar_capacity_kw": 10.0}},
            changes=[
                FieldChange(
                    path="$.equipment.solar_capacity_kw",
                    old_value=7.5,
                    new_value=10.0,
                ),
            ],
            triggered_by_step_id="step-1",
        ),
        # Final output
        FinalOutputStep(
            step_id="step-4",
            timestamp=datetime.now(timezone.utc),
            content="Great! I've updated your solar capacity to 10kW.",
        ),
    ]
    return trace


@pytest.fixture
def bad_trace_missed_fact() -> TraceRun:
    """A trace where the user states a fact but it's NOT saved.

    User says "I work from home now" but memory still has "Office 9-5".
    The memorizer should have updated this but didn't.

    NOTE: This is a SEMANTIC issue that requires LLM to detect.
    The MemoryCorruptionGrader won't catch this.
    """
    trace = create_base_trace("bad-missed-fact")
    trace.steps = [
        # User input with new fact
        UserInputStep(
            step_id="step-1",
            timestamp=datetime.now(timezone.utc),
            content="I started working from home last month. When should I charge my EV?",
        ),
        # Memory read shows old work schedule
        MemoryReadStep(
            step_id="step-2",
            timestamp=datetime.now(timezone.utc),
            query={"namespace": ["profiles", "user_123"], "key": "profile"},
            results=[{
                "equipment": {"solar_capacity_kw": 7.5, "ev_model": "Tesla Model 3"},
                "household": {"work_schedule": "Office 9-5"},  # OLD - should be updated!
            }],
            match_count=1,
        ),
        # NO memory write! The fact was missed.
        # Final output (based on stale data)
        FinalOutputStep(
            step_id="step-3",
            timestamp=datetime.now(timezone.utc),
            content="Based on your commute schedule, I recommend charging overnight.",
        ),
    ]
    return trace


@pytest.fixture
def bad_trace_hallucination() -> TraceRun:
    """A trace where the agent saves something the user NEVER said.

    User asks about EV charging, but agent writes "planning to buy solar"
    which the user never mentioned.

    NOTE: This is a SEMANTIC issue that requires LLM to detect.
    """
    trace = create_base_trace("bad-hallucination")
    trace.steps = [
        # User input - just asks about EV charging
        UserInputStep(
            step_id="step-1",
            timestamp=datetime.now(timezone.utc),
            content="When should I charge my Tesla tonight?",
        ),
        # Memory read
        MemoryReadStep(
            step_id="step-2",
            timestamp=datetime.now(timezone.utc),
            query={"namespace": ["profiles", "user_123"], "key": "profile"},
            results=[{
                "equipment": {"ev_model": "Tesla Model 3"},
            }],
            match_count=1,
        ),
        # Memory write with HALLUCINATED data
        MemoryWriteStep(
            step_id="step-3",
            timestamp=datetime.now(timezone.utc),
            namespace=["profiles", "user_123"],
            key="profile",
            operation="put",
            data={"notes": [{"topic": "future_plans", "content": "Planning to install solar panels"}]},
            changes=[
                FieldChange(
                    path="$.notes",
                    old_value=None,
                    new_value=[{"topic": "future_plans", "content": "Planning to install solar panels"}],
                ),
            ],
            triggered_by_step_id="step-1",
        ),
        FinalOutputStep(
            step_id="step-4",
            timestamp=datetime.now(timezone.utc),
            content="I recommend charging during off-peak hours.",
        ),
    ]
    return trace


@pytest.fixture
def bad_trace_data_corruption() -> TraceRun:
    """A trace where existing data is CORRUPTED (deleted without replacement).

    User updates their solar capacity, but the write also nullifies
    their EV model which should have been preserved.

    NOTE: This is an INVARIANT violation - always wrong regardless of path.
    The MemoryCorruptionGrader WILL catch this.
    """
    trace = create_base_trace("bad-data-corruption")
    trace.steps = [
        UserInputStep(
            step_id="step-1",
            timestamp=datetime.now(timezone.utc),
            content="I upgraded my solar to 12kW.",
        ),
        MemoryReadStep(
            step_id="step-2",
            timestamp=datetime.now(timezone.utc),
            query={"namespace": ["profiles", "user_123"], "key": "profile"},
            results=[{
                "equipment": {
                    "solar_capacity_kw": 7.5,
                    "ev_model": "Tesla Model 3",  # This should be preserved!
                    "ev_battery_kwh": 75.0,
                },
            }],
            match_count=1,
        ),
        # Memory write with DATA CORRUPTION - ev_model becomes null
        MemoryWriteStep(
            step_id="step-3",
            timestamp=datetime.now(timezone.utc),
            namespace=["profiles", "user_123"],
            key="profile",
            operation="put",
            data={"equipment": {"solar_capacity_kw": 12.0, "ev_model": None}},
            changes=[
                FieldChange(
                    path="$.equipment.solar_capacity_kw",
                    old_value=7.5,
                    new_value=12.0,
                ),
                FieldChange(
                    path="$.equipment.ev_model",
                    old_value="Tesla Model 3",
                    new_value=None,  # DATA CORRUPTION!
                ),
            ],
            triggered_by_step_id="step-1",
        ),
        FinalOutputStep(
            step_id="step-4",
            timestamp=datetime.now(timezone.utc),
            content="Updated your solar capacity to 12kW.",
        ),
    ]
    return trace


# =============================================================================
# Deterministic Grader Tests (MemoryCorruptionGrader)
# =============================================================================


class TestCorruptionGrader:
    """Tests for the MemoryCorruptionGrader (invariant checks only)."""

    def test_good_trace_passes(self, good_trace):
        """A good trace should pass with no corruption detected."""
        grader = MemoryCorruptionGrader()
        result = grader.grade(good_trace)

        assert result.passed is True
        assert result.score == 1.0
        assert len(result.errors) == 0

    def test_detects_data_corruption(self, bad_trace_data_corruption):
        """Should detect when existing data is deleted/nullified."""
        grader = MemoryCorruptionGrader()
        result = grader.grade(bad_trace_data_corruption)

        assert result.passed is False
        assert len(result.errors) >= 1

        # Find the corruption error
        corruption_errors = [e for e in result.errors if e.check_name == "data_corruption"]
        assert len(corruption_errors) == 1
        assert "ev_model" in corruption_errors[0].description or "deleted" in corruption_errors[0].description.lower()

    def test_missed_fact_not_detected(self, bad_trace_missed_fact):
        """Missed facts are SEMANTIC issues - corruption grader should pass.

        This demonstrates the separation of concerns:
        - MemoryCorruptionGrader: Only checks invariants
        - MemoryHygieneJudge: Handles semantic issues (missed facts)
        """
        grader = MemoryCorruptionGrader()
        result = grader.grade(bad_trace_missed_fact)

        # Corruption grader should PASS because no data was corrupted
        # The missed fact is a semantic issue for the LLM judge
        assert result.passed is True
        assert len(result.errors) == 0

    def test_hallucination_not_detected(self, bad_trace_hallucination):
        """Hallucinations are SEMANTIC issues - corruption grader should pass.

        This demonstrates the separation of concerns:
        - MemoryCorruptionGrader: Only checks invariants
        - MemoryHygieneJudge: Handles semantic issues (hallucinations)
        """
        grader = MemoryCorruptionGrader()
        result = grader.grade(bad_trace_hallucination)

        # Corruption grader should PASS because no data was corrupted
        # The hallucination is a semantic issue for the LLM judge
        assert result.passed is True
        assert len(result.errors) == 0


# =============================================================================
# LLM Judge Tests (require Ollama)
# =============================================================================


def ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        from context_forge.graders.judges.backends import OllamaBackend
        backend = OllamaBackend(model="llama3.2")
        return backend.is_available()
    except Exception:
        return False


@pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
class TestSemanticJudge:
    """Tests for semantic evaluation (LLM-based via HybridMemoryHygieneGrader)."""

    def test_good_trace_passes(self, good_trace):
        """A good trace should pass the semantic evaluation."""
        from context_forge.graders.judges.backends import OllamaBackend

        grader = HybridMemoryHygieneGrader(
            llm_backend=OllamaBackend(model="llama3.2")
        )
        result = grader.grade(good_trace)

        print(f"Score: {result.score}, Passed: {result.passed}")
        for e in result.evidence:
            print(f"  [{e.severity.value}] {e.check_name}: {e.description}")

    def test_detects_missed_fact(self, bad_trace_missed_fact):
        """LLM should detect that user stated a fact that wasn't saved."""
        from context_forge.graders.judges.backends import OllamaBackend

        grader = HybridMemoryHygieneGrader(
            llm_backend=OllamaBackend(model="llama3.2"),
        )
        result = grader.grade(bad_trace_missed_fact)

        print(f"\nMissed Fact Test:")
        print(f"Score: {result.score}, Passed: {result.passed}")
        for e in result.evidence:
            print(f"  [{e.severity.value}] {e.check_name}: {e.description}")

        # The LLM should identify the missed fact about working from home
        missed_fact_evidence = [
            e for e in result.evidence
            if e.check_name in ("missed_fact", "possible_missed_fact")
        ]
        # We expect the LLM to catch this
        assert len(missed_fact_evidence) >= 1 or result.passed is False

    def test_detects_hallucination(self, bad_trace_hallucination):
        """LLM should detect that agent saved something user didn't say."""
        from context_forge.graders.judges.backends import OllamaBackend

        grader = HybridMemoryHygieneGrader(
            llm_backend=OllamaBackend(model="llama3.2"),
        )
        result = grader.grade(bad_trace_hallucination)

        print(f"\nHallucination Test:")
        print(f"Score: {result.score}, Passed: {result.passed}")
        for e in result.evidence:
            print(f"  [{e.severity.value}] {e.check_name}: {e.description}")

        # The LLM should identify the hallucination about solar plans
        hallucination_evidence = [
            e for e in result.evidence
            if e.check_name in ("hallucination", "possible_hallucination")
        ]
        # We expect the LLM to catch this
        assert len(hallucination_evidence) >= 1 or result.passed is False


# =============================================================================
# Smoke Tests
# =============================================================================


def test_corruption_grader_smoke():
    """Quick smoke test that MemoryCorruptionGrader works."""
    trace = create_base_trace("smoke-test")
    trace.steps = [
        UserInputStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            content="Hello",
        ),
        MemoryWriteStep(
            step_id="s2",
            timestamp=datetime.now(timezone.utc),
            namespace=["test"],
            key="data",
            operation="put",
            data={"foo": "bar"},
            changes=[FieldChange(path="$.foo", old_value=None, new_value="bar")],
        ),
    ]

    grader = MemoryCorruptionGrader()
    result = grader.grade(trace)

    assert result.grader_name == "memory_corruption"
    assert isinstance(result.passed, bool)
    assert 0.0 <= result.score <= 1.0


def test_hybrid_grader_without_llm():
    """HybridMemoryHygieneGrader should work without LLM (corruption only)."""
    trace = create_base_trace("hybrid-no-llm")
    trace.steps = [
        UserInputStep(
            step_id="s1",
            timestamp=datetime.now(timezone.utc),
            content="Hello",
        ),
        MemoryWriteStep(
            step_id="s2",
            timestamp=datetime.now(timezone.utc),
            namespace=["test"],
            key="data",
            operation="put",
            data={"foo": "bar"},
            changes=[FieldChange(path="$.foo", old_value=None, new_value="bar")],
        ),
    ]

    # No LLM backend - only corruption checks run
    grader = HybridMemoryHygieneGrader()
    result = grader.grade(trace)

    assert result.grader_name == "hybrid_memory_hygiene"
    assert result.passed is True
    assert "corruption" in result.metadata["layers_run"]
    assert "semantic" not in result.metadata["layers_run"]
