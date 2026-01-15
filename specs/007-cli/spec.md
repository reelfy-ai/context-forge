# Feature Specification: CLI

**Feature Branch**: `007-cli`
**Created**: 2025-01-14
**Status**: Draft
**Priority**: P2 (Important for Full MVP)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Evaluation from Config (Priority: P1)

As an **agent developer**, I want to run evaluations with a single command, so that I can quickly validate my agent without writing code.

**Why this priority**: CLI is the primary interface for most users. Everything else is accessed through it.

**Independent Test**: Can be fully tested by running CLI with a config file and verifying output.

**Acceptance Scenarios**:

1. **Given** a YAML config and a trace file, **When** I run `contextforge run --config evals.yaml --trace trace.jsonl`, **Then** all configured graders execute and results are reported
2. **Given** a config with reporter settings, **When** run completes, **Then** output files are created in specified locations
3. **Given** invalid config syntax, **When** I run the command, **Then** I get a clear error with line number before any evaluation starts

---

### User Story 2 - Collect OTel Traces (Priority: P1)

As a **team with existing observability**, I want to collect traces via OTLP, so that I can evaluate without modifying my agent code.

**Why this priority**: Zero-code integration is a key differentiator. CLI must support it.

**Independent Test**: Can be fully tested by sending OTel spans to the collector and verifying trace file is created.

**Acceptance Scenarios**:

1. **Given** OTel/OpenInference spans being emitted, **When** I run `contextforge collect --otlp-port 4317`, **Then** traces are collected and converted to ContextForge format
2. **Given** collector is running, **When** I add `--eval evals.yaml`, **Then** evaluation runs automatically on each completed trace
3. **Given** collector mode, **When** I press Ctrl+C, **Then** it shuts down gracefully and reports summary

---

### User Story 3 - Validate Config (Priority: P2)

As an **agent developer**, I want to validate my config without running evaluation, so that I can catch errors before CI.

**Why this priority**: Fast feedback loop. Config validation is quick and prevents wasted CI time.

**Independent Test**: Can be fully tested by running validate command with valid/invalid configs.

**Acceptance Scenarios**:

1. **Given** a valid config file, **When** I run `contextforge validate --config evals.yaml`, **Then** it reports "Config valid" with exit code 0
2. **Given** an invalid config, **When** I validate, **Then** it reports specific errors with line numbers and exits non-zero
3. **Given** a config referencing missing rubric files, **When** validated, **Then** it warns about missing files

---

### User Story 4 - Replay Mode (Priority: P2)

As a **DevOps engineer**, I want to run in replay mode from CLI, so that CI executions are deterministic.

**Why this priority**: CI determinism requires replay. Must be easily activatable.

**Independent Test**: Can be fully tested by running with --replay flag and verifying no external calls.

**Acceptance Scenarios**:

1. **Given** a trace with recordings, **When** I run with `--replay`, **Then** tool calls use recorded responses
2. **Given** replay mode with signature mismatch, **When** running with `--strict`, **Then** it fails with clear error
3. **Given** recording mode, **When** I run with `--record`, **Then** tool responses are saved for future replay

---

### Edge Cases

- What happens when OTLP port is already in use?
- How are multiple trace files handled (directory input)?
- What if config references graders that aren't installed?
- How is progress displayed for long-running evaluations?
- What happens on keyboard interrupt during evaluation?

## Requirements *(mandatory)*

### Functional Requirements

**Core Commands**
- **FR-001**: CLI MUST provide `run` command for evaluation
- **FR-002**: CLI MUST provide `collect` command for OTel ingestion
- **FR-003**: CLI MUST provide `validate` command for config validation
- **FR-004**: CLI MUST provide `--help` for all commands

**Run Command**
- **FR-005**: Run MUST accept `--config` for evaluation config file
- **FR-006**: Run MUST accept `--trace` for input trace file(s)
- **FR-007**: Run MUST accept `--output` for results directory
- **FR-008**: Run MUST support `--replay` and `--record` modes
- **FR-009**: Run MUST support `--strict` for replay signature enforcement

**Collect Command**
- **FR-010**: Collect MUST accept `--otlp-port` for gRPC endpoint
- **FR-011**: Collect MUST accept `--output` for trace output directory
- **FR-012**: Collect SHOULD accept `--eval` for inline evaluation
- **FR-013**: Collect MUST support graceful shutdown on SIGINT

**Output & UX**
- **FR-014**: CLI MUST return appropriate exit codes (0=success, 1=failure, 2=error)
- **FR-015**: CLI MUST support `--quiet` for minimal output
- **FR-016**: CLI MUST support `--verbose` for debug output
- **FR-017**: Progress SHOULD be displayed for long operations

### Key Entities

- **CLI**: Main command-line interface (using Click or Typer)
- **RunCommand**: Executes evaluation from config
- **CollectCommand**: Runs OTel collector
- **ValidateCommand**: Validates config files

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can run first evaluation within 2 minutes of installation
- **SC-002**: CLI provides helpful error messages with suggested fixes
- **SC-003**: Exit codes are consistent and documented
- **SC-004**: `--help` provides complete usage information for all commands
- **SC-005**: Tab completion works in bash/zsh (if using Click/Typer)

## Next Steps

Run `/speckit.plan` to generate:
- `plan.md` - Technical implementation plan
- `contracts/` - CLI argument specifications
