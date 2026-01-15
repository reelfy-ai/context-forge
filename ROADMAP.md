# ContextForge Roadmap & Planning Guide

## Overview

**ContextForge** is an open-source evaluation framework for context-aware, agentic AI systems. It evaluates **agent trajectories** (the full sequence of events during an agent run), not just final outputs.

**Key Differentiator**: Framework-agnostic with 4 integration levels (Zero-Code → One-Line → Callback → Explicit).

---

## Current State

### Specs Created (spec.md only)

| Feature | Priority | Description | Next Step |
|---------|----------|-------------|-----------|
| 001-trace-capture | **P1** | 4 integration levels for capturing agent behavior | `/speckit.plan` |
| 002-deterministic-graders | **P1** | Budget, loop, tool schema graders | `/speckit.plan` |
| 003-llm-judges | **P2** | Ollama-first LLM evaluation | `/speckit.plan` |
| 004-eval-configuration | **P2** | YAML config for evaluation suites | `/speckit.plan` |
| 005-ci-replay | **P2** | Record/replay for deterministic CI | `/speckit.plan` |
| 006-reports | **P2** | JUnit, Markdown, JSON output formats | `/speckit.plan` |
| 007-cli | **P2** | Command-line interface (run, collect, validate) | `/speckit.plan` |

### Infrastructure Ready

- [x] GitHub Spec-Kit installed and configured
- [x] Constitution defined (`.specify/memory/constitution.md`)
- [x] All 7 feature specs created with user stories
- [x] Pure spec-kit directory structure
- [x] Complete architecture coverage

---

## MVP Scope

### P1 Features (Must Have)

**001-trace-capture** - Without trace capture, nothing else works.
- User Story 1: Auto-Instrument Framework Agent (Level 2: One-Line)
- User Story 2: Ingest Existing OpenTelemetry Traces (Level 1: Zero-Code)
- User Story 3: Callback Handler Integration (Level 3: Callback)
- User Story 4: Explicit Tracer API (Level 4: Explicit)

**002-deterministic-graders** - Core evaluation capability.
- User Story 1: Budget Enforcement
- User Story 2: Loop Detection
- User Story 3: Tool Schema Validation

### P2 Features (Important for Full MVP)

**003-llm-judges** - Subjective quality evaluation.
- User Story 1: Evaluate Trajectory Quality
- User Story 2: Reproducible LLM Evaluation
- User Story 3: Local-First Evaluation (Ollama)

**004-eval-configuration** - Team collaboration and CI.
- User Story 1: Declarative Eval Suite
- User Story 2: Multiple Output Formats
- User Story 3: Compose Grader Configurations

**005-ci-replay** - Deterministic CI execution.
- User Story 1: Record Tool Responses
- User Story 2: Replay for Deterministic CI
- User Story 3: Strict Signature Matching

**006-reports** - Output format generation.
- User Story 1: JUnit XML for CI
- User Story 2: Markdown for Humans
- User Story 3: JSON for Dashboards

**007-cli** - Command-line interface.
- User Story 1: Run Evaluation from Config
- User Story 2: Collect OTel Traces
- User Story 3: Validate Config
- User Story 4: Replay Mode

---

## Planning Order

### Phase 1: Plan P1 Features (Do First)

```bash
# 1. Plan trace capture (foundation of everything)
/speckit.plan 001-trace-capture

# 2. Plan deterministic graders (core evaluation)
/speckit.plan 002-deterministic-graders
```

**Why this order**: Graders depend on traces. Trace schema must be finalized first.

### Phase 2: Generate Tasks for P1

```bash
/speckit.tasks 001-trace-capture
/speckit.tasks 002-deterministic-graders
```

### Phase 3: Implement P1 (MVP Core)

```bash
/speckit.implement 001-trace-capture
/speckit.implement 002-deterministic-graders
```

### Phase 4: Plan & Implement P2

```bash
# Plan all P2 features
/speckit.plan 003-llm-judges
/speckit.plan 004-eval-configuration
/speckit.plan 005-ci-replay
/speckit.plan 006-reports
/speckit.plan 007-cli

# Generate tasks
/speckit.tasks 003-llm-judges
/speckit.tasks 004-eval-configuration
/speckit.tasks 005-ci-replay
/speckit.tasks 006-reports
/speckit.tasks 007-cli

# Implement
/speckit.implement 003-llm-judges
/speckit.implement 004-eval-configuration
/speckit.implement 005-ci-replay
/speckit.implement 006-reports
/speckit.implement 007-cli
```

---

## Key Architecture Decisions

### 4-Level Integration (from ARCHITECTURE.md)

```
┌─────────────────────────────────────────────────────────────────────┐
│                       AGENT FRAMEWORKS                              │
│    LangChain │ LangGraph │ CrewAI │ AutoGen │ smolagents │ Custom   │
└──────┬─────────────┬─────────────┬─────────────┬─────────────┬──────┘
       │             │             │             │             │
       ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INSTRUMENTATION LAYER                            │
│  Level 1: OTel    Level 2: Instrumentor   Level 3: Callback  Level 4│
│  (Zero-Code)      (One-Line)              (Handler)          (Tracer)│
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTEXTFORGE CORE                              │
│     Canonical Trace Spec  →  Graders  →  Reports                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Constitution Principles (Non-Negotiable)

1. **Framework Agnosticism** - Graders operate only on traces, never on framework objects
2. **Traces as First-Class** - Canonical trace is the stable contract
3. **Multi-Level Integration** - 4 levels for different use cases
4. **Spec-Driven Development** - Specs are source of truth
5. **CI-Safe by Design** - Tool record/replay is first-class
6. **Grader Quality Standards** - Deterministic, stateless, evidence-based
7. **Local-First, Ollama-First** - No mandatory cloud dependencies

---

## Technical Context (for /speckit.plan)

When running `/speckit.plan`, use this context:

```
Language/Version: Python 3.10+
Primary Dependencies: Pydantic, OpenTelemetry SDK
Storage: JSONL files (traces), JSON (recordings)
Testing: pytest
Target Platform: Linux/macOS/Windows
Performance Goals: <100ms trace serialization, <1s grader execution
Constraints: No heavy runtime dependencies in core
```

---

## Success Criteria (MVP)

- [ ] Users can add tracing to LangChain agent with 1 line of code
- [ ] Users can run basic evaluation within 5 minutes of installation
- [ ] Deterministic graders produce identical results on repeated runs
- [ ] CI evaluations complete in under 60 seconds for typical traces
- [ ] All grader results include actionable evidence

---

## Post-MVP Features (Future)

- Domain packs (creative AI, finance, support automation)
- Dashboard/visualization
- Cloud-hosted evaluation service
- More framework instrumentors (Haystack, DSPy, etc.)
- Advanced replay with fuzzy matching

---

## Quick Reference

### Spec-Kit Commands

```bash
/speckit.constitution    # View project principles
/speckit.specify        # Create new feature spec
/speckit.clarify        # Clarify ambiguous requirements
/speckit.plan           # Generate technical plan
/speckit.tasks          # Break into work items
/speckit.implement      # Execute implementation
```

### Key Files

- `.specify/memory/constitution.md` - Project principles
- `specs/*/spec.md` - Feature specifications
- `ARCHITECTURE.md` - High-level design
- `CLAUDE.md` - Development guidance

### Next Session Start

```bash
# Review current state
cat specs/README.md

# Start planning P1 features
/speckit.plan 001-trace-capture
```
