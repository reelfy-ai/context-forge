# ContextForge

**Evaluation framework for context-aware, agentic AI systems.**

ContextForge evaluates agent **trajectories** (the full sequence of events during an agent run), not just final outputs. This catches behavioral failures that output-only evaluation misses.

## Key Features

- **Trajectory-based evaluation**: Analyze LLM calls, tool usage, memory operations, and more
- **Framework-agnostic**: Works with LangChain, LangGraph, CrewAI, AutoGen, and custom agents
- **Hybrid grading**: Combine deterministic rules with LLM judges
- **Local-first LLM**: Uses Ollama for evaluation without sending data to cloud APIs

## Quick Example

```python
from context_forge.instrumentation import Tracer
from context_forge.graders import HybridMemoryHygieneGrader
from context_forge.graders.judges.backends import OllamaBackend

# Capture a trace
with Tracer.run(run_id="my-agent-run", agent_name="MyAgent") as tracer:
    tracer.user_input("What's the weather?")
    tracer.llm_call(model="gpt-4", messages=[...], response="...")
    tracer.tool_call(name="weather_api", args={"city": "NYC"}, result={"temp": 72})

# Evaluate the trace
grader = HybridMemoryHygieneGrader(
    llm_backend=OllamaBackend(model="llama3.2")
)
result = grader.grade(tracer.get_trace())

# View results
result.print_report()
```

## Installation

```bash
pip install contextforge-eval

# With framework-specific extras
pip install contextforge-eval[langgraph]
pip install contextforge-eval[crewai]
pip install contextforge-eval[all]
```

## Next Steps

- [Quickstart Guide](quickstart.md) - Get up and running in 5 minutes
- [Architecture Overview](architecture.md) - Understand the design
- [Writing Custom Graders](guides/custom-graders.md) - Build your own evaluators
- [API Reference](api/index.md) - Complete API documentation