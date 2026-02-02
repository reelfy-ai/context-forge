"""Core types and metadata models for ContextForge traces.

This module implements:
- T013: StepType enum
- T014: AgentInfo and TaskInfo models
- T015: ResourceImpact and RetrievalResult models
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class StepType(str, Enum):
    """Discriminator for trace step types.

    Each value represents a distinct operation that can occur during
    an agent execution run.
    """

    USER_INPUT = "user_input"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    STATE_CHANGE = "state_change"
    INTERRUPT = "interrupt"
    FINAL_OUTPUT = "final_output"


class AgentInfo(BaseModel):
    """Metadata about the agent being traced.

    Attributes:
        name: Agent name/identifier (required)
        version: Agent version string
        framework: Framework used (langchain, crewai, langgraph, custom)
        framework_version: Version of the framework
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    version: Optional[str] = None
    framework: Optional[str] = None
    framework_version: Optional[str] = None


class TaskInfo(BaseModel):
    """Metadata about the task being executed.

    Attributes:
        description: Human-readable task description
        goal: The objective or goal of the task
        input: Task input data as a dictionary
    """

    model_config = ConfigDict(extra="ignore")

    description: Optional[str] = None
    goal: Optional[str] = None
    input: Optional[dict[str, Any]] = None


class ResourceImpact(BaseModel):
    """Cost or credit impact of a tool call.

    Used to track resource consumption for tools that have
    associated costs (API credits, compute units, etc.).

    Attributes:
        amount: Numeric amount of resource consumed
        unit: Unit of measurement (credits, USD, compute_units, etc.)
        breakdown: Optional detailed breakdown by category
    """

    model_config = ConfigDict(extra="ignore")

    amount: float
    unit: str
    breakdown: Optional[dict[str, Any]] = None


class RetrievalResult(BaseModel):
    """A single retrieved document or item.

    Represents one result from a retrieval operation (vector search,
    keyword search, etc.).

    Attributes:
        content: The retrieved content (text, document chunk, etc.)
        score: Relevance score from 0.0 to 1.0 (higher is more relevant)
        metadata: Additional metadata about the retrieved item
    """

    model_config = ConfigDict(extra="ignore")

    content: str
    score: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


class FieldChange(BaseModel):
    """A single field-level change in a memory write operation.

    Model-agnostic representation of a field modification using JSON path
    notation. Enables hygiene grading without domain knowledge.

    Attributes:
        path: JSON path to the changed field (e.g., "$.equipment.solar_capacity_kw")
        old_value: Previous value (None if field didn't exist)
        new_value: New value (None if field was deleted)
    """

    model_config = ConfigDict(extra="ignore")

    path: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
