# ContextForge Quickstart Guide

Get started with ContextForge in 5 minutes.

## What is ContextForge?

ContextForge evaluates **agent trajectories** — the full sequence of steps an AI agent takes, not just the final output. This includes:
- LLM calls and their token usage
- Tool calls and results
- Memory operations
- State transitions

## Installation

```bash
# Install from PyPI
pip install contextforge-eval

# With framework-specific extras
pip install contextforge-eval[langgraph]   # LangGraph support
pip install contextforge-eval[crewai]      # CrewAI support
pip install contextforge-eval[pydanticai]  # PydanticAI support
pip install contextforge-eval[all]         # All framework integrations
```

### For Contributors

```bash
# Clone the repository
git clone https://github.com/reelfy-ai/context-forge.git
cd context-forge

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Choose Your Integration Level

ContextForge provides **4 integration levels**. Pick the one that fits your setup:

| Level | User Effort | Best For |
|-------|-------------|----------|
| **Level 1: Zero-Code** | None | Teams with existing OTel/OpenInference |
| **Level 2: One-Line** | Add 1 line | LangChain, CrewAI, AutoGen users |
| **Level 3: Callback** | Pass handler | Explicit per-call tracing |
| **Level 4: Explicit** | Use Tracer API | Custom agents, full control |

---

## Level 1: Zero-Code (OTel Ingestion) — 🔜 Coming Soon

If you already have OpenTelemetry/OpenInference instrumentation:

```bash
# Planned: Collect traces from existing OpenTelemetry pipeline
contextforge collect --otlp-port 4317 --eval evals.yaml
```

This feature is on our roadmap. Currently, use Level 2-4 for trace capture.

---

## Level 2: One-Line Instrumentation

For LangChain, CrewAI, AutoGen, and other frameworks:

```python
from contextforge.instrumentation import LangChainInstrumentor

LangChainInstrumentor().instrument()

# Your existing code works unchanged - all calls are traced automatically
from langchain_openai import ChatOpenAI
llm = ChatOpenAI()
response = llm.invoke("Hello!")  # Automatically traced
```

Or via environment variable (zero code changes):
```bash
CONTEXTFORGE_INSTRUMENT_LANGCHAIN=true python my_agent.py
```

---

## Level 3: Callback Handler

For per-call control with frameworks that support callbacks:

```python
from contextforge.callbacks import ContextForgeHandler

handler = ContextForgeHandler()
chain.invoke(input, config={"callbacks": [handler]})
```

---

## Level 4: Explicit Tracer API

For custom agents or when you need full control, use the Tracer context manager:

```python
from context_forge import Tracer

with Tracer.run(task="my_task") as t:
    # Record what the user said
    t.user_input("Hello, can you help me?")

    # Call your LLM (your actual code here)
    response = my_llm.generate(prompt)

    # Record the LLM call
    t.llm_call(
        model="gpt-4",
        output=response,
        usage={"input_tokens": 50, "output_tokens": 30, "total_tokens": 80}
    )

    # Record the final output
    t.final_output(response)

# Access the trace after the context exits
trace = t.trace
print(f"Recorded {len(trace.steps)} steps")
```

### Adding Tool Calls (Level 4)

If your agent uses tools, record them with the explicit API:

```python
with Tracer.run(task="weather_check") as t:
    t.user_input("What's the weather in Paris?")

    # LLM decides to call a tool
    t.llm_call(
        model="gpt-4",
        output="",
        tool_calls=[{"name": "weather_api", "args": {"city": "Paris"}}]
    )

    # Execute and record the tool call
    result = weather_api(city="Paris")
    t.tool_call(
        tool="weather_api",
        args={"city": "Paris"},
        result=result,
        latency_ms=150
    )

    # LLM generates final response
    t.llm_call(model="gpt-4", output="It's sunny in Paris!")
    t.final_output("It's sunny in Paris!")
```

---

## Running Graders (All Levels)

Once you have traces (from any integration level), evaluate them with graders:

```python
from context_forge.graders import HybridMemoryHygieneGrader
from context_forge.graders.judges.backends import OllamaBackend

# Create a grader (combines deterministic + LLM evaluation)
grader = HybridMemoryHygieneGrader(
    llm_backend=OllamaBackend(model="llama3.2")
)

# Run the grader
result = grader.grade(trace)

print(f"Passed: {result.passed}")
print(f"Score: {result.score}")

# Print formatted report
result.print_report()

# Or access evidence programmatically
if not result.passed:
    for evidence in result.errors:
        print(f"  - [{evidence.check_name}] {evidence.description}")
```

## Evaluation Levels

ContextForge provides two evaluation approaches, depending on your needs:

### Level 2: Simple Evaluation (Recommended Start)

For quick, single-turn evaluation with minimal setup:

```python
from context_forge.evaluation import evaluate_agent
from langgraph.store.memory import InMemoryStore

# Set up your agent
store = InMemoryStore()
# ... populate store with user profile ...
graph = build_my_graph(store=store)

# Evaluate with one function call
result = evaluate_agent(
    graph=graph,
    message="I work from home now. When should I charge my EV?",
    store=store,
    user_id="user_123",
)

# Check results
if not result.passed:
    for error in result.errors:
        print(f"Issue: {error.description}")
```

### Level 3: Multi-Turn Simulation

For comprehensive testing with personas and scenarios:

```python
from context_forge import SimulationRunner, LangGraphAdapter
from context_forge.harness.user_simulator import GenerativeScenario, Persona

# Define a user persona
persona = Persona(
    name="Sarah",
    background="Homeowner with 7.5kW solar and Tesla Model 3",
    goals=["Get EV charging recommendation"],
)

# Create a multi-turn scenario
scenario = GenerativeScenario(
    persona=persona,
    initial_message="When should I charge my EV tonight?",
    max_turns=5,
)

# Set up adapter and runner
adapter = LangGraphAdapter(graph=graph, ...)
runner = SimulationRunner(adapter=adapter)

# Run simulation
result = await runner.run(scenario)
```

**When to use which:**
- **Level 2**: Quick testing, CI pipelines, simple scenarios
- **Level 3**: Systematic testing, multiple user types, complex conversations

---

## Configure Evaluation Suites — 🔜 Coming Soon

YAML configuration for evaluation suites is on our roadmap:

```yaml
# Planned: evals.yaml
suite:
  name: my_agent_evals

graders:
  - name: memory_hygiene
    config:
      llm_backend: ollama
      model: llama3.2

  - name: budget
    config:
      max_tokens: 5000
      max_tool_calls: 10
```

**Currently available**: Programmatic configuration via Python API (see above).

## CI Integration: Deterministic Tests — 🔜 Coming Soon

Tool recording and replay for CI is on our roadmap:

```yaml
# Planned: scenarios/test_case.yaml
id: happy_path
task_id: refund_request

input:
  user_message: "Refund order #12345"

tool_fixtures:
  - tool: order_lookup
    args: {order_id: "12345"}
    result: {status: "delivered", amount: 99.99}
```

**Currently available**: Export traces as JSON for custom CI integration.

## Available Graders

| Grader | Purpose | Type | Status |
|--------|---------|------|--------|
| `MemoryCorruptionGrader` | Detect data loss/corruption | Deterministic | ✅ Available |
| `MemoryHygieneJudge` | Detect missed facts, hallucinations | LLM Judge | ✅ Available |
| `HybridMemoryHygieneGrader` | Combined memory evaluation | Hybrid | ✅ Available |
| `BudgetGrader` | Token/tool/time limits | Deterministic | 🔜 Coming Soon |
| `LoopGrader` | Detect repetition | Deterministic | 🔜 Coming Soon |
| `SchemaGrader` | Validate tool usage | Deterministic | 🔜 Coming Soon |
| `RetrievalRelevanceGrader` | Measure retrieval usage | Deterministic | 🔜 Coming Soon |
| `ContextWindowGrader` | Detect bloated context | Deterministic | 🔜 Coming Soon |
| `TrajectoryJudge` | General LLM evaluation | LLM Judge | 🔜 Coming Soon |

## Project Structure

```
your_project/
├── evals.yaml           # Evaluation config
├── tasks/               # Task definitions
│   └── my_task.yaml
├── scenarios/           # Test scenarios
│   └── happy_path.yaml
├── rubrics/             # LLM judge rubrics
│   └── quality.md
└── traces/              # Generated traces
```

## Level 4 Advanced Patterns

These patterns use the explicit Tracer API for advanced control.

### Async Agents

```python
async with Tracer.run_async(task="async_task") as t:
    t.user_input("Query")
    response = await my_async_llm.generate(prompt)
    t.llm_call(model="gpt-4", output=response)
```

### Multi-Agent Systems

```python
with Tracer.run(task="multi_agent") as t:
    t.llm_call(model="gpt-4", output="Plan", actor="planner")
    t.tool_call(tool="search", args={}, result={}, actor="executor")
```

### Custom Graders

```python
from context_forge.graders import Grader, GraderResult, GraderRequirements

class MyGrader(Grader):
    name = "my_grader"
    version = "1.0.0"
    deterministic = True
    requirements = GraderRequirements(
        capabilities={"llm_calls"}
    )

    def grade(self, trace, config):
        # Your evaluation logic
        return GraderResult(
            grader_name=self.name,
            grader_version=self.version,
            passed=True,
            score=1.0
        )
```

## Next Steps

1. **Run examples**: `python examples/basic/01_simple_trace.py`
2. **Read specs**: See `specs/foundation/` for detailed contracts
3. **Explore architecture**: Read `ARCHITECTURE.md`
4. **Contribute**: Check `CONTRIBUTING.md`

## Getting Help

- [GitHub Issues](https://github.com/reelfy-ai/context-forge/issues)
- [Specifications](specs/README.md)
- [Architecture](ARCHITECTURE.md)

## Quick Reference

```python
# Tracer methods
t.user_input(content)                    # Record user input
t.llm_call(model, output, usage=...)     # Record LLM call
t.tool_call(tool, args, result)          # Record tool call
t.retrieval(query, results)              # Record retrieval
t.memory_read(key, value)                # Record memory read
t.memory_write(key, value)               # Record memory write
t.state_transition(from_s, to_s)         # Record state change
t.final_output(content)                  # Record final output
t.error(error_type, message)             # Record error

# Access trace
trace = t.trace                          # After context exits
trace.steps                              # List of steps
trace.budgets                            # Token/tool counts
trace.outcome                            # success/partial/fail
trace.capabilities                       # What was captured
```
