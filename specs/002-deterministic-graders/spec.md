# Feature Specification: Deterministic Graders

**Feature Branch**: `002-deterministic-graders`
**Created**: 2025-01-14
**Status**: Draft
**Priority**: P1 (Must Have for MVP)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Budget Enforcement (Priority: P1)

As an **agent developer**, I want to check if my agent stayed within resource limits, so that I can prevent runaway costs and ensure efficiency.

**Why this priority**: Budget overruns are the most common and costly agent failure mode.

**Independent Test**: Can be fully tested by running budget grader against a trace with known token counts.

**Acceptance Scenarios**:

1. **Given** a trace with token usage data, **When** I run the budget grader with `max_tokens=5000`, **Then** I get a pass/fail result with evidence showing actual vs limit
2. **Given** a trace exceeding the tool call limit, **When** I run budget grader with `max_tool_calls=10`, **Then** it fails and reports which calls exceeded the limit
3. **Given** a passing trace, **When** I examine the result, **Then** I can see utilization percentage (e.g., "used 3000/5000 tokens = 60%")

---

### User Story 2 - Loop Detection (Priority: P1)

As an **agent developer**, I want to detect when my agent is thrashing or stuck in loops, so that I can identify degenerate behavior patterns.

**Why this priority**: Loops waste resources and indicate agent confusion. Early detection prevents cascading failures.

**Independent Test**: Can be fully tested by running loop grader against a trace with repeated similar steps.

**Acceptance Scenarios**:

1. **Given** a trace with repeated similar LLM calls, **When** I run the loop grader with `max_repeats=3`, **Then** it identifies the thrashing pattern and reports which steps are repetitive
2. **Given** a trace with legitimate retries (different parameters), **When** analyzed, **Then** it correctly distinguishes retries from loops
3. **Given** a detected loop, **When** I examine evidence, **Then** I can see the step IDs involved and similarity scores

---

### User Story 3 - Tool Schema Validation (Priority: P2)

As an **agent developer**, I want to verify my agent only uses approved tools with valid arguments, so that I can ensure security and correctness.

**Why this priority**: Unauthorized tool usage is a security risk. Schema validation catches bugs early.

**Independent Test**: Can be fully tested by running tool schema grader against a trace with known tool calls.

**Acceptance Scenarios**:

1. **Given** a trace with tool calls, **When** I run tool schema grader with an allowlist `["search", "db_query"]`, **Then** it reports any tools used that weren't in the allowlist
2. **Given** a tool call with invalid arguments, **When** validated against a JSON schema, **Then** it reports the specific validation errors
3. **Given** all tools are valid, **When** grader runs, **Then** it passes with evidence showing each tool was checked

---

### Edge Cases

- What happens when a trace has no tool calls but tool schema grader is configured?
- How are partial token counts handled (some LLM calls missing usage data)?
- What constitutes "similar enough" for loop detection?
- How are nested tool calls (tool calling another tool) validated?

## Requirements *(mandatory)*

### Functional Requirements

**Grader Interface**
- **FR-001**: All graders MUST implement a common Grader interface
- **FR-002**: All graders MUST return structured GraderResult with pass/fail, score, and evidence
- **FR-003**: Graders MUST declare required step types and trace capabilities
- **FR-004**: Graders MUST be deterministic (same trace → same result)
- **FR-005**: Graders MUST be stateless and side-effect free

**Evidence Requirements**
- **FR-006**: Every grader result MUST include evidence pointers (step_ids referenced)
- **FR-007**: Evidence MUST include human-readable descriptions of what was checked
- **FR-008**: Evidence MUST include thresholds/limits that were applied
- **FR-009**: Failed results MUST explain why they failed with specific data

**Budget Grader**
- **FR-010**: Budget grader MUST support token limits (input, output, total)
- **FR-011**: Budget grader MUST support tool call count limits
- **FR-012**: Budget grader SHOULD support time/latency limits

**Loop Grader**
- **FR-013**: Loop grader MUST detect repeated similar steps
- **FR-014**: Loop grader MUST be configurable for similarity threshold
- **FR-015**: Loop grader MUST report which steps form the loop

**Tool Schema Grader**
- **FR-016**: Tool schema grader MUST support tool allowlist/blocklist
- **FR-017**: Tool schema grader SHOULD support JSON schema validation for tool arguments

### Key Entities

- **Grader**: Base class for all evaluation components
- **GraderResult**: Structured output with pass/fail, score, evidence
- **Evidence**: Detailed proof of what was evaluated and why
- **GraderRequirements**: Declaration of what a grader needs from a trace

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Deterministic graders produce identical results on repeated runs (100% reproducibility)
- **SC-002**: Grader execution completes in under 1 second for typical traces (<1000 steps)
- **SC-003**: All grader results include actionable evidence (step IDs, excerpts, thresholds)
- **SC-004**: Budget grader correctly identifies 100% of limit violations
- **SC-005**: Loop grader has <5% false positive rate on legitimate retry patterns

## Next Steps

Run `/speckit.plan` to generate:
- `plan.md` - Technical implementation plan
- `data-model.md` - Grader, GraderResult, Evidence entity definitions
- `contracts/` - API specifications for grader interface
