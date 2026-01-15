# Feature Specification: CI Replay

**Feature Branch**: `005-ci-replay`
**Created**: 2025-01-14
**Status**: Draft
**Priority**: P2 (Important for Full MVP)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record Tool Responses (Priority: P1)

As a **test engineer**, I want to record real tool responses during a test run, so that I can replay them later for deterministic CI.

**Why this priority**: CI requires determinism. Recording real responses enables offline replay.

**Independent Test**: Can be fully tested by running in record mode and verifying responses are stored.

**Acceptance Scenarios**:

1. **Given** an agent run in record mode, **When** tools are called, **Then** request/response pairs are stored alongside the trace
2. **Given** a recorded session, **When** I examine the recording, **Then** I can see tool name, arguments, response, and timing for each call
3. **Given** multiple tool calls, **When** recorded, **Then** they're stored in order with correlation to trace steps

---

### User Story 2 - Replay for Deterministic CI (Priority: P1)

As a **DevOps engineer**, I want to run evaluations in CI with deterministic results, so that I can catch regressions reliably.

**Why this priority**: Flaky tests are worse than no tests. Replay ensures consistency.

**Independent Test**: Can be fully tested by running same scenario twice in replay mode and comparing results.

**Acceptance Scenarios**:

1. **Given** a recorded trace with tool responses, **When** I run in replay mode, **Then** tool calls return the recorded responses instead of calling real tools
2. **Given** replay mode, **When** evaluation runs, **Then** no external API calls are made
3. **Given** the same trace and recording, **When** I run replay 10 times, **Then** I get identical results each time

---

### User Story 3 - Strict Signature Matching (Priority: P2)

As a **quality engineer**, I want strict mode to fail when tool signatures change, so that I can detect when my agent's behavior has drifted.

**Why this priority**: Catching signature drift early prevents silent failures in production.

**Independent Test**: Can be fully tested by modifying tool args and verifying strict mode fails.

**Acceptance Scenarios**:

1. **Given** replay in strict mode, **When** a tool call signature doesn't match recording, **Then** it fails with a clear error showing the mismatch
2. **Given** a signature mismatch, **When** I examine the error, **Then** I can see expected vs actual: tool name, arguments, order
3. **Given** lenient mode, **When** minor non-semantic differences exist, **Then** replay still succeeds (future feature)

---

### Edge Cases

- What happens when replay encounters a tool call not in the recording?
- How are non-deterministic tool responses handled (timestamps, random IDs)?
- What if recorded response format changes between versions?
- How are parallel tool calls matched to recordings?
- What happens when tool order changes but calls are the same?

## Requirements *(mandatory)*

### Functional Requirements

**Recording**
- **FR-001**: System MUST support recording tool call request/response pairs
- **FR-002**: Recordings MUST be stored in a portable format (JSON/JSONL)
- **FR-003**: Recordings MUST include: tool name, arguments, response, timestamp, latency
- **FR-004**: Recordings MUST be associated with specific trace runs

**Replay**
- **FR-005**: System MUST support replay mode that returns recorded responses
- **FR-006**: Replay MUST NOT make external API/tool calls
- **FR-007**: Replay MUST match tool calls by name and canonicalized arguments
- **FR-008**: Replay MUST support strict mode (fail on any mismatch)

**Canonicalization**
- **FR-009**: Tool arguments MUST be canonicalized for matching (sorted keys, normalized values)
- **FR-010**: Canonicalization MUST handle JSON-serializable arguments
- **FR-011**: Secrets/credentials MUST be redacted in recordings

**CI Integration**
- **FR-012**: Replay mode MUST be activatable via CLI flag or environment variable
- **FR-013**: Strict mode failures MUST produce clear, actionable error messages
- **FR-014**: Recordings MUST be committable to version control

### Key Entities

- **ToolRecording**: Stored request/response pair for a tool call
- **RecordingStore**: Storage backend for recordings (file-based)
- **ReplayMatcher**: Matches incoming tool calls to recordings
- **CanonicalArgs**: Normalized representation of tool arguments

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Replay produces 100% identical results for same trace + recording
- **SC-002**: Strict mode catches 100% of signature mismatches
- **SC-003**: Recordings add <10% storage overhead compared to traces
- **SC-004**: Replay mode runs at least as fast as original execution
- **SC-005**: Recording format is stable across minor version upgrades

## Next Steps

Run `/speckit.plan` to generate:
- `plan.md` - Technical implementation plan
- `data-model.md` - ToolRecording, RecordingStore, CanonicalArgs definitions
- `contracts/` - Recording format specification
