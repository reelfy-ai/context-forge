# Implementation Plan: Trace Capture

**Branch**: `001-trace-capture` | **Date**: 2026-01-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-trace-capture/spec.md`

## Summary

ContextForge Trace Capture provides a multi-level integration system for capturing agent behavior as structured traces. The system supports 4 integration levels: OTel/OpenInference ingestion (Level 1), auto-instrumentation (Level 2), callback handlers (Level 3), and explicit Tracer API (Level 4). All traces conform to a stable TraceRun/TraceStep schema that graders can evaluate without framework-specific dependencies.

## Technical Context

**Language/Version**: Python 3.10+ (per constitution)
**Primary Dependencies**:
- Pydantic (data models, per constitution)
- opentelemetry-api, opentelemetry-sdk (OTel ingestion)
- opentelemetry-semantic-conventions-ai (OpenInference support)
- langchain-core (for LangChain instrumentor callbacks)

**Storage**: JSON files (trace output), no persistent storage required for core
**Testing**: pytest with pytest-asyncio (per spec FR-017, TDD required per FR-015)
**Target Platform**: Linux/macOS/Windows (Python library)
**Project Type**: Single Python package
**Performance Goals**:
- SC-003: Traces serialized to JSON in under 100ms for <1000 steps
- SC-004: Handle 10,000+ steps without memory errors
- SC-005: Millisecond timestamp precision

**Constraints**:
- No heavy runtime dependencies in core (per constitution)
- Framework integrations as optional extras
- Local-first, Ollama-first (no mandatory cloud dependencies)

**Scale/Scope**:
- Support traces up to 10,000+ steps
- Multiple concurrent instrumentors producing independent traces

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Framework Agnosticism | PASS | Instrumentors produce traces; graders never see framework objects |
| II. Traces as First-Class | PASS | TraceRun/TraceStep are core entities; schema stability required (FR-001) |
| III. Multi-Level Integration | PASS | All 4 levels implemented (FR-009 to FR-012) |
| IV. Spec-Driven Development | PASS | Spec complete with clarifications before planning |
| V. CI-Safe by Design | PASS | Tool record/replay supported via deterministic trace format |
| VI. Grader Quality Standards | N/A | This feature is trace capture, not graders |
| VII. Local-First | PASS | No cloud dependencies; OTel is transport layer |

**Technical Constraints Check**:
| Constraint | Status | Evidence |
|------------|--------|----------|
| Python 3.10+ | PASS | Target version |
| Type hints for public APIs | PASS | Required in implementation |
| Pydantic for data models | PASS | TraceRun, TraceStep will use Pydantic |
| Black/Ruff formatting | PASS | Applied during implementation |
| No heavy runtime dependencies | PASS | Core has minimal deps; frameworks are extras |
| pytest for tests | PASS | FR-017 specifies pytest |

**Pre-Implementation Gates**:
- [x] Spec exists and is approved
- [x] Constitution principles not violated
- [x] Required capabilities declared

## Project Structure

### Documentation (this feature)

```text
specs/001-trace-capture/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── tracer-api.md
│   ├── instrumentor-api.md
│   └── span-converter-api.md
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
context_forge/
├── core/                    # Stable contracts (trace spec, types, registry)
│   ├── __init__.py
│   ├── types.py             # StepType enum, base types
│   ├── trace.py             # TraceRun, TraceStep Pydantic models
│   └── registry.py          # Instrumentor registry
│
├── instrumentation/
│   ├── __init__.py
│   ├── base.py              # Instrumentor base class
│   ├── tracer.py            # Explicit Tracer API (Level 4)
│   │
│   ├── otel/                # OTel/OpenInference ingestion (Level 1)
│   │   ├── __init__.py
│   │   ├── collector.py     # OTLP receiver
│   │   └── converter.py     # SpanConverter: OTel spans → TraceSteps
│   │
│   ├── instrumentors/       # Framework auto-instrumentation (Level 2)
│   │   ├── __init__.py
│   │   ├── langchain.py     # LangChainInstrumentor
│   │   └── crewai.py        # CrewAIInstrumentor
│   │
│   └── callbacks/           # Framework callback handlers (Level 3)
│       ├── __init__.py
│       └── langchain.py     # ContextForgeHandler for LangChain
│
└── cli/                     # CLI (future)
    └── __init__.py

tests/
├── conftest.py              # Shared fixtures (sample traces, mock agents)
├── unit/
│   ├── test_trace_schema.py      # TraceRun, TraceStep validation
│   ├── test_step_types.py        # All step types serialize correctly
│   └── test_tracer_api.py        # Explicit tracer API
│
├── integration/
│   ├── test_langchain_instrumentor.py
│   ├── test_otel_ingestion.py
│   └── test_callback_handler.py
│
└── contract/
    └── test_trace_stability.py   # Schema backward compatibility
```

**Structure Decision**: Single Python package following the layout specified in CLAUDE.md. The `core/` module contains stable contracts; `instrumentation/` contains all 4 integration levels organized by method.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |
