"""Trace models for ContextForge.

This module implements the canonical trace schema:
- T016: BaseStep model
- T017-T022: All step type models
- T023: TraceStep discriminated union
- T024: TraceRun model
"""

from datetime import datetime
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from context_forge.core.types import (
    AgentInfo,
    FieldChange,
    ResourceImpact,
    RetrievalResult,
    StepType,
    TaskInfo,
)


class BaseStep(BaseModel):
    """Base fields shared by all step types.

    All trace steps inherit these common fields for identification,
    timing, and hierarchical organization.

    Attributes:
        step_id: Unique identifier for this step within the trace
        timestamp: When this step occurred (ISO8601 with ms precision)
        parent_step_id: Optional reference to parent step for nested calls
        metadata: Optional additional metadata for this step
    """

    model_config = ConfigDict(
        validate_by_alias=True,
        extra="ignore",
    )

    step_id: str
    timestamp: datetime
    parent_step_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class LLMCallStep(BaseStep):
    """An LLM invocation step.

    Records a call to a language model including the prompt,
    response, and resource usage.

    Attributes:
        step_type: Discriminator (always 'llm_call')
        model: Model identifier (e.g., 'gpt-4', 'claude-3-opus')
        input: Prompt text or list of messages
        output: Model response text or structured output
        tokens_in: Number of input/prompt tokens
        tokens_out: Number of output/completion tokens
        tokens_total: Total tokens (input + output)
        latency_ms: Response latency in milliseconds
        cost_estimate: Estimated cost in USD
        provider: LLM provider name (openai, anthropic, etc.)
    """

    step_type: Literal[StepType.LLM_CALL] = StepType.LLM_CALL
    model: str
    input: str | list[dict[str, Any]]
    output: str | dict[str, Any]
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    tokens_total: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_estimate: Optional[float] = None
    provider: Optional[str] = None


class ToolCallStep(BaseStep):
    """A tool/function invocation step.

    Records execution of a tool with its arguments and result.

    Attributes:
        step_type: Discriminator (always 'tool_call')
        tool_name: Tool identifier
        arguments: Arguments passed to the tool
        result: Tool execution result
        latency_ms: Execution time in milliseconds
        success: Whether the tool call succeeded
        error: Error message if the call failed
        resource_impact: Optional cost/credit impact
    """

    step_type: Literal[StepType.TOOL_CALL] = StepType.TOOL_CALL
    tool_name: str
    arguments: dict[str, Any]
    result: Optional[Any] = None
    latency_ms: Optional[int] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    resource_impact: Optional[ResourceImpact] = None


class RetrievalStep(BaseStep):
    """A retrieval/search step.

    Records a query to a retrieval system (vector DB, search, etc.)
    and its results.

    Attributes:
        step_type: Discriminator (always 'retrieval')
        query: The search/retrieval query
        results: List of retrieved documents/items
        match_count: Number of matches returned
        latency_ms: Query execution time in milliseconds
    """

    step_type: Literal[StepType.RETRIEVAL] = StepType.RETRIEVAL
    query: str
    results: list[RetrievalResult]
    match_count: int
    latency_ms: Optional[int] = None


class MemoryReadStep(BaseStep):
    """A memory read operation step.

    Records reading from agent memory (context, history, etc.).

    Attributes:
        step_type: Discriminator (always 'memory_read')
        query: Memory query (string or structured)
        results: Items retrieved from memory
        match_count: Number of matches found
        relevance_scores: Optional relevance scores for results
        total_available: Total items available in memory
    """

    step_type: Literal[StepType.MEMORY_READ] = StepType.MEMORY_READ
    query: str | dict[str, Any]
    results: list[Any]
    match_count: int
    relevance_scores: Optional[list[float]] = None
    total_available: Optional[int] = None


class MemoryWriteStep(BaseStep):
    """A memory write operation step.

    Records writing to agent memory with field-level change tracking
    for model-agnostic hygiene grading.

    Attributes:
        step_type: Discriminator (always 'memory_write')
        namespace: Storage namespace as list (e.g., ["profiles", "user_123"])
        key: Storage key within the namespace
        operation: Operation type (put, delete)
        data: The complete data being written (for reference)
        changes: Field-level changes with JSON paths (model-agnostic)
        triggered_by_step_id: Step ID that triggered this write (for trace linking)
        entity_type: Legacy field for backward compatibility
        entity_id: Optional identifier for the entity
    """

    step_type: Literal[StepType.MEMORY_WRITE] = StepType.MEMORY_WRITE
    namespace: Optional[list[str]] = None
    key: Optional[str] = None
    operation: Literal["add", "update", "delete", "put"]
    data: dict[str, Any]
    changes: Optional[list[FieldChange]] = None
    triggered_by_step_id: Optional[str] = None
    entity_type: Optional[str] = None  # Legacy, derived from namespace if not set
    entity_id: Optional[str] = None


class InterruptStep(BaseStep):
    """A human-in-the-loop interrupt step.

    Records when the agent pauses for human input.

    Attributes:
        step_type: Discriminator (always 'interrupt')
        prompt: The prompt/question shown to the user
        response: The user's response
        wait_duration_ms: How long the agent waited for response
    """

    step_type: Literal[StepType.INTERRUPT] = StepType.INTERRUPT
    prompt: str
    response: str | dict[str, Any]
    wait_duration_ms: int


class StateChangeStep(BaseStep):
    """An agent state change step.

    Records changes to internal agent state.

    Attributes:
        step_type: Discriminator (always 'state_change')
        state_key: The state field that changed
        old_value: Previous value (if available)
        new_value: New value
        reason: Optional reason for the change
    """

    step_type: Literal[StepType.STATE_CHANGE] = StepType.STATE_CHANGE
    state_key: str
    old_value: Optional[Any] = None
    new_value: Any
    reason: Optional[str] = None


class UserInputStep(BaseStep):
    """A user input step.

    Records input provided by the user to the agent.

    Attributes:
        step_type: Discriminator (always 'user_input')
        content: The user's input content
        input_type: Type of input (text, file, voice, etc.)
    """

    step_type: Literal[StepType.USER_INPUT] = StepType.USER_INPUT
    content: str
    input_type: Optional[str] = None


class FinalOutputStep(BaseStep):
    """A final output step.

    Records the agent's final response/output.

    Attributes:
        step_type: Discriminator (always 'final_output')
        content: The final output content
        format: Output format (text, json, markdown, etc.)
    """

    step_type: Literal[StepType.FINAL_OUTPUT] = StepType.FINAL_OUTPUT
    content: Any
    format: Optional[str] = None


# Discriminated union for all step types
TraceStep = Annotated[
    Union[
        LLMCallStep,
        ToolCallStep,
        RetrievalStep,
        MemoryReadStep,
        MemoryWriteStep,
        InterruptStep,
        StateChangeStep,
        UserInputStep,
        FinalOutputStep,
    ],
    Field(discriminator="step_type"),
]


class TraceRun(BaseModel):
    """Complete record of an agent execution run.

    This is the top-level container for a trace, holding all steps
    and metadata about the run.

    Attributes:
        run_id: Unique identifier for this run (UUID v4)
        started_at: When the run started (ISO8601)
        ended_at: When the run ended (None if still running)
        agent_info: Metadata about the agent
        task_info: Optional metadata about the task
        steps: Ordered list of trace steps
        metadata: Additional run-level metadata
    """

    model_config = ConfigDict(
        validate_by_alias=True,
        extra="ignore",
    )

    run_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    agent_info: AgentInfo
    task_info: Optional[TaskInfo] = None
    steps: list[TraceStep] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_steps(self) -> "TraceRun":
        """Validate step constraints.

        Checks:
        - All step_ids are unique within the trace
        - ended_at >= started_at if both are set
        """
        # Check unique step_ids
        step_ids = [step.step_id for step in self.steps]
        duplicates = [sid for sid in step_ids if step_ids.count(sid) > 1]
        if duplicates:
            raise ValueError(
                f"Duplicate step_ids found: {list(set(duplicates))}. "
                "Each step must have a unique step_id within a trace."
            )

        # Check ended_at >= started_at
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError(
                f"ended_at ({self.ended_at}) cannot be before started_at ({self.started_at})"
            )

        return self

    def add_step(self, step: TraceStep) -> None:
        """Add a step to the trace.

        Args:
            step: The step to add
        """
        self.steps.append(step)

    def get_steps_by_type(self, step_type: StepType) -> list[TraceStep]:
        """Get all steps of a specific type.

        Args:
            step_type: The type of steps to retrieve

        Returns:
            List of matching steps
        """
        return [s for s in self.steps if s.step_type == step_type]

    def get_llm_calls(self) -> list[LLMCallStep]:
        """Get all LLM call steps."""
        return [s for s in self.steps if isinstance(s, LLMCallStep)]

    def get_tool_calls(self) -> list[ToolCallStep]:
        """Get all tool call steps."""
        return [s for s in self.steps if isinstance(s, ToolCallStep)]

    def total_tokens(self) -> int:
        """Calculate total tokens used across all LLM calls."""
        total = 0
        for step in self.get_llm_calls():
            if step.tokens_total is not None:
                total += step.tokens_total
            elif step.tokens_in is not None and step.tokens_out is not None:
                total += step.tokens_in + step.tokens_out
        return total

    def total_tool_calls(self) -> int:
        """Count total tool calls in the trace."""
        return len(self.get_tool_calls())

    def to_json(self, **kwargs) -> str:
        """Serialize the trace to JSON.

        Args:
            **kwargs: Additional arguments passed to model_dump_json

        Returns:
            JSON string representation
        """
        return self.model_dump_json(exclude_none=True, **kwargs)
