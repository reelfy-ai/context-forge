# Instrumentation Research: Making ContextForge Framework-Agnostic

## Executive Summary

The current ContextForge Tracer API requires manual instrumentation, which is:
- **Invasive**: Users must modify their agent code
- **Framework-coupled**: Our API, not theirs
- **Disconnected**: Not integrated with existing observability tools

The industry has converged on a better approach. This document analyzes how observability tools achieve **zero-code or minimal-code instrumentation** and proposes how ContextForge should adopt these patterns.

---

## Industry Approaches

### 1. OpenTelemetry Auto-Instrumentation

**Source**: [OpenTelemetry Python Zero-Code Instrumentation](https://opentelemetry.io/docs/zero-code/python/)

**How it works**:
```bash
# Install
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install

# Run (no code changes!)
opentelemetry-instrument python my_app.py
```

**Mechanism**: [Monkey patching at import time](https://opentelemetry.io/blog/2025/demystifying-auto-instrumentation/)
- Functions are first-class objects in Python
- At runtime, replace functions with instrumented wrappers
- Wrappers capture telemetry before/after calling original function
- Uses `require-in-the-middle` (Node.js) or import hooks (Python)

**Pros**:
- Zero code changes for supported libraries
- Industry standard (OTel is the de facto standard)
- Works with any OTel-compatible backend

**Cons**:
- Import order can cause issues
- Pre-compiled code can't be patched
- Overhead from function wrapping

---

### 2. OpenInference (Arize AI)

**Source**: [OpenInference GitHub](https://github.com/Arize-ai/openinference)

**What it is**: OpenTelemetry-compatible semantic conventions + instrumentors specifically for AI/LLM applications.

**Key Components**:
1. **Specification**: Semantic conventions for LLM calls, embeddings, retrieval
2. **Instrumentors**: Auto-instrumentation for 30+ frameworks
3. **Span Processors**: Normalize traces from different sources

**Supported Frameworks**:
- OpenAI, Anthropic, Bedrock, Mistral, Groq, VertexAI
- LangChain, LlamaIndex, CrewAI, AutoGen, smolagents
- DSPy, Instructor, Haystack

**Usage**:
```python
from openinference.instrumentation.openai import OpenAIInstrumentor
OpenAIInstrumentor().instrument()

# Now all OpenAI calls are traced automatically
```

**Why this matters for ContextForge**:
- OpenInference is becoming the standard for AI observability
- Many frameworks already have instrumentors
- We could consume OpenInference traces instead of requiring our own

---

### 3. LangSmith (LangChain)

**Source**: [LangSmith Observability](https://www.langchain.com/langsmith/observability)

**Approach**: Environment variable activation
```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=your_key
# That's it - all LangChain/LangGraph calls are traced
```

**For non-LangChain code**: `@traceable` decorator
```python
from langsmith import traceable

@traceable
def my_function():
    # Automatically traced
    pass
```

**Key insight**: Single environment variable enables full tracing for native LangChain code.

---

### 4. Langfuse (Open Source)

**Source**: [Langfuse](https://langfuse.com/)

**Approach**: Multiple integration methods
1. **Native SDKs**: Python/JS with decorators
2. **Framework callbacks**: LangChain callback handler
3. **OpenTelemetry**: Import OpenInference traces
4. **OpenAI drop-in**: `from langfuse.openai import openai`

**LangChain Integration**:
```python
from langfuse.callback import CallbackHandler
langfuse_handler = CallbackHandler()

# Pass to any LangChain call
chain.invoke(input, config={"callbacks": [langfuse_handler]})
```

**Key insight**: Callbacks are the least invasive integration for frameworks that support them.

---

### 5. CrewAI Observability

**Source**: [CrewAI Tracing](https://docs.crewai.com/en/observability/tracing)

**Built-in tracing**: CrewAI has native observability via CrewAI AMP platform.

**Third-party integration**: Uses OpenInference
```python
from openinference.instrumentation.crewai import CrewAIInstrumentor
CrewAIInstrumentor().instrument(skip_dep_check=True)
```

**Key insight**: Modern agent frameworks are building OpenInference support directly.

---

### 6. AutoGen (Microsoft)

**Source**: [AutoGen Tracing](https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/tracing.html)

**Native OpenTelemetry**: AutoGen 0.4+ has built-in OTel support
- Runtime tracing (automatically logs message metadata)
- Tool execution spans (following GenAI semantic conventions)
- Agent operation spans

**Disable tracing**:
```python
# Set environment variable
AUTOGEN_DISABLE_RUNTIME_TRACING=true
```

**Key insight**: Newest frameworks are building OTel support natively.

---

### 7. smolagents (HuggingFace)

**Source**: [smolagents OpenTelemetry](https://huggingface.co/docs/smolagents/en/tutorials/inspect_runs)

**OpenInference integration**:
```python
from openinference.instrumentation.smolagents import SmolagentsInstrumentor
SmolagentsInstrumentor().instrument()
# All agent runs are now traced
```

**Key insight**: Even minimalist frameworks adopt OpenInference.

---

## Synthesis: What ContextForge Should Do

### The Problem We're Solving

ContextForge wants to **evaluate** traces, not just **collect** them. However, our current approach requires users to:
1. Learn our Tracer API
2. Manually instrument their code
3. Replace their existing observability

This is backwards. We should:
1. **Consume traces** from existing observability (OTel, OpenInference)
2. **Provide optional instrumentors** for frameworks without good coverage
3. **Keep our Tracer API** for custom agents that need explicit control

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT FRAMEWORKS                            │
│  LangChain │ LangGraph │ CrewAI │ AutoGen │ smolagents │ Custom │
└──────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────┘
       │         │         │         │         │         │
       ▼         ▼         ▼         ▼         ▼         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INSTRUMENTATION LAYER                         │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ OpenInference│  │  Callbacks  │  │  ContextForge Tracer   │ │
│  │ Instrumentors│  │  (native)   │  │  (explicit control)    │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│         ▼                ▼                      ▼               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              OpenTelemetry Spans / Traces                   ││
│  │              (OpenInference Semantic Conventions)           ││
│  └──────────────────────────┬──────────────────────────────────┘│
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXTFORGE CORE                            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ OTel Span   │  │ Canonical   │  │      Graders            │ │
│  │ → Trace     │  │ Trace Spec  │  │  (Operate on traces)    │ │
│  │ Converter   │  │             │  │                         │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│         └────────────────┴──────────────────────┘               │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Evaluation Results                        ││
│  │              Reports (JUnit, Markdown, JSON)                ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Integration Levels

| Level | User Effort | How It Works |
|-------|-------------|--------------|
| **Zero-Code** | Install + env var | `CONTEXTFORGE_ENABLED=true` + existing OpenInference |
| **One-Line** | Add instrumentor | `ContextForgeInstrumentor().instrument()` |
| **Callback** | Pass callback | `config={"callbacks": [contextforge_handler]}` |
| **Explicit** | Use Tracer API | Current approach (for custom agents) |

### Implementation Strategy

#### Phase 1: OpenTelemetry Ingestion
1. Create `contextforge-otel-collector` that receives OTel/OpenInference spans
2. Convert OpenInference spans to ContextForge traces
3. Run graders on imported traces

```python
# User runs their existing instrumented code
from openinference.instrumentation.langchain import LangChainInstrumentor
LangChainInstrumentor().instrument()

# ContextForge collects via OTel
# contextforge collect --otel-endpoint localhost:4317
```

#### Phase 2: Native Instrumentors
Provide ContextForge-specific instrumentors that emit to our trace format directly:

```python
from contextforge.instrumentation import instrument_langchain, instrument_crewai

instrument_langchain()  # Monkey-patches LangChain
instrument_crewai()     # Monkey-patches CrewAI

# User code unchanged, traces flow to ContextForge
```

#### Phase 3: Framework Callbacks
For frameworks with callback systems:

```python
from contextforge.callbacks import LangChainHandler

handler = LangChainHandler()
chain.invoke(input, config={"callbacks": [handler]})

# Or globally
set_global_handler(handler)
```

#### Phase 4: Environment Variable Activation
Ultimate goal - zero code changes:

```bash
export CONTEXTFORGE_ENABLED=true
export CONTEXTFORGE_ENDPOINT=http://localhost:8080
python my_agent.py  # Automatically instrumented
```

---

## Comparison: Current vs Proposed

### Current Approach (Manual)
```python
from context_forge import Tracer

with Tracer.run(task="my_task") as t:
    t.user_input("Hello")
    # User must manually trace every step
    response = my_llm.generate(prompt)
    t.llm_call(model="gpt-4", output=response)
    t.final_output(response)
```

**Problems**:
- Invasive (requires code changes)
- Error-prone (easy to forget steps)
- Not compatible with existing agents
- Duplicates work (LLM calls already traced by other tools)

### Proposed Approach (Auto)
```python
# Option 1: One-liner with existing framework
from contextforge.instrumentation import instrument_langchain
instrument_langchain()
# Existing LangChain code works unchanged

# Option 2: Consume existing OpenInference traces
# (no code changes at all - just run collector)
# contextforge collect --source otel://localhost:4317

# Option 3: Explicit control (keep current API for custom agents)
from context_forge import Tracer
with Tracer.run(task="custom_agent") as t:
    # Explicit tracing for custom logic
```

---

## Spec Updates Required

### New Specs Needed

| Spec | Purpose |
|------|---------|
| **007-otel-ingestion** | How to import OTel/OpenInference spans |
| **008-instrumentor-interface** | Base class for framework instrumentors |
| **009-callback-handlers** | Framework callback integrations |

### Updated Specs

| Spec | Changes |
|------|---------|
| **001-trace-schema** | Add OTel span ID mapping |
| **002-tracer-api** | Position as "explicit mode" option |
| **ARCHITECTURE.md** | Add instrumentation layer diagram |

---

## Recommendations

1. **Adopt OpenInference semantic conventions** for our trace schema
2. **Build OTel span → ContextForge trace converter** as first priority
3. **Provide instrumentors** for frameworks without good OpenInference support
4. **Keep Tracer API** for custom agents and explicit control
5. **Support callbacks** for LangChain, CrewAI, etc.
6. **Target environment variable activation** as the ultimate UX goal

---

## Sources

- [OpenTelemetry Python Zero-Code Instrumentation](https://opentelemetry.io/docs/zero-code/python/)
- [Demystifying Auto-Instrumentation](https://opentelemetry.io/blog/2025/demystifying-auto-instrumentation/)
- [OpenInference GitHub](https://github.com/Arize-ai/openinference)
- [LangSmith Observability](https://www.langchain.com/langsmith/observability)
- [Langfuse LangChain Integration](https://langfuse.com/integrations/frameworks/langchain)
- [CrewAI Tracing](https://docs.crewai.com/en/observability/tracing)
- [AutoGen Tracing](https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/tracing.html)
- [smolagents OpenTelemetry](https://huggingface.co/docs/smolagents/en/tutorials/inspect_runs)
- [SigNoz CrewAI Observability](https://signoz.io/docs/crewai-observability/)
