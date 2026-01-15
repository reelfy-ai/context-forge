# ContextForge

**Open-source evaluation framework for context-aware, agentic AI systems**

ContextForge is an open-source framework for evaluating **agent behavior and context engineering** in modern AI systems.

> We don't just evaluate outputs.
> We evaluate **how context is built, used, and evolves across agent trajectories**.

ContextForge is designed to be:
- **Framework-agnostic** — works with LangChain, CrewAI, AutoGen, or custom agents
- **Local-first** — run evaluations on your machine with local LLM judges (Ollama)
- **CI-safe** — deterministic replay for reliable regression testing
- **Extensible** — add custom graders, rubrics, and domain-specific evaluation packs

---

## Key Concepts

Before diving in, here are the core ideas behind ContextForge:

### Trajectory
A **trajectory** is the complete sequence of events during an agent run: every LLM call, tool invocation, memory read/write, retrieval step, and state change. Unlike single-turn evaluation, trajectory evaluation captures *how* an agent arrives at its answer — not just *what* it outputs.

### Context Engineering
**Context engineering** is the practice of designing how information flows into and through an agent. It consists of [six interconnected pillars](https://weaviate.io/blog/context-engineering):

| Pillar | What It Does | What Can Go Wrong |
|--------|--------------|-------------------|
| **Agents** | Orchestrate decisions and task execution | Poor planning, stuck in loops, wrong tool selection |
| **Query Augmentation** | Refine user input for downstream tasks | Queries that miss intent, over-broad or too narrow |
| **Retrieval** | Surface relevant information (RAG) | Wrong chunks, irrelevant results, missing context |
| **Prompting** | Guide how the model uses context | Hallucination, ignoring retrieved data, format errors |
| **Memory** | Preserve context across interactions | Stale data resurfacing, memory bloat, lost history |
| **Tools** | Enable real-world actions | Incorrect args, unnecessary calls, missing error handling |

ContextForge's graders are designed to evaluate each of these pillars — detecting when agents make poor decisions, when retrieval returns irrelevant results, when memory becomes polluted, or when tools are misused.

### Graders
**Graders** are the evaluation components that analyze traces and produce scores, pass/fail verdicts, and evidence. Each grader targets specific context engineering pillars:

| Grader | Type | Pillars Evaluated |
|--------|------|-------------------|
| *BudgetGrader* | Deterministic | Agents, Tools — enforce token/tool/time limits |
| *LoopGrader* | Deterministic | Agents — detect repeated actions or state cycles |
| *SchemaGrader* | Deterministic | Tools, Prompting — validate tool args and output format |
| *MemoryHygieneGrader* | Deterministic | Memory — detect stale or duplicate data resurfacing |
| *RetrievalRelevanceGrader* | Deterministic | Retrieval — measure if retrieved chunks were actually used |
| *ContextWindowGrader* | Deterministic | Retrieval, Memory — detect bloated or irrelevant context |
| *TrajectoryJudge* | LLM-as-judge | All pillars — qualitative assessment of reasoning, planning, and context usage |

**Deterministic graders** provide fast, reproducible checks with predictable outcomes.
**LLM-as-judge graders** use a local LLM (Ollama-first) for qualitative evaluation that's harder to express as rules.

Graders are **composable** — combine them into evaluation suites that match your quality bar.

---

## Why ContextForge Exists

Most AI evaluation tools were built for:
- single-turn prompts
- static RAG pipelines
- isolated model outputs

But **agentic systems fail in different ways**:
- bloated or polluted context windows
- irrelevant memory resurfacing
- poor query augmentation
- unnecessary or incorrect tool usage
- contradictory context fragments
- silent degradation across multi-step reasoning

These are *context and system failures*, not just model failures.

ContextForge exists to make those failures **observable, testable, and comparable**.

---

## Example: Catching a Loop

Your support agent handles refund requests. During testing, you notice it sometimes takes 30+ seconds to respond. Why?

```
# ContextForge evaluation output

LoopGrader: FAIL
  - Agent called `check_order_status` 6 times with identical arguments
  - Steps 4, 7, 12, 15, 19, 23 are duplicates
  - Evidence: step_id=4 args={"order_id": "12345"}

BudgetGrader: FAIL
  - Token usage: 8,432 (limit: 5,000)
  - Tool calls: 14 (limit: 10)

Recommendation: Agent is stuck in a retry loop. Check tool error handling.
```

Without trajectory evaluation, you'd only see "agent responded correctly" — missing the inefficiency entirely.

---

## What You'll Learn

After running ContextForge on your agent, you'll be able to answer:

- **Efficiency**: Is my agent wasting tokens or making redundant tool calls?
- **Correctness**: Are tool arguments valid? Is the output schema correct?
- **Context quality**: Is retrieved information actually being used? Is memory being managed well?
- **Reliability**: Does my agent behave consistently across runs?
- **Regression safety**: Did my last change break something that used to work?

---

## What Makes ContextForge Different

| Capability | ContextForge |
|----------|--------------|
| Output-only scoring | No |
| Trajectory-based evaluation | Yes |
| Context engineering evals | Yes |
| Memory hygiene detection | Yes |
| Tool orchestration evals | Yes |
| Deterministic replay (CI) | Yes |
| Local LLM judges (Ollama) | Yes |
| Framework-agnostic graders | Yes |

---

## Framework-Agnostic by Design

ContextForge separates concerns explicitly:

- **Adapters** translate framework-specific events into traces
- **Traces** are the stable, canonical contract
- **Graders** operate only on traces — never on framework objects

This means:
- LangGraph, LangChain, AutoGen, CrewAI, smolagents, or custom agents can all use the same graders
- New frameworks can integrate without changing grader logic
- Evaluations remain stable even as runtimes evolve

If your system can emit events, ContextForge can evaluate it.

---

## Integration Levels

ContextForge offers multiple ways to capture agent behavior, from zero-code to explicit control.

### Level 1: Zero-Code (via OpenTelemetry)
If you already use OpenInference or OpenTelemetry for LLM observability, ContextForge can ingest those traces directly.

```bash
# Collect traces from existing OpenTelemetry pipeline
contextforge collect --otlp-port 4317 --eval evals.yaml
```

---

### Level 2: One-Line Instrumentation
Add auto-instrumentation to existing frameworks (LangChain, CrewAI, etc.) with one line.

```python
from contextforge.instrumentation import LangChainInstrumentor

LangChainInstrumentor().instrument()

# Your existing LangChain code works unchanged - all calls are traced
from langchain_openai import ChatOpenAI
llm = ChatOpenAI()
response = llm.invoke("Hello!")  # Automatically traced
```

Or via environment variable (no code changes):
```bash
CONTEXTFORGE_INSTRUMENT_LANGCHAIN=true python my_agent.py
```

---

### Level 3: Callback Handler
For frameworks with callback systems, pass the ContextForge handler.

```python
from contextforge.callbacks import ContextForgeHandler

handler = ContextForgeHandler()
chain.invoke(input, config={"callbacks": [handler]})
```

---

### Level 4: Explicit Tracer API
For custom agents or when you need full control, use the Tracer API.

```python
from context_forge import Tracer

with Tracer.run(task="refund_request") as t:
    t.user_input("I want a refund")

    out = llm.generate(prompt)
    t.llm_call(model="gpt-4", output=out)

    result = db_query(...)
    t.tool_call("db_query", args, result)

    t.final_output(out)
```

---

## Evaluation Configuration

Users define **what to evaluate**, not how data is stored.

```yaml
suite: checkout_agent
graders:
  - budget:
      max_tokens: 5000
      max_tool_calls: 10
  - loops:
      max_repeats: 3
  - tool_schema:
      allowlist: ["search", "db_query", "email_send"]
  - trajectory_judge:
      backend: ollama
      model: llama3.1
      rubric: rubrics/context_quality.md
```

---

## CI and Regression Testing

ContextForge supports:
- tool call recording and replay
- deterministic evaluation runs
- regression diffs between versions
- JUnit / Markdown / JSON reports

This makes agent evaluation **part of normal software delivery**, not an afterthought.

---

## Project Structure

```
context_forge/
  core/              # trace spec, contracts
  instrumentation/   # adapters & tracer
  harness/           # tasks, scenarios, replay
  graders/           # deterministic + judge-based
  domains/           # industry-specific eval packs
  reports/           # CI & dashboards
  cli/               # contextforge CLI
```

---

## Domain Packs

ContextForge supports **domain packs** that add:
- custom graders
- rubrics
- task templates

Examples:
- Context engineering (reference domain)
- Creative AI (Reelfy)
- Finance & compliance
- Support automation

Domain packs extend ContextForge without bloating the core.

---

## Project Status

🚧 **Early-stage, design-first**

The current focus is on:
- stable trace specification
- tracer and adapter APIs
- deterministic graders
- CI-safe replay

APIs are evolving, but contracts are being designed deliberately.

---

## Getting Started

**New to ContextForge?** See the **[QUICKSTART.md](QUICKSTART.md)** guide and check out the **[examples/](examples/)** directory.

---

## Specifications

ContextForge follows **Spec-Driven Development** with [GitHub Spec-Kit](https://github.com/github/spec-kit). Formal specifications define contracts before implementation.

### Feature Specs

| Feature | Priority | Description |
|---------|----------|-------------|
| [001-trace-capture](specs/001-trace-capture/spec.md) | P1 | Capture agent behavior (instrumentation, OTel, Tracer API) |
| [002-deterministic-graders](specs/002-deterministic-graders/spec.md) | P1 | Rule-based evaluation (budget, loops, tool schema) |
| [003-llm-judges](specs/003-llm-judges/spec.md) | P2 | LLM-based quality evaluation (Ollama-first) |
| [004-eval-configuration](specs/004-eval-configuration/spec.md) | P2 | YAML config for evaluation suites |
| [005-ci-replay](specs/005-ci-replay/spec.md) | P2 | Record/replay for deterministic CI |
| [006-reports](specs/006-reports/spec.md) | P2 | JUnit XML, Markdown, JSON output formats |
| [007-cli](specs/007-cli/spec.md) | P2 | Command-line interface (run, collect, validate) |

Each feature directory contains:
- `spec.md` — User stories, requirements, success criteria
- After `/speckit.plan`: `plan.md`, `research.md`, `data-model.md`, `contracts/`

See [specs/README.md](specs/README.md) for the full spec process and directory structure.

---

## License

ContextForge is licensed under the **Apache License 2.0**.

This enables:
- free commercial use
- open contribution
- patent protection for contributors

---

## Origin

ContextForge is the first open-source project of **Reelfy**.

Reelfy builds creative, agent-driven AI systems where **context quality determines output quality**.

ContextForge is framework-neutral and community-driven.

---

## Vision

> If agents are the future of software,  
> **ContextForge is how we evaluate the systems they live in.**