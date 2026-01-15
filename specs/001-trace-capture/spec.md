# Feature Specification: Trace Capture

**Feature Branch**: `001-trace-capture`
**Created**: 2025-01-14
**Status**: Draft
**Priority**: P1 (Must Have for MVP)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-Instrument Framework Agent (Priority: P1)

As an **agent developer using LangChain/CrewAI/AutoGen**, I want to capture what my agent does with minimal code changes, so that I can evaluate its behavior without rewriting my agent.

**Why this priority**: Most users are already using a framework. One-line instrumentation is the lowest friction entry point.

**Independent Test**: Can be fully tested by running a LangChain agent with instrumentor and verifying a trace file is produced.

**Acceptance Scenarios**:

1. **Given** an agent using LangChain, **When** I add `LangChainInstrumentor().instrument()`, **Then** all LLM calls, tool calls, and retrieval operations are automatically captured in a trace file
2. **Given** an agent using CrewAI, **When** I add `CrewAIInstrumentor().instrument()`, **Then** all crew activities are captured without modifying my crew code
3. **Given** instrumentation is enabled, **When** my agent completes a run, **Then** I can access the trace with timestamps, inputs, outputs, and token usage for each step

---

### User Story 2 - Ingest Existing OpenTelemetry Traces (Priority: P1)

As a **team with existing observability**, I want to evaluate traces I'm already collecting, so that I don't need to add another instrumentation layer.

**Why this priority**: Many teams already have OpenTelemetry/OpenInference. Zero-code integration removes adoption friction.

**Independent Test**: Can be fully tested by sending OTel spans to the collector and verifying they convert to ContextForge traces.

**Acceptance Scenarios**:

1. **Given** I have OpenInference instrumentation, **When** I point ContextForge at my OTLP endpoint, **Then** my existing traces are converted and available for evaluation
2. **Given** traces from multiple frameworks (LangChain + custom code), **When** they're ingested via OTel, **Then** they're unified into a single ContextForge trace format
3. **Given** OTel spans with LLM call attributes, **When** converted, **Then** token usage, model info, and timing are preserved

---

### User Story 3 - Callback Handler Integration (Priority: P2)

As an **agent developer**, I want to pass a callback handler to specific calls, so that I can selectively trace parts of my agent without global instrumentation.

**Why this priority**: Some teams need per-call control. Callbacks fit naturally into LangChain/CrewAI patterns.

**Independent Test**: Can be fully tested by passing ContextForge handler to a chain invoke and verifying trace is captured.

**Acceptance Scenarios**:

1. **Given** a LangChain chain, **When** I pass `config={"callbacks": [ContextForgeHandler()]}`, **Then** that specific call is traced without affecting other calls
2. **Given** multiple chains with different handlers, **When** I run them, **Then** each produces its own trace
3. **Given** a handler configured with redaction, **When** tracing captures PII, **Then** sensitive data is redacted before storage

---

### User Story 4 - Explicit Tracer API (Priority: P2)

As a **custom agent developer**, I want full control over what gets traced, so that I can capture exactly what matters for my evaluation.

**Why this priority**: Some agents don't fit framework patterns. Explicit API provides escape hatch.

**Independent Test**: Can be fully tested by using Tracer context manager and verifying all recorded steps appear in trace.

**Acceptance Scenarios**:

1. **Given** a custom agent, **When** I use `Tracer.run()` context manager, **Then** I can manually record each step with `t.llm_call()`, `t.tool_call()`, etc.
2. **Given** I'm recording steps manually, **When** I call `t.retrieval()`, **Then** I can include query, results, and scores
3. **Given** async agent code, **When** I use `async with Tracer.run_async()`, **Then** concurrent steps are properly captured with correct ordering

---

### Edge Cases

- What happens when instrumentation is added after agent initialization?
- How are nested/recursive agent calls represented in the trace?
- What happens when OTel spans are missing required attributes?
- How are very large traces (>10k steps) handled without memory issues?
- What happens when multiple instrumentors are active simultaneously?

## Requirements *(mandatory)*

### Functional Requirements

**Trace Format**
- **FR-001**: System MUST produce traces in a documented, stable JSON format (TraceRun schema)
- **FR-002**: Each trace MUST include run metadata: run_id, started_at, ended_at, agent info, task info
- **FR-003**: Each step MUST include: step_id, step_type, timestamp, inputs, outputs
- **FR-004**: System MUST support step types: user_input, llm_call, tool_call, retrieval, memory_read, memory_write, state_change, final_output

**LLM Call Capture**
- **FR-005**: LLM calls MUST capture: model identifier, input/prompt, output/response
- **FR-006**: LLM calls SHOULD capture: token usage (input, output, total), latency, cost estimate

**Tool Call Capture**
- **FR-007**: Tool calls MUST capture: tool name, arguments, result
- **FR-008**: Tool calls SHOULD capture: latency, success/failure status

**Integration Methods**
- **FR-009**: System MUST support auto-instrumentation via `Instrumentor().instrument()` pattern
- **FR-010**: System MUST support OTel/OpenInference span ingestion via OTLP
- **FR-011**: System MUST support explicit tracing via Tracer context manager API
- **FR-012**: System MUST support framework callback handlers

**Concurrency & Async**
- **FR-013**: System MUST handle async agent operations correctly
- **FR-014**: System MUST handle concurrent step emission without data corruption

### Key Entities

- **TraceRun**: Complete record of an agent run (metadata + ordered steps)
- **TraceStep**: Single event in the trace (LLM call, tool call, etc.)
- **StepType**: Enum of supported step types
- **Instrumentor**: Auto-instrumentation component for a specific framework
- **SpanConverter**: Converts OTel/OpenInference spans to TraceSteps

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can add tracing to a LangChain agent with 1 line of code
- **SC-002**: OTel ingestion supports OpenInference semantic conventions
- **SC-003**: Traces are serialized to JSON in under 100ms for typical runs (<1000 steps)
- **SC-004**: System handles traces with 10,000+ steps without memory errors
- **SC-005**: All step types include timestamp with millisecond precision
- **SC-006**: Token usage is captured for 95%+ of LLM calls when available from provider

## Next Steps

Run `/speckit.plan` to generate:
- `plan.md` - Technical implementation plan
- `research.md` - Technology decisions and rationale
- `data-model.md` - TraceRun, TraceStep entity definitions
- `contracts/` - API specifications for Tracer, Instrumentor, SpanConverter
