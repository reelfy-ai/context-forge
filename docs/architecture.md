# ContextForge Architecture

ContextForge evaluates **agent trajectories** and **context engineering quality**.  
It is designed to be **framework-agnostic**, **local-first**, and **CI-safe**.

This document describes the technical architecture: trace model, harness, graders, runners, and extension points.

---

## 1. Key concepts

### Trajectory
A **trajectory** is the full sequence of events that occurred during an agent run:
- messages in/out of the LLM
- retrieval steps and retrieved context
- tool calls + results
- memory writes/reads
- state transitions
- final output and outcome

ContextForge evaluates the **trajectory**, not only the final answer.

### The Six Pillars of Context Engineering
ContextForge evaluates agent quality through the lens of [six context engineering pillars](https://weaviate.io/blog/context-engineering):

| Pillar | Evaluation Focus |
|--------|------------------|
| **Agents** | Decision quality, planning, loop detection, budget discipline |
| **Query Augmentation** | Input refinement, intent preservation, query expansion quality |
| **Retrieval** | Chunk relevance, retrieval fitness, context selection/pruning |
| **Prompting** | Output format compliance, instruction following, hallucination detection |
| **Memory** | Memory hygiene, stale data detection, context window management |
| **Tools** | Tool necessity, argument correctness, error handling, orchestration |

Each pillar can fail in specific ways: context poisoning, distraction (irrelevant data), confusion (contradictory data), or clash (conflicting sources). ContextForge's graders are designed to detect these failure modes.

---

## 2. High-level component map

```
┌─────────────────────────────────────────────────────────────────────┐
│                       AGENT FRAMEWORKS                              │
│    LangChain │ LangGraph │ CrewAI │ AutoGen │ smolagents │ Custom   │
└──────┬─────────────┬─────────────┬─────────────┬─────────────┬──────┘
       │             │             │             │             │
       ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INSTRUMENTATION LAYER                            │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │  OpenInference  │  │    Callback     │  │  ContextForge       │ │
│  │  Instrumentors  │  │    Handlers     │  │  Tracer API         │ │
│  │  (Zero-Code)    │  │  (One-Line)     │  │  (Explicit)         │ │
│  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘ │
│           │                    │                      │            │
│           └────────────────────┴──────────────────────┘            │
│                                │                                    │
│                                ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │         OpenTelemetry / OpenInference Spans                 │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTEXTFORGE CORE                              │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │  OTel Span →    │  │   Canonical     │  │     Trace Store     │ │
│  │  Trace Converter│──│   Trace Spec    │──│  (JSONL / SQLite)   │ │
│  └─────────────────┘  └────────┬────────┘  └─────────────────────┘ │
│                                │                                    │
│                                ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Eval Harness                             │   │
│  │          (Tasks + Environments + Scenarios)                 │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Grader Engine                            │   │
│  │  Deterministic │ LLM-as-Judge (Ollama) │ Human Review       │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │            Reports + CI Artifacts                           │   │
│  │              (Markdown / JUnit / JSON)                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Package layout (target)

```
context_forge/
  __init__.py
  core/
    types.py              # dataclasses / pydantic models
    trace_spec.py         # canonical trace schema
    registry.py           # plugin registration
  instrumentation/
    base.py               # Instrumentor base class
    tracer.py             # Explicit Tracer API (Level 4)
    otel/
      converter.py        # OTel/OpenInference → Trace converter
      receiver.py         # OTLP gRPC receiver
    instrumentors/        # Framework-specific instrumentors (Level 2)
      langchain.py
      crewai.py
      autogen.py
      openai.py
    callbacks/            # Framework callback handlers (Level 3)
      langchain.py
      crewai.py
  harness/
    tasks.py              # Task definitions
    scenario.py           # Scenario / fixtures
    environment.py        # Tools + constraints
    runner.py             # executes tasks, produces traces
    replay.py             # record/replay tool calls
  graders/
    base.py               # grader interface + results
    deterministic/
      budget.py
      loops.py
      schema.py
      context_window.py
      memory_hygiene.py
      tool_correctness.py
    judges/
      base.py             # judge interface
      ollama.py           # Ollama backend (default)
      openai_compat.py    # optional
      prompts/            # judge prompt templates
  domains/
    context_engineering/  # reference domain pack
      graders/
      rubrics/
    creative/             # future (Reelfy pack)
  reports/
    markdown.py
    junit.py
    json.py
  cli/
    main.py               # contextforge CLI
examples/
docs/
```

Notes:
- **core** contains stable contracts: trace spec, interfaces, registries.
- **instrumentation** provides multiple integration levels:
  - **otel/**: Zero-code ingestion from existing OTel/OpenInference pipelines
  - **instrumentors/**: One-line auto-instrumentation via monkey-patching
  - **callbacks/**: Framework callback handlers for explicit tracing
  - **tracer.py**: Explicit Tracer API for full control
- **domains** are optional packs that can evolve independently.
- Instrumentors and judge backends are optional dependencies.

---

## 4. Canonical Trace Spec

> **Formal specification:** [specs/001-trace-capture/spec.md](specs/001-trace-capture/spec.md)

### 4.1 Trace goals
A ContextForge trace must be:
- **complete**: captures key agent events
- **portable**: independent of runtime/framework
- **replayable**: supports deterministic regression testing
- **auditable**: stores inputs/outputs needed to explain grades

### 4.2 Minimal schema (conceptual)

```json
{
  "run": {
    "run_id": "uuid",
    "started_at": "iso8601",
    "ended_at": "iso8601",
    "seed": 1337,
    "agent": {"name": "agent", "version": "v0.1.0"},
    "task": {"id": "task_id", "goal": "…", "dataset": "optional"},
    "env": {"name": "local", "toolset": ["search", "db_query"]}
  },
  "steps": [
    {
      "step_id": 1,
      "type": "llm_call",
      "model": "llama3.1",
      "input": {"system": "...", "messages": [...]},
      "output": {"text": "...", "tool_calls": [...]},
      "usage": {"tokens_in": 1200, "tokens_out": 350},
      "timing": {"latency_ms": 420}
    },
    {
      "step_id": 2,
      "type": "retrieval",
      "query": "...",
      "results": [{"doc_id": "...", "score": 0.72, "content": "..."}]
    },
    {
      "step_id": 3,
      "type": "tool_call",
      "tool": "search",
      "args": {"q": "..."},
      "result": {"items": [...]},
      "timing": {"latency_ms": 180}
    },
    {
      "step_id": 4,
      "type": "memory_write",
      "memory": "long_term",
      "key": "user_pref",
      "value": "..."
    }
  ],
  "artifacts": {
    "final_output": "...",
    "state_final": {},
    "errors": []
  },
  "budgets": {
    "tokens_total": 0,
    "tool_calls_total": 0,
    "latency_total_ms": 0,
    "cost_estimate_usd": 0
  },
  "outcome": {"status": "success|partial|fail", "reason": "optional"}
}
```

### 4.3 Step types (initial set)
- `user_input`
- `llm_call`
- `retrieval`
- `tool_call`
- `tool_result` (optional if separated from tool_call)
- `memory_read`
- `memory_write`
- `state_transition`
- `final_output`
- `error`

The spec intentionally allows more types over time.

### 4.4 User interaction overview

The canonical trace schema is an **internal contract** produced automatically by
ContextForge instrumentation.

Users do **not** author or manage trace JSON directly.

Integration is performed via:
- framework adapters (zero boilerplate)
- a lightweight Tracer API (minimal boilerplate)
- custom adapters for advanced runtimes

The detailed user-facing contracts, guarantees, and APIs are defined in
**SPEC.md**.

---

## 5. Instrumentation Layer

> **Formal specification:** [specs/001-trace-capture/spec.md](specs/001-trace-capture/spec.md)

ContextForge follows industry standards (OpenTelemetry, OpenInference) to provide multiple integration levels:

### 5.1 Integration Levels

| Level | User Effort | How It Works |
|-------|-------------|--------------|
| **Level 1: Zero-Code** | None | Ingest existing OTel/OpenInference traces |
| **Level 2: One-Line** | Add instrumentor | `LangChainInstrumentor().instrument()` |
| **Level 3: Callback** | Pass handler | `config={"callbacks": [handler]}` |
| **Level 4: Explicit** | Use Tracer API | Full control via `Tracer.run()` |

### 5.2 Level 1: Zero-Code (OTel Ingestion)

If users already have OpenTelemetry/OpenInference instrumentation, ContextForge can ingest traces directly:

```bash
# Collect traces from existing OpenTelemetry pipeline
contextforge collect --otlp-port 4317 --eval evals.yaml
```

### 5.3 Level 2: One-Line Instrumentation

Auto-instrument frameworks with a single line (monkey-patching pattern):

```python
from contextforge.instrumentation import LangChainInstrumentor

LangChainInstrumentor().instrument()

# Existing LangChain code works unchanged - all calls traced
from langchain_openai import ChatOpenAI
llm = ChatOpenAI()
response = llm.invoke("Hello!")  # Automatically traced
```

Or via environment variable:
```bash
CONTEXTFORGE_INSTRUMENT_LANGCHAIN=true python my_agent.py
```

### 5.4 Level 3: Callback Handlers

For frameworks with callback systems, pass the ContextForge handler:

```python
from contextforge.callbacks import ContextForgeHandler

handler = ContextForgeHandler()
chain.invoke(input, config={"callbacks": [handler]})
```

### 5.5 Level 4: Explicit Tracer API

For custom agents or when you need full control:

```python
from context_forge import Tracer

with Tracer.run(task="refund_request") as t:
    t.user_input("I want a refund")
    t.llm_call(model="gpt-4", output=response)
    t.tool_call("db_query", args, result)
    t.final_output(response)
```

### 5.6 Design Constraints

All instrumentation methods:
- MUST produce conformant ContextForge traces (Spec 001)
- MUST avoid global state; support concurrency
- MUST support both sync and async agents
- SHOULD support redaction hooks for PII/secrets

---

## 6. Evaluation Harness

### 6.1 Task
A Task defines:
- goal / objective
- inputs
- constraints (format, tools allowed, budgets)
- success criteria
- rubrics for judge graders (optional)

### 6.2 Environment
An Environment defines:
- available tools (real or mocked)
- tool schemas and constraints
- external resources (vector db, APIs) (optional)
- policy and safety filters

### 6.3 Scenario
A Scenario provides deterministic fixtures:
- recorded tool responses
- frozen time (optional)
- seeded randomness
- dataset selection

### 6.4 Runner
The runner executes: `(agent, task, scenario) -> trace`.

---

## 7. Tool Record / Replay (CI safety)

### Why it matters
Agents often depend on:
- network calls
- changing data
- stochastic LLM outputs

To run evals in CI, ContextForge supports tool **recording** and **replay**.

### Behavior
- **record mode**: call real tools, store (request, response, metadata)
- **replay mode**: replace tool execution with stored responses
- **strict mode**: fail if tool call signature diverges
- **fuzzy mode** (future): allow minor argument drift

This makes multi-step agent runs reproducible.

---

## 8. Grader Engine

> **Formal specification:** [specs/002-deterministic-graders/spec.md](specs/002-deterministic-graders/spec.md)

### 8.1 Grader interface (conceptual)
Each grader takes a trace and returns:
- score(s)
- pass/fail (optional)
- evidence (step references, excerpts)
- metadata (runtime, thresholds, confidence)

Graders must be **composable** and **independent**.

### 8.2 Deterministic graders (rules)
Each grader targets specific context engineering pillars:

| Grader | Pillars | What It Detects |
|--------|---------|-----------------|
| **BudgetGrader** | Agents, Tools | Token/tool/time limit violations |
| **LoopGrader** | Agents | Repeated tool thrashing or state cycles |
| **SchemaGrader** | Tools, Prompting | Invalid tool args/outputs, format errors |
| **ContextWindowGrader** | Retrieval, Memory | Bloated or irrelevant context injection |
| **MemoryHygieneGrader** | Memory | Stale or duplicate data resurfacing |
| **RetrievalRelevanceGrader** | Retrieval | Retrieved chunks not used in response |
| **ToolCorrectnessGrader** | Tools | Unnecessary calls, incorrect arguments |
| **ConflictGrader** | Retrieval, Memory | Contradictory context fragments (clash) |

### 8.3 LLM-as-judge graders (Ollama-first)
Used for qualitative evaluation across **all six pillars**:
- **Agents**: decision appropriateness, plan quality
- **Query Augmentation**: query refinement quality
- **Retrieval**: context relevance and usage
- **Prompting**: instruction following, output coherence
- **Memory**: appropriate recall and context management
- **Tools**: reflection adequacy, tool selection rationale

**Reproducibility requirements**
- store judge prompt template + filled prompt
- store judge model id + parameters (temp, top_p)
- store judge output raw + parsed
- support multi-judge and majority vote (future)

### 8.4 Human graders (optional)
Export traces + evidence to support manual review:
- CSV/JSON export
- annotation schema (future)
- inter-rater agreement (future)

---

## 9. Reports & artifacts

Outputs are generated from a run set:
- Markdown summary (local + GitHub)
- JUnit XML (CI)
- JSON metrics (dashboards)

Key aggregations:
- success rate (overall + by task)
- budget compliance
- tool error rates
- loop rate
- judge score distributions
- regression diffs vs baseline

---

## 10. Evaluation modes

### Mode A: CI Regression (deterministic)
- tool replay
- deterministic graders
- fast + stable
- optional fixed local judge

### Mode B: Pre-release Validation (hybrid)
- sampled tasks
- deterministic + judge graders
- multi-run stability checks

### Mode C: Production Monitoring (future)
- trace ingestion from live traffic
- asynchronous grading
- drift alerts and dashboards

---

## 11. Plugin & extension model

ContextForge supports three extension paths:

### 11.1 Domain packs (recommended)
Create a package that registers:
- tasks
- graders
- rubrics
- reporters (optional)

Example:
- `context_forge-domains-creative`
- `context_forge-domains-finance`

### 11.2 Custom graders
Implement the grader interface and register it.

### 11.3 Custom adapters
Implement adapter interface for your runtime.

---

## 12. Roadmap-driven stability promises

To keep the project reliable for adopters:

### Stable contracts (semver-protected)
- Trace Spec (core schema + backward compatible additions)
- Grader result format
- CLI interface (major-version changes only)

### Experimental areas
- judge prompts / rubrics
- framework-specific adapters
- domain packs (evolve faster than core)

---

## 13. Reelfy modules (future, but designed-in)

ContextForge will include optional domain packs for creative systems such as Reelfy, including graders for:
- narrative coherence across steps
- repetition & shot diversity
- style drift
- character consistency (trace-based signals)
- “creative fatigue” over long trajectories

These will live under `domains/creative` (or a separate package) to keep core neutral.

---
