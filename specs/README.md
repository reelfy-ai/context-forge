# ContextForge Specifications

This directory contains the formal specifications for ContextForge, following **GitHub Spec-Kit** for spec-driven development.

## Spec-Kit Workflow

```
/speckit.specify → /speckit.clarify → /speckit.plan → /speckit.tasks → /speckit.implement
     (WHAT)          (Questions)          (HOW)          (WORK)           (CODE)
```

| Command | Purpose | Output |
|---------|---------|--------|
| `/speckit.constitution` | View project principles | - |
| `/speckit.specify` | Create user-focused feature spec | `spec.md` |
| `/speckit.clarify` | Ask questions to de-risk ambiguity | Updates `spec.md` |
| `/speckit.plan` | Create technical implementation plan | `plan.md`, `research.md`, `data-model.md`, `contracts/` |
| `/speckit.tasks` | Generate actionable task breakdown | `tasks.md` |
| `/speckit.implement` | Execute implementation | Code |

## Directory Structure

Each feature follows the spec-kit standard:

```
specs/
├── README.md
├── SPEC_TEMPLATE.md
│
├── 001-trace-capture/              # P1: "Trace My Agent"
│   ├── spec.md                     # User stories, requirements (created)
│   ├── plan.md                     # Technical plan (after /speckit.plan)
│   ├── research.md                 # Research decisions (after /speckit.plan)
│   ├── data-model.md               # Entity definitions (after /speckit.plan)
│   ├── contracts/                  # API specs (after /speckit.plan)
│   └── tasks.md                    # Task breakdown (after /speckit.tasks)
│
├── 002-deterministic-graders/      # P1: "Evaluate with Graders"
│   └── spec.md
│
├── 003-llm-judges/                 # P2: "LLM Evaluation"
│   └── spec.md
│
├── 004-eval-configuration/         # P2: "Configure Suites"
│   └── spec.md
│
├── 005-ci-replay/                  # P2: "CI Integration"
│   └── spec.md
│
├── 006-reports/                    # P2: "Output Formats"
│   └── spec.md
│
└── 007-cli/                        # P2: "Command-Line Interface"
    └── spec.md
```

## Feature Priorities

| Feature | Priority | Description | Status |
|---------|----------|-------------|--------|
| 001-trace-capture | **P1** | Capture agent behavior (4 integration levels) | spec.md ✓ |
| 002-deterministic-graders | **P1** | Rule-based evaluation (budget, loops, tool schema) | spec.md ✓ |
| 003-llm-judges | **P2** | LLM-based quality evaluation (Ollama-first) | spec.md ✓ |
| 004-eval-configuration | **P2** | YAML config for evaluation suites | spec.md ✓ |
| 005-ci-replay | **P2** | Record/replay for deterministic CI | spec.md ✓ |
| 006-reports | **P2** | JUnit XML, Markdown, JSON output formats | spec.md ✓ |
| 007-cli | **P2** | Command-line interface (run, collect, validate) | spec.md ✓ |

**P1** = Must have for MVP
**P2** = Important for full MVP

## Getting Started

### For Users

1. **[QUICKSTART.md](../QUICKSTART.md)** - 5-minute getting started guide
2. **[examples/](../examples/)** - Runnable code examples

### For Contributors

1. Read the constitution: `/speckit.constitution`
2. Pick a feature spec to work on
3. Run `/speckit.plan` to generate implementation artifacts
4. Run `/speckit.tasks` to break down into work items
5. Run `/speckit.implement` to code

## Creating New Features

```bash
# Start a new feature
/speckit.specify [description of what you want to build]

# Clarify any ambiguous requirements
/speckit.clarify

# Create technical implementation plan
/speckit.plan

# Break into tasks
/speckit.tasks

# Implement
/speckit.implement
```

## References

- [ARCHITECTURE.md](../ARCHITECTURE.md) - High-level design overview
- [SPEC_GUIDELINES.md](../SPEC_GUIDELINES.md) - Design principles and policies
