"""Explicit Tracer API for ContextForge.

This module implements:
- T080-T092: Tracer class with all step recording methods

Provides full manual control over trace capture for custom agents
that don't use standard frameworks.

Usage:
    with Tracer.run(agent_info={"name": "my-agent"}) as t:
        t.user_input(content="Hello")
        t.llm_call(model="gpt-4", input="Hello", output="Hi!")
        t.final_output(content="Hi!")

    trace = t.get_trace()
    t.save("./traces/my-trace.json")
"""

import json
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from context_forge.core.trace import (
    FinalOutputStep,
    InterruptStep,
    LLMCallStep,
    MemoryReadStep,
    MemoryWriteStep,
    RetrievalStep,
    StateChangeStep,
    ToolCallStep,
    TraceRun,
    UserInputStep,
)
from context_forge.core.types import AgentInfo, ResourceImpact, RetrievalResult, TaskInfo
from context_forge.exceptions import TracerNotActiveError


class Tracer:
    """Manual trace recorder for custom agents.

    Provides a fluent API for explicitly recording trace steps.
    Use as a context manager to ensure proper trace lifecycle.

    Attributes:
        trace: The TraceRun being recorded
    """

    def __init__(
        self,
        agent_info: AgentInfo | dict[str, Any],
        task_info: Optional[TaskInfo | dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ):
        """Initialize tracer.

        Args:
            agent_info: Agent metadata (AgentInfo or dict)
            task_info: Optional task metadata
            run_id: Optional custom run ID (auto-generated if not provided)
        """
        # Convert dict to AgentInfo if needed
        if isinstance(agent_info, dict):
            agent_info = AgentInfo(**agent_info)
        if isinstance(task_info, dict):
            task_info = TaskInfo(**task_info)

        self._trace = TraceRun(
            run_id=run_id or str(uuid.uuid4()),
            started_at=datetime.now(timezone.utc),
            agent_info=agent_info,
            task_info=task_info,
        )
        self._is_active = False
        self._step_counter = 0
        self._current_parent_id: Optional[str] = None

    @property
    def trace(self) -> TraceRun:
        """Get the current trace."""
        return self._trace

    @property
    def is_active(self) -> bool:
        """Whether the tracer is currently active."""
        return self._is_active

    def _generate_step_id(self) -> str:
        """Generate a unique step ID."""
        self._step_counter += 1
        return f"step-{self._step_counter:04d}"

    def _ensure_active(self) -> None:
        """Ensure tracer is active, raise if not."""
        if not self._is_active:
            raise TracerNotActiveError("Tracer is not active. Use Tracer.run() context manager.")

    @classmethod
    @contextmanager
    def run(
        cls,
        agent_info: AgentInfo | dict[str, Any],
        task_info: Optional[TaskInfo | dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ):
        """Create and run a tracer as a context manager.

        Args:
            agent_info: Agent metadata
            task_info: Optional task metadata
            run_id: Optional custom run ID

        Yields:
            Active Tracer instance

        Example:
            with Tracer.run(agent_info={"name": "my-agent"}) as t:
                t.llm_call(...)
        """
        tracer = cls(agent_info=agent_info, task_info=task_info, run_id=run_id)
        tracer._is_active = True
        try:
            yield tracer
        finally:
            tracer._trace.ended_at = datetime.now(timezone.utc)
            tracer._is_active = False

    @classmethod
    @asynccontextmanager
    async def run_async(
        cls,
        agent_info: AgentInfo | dict[str, Any],
        task_info: Optional[TaskInfo | dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ):
        """Create and run a tracer as an async context manager.

        Args:
            agent_info: Agent metadata
            task_info: Optional task metadata
            run_id: Optional custom run ID

        Yields:
            Active Tracer instance

        Example:
            async with Tracer.run_async(agent_info={"name": "my-agent"}) as t:
                await some_async_operation()
                t.llm_call(...)
        """
        tracer = cls(agent_info=agent_info, task_info=task_info, run_id=run_id)
        tracer._is_active = True
        try:
            yield tracer
        finally:
            tracer._trace.ended_at = datetime.now(timezone.utc)
            tracer._is_active = False

    # Step Recording Methods

    def user_input(
        self,
        content: str,
        input_type: Optional[str] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record a user input step.

        Args:
            content: The user's input content
            input_type: Type of input (text, file, voice, etc.)
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        step = UserInputStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            content=content,
            input_type=input_type,
        )
        self._trace.add_step(step)
        return step_id

    def llm_call(
        self,
        model: str,
        input: str | list[dict[str, Any]],
        output: str | dict[str, Any],
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        tokens_total: Optional[int] = None,
        latency_ms: Optional[int] = None,
        cost_estimate: Optional[float] = None,
        provider: Optional[str] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record an LLM call step.

        Args:
            model: Model identifier (e.g., 'gpt-4', 'claude-3')
            input: Prompt text or list of messages
            output: Model response
            tokens_in: Input token count
            tokens_out: Output token count
            tokens_total: Total token count
            latency_ms: Response latency in milliseconds
            cost_estimate: Estimated cost in USD
            provider: LLM provider name
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        step = LLMCallStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            model=model,
            input=input,
            output=output,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tokens_total=tokens_total,
            latency_ms=latency_ms,
            cost_estimate=cost_estimate,
            provider=provider,
        )
        self._trace.add_step(step)
        return step_id

    def tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        latency_ms: Optional[int] = None,
        success: Optional[bool] = None,
        error: Optional[str] = None,
        resource_impact: Optional[ResourceImpact | dict[str, Any]] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record a tool call step.

        Args:
            tool_name: Tool identifier
            arguments: Arguments passed to the tool
            result: Tool execution result
            latency_ms: Execution time in milliseconds
            success: Whether the tool call succeeded
            error: Error message if failed
            resource_impact: Cost/credit impact
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        # Convert dict to ResourceImpact if needed
        if isinstance(resource_impact, dict):
            resource_impact = ResourceImpact(**resource_impact)

        step = ToolCallStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            latency_ms=latency_ms,
            success=success,
            error=error,
            resource_impact=resource_impact,
        )
        self._trace.add_step(step)
        return step_id

    def retrieval(
        self,
        query: str,
        results: list[RetrievalResult | dict[str, Any]],
        match_count: Optional[int] = None,
        latency_ms: Optional[int] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record a retrieval step.

        Args:
            query: The search/retrieval query
            results: List of retrieved documents
            match_count: Number of matches (defaults to len(results))
            latency_ms: Query execution time
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        # Convert dicts to RetrievalResult if needed
        converted_results = []
        for r in results:
            if isinstance(r, dict):
                converted_results.append(RetrievalResult(**r))
            else:
                converted_results.append(r)

        step = RetrievalStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            query=query,
            results=converted_results,
            match_count=match_count if match_count is not None else len(converted_results),
            latency_ms=latency_ms,
        )
        self._trace.add_step(step)
        return step_id

    def memory_read(
        self,
        query: str | dict[str, Any],
        results: list[Any],
        match_count: Optional[int] = None,
        relevance_scores: Optional[list[float]] = None,
        total_available: Optional[int] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record a memory read step.

        Args:
            query: Memory query (string or structured)
            results: Items retrieved from memory
            match_count: Number of matches (defaults to len(results))
            relevance_scores: Relevance scores for results
            total_available: Total items available in memory
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        step = MemoryReadStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            query=query,
            results=results,
            match_count=match_count if match_count is not None else len(results),
            relevance_scores=relevance_scores,
            total_available=total_available,
        )
        self._trace.add_step(step)
        return step_id

    def memory_write(
        self,
        entity_type: str,
        operation: str,
        data: dict[str, Any],
        entity_id: Optional[str] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record a memory write step.

        Args:
            entity_type: Type of entity being written
            operation: Operation type ('add', 'update', 'delete')
            data: The data being written
            entity_id: Optional entity identifier
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        step = MemoryWriteStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            entity_type=entity_type,
            operation=operation,
            data=data,
            entity_id=entity_id,
        )
        self._trace.add_step(step)
        return step_id

    def interrupt(
        self,
        prompt: str,
        response: str | dict[str, Any],
        wait_duration_ms: int,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record an interrupt (human-in-the-loop) step.

        Args:
            prompt: The prompt shown to the user
            response: The user's response
            wait_duration_ms: How long the agent waited
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        step = InterruptStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            prompt=prompt,
            response=response,
            wait_duration_ms=wait_duration_ms,
        )
        self._trace.add_step(step)
        return step_id

    def state_change(
        self,
        state_key: str,
        new_value: Any,
        old_value: Optional[Any] = None,
        reason: Optional[str] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record a state change step.

        Args:
            state_key: The state field that changed
            new_value: The new value
            old_value: The previous value (if known)
            reason: Reason for the change
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        step = StateChangeStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            state_key=state_key,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
        self._trace.add_step(step)
        return step_id

    def final_output(
        self,
        content: Any,
        format: Optional[str] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Record a final output step.

        Args:
            content: The final output content
            format: Output format (text, json, markdown, etc.)
            parent_step_id: Optional parent step for nesting
            metadata: Optional additional metadata

        Returns:
            The step ID of the created step
        """
        self._ensure_active()
        step_id = self._generate_step_id()

        step = FinalOutputStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=parent_step_id or self._current_parent_id,
            metadata=metadata,
            content=content,
            format=format,
        )
        self._trace.add_step(step)
        return step_id

    # Utility Methods

    def get_trace(self) -> TraceRun:
        """Get the recorded trace.

        Returns:
            The TraceRun object with all recorded steps
        """
        return self._trace

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize the trace to JSON.

        Args:
            indent: Indentation level for pretty printing

        Returns:
            JSON string representation of the trace
        """
        return self._trace.to_json(indent=indent)

    def save(self, path: str | Path) -> Path:
        """Save the trace to a file.

        Args:
            path: File path to save to

        Returns:
            Path to the saved file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            f.write(self.to_json(indent=2))

        return path

    @contextmanager
    def nested(self, parent_step_id: str):
        """Context manager for nested steps.

        All steps recorded within this context will have
        their parent_step_id set to the specified value.

        Args:
            parent_step_id: The parent step ID for nested steps

        Example:
            llm_id = t.llm_call(...)
            with t.nested(llm_id):
                t.tool_call(...)  # Will have parent_step_id = llm_id
        """
        old_parent = self._current_parent_id
        self._current_parent_id = parent_step_id
        try:
            yield
        finally:
            self._current_parent_id = old_parent
