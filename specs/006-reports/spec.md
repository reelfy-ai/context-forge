# Feature Specification: Reports

**Feature Branch**: `006-reports`
**Created**: 2025-01-14
**Status**: Draft
**Priority**: P2 (Important for Full MVP)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - JUnit XML for CI (Priority: P1)

As a **DevOps engineer**, I want evaluation results in JUnit XML format, so that my CI system can display pass/fail status and track trends.

**Why this priority**: JUnit XML is the universal CI format. Without it, CI integration is manual.

**Independent Test**: Can be fully tested by running evaluation and validating output against JUnit XSD schema.

**Acceptance Scenarios**:

1. **Given** a completed evaluation with 5 graders, **When** JUnit reporter runs, **Then** output contains one `<testsuite>` with 5 `<testcase>` elements
2. **Given** a grader that failed, **When** JUnit report is generated, **Then** the testcase includes a `<failure>` element with the grader's evidence
3. **Given** JUnit XML output, **When** imported into Jenkins/GitHub Actions/GitLab CI, **Then** it displays correctly without errors

---

### User Story 2 - Markdown for Humans (Priority: P1)

As an **agent developer**, I want a readable summary of evaluation results, so that I can quickly understand what passed and failed.

**Why this priority**: Developers need to read results. Markdown renders nicely in terminals, PRs, and docs.

**Independent Test**: Can be fully tested by generating report and verifying sections are present.

**Acceptance Scenarios**:

1. **Given** evaluation results, **When** Markdown reporter runs, **Then** output includes summary table with pass/fail counts
2. **Given** a failed grader with evidence, **When** report is generated, **Then** evidence is displayed in a readable format with step references
3. **Given** multiple graders, **When** report is generated, **Then** each grader has its own section with score and details

---

### User Story 3 - JSON for Dashboards (Priority: P2)

As a **platform engineer**, I want structured JSON output, so that I can build dashboards and aggregate results across runs.

**Why this priority**: Programmatic access enables automation but isn't required for basic usage.

**Independent Test**: Can be fully tested by validating JSON output against schema.

**Acceptance Scenarios**:

1. **Given** evaluation results, **When** JSON reporter runs, **Then** output is valid JSON with all grader results
2. **Given** JSON output, **When** parsed programmatically, **Then** I can extract scores, evidence, and metadata for any grader
3. **Given** multiple evaluation runs, **When** JSON outputs are collected, **Then** they can be aggregated for trend analysis

---

### Edge Cases

- What happens when a grader returns no evidence?
- How are very long evidence strings handled (truncation)?
- What if output directory doesn't exist?
- How are special characters in evidence escaped for each format?
- What happens when evaluation is interrupted mid-run?

## Requirements *(mandatory)*

### Functional Requirements

**Reporter Interface**
- **FR-001**: All reporters MUST implement a common Reporter interface
- **FR-002**: Reporters MUST accept a list of GraderResult objects
- **FR-003**: Reporters MUST support configurable output paths
- **FR-004**: Reporters MUST handle empty results gracefully

**JUnit Reporter**
- **FR-005**: JUnit reporter MUST produce valid JUnit XML (XSD compliant)
- **FR-006**: Each grader result MUST map to one `<testcase>`
- **FR-007**: Failed graders MUST include `<failure>` with evidence message
- **FR-008**: Reporter MUST include timing information when available

**Markdown Reporter**
- **FR-009**: Markdown reporter MUST include summary section with totals
- **FR-010**: Markdown reporter MUST include per-grader sections
- **FR-011**: Evidence MUST be formatted for readability (code blocks, lists)
- **FR-012**: Reporter SHOULD support configurable detail level (summary/full)

**JSON Reporter**
- **FR-013**: JSON reporter MUST produce valid JSON
- **FR-014**: Output MUST include all GraderResult fields
- **FR-015**: Output MUST include run metadata (timestamp, trace info)
- **FR-016**: Output SHOULD follow a documented schema

### Key Entities

- **Reporter**: Base interface for all output formatters
- **JUnitReporter**: Produces JUnit XML
- **MarkdownReporter**: Produces human-readable Markdown
- **JSONReporter**: Produces structured JSON
- **ReportConfig**: Configuration for reporter behavior

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: JUnit XML validates against standard JUnit XSD schema
- **SC-002**: JUnit reports display correctly in GitHub Actions, Jenkins, GitLab CI
- **SC-003**: Markdown reports are readable without scrolling for typical evaluations (<10 graders)
- **SC-004**: JSON output can be parsed by standard JSON libraries without errors
- **SC-005**: Report generation adds <100ms to total evaluation time

## Next Steps

Run `/speckit.plan` to generate:
- `plan.md` - Technical implementation plan
- `data-model.md` - Reporter interface definitions
- `contracts/` - Output format schemas (JUnit XSD, JSON Schema)
