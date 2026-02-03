# API Contract: SpanConverter (Level 1 - OTel Ingestion)

**Feature**: 001-trace-capture | **Version**: 1.0.0

## Overview

SpanConverter transforms OpenTelemetry/OpenInference spans into ContextForge TraceSteps. This is Level 1 integration - zero-code ingestion for teams with existing observability.

## Module

```python
from context_forge.instrumentation.otel import SpanConverter
from context_forge.instrumentation.otel import OTLPCollector
```

---

## SpanConverter

### Constructor

```python
SpanConverter(
    strict_mode: bool = False,
    warn_on_missing: bool = True,
    custom_mappings: dict[str, str] | None = None,
)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `strict_mode` | `bool` | No | `False` | Reject spans with missing required attrs |
| `warn_on_missing` | `bool` | No | `True` | Log warnings for missing attributes |
| `custom_mappings` | `dict` | No | `None` | Custom attribute name mappings |

### Methods

#### convert_span()

Convert a single OTel span to TraceStep.

```python
def convert_span(
    self,
    span: ReadableSpan,
) -> TraceStep | None:
    """
    Convert an OpenTelemetry span to a ContextForge TraceStep.

    Args:
        span: OpenTelemetry ReadableSpan

    Returns:
        TraceStep if conversion successful, None if span should be skipped

    Raises:
        ConversionError: If strict_mode=True and required attributes missing
    """
```

#### convert_trace()

Convert a collection of spans to TraceRun.

```python
def convert_trace(
    self,
    spans: list[ReadableSpan],
    agent_info: AgentInfo | dict | None = None,
) -> TraceRun:
    """
    Convert a collection of OTel spans to a ContextForge TraceRun.

    Args:
        spans: List of OpenTelemetry spans (same trace_id)
        agent_info: Optional agent metadata override

    Returns:
        TraceRun with converted steps
    """
```

---

## Attribute Mappings

### OpenInference → ContextForge

| OpenInference Attribute | ContextForge Field | StepType |
|------------------------|-------------------|----------|
| `openinference.span.kind` | `step_type` (mapped) | - |
| `llm.model_name` | `model` | `llm_call` |
| `llm.token_count.prompt` | `tokens_in` | `llm_call` |
| `llm.token_count.completion` | `tokens_out` | `llm_call` |
| `llm.input_messages` | `input` | `llm_call` |
| `llm.output_messages` | `output` | `llm_call` |
| `retrieval.documents` | `results` | `retrieval` |

### Span Kind Mapping

| OpenInference `span.kind` | ContextForge `step_type` |
|--------------------------|-------------------------|
| `LLM` | `llm_call` |
| `TOOL` | `tool_call` |
| `RETRIEVER` | `retrieval` |
| `EMBEDDING` | `retrieval` |
| `CHAIN` | `state_change` |
| `AGENT` | `state_change` |
| `RERANKER` | `retrieval` |
| `GUARDRAIL` | `state_change` |

### Custom Mappings

```python
converter = SpanConverter(
    custom_mappings={
        "my.custom.model": "model",
        "my.custom.tokens": "tokens_in",
    }
)
```

---

## OTLPCollector

Collector for receiving OTLP spans.

### Constructor

```python
OTLPCollector(
    endpoint: str = "0.0.0.0:4317",
    converter: SpanConverter | None = None,
    output_path: str | Path | None = None,
)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `endpoint` | `str` | No | `"0.0.0.0:4317"` | OTLP gRPC endpoint |
| `converter` | `SpanConverter` | No | `None` | Custom converter |
| `output_path` | `str \| Path` | No | `None` | Trace output path |

### Methods

#### start()

Start the collector.

```python
async def start(self) -> None:
    """Start receiving OTLP spans."""
```

#### stop()

Stop the collector.

```python
async def stop(self) -> None:
    """Stop the collector and finalize traces."""
```

#### get_traces()

Get collected traces.

```python
def get_traces(self) -> list[TraceRun]:
    """Get all complete traces."""
```

---

## Usage Examples

### Direct Span Conversion

```python
from opentelemetry.sdk.trace import ReadableSpan
from context_forge.instrumentation.otel import SpanConverter

converter = SpanConverter()

# Convert single span
step = converter.convert_span(otel_span)

# Convert trace (collection of spans)
trace = converter.convert_trace(spans, agent_info={"name": "my-agent"})
```

### OTLP Collector

```python
import asyncio
from context_forge.instrumentation.otel import OTLPCollector

async def main():
    collector = OTLPCollector(
        endpoint="0.0.0.0:4317",
        output_path="./traces",
    )

    await collector.start()

    # Collector receives spans from external sources
    # e.g., OpenInference-instrumented LangChain apps

    # ... wait for spans ...

    traces = collector.get_traces()
    print(f"Collected {len(traces)} traces")

    await collector.stop()

asyncio.run(main())
```

### Integration with Existing Pipeline

```python
# Point existing OpenTelemetry exporter to ContextForge collector
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(endpoint="localhost:4317")
# Traces flow to ContextForge collector
```

---

## Best-Effort Conversion (FR-010a)

Per spec, conversion uses best-effort approach:

```python
converter = SpanConverter(
    strict_mode=False,   # Don't reject incomplete spans
    warn_on_missing=True,  # Log warnings for missing attrs
)

# Missing attributes get None/default values
step = converter.convert_span(incomplete_span)
# step.tokens_in will be None if not present in span
```

### Warnings

When `warn_on_missing=True`:

```
WARNING: Span {span_id} missing required attribute 'llm.model_name', using default
WARNING: Span {span_id} missing token counts, usage metrics unavailable
```

---

## Error Handling

```python
from context_forge.exceptions import ConversionError, CollectorError

# Strict mode raises on missing required attributes
converter = SpanConverter(strict_mode=True)

try:
    step = converter.convert_span(incomplete_span)
except ConversionError as e:
    print(f"Conversion failed: {e}")

# Collector errors
try:
    await collector.start()
except CollectorError as e:
    print(f"Collector failed: {e}")
```

---

## Performance Characteristics

| Operation | Target | Notes |
|-----------|--------|-------|
| Span conversion | < 0.1ms per span | In-memory transform |
| Trace assembly | < 10ms for 1000 spans | Sorting + linking |
| OTLP receive | Matches OTel SDK | gRPC streaming |

---

## Thread Safety

- `SpanConverter` methods are stateless and thread-safe
- `OTLPCollector` uses internal locking for trace assembly
- Multiple sources can send spans to same collector