# ContextForge Examples

This directory contains runnable examples to help you get started with ContextForge.

## Directory Structure

```
examples/
├── basic/              # Getting started examples
│   ├── 01_simple_trace.py
│   ├── 02_tool_calls.py
│   └── 03_multi_agent.py
├── graders/            # Grader usage examples
│   ├── budget_grader.py
│   └── custom_grader.py
└── scenarios/          # Task and scenario examples
    ├── tasks/
    │   └── refund_request.yaml
    ├── scenarios/
    │   └── refund_eligible.yaml
    └── datasets/
        └── refund_samples.jsonl
```

## Quick Start

### 1. Basic Tracing

```bash
python examples/basic/01_simple_trace.py
```

### 2. Tool Call Tracing

```bash
python examples/basic/02_tool_calls.py
```

### 3. Running Graders

```bash
python examples/graders/budget_grader.py
```

## Prerequisites

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (when available)
pip install -e .
```

## Example Output

Each example prints its output to stdout. For example:

```
=== Simple Trace Example ===
Trace ID: abc123-...
Steps: 3
Outcome: success
```

## Next Steps

After running these examples:
1. Read the [QUICKSTART.md](../QUICKSTART.md) guide
2. Explore the [specs/](../specs/) for detailed contracts
3. Check [ARCHITECTURE.md](../ARCHITECTURE.md) for the big picture
