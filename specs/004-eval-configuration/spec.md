# Feature Specification: Evaluation Configuration

**Feature Branch**: `004-eval-configuration`
**Created**: 2025-01-14
**Status**: Draft
**Priority**: P2 (Important for Full MVP)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declarative Eval Suites (Priority: P1)

As an **agent developer**, I want to define my evaluation rules in a YAML file, so that I can version control them and share with my team.

**Why this priority**: Config files enable reproducibility, collaboration, and CI integration.

**Independent Test**: Can be fully tested by creating a YAML config and running the CLI against a trace.

**Acceptance Scenarios**:

1. **Given** a YAML config with multiple graders, **When** I run `contextforge run --config evals.yaml`, **Then** all configured graders execute in order
2. **Given** a config file in my repository, **When** a team member clones and runs it, **Then** they get the same evaluation behavior
3. **Given** a grader with parameters, **When** I specify `max_tokens: 5000` in config, **Then** that parameter is used instead of default

---

### User Story 2 - Multiple Output Formats (Priority: P1)

As a **DevOps engineer**, I want evaluation results in multiple formats, so that I can integrate with different systems.

**Why this priority**: CI systems need JUnit XML, humans need Markdown, dashboards need JSON.

**Independent Test**: Can be fully tested by running with reporter config and verifying output files.

**Acceptance Scenarios**:

1. **Given** config with `reporters: [junit, markdown]`, **When** evaluation completes, **Then** I get both `results.xml` and `results.md` files
2. **Given** JUnit reporter, **When** a grader fails, **Then** the XML contains a proper test failure that CI systems can parse
3. **Given** JSON reporter, **When** evaluation completes, **Then** output includes all scores, evidence, and metadata in structured format

---

### User Story 3 - Grader Composition (Priority: P2)

As a **quality engineer**, I want to compose multiple graders into a suite, so that I can run comprehensive evaluations with a single command.

**Why this priority**: Real evaluations need multiple checks. Composition reduces repetition.

**Independent Test**: Can be fully tested by creating a config with 5+ graders and verifying all run.

**Acceptance Scenarios**:

1. **Given** a suite with budget, loop, and tool schema graders, **When** I run the suite, **Then** all graders execute and results are aggregated
2. **Given** one grader fails, **When** suite completes, **Then** other graders still run and I see all results
3. **Given** a grader requires capabilities the trace lacks, **When** running, **Then** that grader is skipped with a warning (not error)

---

### Edge Cases

- What happens when config YAML has syntax errors?
- How are grader conflicts handled (same grader configured twice)?
- What if a referenced rubric file doesn't exist?
- How are relative paths resolved in config files?
- What happens when output directory doesn't exist?

## Requirements *(mandatory)*

### Functional Requirements

**Config Format**
- **FR-001**: System MUST support YAML configuration files
- **FR-002**: Config MUST support suite-level metadata (name, description)
- **FR-003**: Config MUST support grader list with per-grader parameters
- **FR-004**: Config MUST support reporter configuration

**Grader Configuration**
- **FR-005**: Each grader MUST be configurable by name
- **FR-006**: Graders MUST accept parameters as key-value pairs
- **FR-007**: Graders SHOULD have sensible defaults for all parameters
- **FR-008**: Unknown grader names MUST produce clear errors

**Reporter Configuration**
- **FR-009**: System MUST support JUnit XML reporter (CI integration)
- **FR-010**: System MUST support Markdown reporter (human readable)
- **FR-011**: System MUST support JSON reporter (structured data)
- **FR-012**: Reporter output paths MUST be configurable

**Validation**
- **FR-013**: Config files MUST be validated before execution
- **FR-014**: Validation errors MUST include line numbers and clear messages
- **FR-015**: Referenced files (rubrics, schemas) MUST be checked for existence

### Key Entities

- **EvalConfig**: Root configuration object
- **GraderConfig**: Configuration for a single grader
- **ReporterConfig**: Configuration for output format
- **ConfigLoader**: YAML parser and validator

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Config validation catches 100% of syntax and schema errors before execution
- **SC-002**: Same config file produces identical results across different machines
- **SC-003**: CLI can load and run config in under 2 seconds (excluding grader execution)
- **SC-004**: JUnit XML output is valid according to JUnit schema
- **SC-005**: Config supports all grader parameters documented in grader specs

## Next Steps

Run `/speckit.plan` to generate:
- `plan.md` - Technical implementation plan
- `data-model.md` - EvalConfig, GraderConfig, ReporterConfig definitions
- `contracts/` - YAML configuration schema
