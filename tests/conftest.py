"""
Shared pytest fixtures for ContextForge tests.

These fixtures provide reusable test data and utilities.
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List

# NOTE: These imports will work once the package is implemented
# from context_forge.core.trace_spec import (
#     TraceRun, TraceStep, StepType, TraceBudgets, TraceOutcome,
#     AgentInfo, TaskInfo, TokenUsage
# )


# =============================================================================
# Mock Data Classes (until implementation exists)
# =============================================================================

class MockStepType:
    USER_INPUT = "user_input"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    FINAL_OUTPUT = "final_output"
    ERROR = "error"


class MockTraceStep:
    def __init__(self, step_id, step_type, timestamp=None, data=None, actor=None):
        self.step_id = step_id
        self.step_type = step_type
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.data = data or {}
        self.actor = actor
        self.timing = None
        self.error = None


class MockTraceBudgets:
    def __init__(self):
        self.tokens_input = 0
        self.tokens_output = 0
        self.tokens_total = 0
        self.tool_calls_total = 0
        self.retrieval_calls_total = 0
        self.latency_total_ms = 0


class MockTraceOutcome:
    def __init__(self, status="success", reason=None):
        self.status = status
        self.reason = reason


class MockTraceRun:
    def __init__(self, **kwargs):
        self.trace_version = kwargs.get("trace_version", "1.0.0")
        self.run_id = kwargs.get("run_id", "test-run-123")
        self.started_at = kwargs.get("started_at", datetime.now(timezone.utc))
        self.ended_at = kwargs.get("ended_at")
        self.steps: List[MockTraceStep] = kwargs.get("steps", [])
        self.budgets = kwargs.get("budgets", MockTraceBudgets())
        self.outcome = kwargs.get("outcome")
        self.capabilities = kwargs.get("capabilities", {
            "llm_calls": False,
            "tool_calls": False,
            "retrieval": False,
            "memory": False,
            "multi_agent": False,
        })


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_timestamp():
    """Provide a fixed timestamp for deterministic tests."""
    return datetime(2025, 1, 14, 10, 0, 0)


@pytest.fixture
def minimal_trace():
    """Create a minimal valid trace with no steps."""
    return MockTraceRun(
        run_id="minimal-trace-001",
        steps=[],
        outcome=MockTraceOutcome(status="success")
    )


@pytest.fixture
def simple_trace(sample_timestamp):
    """Create a simple trace with user input and output."""
    steps = [
        MockTraceStep(
            step_id=1,
            step_type=MockStepType.USER_INPUT,
            timestamp=sample_timestamp,
            data={"content": "Hello"}
        ),
        MockTraceStep(
            step_id=2,
            step_type=MockStepType.FINAL_OUTPUT,
            timestamp=sample_timestamp + timedelta(seconds=1),
            data={"content": "Hi there!"}
        ),
    ]

    trace = MockTraceRun(
        run_id="simple-trace-001",
        started_at=sample_timestamp,
        ended_at=sample_timestamp + timedelta(seconds=1),
        steps=steps,
        outcome=MockTraceOutcome(status="success")
    )
    return trace


@pytest.fixture
def trace_with_llm_calls(sample_timestamp):
    """Create a trace with LLM calls and token usage."""
    steps = [
        MockTraceStep(
            step_id=1,
            step_type=MockStepType.USER_INPUT,
            timestamp=sample_timestamp,
            data={"content": "What is 2+2?"}
        ),
        MockTraceStep(
            step_id=2,
            step_type=MockStepType.LLM_CALL,
            timestamp=sample_timestamp + timedelta(milliseconds=100),
            data={
                "model": "gpt-4",
                "output": {"content": "2+2 equals 4."},
                "usage": {"input_tokens": 10, "output_tokens": 8, "total_tokens": 18}
            }
        ),
        MockTraceStep(
            step_id=3,
            step_type=MockStepType.FINAL_OUTPUT,
            timestamp=sample_timestamp + timedelta(milliseconds=200),
            data={"content": "2+2 equals 4."}
        ),
    ]

    budgets = MockTraceBudgets()
    budgets.tokens_total = 18
    budgets.tokens_input = 10
    budgets.tokens_output = 8

    trace = MockTraceRun(
        run_id="llm-trace-001",
        started_at=sample_timestamp,
        steps=steps,
        budgets=budgets,
        outcome=MockTraceOutcome(status="success")
    )
    trace.capabilities["llm_calls"] = True
    return trace


@pytest.fixture
def trace_with_tools(sample_timestamp):
    """Create a trace with tool calls."""
    steps = [
        MockTraceStep(
            step_id=1,
            step_type=MockStepType.USER_INPUT,
            timestamp=sample_timestamp,
            data={"content": "What's the weather?"}
        ),
        MockTraceStep(
            step_id=2,
            step_type=MockStepType.LLM_CALL,
            timestamp=sample_timestamp + timedelta(milliseconds=100),
            data={
                "model": "gpt-4",
                "output": {"tool_calls": [{"name": "weather", "args": {"city": "Paris"}}]}
            }
        ),
        MockTraceStep(
            step_id=3,
            step_type=MockStepType.TOOL_CALL,
            timestamp=sample_timestamp + timedelta(milliseconds=200),
            data={
                "tool": "weather",
                "args": {"city": "Paris"},
                "result": {"temp": 22, "condition": "sunny"},
                "status": "success"
            }
        ),
        MockTraceStep(
            step_id=4,
            step_type=MockStepType.LLM_CALL,
            timestamp=sample_timestamp + timedelta(milliseconds=300),
            data={
                "model": "gpt-4",
                "output": {"content": "It's sunny in Paris, 22°C."}
            }
        ),
        MockTraceStep(
            step_id=5,
            step_type=MockStepType.FINAL_OUTPUT,
            timestamp=sample_timestamp + timedelta(milliseconds=400),
            data={"content": "It's sunny in Paris, 22°C."}
        ),
    ]

    budgets = MockTraceBudgets()
    budgets.tool_calls_total = 1
    budgets.tokens_total = 50

    trace = MockTraceRun(
        run_id="tool-trace-001",
        started_at=sample_timestamp,
        steps=steps,
        budgets=budgets,
        outcome=MockTraceOutcome(status="success")
    )
    trace.capabilities["llm_calls"] = True
    trace.capabilities["tool_calls"] = True
    return trace


@pytest.fixture
def multi_agent_trace(sample_timestamp):
    """Create a trace with multiple agents."""
    steps = [
        MockTraceStep(
            step_id=1,
            step_type=MockStepType.USER_INPUT,
            timestamp=sample_timestamp,
            data={"content": "Book a flight"}
        ),
        MockTraceStep(
            step_id=2,
            step_type=MockStepType.LLM_CALL,
            timestamp=sample_timestamp + timedelta(milliseconds=100),
            data={"model": "gpt-4", "output": {"content": "Planning..."}},
            actor="planner"
        ),
        MockTraceStep(
            step_id=3,
            step_type=MockStepType.TOOL_CALL,
            timestamp=sample_timestamp + timedelta(milliseconds=200),
            data={"tool": "flight_search", "args": {}, "result": {}},
            actor="executor"
        ),
    ]

    trace = MockTraceRun(
        run_id="multi-agent-trace-001",
        started_at=sample_timestamp,
        steps=steps,
        outcome=MockTraceOutcome(status="success")
    )
    trace.capabilities["llm_calls"] = True
    trace.capabilities["tool_calls"] = True
    trace.capabilities["multi_agent"] = True
    return trace


@pytest.fixture
def failing_trace(sample_timestamp):
    """Create a trace that ended with an error."""
    steps = [
        MockTraceStep(
            step_id=1,
            step_type=MockStepType.USER_INPUT,
            timestamp=sample_timestamp,
            data={"content": "Do something risky"}
        ),
        MockTraceStep(
            step_id=2,
            step_type=MockStepType.ERROR,
            timestamp=sample_timestamp + timedelta(milliseconds=100),
            data={
                "error_type": "RuntimeError",
                "message": "Something went wrong",
                "recoverable": False
            }
        ),
    ]

    trace = MockTraceRun(
        run_id="failing-trace-001",
        started_at=sample_timestamp,
        steps=steps,
        outcome=MockTraceOutcome(status="error", reason="RuntimeError: Something went wrong")
    )
    return trace


@pytest.fixture
def budget_exceeded_trace(sample_timestamp):
    """Create a trace that exceeds typical budget limits."""
    # Create many LLM calls with high token usage
    steps = [
        MockTraceStep(
            step_id=1,
            step_type=MockStepType.USER_INPUT,
            timestamp=sample_timestamp,
            data={"content": "Complex task"}
        )
    ]

    # Add 10 LLM calls with 1000 tokens each
    for i in range(10):
        steps.append(MockTraceStep(
            step_id=i + 2,
            step_type=MockStepType.LLM_CALL,
            timestamp=sample_timestamp + timedelta(seconds=i),
            data={
                "model": "gpt-4",
                "usage": {"input_tokens": 500, "output_tokens": 500, "total_tokens": 1000}
            }
        ))

    # Add 15 tool calls
    for i in range(15):
        steps.append(MockTraceStep(
            step_id=i + 12,
            step_type=MockStepType.TOOL_CALL,
            timestamp=sample_timestamp + timedelta(seconds=10 + i),
            data={"tool": "some_tool", "args": {"i": i}, "result": {}}
        ))

    budgets = MockTraceBudgets()
    budgets.tokens_total = 10000
    budgets.tool_calls_total = 15

    trace = MockTraceRun(
        run_id="budget-exceeded-trace-001",
        started_at=sample_timestamp,
        steps=steps,
        budgets=budgets,
        outcome=MockTraceOutcome(status="success")
    )
    trace.capabilities["llm_calls"] = True
    trace.capabilities["tool_calls"] = True
    return trace
