# ContextForge Tests

This directory contains the test suite for ContextForge.

## Structure

```
tests/
├── core/               # Core data structure tests
│   ├── test_trace_spec.py
│   └── test_serialization.py
├── graders/            # Grader tests
│   ├── test_base.py
│   ├── test_budget.py
│   └── test_result.py
├── harness/            # Harness tests
│   ├── test_task.py
│   └── test_scenario.py
├── instrumentation/    # Tracer tests
│   └── test_tracer.py
├── conftest.py         # Shared fixtures
└── README.md
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=context_forge --cov-report=html

# Run specific test file
pytest tests/core/test_trace_spec.py

# Run tests matching pattern
pytest -k "test_budget"

# Run with verbose output
pytest -v
```

## Test Categories

### Unit Tests
- Fast, isolated tests
- No external dependencies
- Run on every commit

```bash
pytest tests/ -m "not integration"
```

### Integration Tests
- Test component interactions
- May use fixtures
- Run before merge

```bash
pytest tests/ -m integration
```

## Writing Tests

### Naming Convention
- Files: `test_<module>.py`
- Functions: `test_<behavior>_<condition>`
- Classes: `Test<Component>`

### Example Test

```python
import pytest
from context_forge.core.trace_spec import TraceRun, TraceStep, StepType


class TestTraceRun:
    """Tests for TraceRun dataclass."""

    def test_creates_with_required_fields(self):
        """TraceRun can be created with minimal fields."""
        trace = TraceRun()
        assert trace.trace_version == "1.0.0"
        assert trace.run_id is not None
        assert trace.steps == []

    def test_step_id_must_be_unique(self):
        """Duplicate step IDs raise validation error."""
        trace = TraceRun()
        trace.steps.append(TraceStep(step_id=1, step_type=StepType.USER_INPUT, timestamp=...))
        trace.steps.append(TraceStep(step_id=1, step_type=StepType.LLM_CALL, timestamp=...))

        with pytest.raises(ValidationError):
            trace.validate()
```

## Fixtures

Common fixtures are in `conftest.py`:

```python
@pytest.fixture
def sample_trace():
    """Create a minimal valid trace."""
    ...

@pytest.fixture
def trace_with_tools():
    """Create a trace with tool calls."""
    ...
```

## CI Requirements

All tests must be:
- **Deterministic**: Same result every run
- **Fast**: < 1 second per test
- **Isolated**: No external dependencies
- **Reproducible**: Work on any machine
