# Research: Trace Capture

**Feature**: 001-trace-capture | **Date**: 2026-01-21

## Executive Summary

This document consolidates research findings for implementing the ContextForge Trace Capture system. Key decisions cover OpenInference semantic conventions for OTel integration, LangChain callback patterns for framework instrumentation, and Pydantic v2 patterns for efficient trace schemas.

---

## 1. OpenInference Semantic Conventions

### Decision
Use OpenInference semantic conventions as the canonical format for OTel/OpenTelemetry span ingestion (Level 1 integration).

### Rationale
- OpenInference is the de facto standard for AI/LLM observability
- Being adopted into OpenTelemetry's official GenAI semantic conventions
- Provides comprehensive attribute coverage for LLM, tool, and retrieval operations
- Enables zero-code integration with existing observability pipelines

### Key Attribute Mappings

| ContextForge Field | OpenInference Attribute | OTel GenAI Attribute |
|--------------------|------------------------|---------------------|
| model | `llm.model_name` | `gen_ai.request.model` |
| input_tokens | `llm.token_count.prompt` | `gen_ai.usage.input_tokens` |
| output_tokens | `llm.token_count.completion` | `gen_ai.usage.output_tokens` |
| tool_name | `llm.tools[].tool.json_schema` | `gen_ai.tool.name` |
| step_type | `openinference.span.kind` | `gen_ai.operation.name` |

### Span Kind Mapping to ContextForge StepType

| OpenInference Span Kind | ContextForge StepType |
|------------------------|----------------------|
| LLM | `llm_call` |
| TOOL | `tool_call` |
| RETRIEVER | `retrieval` |
| EMBEDDING | `retrieval` (sub-type) |
| CHAIN | `state_change` |
| AGENT | `state_change` |
| GUARDRAIL | `state_change` |

### Parent-Child Relationship
- Use flat list with `parent_step_id` references (OTel-style)
- Trace ID shared across all spans in a trace
- Parent Span ID references the parent (null for root)
- This matches FR-003 specification and clarification decision

### Alternatives Considered
1. **Custom schema only**: Rejected - loses existing observability investment
2. **OTel GenAI only**: Rejected - less mature than OpenInference
3. **Both equally**: Rejected - complexity without benefit

---

## 2. LangChain Callback Patterns

### Decision
Implement `ContextForgeHandler` extending `BaseCallbackHandler` for Level 3 integration, with `AsyncCallbackHandler` support.

### Rationale
- LangChain callbacks are the standard pattern for per-call instrumentation
- Provides access to all LLM, tool, chain, and retriever events
- Token usage captured reliably via `on_llm_end` callback
- Async support required for concurrent agent operations (FR-013)

### Key Callback Methods for ContextForge

| Method | Triggers | ContextForge StepType |
|--------|----------|----------------------|
| `on_llm_start` / `on_llm_end` | LLM invocation | `llm_call` |
| `on_chat_model_start` | Chat model invocation | `llm_call` |
| `on_tool_start` / `on_tool_end` | Tool execution | `tool_call` |
| `on_retriever_start` / `on_retriever_end` | RAG retrieval | `retrieval` |
| `on_chain_start` / `on_chain_end` | Chain execution | `state_change` |
| `on_agent_action` / `on_agent_finish` | Agent decisions | `state_change` |

### Token Usage Capture Pattern

```python
def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs):
    for generation in response.generations:
        if hasattr(generation, 'message') and hasattr(generation.message, 'usage_metadata'):
            usage = generation.message.usage_metadata
            # usage contains: input_tokens, output_tokens, total_tokens
```

### Async Handler Pattern

```python
class ContextForgeAsyncHandler(AsyncCallbackHandler):
    async def on_llm_end(self, response, *, run_id, **kwargs):
        # Async operations allowed here
        await self.emit_step(step_data)
```

### Configuration Best Practices
- Use `raise_error=False` to prevent callback failures from breaking agent execution
- Use `run_id` and `parent_run_id` for trace hierarchy (matches parent_step_id design)
- Support multiple handlers via list: `config={"callbacks": [handler1, handler2]}`

### Alternatives Considered
1. **Monkey patching**: Rejected - fragile, breaks on version updates
2. **Custom wrapper classes**: Rejected - doesn't integrate with LangChain ecosystem
3. **OpenInference LangChain instrumentor only**: Partial - use for Level 2, callbacks for Level 3

---

## 3. Pydantic v2 Trace Schema Patterns

### Decision
Use Pydantic v2 with discriminated unions for step types and TypeAdapter for high-performance serialization.

### Rationale
- Pydantic v2 with jiter is 12x faster than v1
- Discriminated unions provide ~4x faster validation than sequential unions
- TypeAdapter enables efficient serialization of large lists
- AliasChoices enables backward-compatible schema evolution

### Step Type Schema Pattern

```python
from pydantic import BaseModel, Field
from typing import Literal, Union

class LLMCallStep(BaseModel):
    step_type: Literal['llm_call']
    model: str
    # ... step-specific fields

class ToolCallStep(BaseModel):
    step_type: Literal['tool_call']
    tool_name: str
    # ... step-specific fields

# Discriminated union for fast validation
TraceStep = Annotated[
    Union[LLMCallStep, ToolCallStep, ...],
    Field(discriminator='step_type')
]
```

### Performance Optimizations

| Technique | Use Case | Benefit |
|-----------|----------|---------|
| Discriminated unions | Step type validation | ~4x faster than sequential |
| TypeAdapter | List serialization | Avoids model wrapper overhead |
| `exclude_none=True` | JSON output | Smaller payloads |
| JSONL format | Large traces (10k+) | Memory-efficient streaming |

### Backward Compatibility Pattern

```python
class TraceStep(BaseModel):
    step_id: str = Field(
        validation_alias=AliasChoices('step_id', 'id'),  # Accept old name
        serialization_alias='step_id'  # Output new name
    )
```

### ConfigDict Settings

```python
model_config = ConfigDict(
    validate_by_alias=True,   # Accept old field names
    validate_by_name=True,    # Also accept new names
    extra='ignore',           # Forward compatibility
    exclude_none=True,        # Clean JSON output
)
```

### Alternatives Considered
1. **dataclasses + orjson**: Rejected - loses Pydantic validation, orjson not needed
2. **msgspec**: Rejected - less ecosystem support, Pydantic v2 fast enough
3. **attrs**: Rejected - Pydantic better for JSON schema generation

---

## 4. Framework Auto-Instrumentation (Level 2)

### Decision
Follow the `Instrumentor().instrument()` pattern established by OpenInference.

### Rationale
- Matches existing OpenInference instrumentation patterns
- Users familiar with OpenTelemetry auto-instrumentation
- One-line integration (SC-001 requirement)

### Implementation Pattern

```python
from context_forge.instrumentation import LangChainInstrumentor

# One-line instrumentation
LangChainInstrumentor().instrument()

# Existing LangChain code works unchanged
chain.invoke(...)  # Automatically traced
```

### Framework Support Priority
1. **LangChain** (P1) - Most common framework
2. **CrewAI** (P1) - Multi-agent workflows
3. **AutoGen** (P2) - Microsoft ecosystem
4. **LangGraph** (P2) - LangChain graphs

---

## 5. Explicit Tracer API (Level 4)

### Decision
Implement context manager pattern with fluent API for manual step recording.

### Rationale
- Some agents don't use standard frameworks
- Full control needed for custom evaluation scenarios
- Matches User Story 4 acceptance scenarios

### API Design

```python
from context_forge import Tracer

with Tracer.run(agent_info={"name": "custom"}) as t:
    t.llm_call(model="gpt-4", input=prompt, output=response, tokens={...})
    t.tool_call(tool="search", args={...}, result={...})
    t.retrieval(query="...", results=[...], match_count=5)

# Async variant
async with Tracer.run_async() as t:
    await t.llm_call(...)
```

---

## 6. Concurrency and Thread Safety

### Decision
Use thread-local storage for trace context with explicit step emission.

### Rationale
- FR-013: Must handle async operations correctly
- FR-014: No data corruption under concurrent step emission
- Multiple instrumentors produce independent traces (FR-009a)

### Implementation Notes
- Each instrumentor maintains its own trace context
- Step emission is thread-safe via queue or lock
- Async handlers use `asyncio.Lock()` for shared state

---

## Summary of Technology Choices

| Component | Technology | Justification |
|-----------|------------|---------------|
| Data Models | Pydantic v2 | Fast, validated, JSON schema |
| OTel Integration | opentelemetry-api/sdk | Standard transport |
| Semantic Conventions | OpenInference | Industry standard for LLM |
| LangChain Integration | BaseCallbackHandler | Native framework pattern |
| Testing | pytest + pytest-asyncio | Per FR-017 requirement |
| Serialization | Pydantic jiter (built-in) | 12x faster than v1 |

---

## Open Questions Resolved

| Question | Resolution | Source |
|----------|------------|--------|
| OTel attribute names | Use OpenInference conventions | Research |
| Token capture method | `on_llm_end` → `usage_metadata` | LangChain docs |
| Schema evolution | AliasChoices pattern | Pydantic docs |
| Large trace handling | TypeAdapter + JSONL | Performance research |
| Nested call representation | Flat list + parent_step_id | Spec clarification |