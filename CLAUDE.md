# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ContextForge is an open-source evaluation framework for context-aware, agentic AI systems. It evaluates **agent trajectories** (the full sequence of events during an agent run), not just final outputs. The project is early-stage and design-first—currently documentation exists but implementation is pending.

## Development Environment

- Python 3.10+
- Virtual environment: `.venv/` (already created)
- Activate: `source .venv/bin/activate`

## Code Style & Tooling

- Type hints required for public APIs
- Prefer Pydantic or dataclasses for models
- Black / Ruff formatting
- No heavy runtime dependencies in core

## Architecture Principles

### Framework Agnosticism
Graders MUST operate only on traces, never on framework objects (LangChain, LangGraph, AutoGen, etc.). All framework-specific logic belongs in **adapters**, not graders.

### Multi-Level Integration Model
ContextForge follows industry standards (OpenTelemetry, OpenInference) and provides 4 integration levels:

| Level | Method | Use When |
|-------|--------|----------|
| Level 1: Zero-Code | OTel/OpenInference ingestion | Existing observability pipeline |
| Level 2: One-Line | `LangChainInstrumentor().instrument()` | LangChain/CrewAI/AutoGen users |
| Level 3: Callback | `config={"callbacks": [handler]}` | Per-call control |
| Level 4: Explicit | `Tracer.run()` context manager | Custom agents, full control |

### Two-Layer Event Model
- **Canonical Trace (ContextForge)**: stable JSON/Pydantic schema for grading, replay, and reporting (the grading layer)
- **OpenTelemetry/OpenInference Spans**: transport/interchange layer for observability tools

### Target Package Layout
```
context_forge/
  core/              # trace spec, types, registry (stable contracts)
  instrumentation/
    base.py          # Instrumentor base class
    tracer.py        # Explicit Tracer API (Level 4)
    otel/            # OTel/OpenInference → Trace converter (Level 1)
    instrumentors/   # Framework-specific auto-instrumentation (Level 2)
    callbacks/       # Framework callback handlers (Level 3)
  harness/           # tasks, scenarios, environments, runner, replay
  graders/           # deterministic/ and judges/ (Ollama-first)
  domains/           # industry-specific eval packs (separate from core)
  reports/           # markdown, junit, json reporters
  cli/               # contextforge CLI
```

## Key Design Contracts

### Trace Spec
- Backward compatibility is mandatory
- Additive changes only in minor versions
- Never remove or rename fields without aliasing
- New step types must degrade gracefully

### Graders
- Must be deterministic unless explicitly declared otherwise
- Must be stateless and side-effect free
- Must declare required step types and fields
- Must include evidence pointers in results (step_ids, excerpts, thresholds)

### Instrumentation (Instrumentors, Callbacks, OTel Ingestion)
- Must normalize framework events to ContextForge trace steps
- Must NOT expose framework-native objects downstream
- Must support async + concurrency
- Must provide redaction hooks for PII/secrets
- Instrumentors follow the `SomeInstrumentor().instrument()` pattern (OpenInference convention)
- OTel ingestion converts OpenInference spans to ContextForge traces

## Evaluation Configuration

Evals are defined declaratively in YAML:
```yaml
suite: checkout_agent
graders:
  - budget:
      max_tokens: 5000
      max_tool_calls: 10
  - loops:
      max_repeats: 3
  - trajectory_judge:
      backend: ollama
      model: llama3.1
      rubric: rubrics/context_quality.md
```

## CI Safety

Tool record/replay is first-class:
- **record mode**: call real tools, store (request, response, metadata)
- **replay mode**: replace tool execution with stored responses
- **strict mode**: fail if tool call signature diverges

Canonicalize tool calls for replay (stable names, JSON-serializable args, sorted keys).

## Spec-Driven Development

ContextForge uses **Spec-Driven Development**. Specifications define contracts before implementation.

### Spec Directory Structure (GitHub Spec-Kit)
```
specs/
  001-trace-capture/           # P1: Capture agent behavior
  002-deterministic-graders/   # P1: Rule-based evaluation
  003-llm-judges/              # P2: LLM-based evaluation
  004-eval-configuration/      # P2: YAML config for suites
  005-ci-replay/               # P2: Record/replay for CI
```

### Spec-Kit Workflow
Each feature starts with `spec.md` (user stories, requirements). Run `/speckit.plan` to generate technical artifacts:

```
/speckit.specify → /speckit.plan → /speckit.tasks → /speckit.implement
     spec.md         plan.md          tasks.md          code
                     research.md
                     data-model.md
                     contracts/
```

| Feature | Priority | Status |
|---------|----------|--------|
| 001-trace-capture | P1 | spec.md ✓ (4 integration levels) |
| 002-deterministic-graders | P1 | spec.md ✓ |
| 003-llm-judges | P2 | spec.md ✓ |
| 004-eval-configuration | P2 | spec.md ✓ |
| 005-ci-replay | P2 | spec.md ✓ |

### When Adding New Features
1. Run `/speckit.specify [feature description]` to create spec.md
2. Run `/speckit.clarify` if requirements are ambiguous
3. Run `/speckit.plan` to generate technical artifacts
4. Run `/speckit.tasks` to break down into work items
5. Run `/speckit.implement` to code