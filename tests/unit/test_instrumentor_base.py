"""Tests for base instrumentor classes.

Tests:
- T028: BaseInstrumentor interface
- T029: RedactionConfig
"""

import re
import tempfile
from pathlib import Path

import pytest

from context_forge.core.trace import TraceRun, UserInputStep
from context_forge.core.types import AgentInfo
from context_forge.exceptions import (
    InstrumentorAlreadyActiveError,
    InstrumentorNotActiveError,
)
from context_forge.instrumentation.base import BaseInstrumentor, RedactionConfig


class MockInstrumentor(BaseInstrumentor):
    """Mock instrumentor for testing base class."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hooks_installed = False
        self.hooks_removed = False

    @property
    def framework(self) -> str:
        return "mock"

    @property
    def framework_version(self) -> str:
        return "1.0.0"

    def _install_hooks(self) -> None:
        self.hooks_installed = True

    def _remove_hooks(self) -> None:
        self.hooks_removed = True


class TestRedactionConfig:
    """Tests for RedactionConfig (T029)."""

    def test_default_redaction_config(self):
        """Default config has expected patterns and fields."""
        config = RedactionConfig.default()
        assert config.enabled is True
        assert len(config.patterns) > 0
        assert "password" in config.field_names
        assert "api_key" in config.field_names

    def test_redact_email(self):
        """Email addresses are redacted."""
        config = RedactionConfig.default()
        text = "Contact us at test@example.com for help"
        result = config.redact(text)
        assert "test@example.com" not in result
        assert "[REDACTED]" in result

    def test_redact_ssn(self):
        """SSN patterns are redacted."""
        config = RedactionConfig.default()
        text = "SSN: 123-45-6789"
        result = config.redact(text)
        assert "123-45-6789" not in result

    def test_redact_disabled(self):
        """Redaction can be disabled."""
        config = RedactionConfig(enabled=False)
        text = "test@example.com"
        result = config.redact(text)
        assert result == text

    def test_custom_pattern(self):
        """Custom patterns work."""
        config = RedactionConfig(
            patterns=[re.compile(r"SECRET_\w+")],
            enabled=True,
        )
        text = "The key is SECRET_ABC123"
        result = config.redact(text)
        assert "SECRET_ABC123" not in result

    def test_should_redact_field(self):
        """Field name redaction detection works."""
        config = RedactionConfig()
        assert config.should_redact_field("password") is True
        assert config.should_redact_field("user_password") is True
        assert config.should_redact_field("api_key") is True
        assert config.should_redact_field("username") is False
        assert config.should_redact_field("email") is False

    def test_should_redact_field_disabled(self):
        """Field detection respects enabled flag."""
        config = RedactionConfig(enabled=False)
        assert config.should_redact_field("password") is False


class TestBaseInstrumentor:
    """Tests for BaseInstrumentor (T028)."""

    def test_initial_state(self):
        """Instrumentor starts inactive with no traces."""
        inst = MockInstrumentor()
        assert inst.is_active is False
        assert inst.get_traces() == []
        assert inst.hooks_installed is False

    def test_instrument_activates(self):
        """instrument() activates instrumentor."""
        inst = MockInstrumentor()
        result = inst.instrument()
        assert inst.is_active is True
        assert inst.hooks_installed is True
        assert result is inst  # Returns self for chaining

    def test_uninstrument_deactivates(self):
        """uninstrument() deactivates instrumentor."""
        inst = MockInstrumentor()
        inst.instrument()
        inst.uninstrument()
        assert inst.is_active is False
        assert inst.hooks_removed is True

    def test_double_instrument_raises(self):
        """Calling instrument() twice raises error."""
        inst = MockInstrumentor()
        inst.instrument()
        with pytest.raises(InstrumentorAlreadyActiveError):
            inst.instrument()

    def test_uninstrument_without_instrument_raises(self):
        """Calling uninstrument() without instrument() raises error."""
        inst = MockInstrumentor()
        with pytest.raises(InstrumentorNotActiveError):
            inst.uninstrument()

    def test_context_manager(self):
        """Context manager protocol works."""
        inst = MockInstrumentor()
        with inst as i:
            assert i.is_active is True
            assert i is inst
        assert inst.is_active is False

    def test_framework_properties(self):
        """Framework properties are accessible."""
        inst = MockInstrumentor()
        assert inst.framework == "mock"
        assert inst.framework_version == "1.0.0"

    def test_agent_info_configuration(self):
        """Agent info is configurable."""
        inst = MockInstrumentor(
            agent_name="my-agent",
            agent_version="2.0.0",
        )
        inst.instrument()
        inst._start_trace()
        trace = inst._current_trace
        assert trace.agent_info.name == "my-agent"
        assert trace.agent_info.version == "2.0.0"
        assert trace.agent_info.framework == "mock"

    def test_trace_collection(self):
        """Traces are collected correctly."""
        inst = MockInstrumentor()
        inst.instrument()

        # Start and finalize a trace
        trace1 = inst._start_trace()
        trace1_id = trace1.run_id
        inst._finalize_current_trace()

        # Start another trace
        trace2 = inst._start_trace()
        trace2_id = trace2.run_id

        traces = inst.get_traces()
        assert len(traces) == 2
        assert traces[0].run_id == trace1_id
        assert traces[1].run_id == trace2_id

    def test_clear_traces(self):
        """clear_traces() removes all traces."""
        inst = MockInstrumentor()
        inst.instrument()
        inst._start_trace()
        inst._finalize_current_trace()
        inst._start_trace()

        assert len(inst.get_traces()) == 2
        inst.clear_traces()
        assert len(inst.get_traces()) == 0

    def test_output_path_saves_traces(self):
        """Traces are saved when output_path is configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inst = MockInstrumentor(output_path=tmpdir)
            inst.instrument()

            # Create and finalize a trace
            inst._start_trace()
            inst._finalize_current_trace()

            # Check file was created
            files = list(Path(tmpdir).glob("trace-*.json"))
            assert len(files) == 1

            # Verify it's valid JSON
            import json
            with open(files[0]) as f:
                data = json.load(f)
            assert "run_id" in data

    def test_redaction_config_used(self):
        """Redaction config is stored."""
        config = RedactionConfig(replacement="***")
        inst = MockInstrumentor(redaction_config=config)
        assert inst._redaction_config.replacement == "***"
