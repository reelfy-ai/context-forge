"""Base instrumentation classes for ContextForge.

This module implements:
- T033: RedactionConfig model
- T034: BaseInstrumentor abstract class
- T035: instrument() and uninstrument() methods
- T036: get_traces() method
- T037: Context manager protocol
"""

import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Pattern

from pydantic import BaseModel, ConfigDict, Field

from context_forge.core.trace import TraceRun
from context_forge.core.types import AgentInfo
from context_forge.exceptions import (
    InstrumentorAlreadyActiveError,
    InstrumentorNotActiveError,
)


class RedactionConfig(BaseModel):
    """Configuration for PII/secret redaction in traces.

    Allows users to specify patterns and field names that should
    be redacted from trace output.

    Attributes:
        patterns: Regex patterns to match and redact
        field_names: Field names to always redact
        replacement: String to replace redacted content
        enabled: Whether redaction is active
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    patterns: list[Pattern[str]] = Field(default_factory=list)
    field_names: list[str] = Field(
        default_factory=lambda: ["password", "api_key", "secret", "token", "authorization"]
    )
    replacement: str = "[REDACTED]"
    enabled: bool = True

    @classmethod
    def default(cls) -> "RedactionConfig":
        """Create default redaction config with common patterns."""
        return cls(
            patterns=[
                re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
                re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
                re.compile(r"\b\d{16}\b"),  # Credit card (simple)
            ],
            field_names=["password", "api_key", "secret", "token", "authorization", "bearer"],
        )

    def redact(self, value: str) -> str:
        """Apply redaction to a string value.

        Args:
            value: String to potentially redact

        Returns:
            Redacted string if patterns match, original otherwise
        """
        if not self.enabled or not value:
            return value

        result = value
        for pattern in self.patterns:
            result = pattern.sub(self.replacement, result)
        return result

    def should_redact_field(self, field_name: str) -> bool:
        """Check if a field name should be redacted.

        Args:
            field_name: Name of the field to check

        Returns:
            True if the field should be redacted
        """
        if not self.enabled:
            return False
        field_lower = field_name.lower()
        return any(name.lower() in field_lower for name in self.field_names)


class BaseInstrumentor(ABC):
    """Abstract base class for framework instrumentors.

    Provides the common interface for auto-instrumentation of
    agent frameworks. Subclasses implement framework-specific
    hooks.

    Usage:
        instrumentor = LangChainInstrumentor()
        instrumentor.instrument()
        # ... run agent code ...
        traces = instrumentor.get_traces()
        instrumentor.uninstrument()

    Or with context manager:
        with LangChainInstrumentor() as instrumentor:
            # ... run agent code ...
            traces = instrumentor.get_traces()
    """

    def __init__(
        self,
        agent_name: str = "default",
        agent_version: Optional[str] = None,
        output_path: Optional[str | Path] = None,
        redaction_config: Optional[RedactionConfig] = None,
    ):
        """Initialize the instrumentor.

        Args:
            agent_name: Name to assign to traced agent
            agent_version: Version string for the agent
            output_path: Directory to save traces (optional)
            redaction_config: PII redaction configuration
        """
        self._agent_name = agent_name
        self._agent_version = agent_version
        self._output_path = Path(output_path) if output_path else None
        self._redaction_config = redaction_config or RedactionConfig()
        self._is_active = False
        self._traces: list[TraceRun] = []
        self._current_trace: Optional[TraceRun] = None

    @property
    def is_active(self) -> bool:
        """Whether instrumentation is currently active."""
        return self._is_active

    @property
    @abstractmethod
    def framework(self) -> str:
        """Return the framework name (e.g., 'langchain', 'crewai')."""
        pass

    @property
    @abstractmethod
    def framework_version(self) -> Optional[str]:
        """Return the framework version if available."""
        pass

    def instrument(self) -> "BaseInstrumentor":
        """Activate instrumentation.

        Installs hooks into the framework to capture trace events.

        Returns:
            Self for method chaining

        Raises:
            InstrumentorAlreadyActiveError: If already instrumented
        """
        if self._is_active:
            raise InstrumentorAlreadyActiveError(
                f"{self.__class__.__name__} is already active"
            )

        self._install_hooks()
        self._is_active = True
        return self

    def uninstrument(self) -> None:
        """Deactivate instrumentation.

        Removes hooks and finalizes any active traces.

        Raises:
            InstrumentorNotActiveError: If not currently instrumented
        """
        if not self._is_active:
            raise InstrumentorNotActiveError(
                f"{self.__class__.__name__} is not active"
            )

        self._finalize_current_trace()
        self._remove_hooks()
        self._is_active = False

    @abstractmethod
    def _install_hooks(self) -> None:
        """Install framework-specific hooks.

        Subclasses must implement this to add callbacks/patches
        to the target framework.
        """
        pass

    @abstractmethod
    def _remove_hooks(self) -> None:
        """Remove framework-specific hooks.

        Subclasses must implement this to clean up any installed
        callbacks/patches.
        """
        pass

    def get_traces(self) -> list[TraceRun]:
        """Get all captured traces.

        Returns:
            List of TraceRun objects captured during instrumentation
        """
        # Include current trace if active
        traces = list(self._traces)
        if self._current_trace is not None:
            traces.append(self._current_trace)
        return traces

    def clear_traces(self) -> None:
        """Clear all captured traces."""
        self._traces.clear()
        self._current_trace = None

    def _start_trace(self, task_description: Optional[str] = None) -> TraceRun:
        """Start a new trace.

        Args:
            task_description: Optional description of the task

        Returns:
            The new TraceRun object
        """
        self._finalize_current_trace()

        from context_forge.core.types import TaskInfo

        agent_info = AgentInfo(
            name=self._agent_name,
            version=self._agent_version,
            framework=self.framework,
            framework_version=self.framework_version,
        )

        task_info = None
        if task_description:
            task_info = TaskInfo(description=task_description)

        self._current_trace = TraceRun(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc),
            agent_info=agent_info,
            task_info=task_info,
        )
        return self._current_trace

    def _finalize_current_trace(self) -> None:
        """Finalize the current trace and add to completed traces."""
        if self._current_trace is not None:
            self._current_trace.ended_at = datetime.now(timezone.utc)
            self._traces.append(self._current_trace)

            # Save to file if output path configured
            if self._output_path:
                self._save_trace(self._current_trace)

            self._current_trace = None

    def _save_trace(self, trace: TraceRun) -> Path:
        """Save a trace to the output directory.

        Args:
            trace: The trace to save

        Returns:
            Path to the saved file
        """
        if self._output_path is None:
            raise ValueError("No output path configured")

        self._output_path.mkdir(parents=True, exist_ok=True)
        filename = f"trace-{trace.run_id}.json"
        filepath = self._output_path / filename

        with open(filepath, "w") as f:
            f.write(trace.to_json(indent=2))

        return filepath

    def _get_current_trace(self) -> TraceRun:
        """Get or create current trace.

        Returns:
            The current active TraceRun
        """
        if self._current_trace is None:
            self._start_trace()
        return self._current_trace

    def __enter__(self) -> "BaseInstrumentor":
        """Enter context manager, activating instrumentation."""
        return self.instrument()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager, deactivating instrumentation."""
        self.uninstrument()
