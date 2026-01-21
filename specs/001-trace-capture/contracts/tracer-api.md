# API Contract: Tracer (Level 4 - Explicit API)

**Feature**: 001-trace-capture | **Version**: 1.0.0

## Overview

The Tracer API provides explicit, manual control over trace capture for custom agents that don't use standard frameworks. This is Level 4 integration in the ContextForge hierarchy.

## Module

```python
from context_forge import Tracer
from context_forge.instrumentation.tracer import Tracer, AsyncTracer
```

---

## Tracer Class

### Constructor

```python
Tracer(
    agent_info: AgentInfo | dict,
    task_info: TaskInfo | dict | None = None,
    output_path: str | Path | None = None,
    auto_timestamps: bool = True,
)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agent_info` | `AgentInfo \| dict` | Yes | - | Agent metadata |
| `task_info` | `TaskInfo \| dict` | No | `None` | Task metadata |
| `output_path` | `str \| Path` | No | `None` | Path to write trace JSON |
| `auto_timestamps` | `bool` | No | `True` | Auto-generate timestamps |

### Context Manager Usage

```python
# Synchronous
with Tracer.run(agent_info={"name": "my-agent"}) as t:
    t.llm_call(...)
    t.tool_call(...)

# Async
async with Tracer.run_async(agent_info={"name": "my-agent"}) as t:
    await t.llm_call(...)
```

---

## Step Recording Methods

### llm_call()

Record an LLM invocation.

```python
t.llm_call(
    model: str,
    input: str | list[dict],
    output: str | dict,
    *,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    latency_ms: int | None = None,
    cost_estimate: float | None = None,
    provider: str | None = None,
    parent_step_id: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

**Example**:
```python
step_id = t.llm_call(
    model="gpt-4",
    input="What is the capital of France?",
    output="The capital of France is Paris.",
    tokens_in=12,
    tokens_out=8,
    latency_ms=450,
)
```

### tool_call()

Record a tool/function invocation.

```python
t.tool_call(
    tool_name: str,
    arguments: dict,
    result: Any,
    *,
    latency_ms: int | None = None,
    success: bool | None = None,
    error: str | None = None,
    resource_impact: dict | None = None,
    parent_step_id: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

**Example**:
```python
step_id = t.tool_call(
    tool_name="web_search",
    arguments={"query": "weather in Paris"},
    result={"temperature": "22C", "conditions": "sunny"},
    latency_ms=1200,
    success=True,
)
```

### retrieval()

Record a retrieval/RAG operation.

```python
t.retrieval(
    query: str,
    results: list[dict],
    match_count: int,
    *,
    latency_ms: int | None = None,
    parent_step_id: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

**Example**:
```python
step_id = t.retrieval(
    query="company vacation policy",
    results=[
        {"content": "Employees get 20 days...", "score": 0.95},
        {"content": "Holiday scheduling must...", "score": 0.82},
    ],
    match_count=2,
)
```

### memory_read()

Record a memory/context retrieval.

```python
t.memory_read(
    query: str | dict,
    results: list[Any],
    match_count: int,
    *,
    relevance_scores: list[float] | None = None,
    total_available: int | None = None,
    parent_step_id: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

### memory_write()

Record a memory/context update.

```python
t.memory_write(
    entity_type: str,
    operation: Literal['add', 'update', 'delete'],
    data: dict,
    *,
    entity_id: str | None = None,
    parent_step_id: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

### interrupt()

Record a human-in-the-loop pause.

```python
t.interrupt(
    prompt: str,
    response: str | dict,
    wait_duration_ms: int,
    *,
    parent_step_id: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

### state_change()

Record an internal state change.

```python
t.state_change(
    state_key: str,
    new_value: Any,
    *,
    old_value: Any | None = None,
    reason: str | None = None,
    parent_step_id: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

### user_input()

Record user input.

```python
t.user_input(
    content: str,
    *,
    input_type: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

### final_output()

Record final agent output.

```python
t.final_output(
    content: Any,
    *,
    format: str | None = None,
    metadata: dict | None = None,
) -> str  # Returns step_id
```

---

## Trace Access Methods

### get_trace()

Get the complete trace.

```python
t.get_trace() -> TraceRun
```

### to_json()

Serialize trace to JSON string.

```python
t.to_json(
    indent: int | None = None,
    exclude_none: bool = True,
) -> str
```

### save()

Save trace to file.

```python
t.save(
    path: str | Path | None = None,  # Uses output_path if None
) -> Path
```

---

## Async Variants

All step recording methods have async variants when using `Tracer.run_async()`:

```python
async with Tracer.run_async(agent_info={"name": "agent"}) as t:
    await t.llm_call(...)  # Returns Awaitable[str]
    await t.tool_call(...)
```

---

## Error Handling

```python
from context_forge.exceptions import TracerError, StepValidationError

try:
    with Tracer.run(agent_info={"name": "agent"}) as t:
        t.llm_call(model="gpt-4", input="...", output="...")
except StepValidationError as e:
    # Invalid step data
    print(f"Validation error: {e}")
except TracerError as e:
    # General tracer error
    print(f"Tracer error: {e}")
```

---

## Thread Safety

- Tracer instances are **not** thread-safe by default
- Use separate Tracer instances per thread
- For concurrent step emission, use explicit locking or async tracer

---

## Performance Characteristics

| Operation | Target | Notes |
|-----------|--------|-------|
| Step recording | < 1ms | In-memory append |
| JSON serialization | < 100ms for 1000 steps | Per SC-003 |
| Memory usage | < 100MB for 10k steps | Per SC-004 |