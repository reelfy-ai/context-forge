# API Reference

This section contains the complete API documentation for ContextForge, auto-generated from source code docstrings.

## Core Modules

| Module | Description |
|--------|-------------|
| [Trace](core/trace.md) | Trace models and step types |
| [Types](core/types.md) | Common types and data structures |

## Graders

| Module | Description |
|--------|-------------|
| [Base](graders/base.md) | Base grader classes and result types |
| [Memory Hygiene](graders/memory-hygiene.md) | Memory management evaluation |
| [LLM Judges](graders/judges.md) | LLM-based semantic evaluation |

## Instrumentation

| Module | Description |
|--------|-------------|
| [Tracer](instrumentation/tracer.md) | Explicit trace capture API |
| [LangChain](instrumentation/langchain.md) | Auto-instrumentation for LangChain |

## Package Structure

```
context_forge/
    core/           # Trace models and types
    graders/        # Evaluation graders
        deterministic/  # Rule-based graders
        judges/         # LLM-based judges
    instrumentation/    # Trace capture
        instrumentors/  # Auto-instrumentation
    harness/        # Test harness and simulation
```