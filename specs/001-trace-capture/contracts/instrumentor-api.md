# API Contract: Instrumentor (Level 2 - Auto-Instrumentation)

**Feature**: 001-trace-capture | **Version**: 1.0.0

## Overview

Instrumentors provide one-line auto-instrumentation for supported frameworks. This is Level 2 integration in the ContextForge hierarchy, following the OpenInference pattern.

## Module

```python
from context_forge.instrumentation import LangChainInstrumentor
from context_forge.instrumentation import CrewAIInstrumentor
from context_forge.instrumentation.base import BaseInstrumentor
```

---

## Usage Pattern

### One-Line Instrumentation

```python
from context_forge.instrumentation import LangChainInstrumentor

# Instrument globally
LangChainInstrumentor().instrument()

# Your existing code works unchanged
chain = prompt | llm | parser
result = chain.invoke({"input": "Hello"})  # Automatically traced
```

### Scoped Instrumentation

```python
instrumentor = LangChainInstrumentor()
instrumentor.instrument()

try:
    # Traced code
    result = chain.invoke(...)
finally:
    instrumentor.uninstrument()
```

### Context Manager (Recommended)

```python
with LangChainInstrumentor() as instrumentor:
    result = chain.invoke(...)  # Traced
# Auto-uninstrumented after block
```

---

## BaseInstrumentor

Abstract base class for all instrumentors.

### Constructor

```python
BaseInstrumentor(
    output_path: str | Path | None = None,
    tracer_provider: TracerProvider | None = None,
    redaction_config: RedactionConfig | None = None,
)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `output_path` | `str \| Path` | No | `None` | Path for trace output |
| `tracer_provider` | `TracerProvider` | No | `None` | Custom OTel tracer |
| `redaction_config` | `RedactionConfig` | No | `None` | PII redaction settings |

### Methods

#### instrument()

Enable instrumentation.

```python
def instrument(self) -> None:
    """
    Enable auto-instrumentation for this framework.

    After calling, all framework operations are automatically traced.
    """
```

#### uninstrument()

Disable instrumentation.

```python
def uninstrument(self) -> None:
    """
    Disable auto-instrumentation.

    Restores original framework behavior.
    """
```

#### is_instrumented()

Check instrumentation status.

```python
def is_instrumented(self) -> bool:
    """Returns True if currently instrumented."""
```

#### get_traces()

Get collected traces.

```python
def get_traces(self) -> list[TraceRun]:
    """
    Get all traces collected since instrumentation started.

    Returns:
        List of TraceRun objects
    """
```

---

## LangChainInstrumentor

Instrumentor for LangChain and LangGraph.

### Constructor

```python
LangChainInstrumentor(
    output_path: str | Path | None = None,
    tracer_provider: TracerProvider | None = None,
    redaction_config: RedactionConfig | None = None,
    capture_inputs: bool = True,
    capture_outputs: bool = True,
)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `capture_inputs` | `bool` | No | `True` | Capture LLM inputs |
| `capture_outputs` | `bool` | No | `True` | Capture LLM outputs |

### Captured Operations

| LangChain Component | ContextForge StepType | Captured Fields |
|--------------------|----------------------|-----------------|
| LLM/ChatModel | `llm_call` | model, input, output, tokens |
| Tool | `tool_call` | tool_name, arguments, result |
| Retriever | `retrieval` | query, results, scores |
| Chain | `state_change` | inputs, outputs |

### Example

```python
from context_forge.instrumentation import LangChainInstrumentor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Instrument
instrumentor = LangChainInstrumentor(output_path="./traces")
instrumentor.instrument()

# Use LangChain normally
llm = ChatOpenAI(model="gpt-4")
prompt = ChatPromptTemplate.from_template("Tell me about {topic}")
chain = prompt | llm

result = chain.invoke({"topic": "Python"})

# Get traces
traces = instrumentor.get_traces()
print(f"Captured {len(traces[0].steps)} steps")

# Cleanup
instrumentor.uninstrument()
```

---

## CrewAIInstrumentor

Instrumentor for CrewAI multi-agent workflows.

### Constructor

```python
CrewAIInstrumentor(
    output_path: str | Path | None = None,
    tracer_provider: TracerProvider | None = None,
    redaction_config: RedactionConfig | None = None,
)
```

### Captured Operations

| CrewAI Component | ContextForge StepType | Captured Fields |
|-----------------|----------------------|-----------------|
| Agent LLM calls | `llm_call` | model, input, output, tokens |
| Tool usage | `tool_call` | tool_name, arguments, result |
| Task completion | `state_change` | task info, result |
| Crew orchestration | `state_change` | crew state |

### Example

```python
from context_forge.instrumentation import CrewAIInstrumentor
from crewai import Agent, Task, Crew

# Instrument
instrumentor = CrewAIInstrumentor()
instrumentor.instrument()

# Use CrewAI normally
agent = Agent(role="Researcher", goal="...", backstory="...")
task = Task(description="...", agent=agent)
crew = Crew(agents=[agent], tasks=[task])

result = crew.kickoff()

# Get traces
traces = instrumentor.get_traces()
```

---

## RedactionConfig

Configuration for PII/secret redaction.

```python
from context_forge.instrumentation import RedactionConfig

config = RedactionConfig(
    redact_inputs: bool = False,
    redact_outputs: bool = False,
    patterns: list[str] | None = None,  # Regex patterns to redact
    replacement: str = "[REDACTED]",
)
```

### Example

```python
config = RedactionConfig(
    redact_inputs=True,
    patterns=[
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    ],
)

instrumentor = LangChainInstrumentor(redaction_config=config)
```

---

## Multiple Instrumentors

Per FR-009a, multiple instrumentors produce independent traces:

```python
langchain_inst = LangChainInstrumentor()
crewai_inst = CrewAIInstrumentor()

langchain_inst.instrument()
crewai_inst.instrument()

# Both capture independently
# Traces correlatable via shared run context (timestamps, trace IDs)
```

---

## Custom Instrumentor Implementation

```python
from context_forge.instrumentation.base import BaseInstrumentor

class MyFrameworkInstrumentor(BaseInstrumentor):
    def _do_instrument(self) -> None:
        """Override to add framework-specific hooks."""
        # Patch framework methods
        pass

    def _do_uninstrument(self) -> None:
        """Override to remove framework-specific hooks."""
        # Restore original methods
        pass
```

---

## Error Handling

```python
from context_forge.exceptions import InstrumentorError

try:
    instrumentor = LangChainInstrumentor()
    instrumentor.instrument()
except InstrumentorError as e:
    print(f"Failed to instrument: {e}")
```

---

## Thread Safety

- `instrument()` and `uninstrument()` are thread-safe
- Trace collection is thread-safe (uses thread-local storage)
- Multiple threads can invoke instrumented code concurrently