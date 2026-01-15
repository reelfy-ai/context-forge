# Feature Specification: LLM Judges

**Feature Branch**: `003-llm-judges`
**Created**: 2025-01-14
**Status**: Draft
**Priority**: P2 (Important for Full MVP)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trajectory Quality Evaluation (Priority: P1)

As an **agent developer**, I want an LLM to evaluate the quality of my agent's decision-making, so that I can assess subjective aspects that rules can't capture.

**Why this priority**: Many important qualities (reasoning quality, context usage, decision appropriateness) require semantic understanding.

**Independent Test**: Can be fully tested by running trajectory judge with Ollama against a trace and rubric.

**Acceptance Scenarios**:

1. **Given** a trace and a rubric file, **When** I run the trajectory judge with Ollama, **Then** I get a score and explanation based on the rubric criteria
2. **Given** a rubric with multiple criteria, **When** judge evaluates, **Then** I get individual scores for each criterion plus an overall score
3. **Given** a poor quality trace, **When** judged, **Then** the explanation identifies specific steps where quality was lacking

---

### User Story 2 - Reproducibility Metadata (Priority: P1)

As a **quality engineer**, I want complete metadata about LLM judge evaluations, so that I can understand and reproduce judge decisions.

**Why this priority**: LLM outputs vary. Without metadata, judge results are black boxes.

**Independent Test**: Can be fully tested by running judge twice and comparing stored metadata.

**Acceptance Scenarios**:

1. **Given** a judge evaluation, **When** I examine the result, **Then** I can see the exact prompt sent to the LLM
2. **Given** a judge result, **When** I examine metadata, **Then** I can see: model ID, temperature, raw LLM response, parsed score
3. **Given** two runs of the same judge on the same trace, **When** I compare results, **Then** I have all metadata needed to understand any score differences

---

### User Story 3 - Local-First Execution (Priority: P2)

As a **developer with privacy requirements**, I want to run LLM judges locally, so that I don't send sensitive trace data to cloud providers.

**Why this priority**: Many organizations can't send data externally. Ollama support enables local evaluation.

**Independent Test**: Can be fully tested by running judge with Ollama backend and verifying no external network calls.

**Acceptance Scenarios**:

1. **Given** Ollama is installed locally, **When** I configure trajectory judge with `backend: ollama`, **Then** evaluation runs entirely locally
2. **Given** a local model, **When** judge runs, **Then** no data is sent to external APIs
3. **Given** Ollama isn't available, **When** I configure cloud backend, **Then** I can use OpenAI-compatible APIs as fallback

---

### Edge Cases

- What happens when the LLM judge times out?
- How are malformed LLM responses (can't parse score) handled?
- What happens when the rubric references criteria the trace can't satisfy?
- How are very long traces handled (exceed context window)?
- What if Ollama model isn't downloaded yet?

## Requirements *(mandatory)*

### Functional Requirements

**Judge Interface**
- **FR-001**: LLM judges MUST implement the same Grader interface as deterministic graders
- **FR-002**: Judges MUST be explicitly marked as non-deterministic
- **FR-003**: Judges MUST support configurable backends (Ollama, OpenAI-compatible)

**Rubric System**
- **FR-004**: Judges MUST accept rubrics as markdown files
- **FR-005**: Rubrics MUST support multiple evaluation criteria with weights
- **FR-006**: Rubrics SHOULD support scoring scales (1-5, 1-10, pass/fail)

**Reproducibility**
- **FR-007**: Judge results MUST include the exact prompt sent to the LLM
- **FR-008**: Judge results MUST include the raw LLM response
- **FR-009**: Judge results MUST include model ID, temperature, and other parameters
- **FR-010**: Judge results MUST include rubric version (hash or identifier)

**Backend Support**
- **FR-011**: System MUST support Ollama as primary/default backend
- **FR-012**: System SHOULD support OpenAI-compatible APIs
- **FR-013**: Backend configuration MUST be declarative (in eval config)

### Key Entities

- **TrajectoryJudge**: LLM-based grader that evaluates trace quality
- **Rubric**: Markdown document defining evaluation criteria
- **JudgeResult**: Extended GraderResult with LLM-specific metadata
- **JudgeBackend**: Abstraction for LLM providers (Ollama, OpenAI)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: LLM judge results include 100% of required reproducibility metadata
- **SC-002**: Ollama-based evaluation works offline (no network calls)
- **SC-003**: Judge handles traces up to 50k tokens (with summarization if needed)
- **SC-004**: Rubric parsing errors are caught before evaluation starts
- **SC-005**: Judge timeout is configurable with sensible default (60s)

## Technical Specs

LLM judge technical specifications will be created during `/speckit.plan`:
- Judge interface extension
- Rubric format specification
- Backend abstraction layer
- Prompt templates
