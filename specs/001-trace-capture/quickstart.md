# Quickstart: Trace Capture

Get started with ContextForge trace capture in 5 minutes.

## Installation

```bash
pip install context-forge

# Optional: Framework-specific extras
pip install context-forge[langchain]  # LangChain support
pip install context-forge[crewai]     # CrewAI support
pip install context-forge[otel]       # OpenTelemetry support
```

## Choose Your Integration Level

| Level | Best For | Lines of Code |
|-------|----------|---------------|
| Level 2: Auto-Instrument | LangChain/CrewAI users | 1 line |
| Level 1: OTel Ingestion | Existing observability | 0 lines (config) |
| Level 3: Callbacks | Per-call control | 1-3 lines |
| Level 4: Explicit API | Custom agents | 5-10 lines |

---

## Level 2: Auto-Instrumentation (Recommended)

One line to trace your LangChain agent:

```python
from context_forge.instrumentation import LangChainInstrumentor

# Add this ONE line before your agent code
LangChainInstrumentor().instrument()

# Your existing code works unchanged
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOpenAI(model="gpt-4")
prompt = ChatPromptTemplate.from_template("Tell me about {topic}")
chain = prompt | llm

result = chain.invoke({"topic": "Python"})
# ↑ Automatically traced!
```

### Save Traces

```python
instrumentor = LangChainInstrumentor(output_path="./traces")
instrumentor.instrument()

# ... run your agent ...

# Traces saved to ./traces/trace-{run_id}.json
```

---

## Level 1: OTel Ingestion

Already using OpenTelemetry? Point it at ContextForge:

```python
from context_forge.instrumentation.otel import OTLPCollector
import asyncio

async def collect_traces():
    collector = OTLPCollector(endpoint="0.0.0.0:4317")
    await collector.start()

    # Traces from your OpenInference-instrumented apps flow here
    # No code changes needed in your agents!

asyncio.run(collect_traces())
```

Or configure your existing OTLP exporter:

```python
# In your instrumented app
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(endpoint="contextforge-collector:4317")
```

---

## Level 3: Callback Handler

Control tracing per-call:

```python
from context_forge.instrumentation.callbacks import ContextForgeHandler

handler = ContextForgeHandler()

# Trace only this specific call
result = chain.invoke(
    {"topic": "Python"},
    config={"callbacks": [handler]}
)

# Get the trace
trace = handler.get_trace()
```

---

## Level 4: Explicit Tracer API

Full control for custom agents:

```python
from context_forge import Tracer

with Tracer.run(agent_info={"name": "my-custom-agent"}) as t:
    # Record user input
    t.user_input(content="What is 2+2?")

    # Record LLM call
    t.llm_call(
        model="gpt-4",
        input="What is 2+2?",
        output="2+2 equals 4.",
        tokens_in=8,
        tokens_out=6,
    )

    # Record tool call
    t.tool_call(
        tool_name="calculator",
        arguments={"expression": "2+2"},
        result=4,
    )

    # Record final output
    t.final_output(content="The answer is 4.")

# Save trace
trace = t.get_trace()
trace_json = t.to_json()
```

### Async Support

```python
async with Tracer.run_async(agent_info={"name": "async-agent"}) as t:
    await t.llm_call(
        model="gpt-4",
        input="Hello",
        output="Hi there!",
    )
```

---

## View Your Traces

Traces are saved as JSON:

```json
{
  "run_id": "abc123",
  "started_at": "2024-01-21T10:30:00.000Z",
  "ended_at": "2024-01-21T10:30:05.123Z",
  "agent_info": {"name": "my-agent"},
  "steps": [
    {
      "step_id": "step-1",
      "step_type": "llm_call",
      "timestamp": "2024-01-21T10:30:01.000Z",
      "model": "gpt-4",
      "input": "What is 2+2?",
      "output": "2+2 equals 4.",
      "tokens_in": 8,
      "tokens_out": 6
    }
  ]
}
```

---

## Next Steps

1. **Evaluate traces** with ContextForge graders (see 002-deterministic-graders)
2. **Run in CI** with replay mode (see 005-ci-replay)
3. **Add LLM judges** for quality evaluation (see 003-llm-judges)

## Troubleshooting

### "No traces captured"

1. Ensure instrumentor is called **before** creating LLM/chain objects
2. Check that you're using a supported framework version
3. Enable debug logging: `export CONTEXTFORGE_LOG_LEVEL=DEBUG`

### "Missing token counts"

Token counts depend on LLM provider support. Some providers don't return token usage. Check FR-006 compliance.

### "Import errors"

Install the appropriate extra:
```bash
pip install context-forge[langchain]  # For LangChain
pip install context-forge[crewai]     # For CrewAI
```