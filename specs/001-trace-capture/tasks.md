# Tasks: Trace Capture

**Input**: Design documents from `/specs/001-trace-capture/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD is REQUIRED per FR-015, FR-016, FR-017. Tests must exist and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Package root**: `context_forge/`
- **Core contracts**: `context_forge/core/`
- **Instrumentation**: `context_forge/instrumentation/`
- **Tests**: `tests/` (unit/, integration/, contract/)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Python package structure

- [x] T001 Create project structure: `context_forge/`, `tests/`, `pyproject.toml`
- [x] T002 Initialize Python 3.10+ project with Pydantic dependency in `pyproject.toml`
- [x] T003 [P] Configure pytest and pytest-asyncio in `pyproject.toml`
- [x] T004 [P] Configure Black and Ruff formatting in `pyproject.toml`
- [x] T005 [P] Create `context_forge/__init__.py` with package exports
- [x] T006 [P] Create `tests/conftest.py` with shared fixtures (sample traces, mock data)

---

## Phase 2: Foundational (Core Types & Models)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational (TDD - must fail first)

- [x] T007 [P] Write failing test for StepType enum in `tests/unit/test_types.py`
- [x] T008 [P] Write failing test for BaseStep model in `tests/unit/test_trace_schema.py`
- [x] T009 [P] Write failing test for all step type models (LLMCallStep, ToolCallStep, etc.) in `tests/unit/test_step_types.py`
- [x] T010 [P] Write failing test for TraceRun model in `tests/unit/test_trace_schema.py`
- [x] T011 [P] Write failing test for discriminated union validation in `tests/unit/test_trace_schema.py`
- [x] T012 [P] Write failing test for JSON serialization (<100ms for 1000 steps) in `tests/unit/test_trace_schema.py`

### Implementation for Foundational

- [x] T013 [P] Implement StepType enum in `context_forge/core/types.py`
- [x] T014 [P] Implement AgentInfo and TaskInfo models in `context_forge/core/types.py`
- [x] T015 [P] Implement ResourceImpact and RetrievalResult models in `context_forge/core/types.py`
- [x] T016 Implement BaseStep model in `context_forge/core/trace.py` (depends on T013)
- [x] T017 Implement LLMCallStep model in `context_forge/core/trace.py` (depends on T016)
- [x] T018 [P] Implement ToolCallStep model in `context_forge/core/trace.py`
- [x] T019 [P] Implement RetrievalStep model in `context_forge/core/trace.py`
- [x] T020 [P] Implement MemoryReadStep and MemoryWriteStep models in `context_forge/core/trace.py`
- [x] T021 [P] Implement InterruptStep model in `context_forge/core/trace.py`
- [x] T022 [P] Implement StateChangeStep, UserInputStep, FinalOutputStep models in `context_forge/core/trace.py`
- [x] T023 Implement TraceStep discriminated union in `context_forge/core/trace.py` (depends on T017-T022)
- [x] T024 Implement TraceRun model in `context_forge/core/trace.py` (depends on T023)
- [x] T025 [P] Implement custom exceptions in `context_forge/exceptions.py`
- [x] T026 Create `context_forge/core/__init__.py` with public exports
- [x] T027 Verify all foundational tests pass

**Checkpoint**: Foundation ready - all core models tested and working. User story implementation can now begin.

---

## Phase 3: User Story 1 - Auto-Instrument Framework Agent (Priority: P1) 🎯 MVP

**Goal**: One-line instrumentation for LangChain/CrewAI agents with `Instrumentor().instrument()`

**Independent Test**: Run a LangChain agent with `LangChainInstrumentor().instrument()` and verify trace file is produced

### Tests for User Story 1 (TDD - must fail first)

- [x] T028 [P] [US1] Write failing test for BaseInstrumentor interface in `tests/unit/test_instrumentor_base.py`
- [x] T029 [P] [US1] Write failing test for RedactionConfig in `tests/unit/test_instrumentor_base.py`
- [x] T030 [P] [US1] Write failing test for LangChainInstrumentor in `tests/integration/test_langchain_instrumentor.py`
- [ ] T031 [P] [US1] Write failing test for CrewAIInstrumentor in `tests/integration/test_crewai_instrumentor.py`
- [x] T032 [P] [US1] Write failing test for multiple instrumentors (FR-009a) in `tests/integration/test_langchain_instrumentor.py`
- [x] T032a [P] [US1] Write failing test for context manager auto-uninstrument pattern in `tests/integration/test_langchain_instrumentor.py`

### Implementation for User Story 1

- [x] T033 [US1] Implement RedactionConfig model in `context_forge/instrumentation/base.py`
- [x] T034 [US1] Implement BaseInstrumentor abstract class in `context_forge/instrumentation/base.py` (depends on T033)
- [x] T035 [US1] Implement instrument() and uninstrument() methods in `context_forge/instrumentation/base.py`
- [x] T036 [US1] Implement get_traces() method in `context_forge/instrumentation/base.py`
- [x] T037 [US1] Implement context manager protocol in BaseInstrumentor
- [x] T038 [US1] Create `context_forge/instrumentation/instrumentors/__init__.py`
- [x] T039 [US1] Implement LangChainInstrumentor in `context_forge/instrumentation/instrumentors/langchain.py` (depends on T034)
- [x] T040 [US1] Implement LangChain callback hooks for LLM, Tool, Retriever in `context_forge/instrumentation/instrumentors/langchain.py`
- [x] T041 [US1] Implement token usage capture from LangChain callbacks in `context_forge/instrumentation/instrumentors/langchain.py`
- [ ] T042 [US1] Implement CrewAIInstrumentor in `context_forge/instrumentation/instrumentors/crewai.py` (depends on T034)
- [x] T043 [US1] Create `context_forge/instrumentation/__init__.py` with LangChainInstrumentor exports
- [x] T044 [US1] Verify all User Story 1 tests pass (LangChain only - CrewAI pending)

**Checkpoint**: User Story 1 complete - LangChain/CrewAI agents can be traced with one line of code

---

## Phase 4: User Story 2 - Ingest Existing OpenTelemetry Traces (Priority: P1)

**Goal**: Zero-code integration for teams with existing OTel/OpenInference observability

**Independent Test**: Send OTel spans to collector and verify they convert to ContextForge traces

### Tests for User Story 2 (TDD - must fail first)

- [ ] T045 [P] [US2] Write failing test for SpanConverter in `tests/unit/test_span_converter.py`
- [ ] T046 [P] [US2] Write failing test for OpenInference attribute mappings in `tests/unit/test_span_converter.py`
- [ ] T047 [P] [US2] Write failing test for best-effort conversion (FR-010a) in `tests/unit/test_span_converter.py`
- [ ] T048 [P] [US2] Write failing test for OTLPCollector in `tests/integration/test_otel_ingestion.py`
- [ ] T049 [P] [US2] Write failing test for span-to-trace assembly in `tests/integration/test_otel_ingestion.py`

### Implementation for User Story 2

- [ ] T050 [US2] Create `context_forge/instrumentation/otel/__init__.py`
- [ ] T051 [US2] Implement OpenInference attribute constants in `context_forge/instrumentation/otel/constants.py`
- [ ] T052 [US2] Implement SpanConverter class in `context_forge/instrumentation/otel/converter.py`
- [ ] T053 [US2] Implement convert_span() method with span kind mapping in `context_forge/instrumentation/otel/converter.py`
- [ ] T054 [US2] Implement best-effort conversion with warnings for missing attributes in `context_forge/instrumentation/otel/converter.py`
- [ ] T055 [US2] Implement convert_trace() method for trace assembly in `context_forge/instrumentation/otel/converter.py`
- [ ] T056 [US2] Implement custom_mappings support in SpanConverter
- [ ] T057 [US2] Implement OTLPCollector class in `context_forge/instrumentation/otel/collector.py`
- [ ] T058 [US2] Implement async start()/stop() methods in OTLPCollector
- [ ] T059 [US2] Implement get_traces() in OTLPCollector
- [ ] T060 [US2] Update `context_forge/instrumentation/otel/__init__.py` with exports
- [ ] T061 [US2] Verify all User Story 2 tests pass

**Checkpoint**: User Story 2 complete - existing OTel traces can be ingested and converted

---

## Phase 5: User Story 3 - Callback Handler Integration (Priority: P2)

**Goal**: Per-call tracing control via framework callback handlers

**Independent Test**: Pass ContextForgeHandler to chain.invoke() and verify trace is captured

### Tests for User Story 3 (TDD - must fail first)

- [ ] T062 [P] [US3] Write failing test for ContextForgeHandler in `tests/unit/test_callback_handler.py`
- [ ] T063 [P] [US3] Write failing test for per-call trace isolation in `tests/integration/test_callback_handler.py`
- [ ] T064 [P] [US3] Write failing test for PII redaction in callbacks in `tests/integration/test_callback_handler.py`

### Implementation for User Story 3

- [ ] T065 [US3] Create `context_forge/instrumentation/callbacks/__init__.py`
- [ ] T066 [US3] Implement ContextForgeHandler extending BaseCallbackHandler in `context_forge/instrumentation/callbacks/langchain.py`
- [ ] T067 [US3] Implement on_llm_start/on_llm_end handlers in `context_forge/instrumentation/callbacks/langchain.py`
- [ ] T068 [US3] Implement on_tool_start/on_tool_end handlers in `context_forge/instrumentation/callbacks/langchain.py`
- [ ] T069 [US3] Implement on_retriever_start/on_retriever_end handlers in `context_forge/instrumentation/callbacks/langchain.py`
- [ ] T070 [US3] Implement token usage capture from callback response in `context_forge/instrumentation/callbacks/langchain.py`
- [ ] T071 [US3] Implement get_trace() method in ContextForgeHandler
- [ ] T072 [US3] Implement redaction support in ContextForgeHandler
- [ ] T073 [US3] Update exports in `context_forge/instrumentation/callbacks/__init__.py`
- [ ] T074 [US3] Verify all User Story 3 tests pass

**Checkpoint**: User Story 3 complete - callbacks enable per-call tracing control

---

## Phase 6: User Story 4 - Explicit Tracer API (Priority: P2)

**Goal**: Full control over trace capture for custom agents via Tracer context manager

**Independent Test**: Use Tracer.run() context manager to manually record steps and verify trace output

### Tests for User Story 4 (TDD - must fail first)

- [ ] T075 [P] [US4] Write failing test for Tracer context manager in `tests/unit/test_tracer_api.py`
- [ ] T076 [P] [US4] Write failing test for all step recording methods (llm_call, tool_call, etc.) in `tests/unit/test_tracer_api.py`
- [ ] T077 [P] [US4] Write failing test for async Tracer.run_async() in `tests/unit/test_tracer_api.py`
- [ ] T078 [P] [US4] Write failing test for to_json() and save() methods in `tests/unit/test_tracer_api.py`
- [ ] T079 [P] [US4] Write failing test for parent_step_id nesting in `tests/unit/test_tracer_api.py`

### Implementation for User Story 4

- [ ] T080 [US4] Implement Tracer class constructor in `context_forge/instrumentation/tracer.py`
- [ ] T081 [US4] Implement Tracer.run() class method returning context manager in `context_forge/instrumentation/tracer.py`
- [ ] T082 [US4] Implement llm_call() step recording method in `context_forge/instrumentation/tracer.py`
- [ ] T083 [US4] Implement tool_call() step recording method in `context_forge/instrumentation/tracer.py`
- [ ] T084 [US4] Implement retrieval() step recording method in `context_forge/instrumentation/tracer.py`
- [ ] T085 [US4] Implement memory_read() and memory_write() step recording methods in `context_forge/instrumentation/tracer.py`
- [ ] T086 [US4] Implement interrupt() step recording method in `context_forge/instrumentation/tracer.py`
- [ ] T087 [US4] Implement state_change(), user_input(), final_output() methods in `context_forge/instrumentation/tracer.py`
- [ ] T088 [US4] Implement get_trace() method in `context_forge/instrumentation/tracer.py`
- [ ] T089 [US4] Implement to_json() serialization method in `context_forge/instrumentation/tracer.py`
- [ ] T090 [US4] Implement save() file output method in `context_forge/instrumentation/tracer.py`
- [ ] T091 [US4] Implement Tracer.run_async() for async context manager in `context_forge/instrumentation/tracer.py`
- [ ] T092 [US4] Add Tracer to `context_forge/__init__.py` exports
- [ ] T093 [US4] Verify all User Story 4 tests pass

**Checkpoint**: User Story 4 complete - custom agents have full manual tracing control

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, performance validation, and schema stability

- [ ] T094 [P] Write schema backward compatibility tests in `tests/contract/test_trace_stability.py`
- [ ] T095 [P] Write performance test for 10k+ steps without memory errors (SC-004) in `tests/contract/test_trace_stability.py`
- [ ] T096 [P] Write performance test for <100ms JSON serialization (SC-003) in `tests/contract/test_trace_stability.py`
- [ ] T096a [P] Write test validating SC-006: token usage present in 95%+ of LLM call steps in `tests/contract/test_trace_stability.py`
- [ ] T097 Implement Instrumentor registry in `context_forge/core/registry.py` (for future CLI)
- [ ] T098 Create `context_forge/cli/__init__.py` placeholder for future CLI
- [ ] T099 Final integration test: run quickstart.md examples and verify outputs
- [ ] T100 Code cleanup: run Black/Ruff on all files
- [ ] T101 Verify all 101 tests pass (final validation)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → [User Stories in parallel or sequence]
                                           ├── Phase 3 (US1 - Instrumentors)
                                           ├── Phase 4 (US2 - OTel Ingestion)
                                           ├── Phase 5 (US3 - Callbacks)
                                           └── Phase 6 (US4 - Tracer API)
                                                         ↓
                                              Phase 7 (Polish)
```

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational completion
  - US1 and US2 are both P1 priority - can run in parallel
  - US3 and US4 are both P2 priority - can run in parallel after P1
  - Or all can run in parallel if team capacity allows
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Priority | Dependencies | Can Start After |
|-------|----------|--------------|-----------------|
| US1 (Instrumentors) | P1 | Phase 2 only | Foundational complete |
| US2 (OTel Ingestion) | P1 | Phase 2 only | Foundational complete |
| US3 (Callbacks) | P2 | Phase 2 only | Foundational complete |
| US4 (Tracer API) | P2 | Phase 2 only | Foundational complete |

**Note**: All user stories are independent and can be implemented/tested without other stories.

### Within Each User Story (TDD Order)

1. Write tests FIRST → verify they FAIL
2. Implement models/types
3. Implement services/logic
4. Implement public API
5. Verify tests PASS

---

## Parallel Opportunities

### Phase 2 (Foundational) Parallelism

```bash
# All test files can be written in parallel:
T007, T008, T009, T010, T011, T012 → parallel

# After StepType (T013), these can run in parallel:
T014, T015 → parallel (types.py models)

# After BaseStep (T016), all step types can run in parallel:
T017, T018, T019, T020, T021, T022 → parallel
```

### User Story Parallelism

```bash
# After Phase 2 complete, all user stories can start:
US1 (T028-T044) | US2 (T045-T061) | US3 (T062-T074) | US4 (T075-T093)
```

### Within User Story 1 (Example)

```bash
# Tests can run in parallel:
T028, T029, T030, T031, T032 → parallel

# After BaseInstrumentor (T034):
T039, T042 → parallel (LangChain and CrewAI instrumentors)
```

---

## Implementation Strategy

### MVP First (Phase 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (LangChain Instrumentor)
4. **STOP and VALIDATE**: Test with real LangChain agent
5. Deploy/demo - MVP complete!

**MVP delivers**: One-line tracing for LangChain agents (SC-001)

### Incremental Delivery

| Milestone | Phases | Value Delivered |
|-----------|--------|-----------------|
| MVP | 1-3 | LangChain/CrewAI auto-instrumentation |
| +OTel | +4 | Zero-code OTel ingestion |
| +Callbacks | +5 | Per-call tracing control |
| +Tracer | +6 | Full manual control |
| Complete | +7 | Performance validated, schema stable |

### Recommended Execution Order

For a single developer:
1. Phase 1 → Phase 2 → Phase 3 (MVP) → Phase 4 → Phase 5 → Phase 6 → Phase 7

For parallel team:
1. All: Phase 1 + Phase 2
2. Dev A: Phase 3 (US1) | Dev B: Phase 4 (US2)
3. Dev A: Phase 5 (US3) | Dev B: Phase 6 (US4)
4. All: Phase 7

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 103 |
| **Setup Tasks** | 6 |
| **Foundational Tasks** | 21 |
| **US1 Tasks** | 18 |
| **US2 Tasks** | 17 |
| **US3 Tasks** | 13 |
| **US4 Tasks** | 19 |
| **Polish Tasks** | 9 |
| **Parallelizable Tasks** | 54 (~52%) |

**MVP Scope**: Phases 1-3 (45 tasks) delivers LangChain/CrewAI instrumentation

**TDD Compliance**: All implementation tasks have corresponding failing tests that must be written first (per FR-015)