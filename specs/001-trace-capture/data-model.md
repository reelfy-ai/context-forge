# Data Model: Trace Capture

**Feature**: 001-trace-capture | **Date**: 2026-01-21

## Entity Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         TraceRun                            │
│  run_id, started_at, ended_at, agent_info, task_info        │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ TraceStep 1 │ │ TraceStep 2 │ │ TraceStep N │  ...      │
│  │ (llm_call)  │ │ (tool_call) │ │ (retrieval) │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│         │              ▲                                    │
│         └──────────────┘  (parent_step_id)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Entities

### TraceRun

Complete record of an agent execution run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `run_id` | `str` | Yes | Unique identifier (UUID) |
| `started_at` | `datetime` | Yes | Run start timestamp (ISO8601, ms precision) |
| `ended_at` | `datetime` | No | Run end timestamp (null if still running) |
| `agent_info` | `AgentInfo` | Yes | Agent metadata |
| `task_info` | `TaskInfo` | No | Task/goal metadata |
| `steps` | `list[TraceStep]` | Yes | Ordered list of trace steps |
| `metadata` | `dict` | No | Additional run metadata |

**Constraints**:
- `run_id` must be globally unique (UUID v4)
- `ended_at` >= `started_at` when present
- `steps` maintains insertion order

### AgentInfo

Metadata about the agent being traced.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Agent name/identifier |
| `version` | `str` | No | Agent version |
| `framework` | `str` | No | Framework (langchain, crewai, custom) |
| `framework_version` | `str` | No | Framework version |

### TaskInfo

Metadata about the task being executed.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | `str` | No | Task description |
| `goal` | `str` | No | Task goal |
| `input` | `dict` | No | Task input data |

---

## TraceStep (Discriminated Union)

Single event in the trace. Uses discriminated union on `step_type` field.

### Base Fields (All Step Types)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step_id` | `str` | Yes | Unique step identifier |
| `step_type` | `StepType` | Yes | Discriminator field |
| `timestamp` | `datetime` | Yes | Step timestamp (ms precision) |
| `parent_step_id` | `str` | No | Parent step for nested calls |
| `metadata` | `dict` | No | Additional metadata |

> **Note**: Each step type defines its own semantic fields (e.g., `input`/`output` for LLMCallStep, `arguments`/`result` for ToolCallStep). There are no generic `inputs`/`outputs` fields on the base schema.

### StepType Enum

```python
class StepType(str, Enum):
    USER_INPUT = "user_input"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    STATE_CHANGE = "state_change"
    INTERRUPT = "interrupt"
    FINAL_OUTPUT = "final_output"
```

---

## Step Type Schemas

### LLMCallStep

| Field | Type | Required | Description | Requirement |
|-------|------|----------|-------------|-------------|
| `step_type` | `Literal['llm_call']` | Yes | Discriminator | - |
| `model` | `str` | Yes | Model identifier | FR-005 |
| `input` | `str \| list[dict]` | Yes | Prompt/messages | FR-005 |
| `output` | `str \| dict` | Yes | Response | FR-005 |
| `tokens_in` | `int` | No | Input tokens | FR-006 |
| `tokens_out` | `int` | No | Output tokens | FR-006 |
| `tokens_total` | `int` | No | Total tokens | FR-006 |
| `latency_ms` | `int` | No | Latency in ms | FR-006 |
| `cost_estimate` | `float` | No | Cost in USD | FR-006 |
| `provider` | `str` | No | LLM provider | - |

### ToolCallStep

| Field | Type | Required | Description | Requirement |
|-------|------|----------|-------------|-------------|
| `step_type` | `Literal['tool_call']` | Yes | Discriminator | - |
| `tool_name` | `str` | Yes | Tool identifier | FR-007 |
| `arguments` | `dict` | Yes | Tool arguments | FR-007 |
| `result` | `Any` | Yes | Tool result | FR-007 |
| `latency_ms` | `int` | No | Latency in ms | FR-008 |
| `success` | `bool` | No | Success/failure | FR-008 |
| `error` | `str` | No | Error message if failed | - |
| `resource_impact` | `ResourceImpact` | No | Cost/credit impact | FR-008d |

### ResourceImpact (Optional)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | `float` | Yes | Resource amount |
| `unit` | `str` | Yes | Unit (credits, USD, etc.) |
| `breakdown` | `dict` | No | Detailed breakdown |

### RetrievalStep

| Field | Type | Required | Description | Requirement |
|-------|------|----------|-------------|-------------|
| `step_type` | `Literal['retrieval']` | Yes | Discriminator | - |
| `query` | `str` | Yes | Retrieval query | FR-003 |
| `results` | `list[RetrievalResult]` | Yes | Retrieved items | FR-003 |
| `match_count` | `int` | Yes | Number of matches | - |
| `latency_ms` | `int` | No | Latency in ms | - |

### RetrievalResult

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | `str` | Yes | Document content |
| `score` | `float` | No | Relevance score (0-1) |
| `metadata` | `dict` | No | Document metadata |

### MemoryReadStep

| Field | Type | Required | Description | Requirement |
|-------|------|----------|-------------|-------------|
| `step_type` | `Literal['memory_read']` | Yes | Discriminator | - |
| `query` | `str \| dict` | Yes | Memory query | FR-008a |
| `results` | `list[Any]` | Yes | Retrieved items | FR-008a |
| `match_count` | `int` | Yes | Number of matches | FR-008a |
| `relevance_scores` | `list[float]` | No | Relevance scores | FR-008b |
| `total_available` | `int` | No | Total items available | FR-008b |

### MemoryWriteStep

| Field | Type | Required | Description | Requirement |
|-------|------|----------|-------------|-------------|
| `step_type` | `Literal['memory_write']` | Yes | Discriminator | - |
| `entity_type` | `str` | Yes | Type of entity | FR-008c |
| `operation` | `Literal['add', 'update', 'delete']` | Yes | Operation type | FR-008c |
| `data` | `dict` | Yes | Data written | FR-008c |
| `entity_id` | `str` | No | Entity identifier | - |

### InterruptStep

| Field | Type | Required | Description | Requirement |
|-------|------|----------|-------------|-------------|
| `step_type` | `Literal['interrupt']` | Yes | Discriminator | - |
| `prompt` | `str` | Yes | Prompt shown to user | FR-004a |
| `response` | `str \| dict` | Yes | User's response | FR-004a |
| `wait_duration_ms` | `int` | Yes | Time waiting for response | FR-004a |

### StateChangeStep

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step_type` | `Literal['state_change']` | Yes | Discriminator |
| `state_key` | `str` | Yes | State field changed |
| `old_value` | `Any` | No | Previous value |
| `new_value` | `Any` | Yes | New value |
| `reason` | `str` | No | Reason for change |

### UserInputStep

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step_type` | `Literal['user_input']` | Yes | Discriminator |
| `content` | `str` | Yes | User's input |
| `input_type` | `str` | No | Type (text, file, etc.) |

### FinalOutputStep

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step_type` | `Literal['final_output']` | Yes | Discriminator |
| `content` | `Any` | Yes | Final output |
| `format` | `str` | No | Output format |

---

## Pydantic Schema Definition

```python
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import AliasChoices


class StepType(str, Enum):
    USER_INPUT = "user_input"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    STATE_CHANGE = "state_change"
    INTERRUPT = "interrupt"
    FINAL_OUTPUT = "final_output"


class BaseStep(BaseModel):
    """Base fields shared by all step types."""
    model_config = ConfigDict(
        validate_by_alias=True,
        extra='ignore',
    )

    step_id: str
    timestamp: datetime
    parent_step_id: Optional[str] = None
    metadata: Optional[dict] = None


class LLMCallStep(BaseStep):
    step_type: Literal[StepType.LLM_CALL]
    model: str
    input: str | list[dict]
    output: str | dict
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    tokens_total: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_estimate: Optional[float] = None
    provider: Optional[str] = None


class ResourceImpact(BaseModel):
    amount: float
    unit: str
    breakdown: Optional[dict] = None


class ToolCallStep(BaseStep):
    step_type: Literal[StepType.TOOL_CALL]
    tool_name: str
    arguments: dict
    result: Any
    latency_ms: Optional[int] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    resource_impact: Optional[ResourceImpact] = None


class RetrievalResult(BaseModel):
    content: str
    score: Optional[float] = None
    metadata: Optional[dict] = None


class RetrievalStep(BaseStep):
    step_type: Literal[StepType.RETRIEVAL]
    query: str
    results: list[RetrievalResult]
    match_count: int
    latency_ms: Optional[int] = None


class MemoryReadStep(BaseStep):
    step_type: Literal[StepType.MEMORY_READ]
    query: str | dict
    results: list[Any]
    match_count: int
    relevance_scores: Optional[list[float]] = None
    total_available: Optional[int] = None


class MemoryWriteStep(BaseStep):
    step_type: Literal[StepType.MEMORY_WRITE]
    entity_type: str
    operation: Literal['add', 'update', 'delete']
    data: dict
    entity_id: Optional[str] = None


class InterruptStep(BaseStep):
    step_type: Literal[StepType.INTERRUPT]
    prompt: str
    response: str | dict
    wait_duration_ms: int


class StateChangeStep(BaseStep):
    step_type: Literal[StepType.STATE_CHANGE]
    state_key: str
    old_value: Optional[Any] = None
    new_value: Any
    reason: Optional[str] = None


class UserInputStep(BaseStep):
    step_type: Literal[StepType.USER_INPUT]
    content: str
    input_type: Optional[str] = None


class FinalOutputStep(BaseStep):
    step_type: Literal[StepType.FINAL_OUTPUT]
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
    Field(discriminator='step_type')
]


class AgentInfo(BaseModel):
    name: str
    version: Optional[str] = None
    framework: Optional[str] = None
    framework_version: Optional[str] = None


class TaskInfo(BaseModel):
    description: Optional[str] = None
    goal: Optional[str] = None
    input: Optional[dict] = None


class TraceRun(BaseModel):
    """Complete record of an agent execution run."""
    model_config = ConfigDict(
        validate_by_alias=True,
        extra='ignore',
    )

    run_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    agent_info: AgentInfo
    task_info: Optional[TaskInfo] = None
    steps: list[TraceStep] = Field(default_factory=list)
    metadata: Optional[dict] = None
```

---

## State Transitions

### TraceRun Lifecycle

```
CREATED → RUNNING → COMPLETED
              ↓
           FAILED
```

| State | Condition |
|-------|-----------|
| CREATED | `run_id` assigned, `started_at` set |
| RUNNING | Steps being added, `ended_at` is None |
| COMPLETED | `ended_at` set, no errors |
| FAILED | `ended_at` set with error metadata |

### Step Ordering

- Steps are ordered by `timestamp`
- `parent_step_id` creates logical hierarchy within flat list
- Concurrent steps may have same timestamp (order preserved by insertion)

---

## Validation Rules

### TraceRun Validation
1. `run_id` must be valid UUID v4 format
2. `started_at` must be valid ISO8601 datetime
3. `ended_at` must be >= `started_at` if present
4. `steps` list can be empty but must be present

### TraceStep Validation
1. `step_id` must be unique within the trace
2. `step_type` must be valid StepType enum value
3. `timestamp` must be valid ISO8601 with millisecond precision
4. `parent_step_id` must reference existing step if present

### Type-Specific Validation
- LLMCallStep: `model` and `input`/`output` required
- ToolCallStep: `tool_name`, `arguments`, `result` required
- MemoryReadStep: `query`, `results`, `match_count` required
- InterruptStep: `prompt`, `response`, `wait_duration_ms` required

---

## Backward Compatibility

### Field Aliases (for OTel/OpenInference ingestion)

| ContextForge Field | Alias (OpenInference) |
|--------------------|----------------------|
| `model` | `llm.model_name` |
| `tokens_in` | `llm.token_count.prompt` |
| `tokens_out` | `llm.token_count.completion` |
| `step_type` | `openinference.span.kind` |

### Evolution Rules (per Constitution)
- Additive changes only in minor versions
- Never remove or rename fields without aliasing
- New step types degrade gracefully (unknown → ignored with warning)
