

# ContextForge Spec Guidelines
**Goal:** define contracts and best practices so ContextForge remains **framework-agnostic**, **replayable**, and **grader-compatible** across any agent runtime.

These guidelines are intended for:
- core maintainers writing the spec
- adapter authors (LangGraph/LangChain/AutoGen/custom)
- domain pack authors writing graders and rubrics
- teams integrating ContextForge into CI / production monitoring

---

## 1. North Star: graders operate on traces, not frameworks

**Rule:** A ContextForge *grader* MUST depend only on the **Canonical Trace Spec**, never on LangChain/LangGraph/AutoGen objects.

Why:
- framework APIs change
- runtime event models differ
- multi-agent orchestration varies
- graders must be reusable across ecosystems

This aligns with the “trace is the request journey” model used in production LLM observability: record steps (LLM calls, retrieval, tools), then evaluate and compare runs. citeturn0search31turn0search2

**Implication:** all compatibility work is concentrated in **adapters**, not graders.

---

## 2. Compatibility strategy: multi-level integration model

To be truly framework-agnostic, ContextForge adopts industry standards and provides multiple integration levels.

> **Formal specifications:**
> - [specs/foundation/007-otel-ingestion.md](specs/foundation/007-otel-ingestion.md) — OTel/OpenInference import
> - [specs/foundation/008-instrumentor-interface.md](specs/foundation/008-instrumentor-interface.md) — Instrumentor pattern

### 2.0 Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                    AGENT FRAMEWORKS                            │
│  LangChain │ CrewAI │ AutoGen │ smolagents │ Custom           │
└──────┬─────────┬─────────┬─────────┬─────────┬────────────────┘
       │         │         │         │         │
       ▼         ▼         ▼         ▼         ▼
┌────────────────────────────────────────────────────────────────┐
│                 INSTRUMENTATION LAYER                          │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐ │
│  │ OpenInference│ │  Callbacks   │ │  ContextForge Tracer  │ │
│  │ Instrumentors│ │  (native)    │ │  (explicit control)   │ │
│  └──────┬───────┘ └──────┬───────┘ └───────────┬────────────┘ │
│         └────────────────┴─────────────────────┘              │
│                          │                                     │
│                          ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐│
│  │           OpenTelemetry / OpenInference Spans             ││
│  └───────────────────────────┬────────────────────────────────┘│
└──────────────────────────────┼─────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│                    CONTEXTFORGE CORE                           │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ OTel → Trace│  │   Canonical  │  │       Graders        │ │
│  │  Converter  │  │  Trace Spec  │  │  (Operate on traces) │ │
│  └─────────────┘  └──────────────┘  └───────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

The following sections describe how each layer works:

### 2.1 Canonical Trace (ContextForge) — The Grading Layer
A stable, versioned JSON/Pydantic schema designed for:
- grading
- replay
- regression diffs
- reporting

This is the **grading layer** — all evaluation happens on ContextForge traces, never on framework objects.

### 2.2 OpenTelemetry & OpenInference — The Transport Layer

The industry has converged on:
- **OpenTelemetry (OTel)** — Standard substrate for observability
- **OpenInference** — AI/LLM semantic conventions (by Arize AI, widely adopted) citeturn0search10turn0search6turn0search14turn0search34

**Guideline:** treat OTel/OpenInference as the *transport/interchange layer*, and ContextForge Trace as the *grading layer*.

#### Bidirectional Flow
- **Import:** OTel/OpenInference spans → ContextForge traces (for evaluation)
- **Export:** ContextForge traces → OTel spans (for observability tools)

### 2.3 Integration Levels

ContextForge provides four levels of integration, from zero-code to full control:

| Level | User Effort | Method |
|-------|-------------|--------|
| **Level 1: Zero-Code** | None | Ingest existing OTel/OpenInference traces via OTLP |
| **Level 2: One-Line** | Add instrumentor | `LangChainInstrumentor().instrument()` |
| **Level 3: Callback** | Pass handler | `config={"callbacks": [handler]}` |
| **Level 4: Explicit** | Use Tracer API | Full control via `Tracer.run()` |

This approach preserves:
- **Neutrality:** OTel works across vendors
- **Stability:** ContextForge trace remains spec-controlled
- **Ecosystem interop:** Teams can use existing observability without code changes

---

## 3. Spec must separate “normative” vs “informative”

To avoid confusion and accidental lock-in:

- **Normative** = MUST/SHOULD/MAY language; defines contracts
- **Informative** = examples, guidance, reference implementations

**Guideline:** keep normative requirements minimal but strict where it matters:
- step types and required fields
- how budgets are computed
- replay guarantees
- grader result format

Everything else belongs in informative annexes (recipes, adapters, rubrics).

---

## 4. Define minimum viable trace semantics (not maximum fields)

Agent frameworks emit wildly different data. To stay compatible, define a **minimal required set** and allow optional enrichment.

### 4.1 Required run-level fields
A trace MUST include:
- `trace_version` (semver or integer)
- `run.run_id`
- `run.started_at`, `run.ended_at` (or duration)
- `run.agent.name` and `run.agent.version` (string)
- `run.task.id` and `run.task.goal` (string)
- `steps[]` ordered list with stable IDs/types
- `outcome.status` (`success|partial|fail`)

### 4.2 Required step-level fields (by type)
Each step MUST include:
- `step_id` (monotonic)
- `type` (enum)
- `timestamp`
- `inputs` / `outputs` (type-specific, may be redacted)
- `error` (nullable)

For types:
- `llm_call`: model id + token usage when available
- `tool_call`: tool name + args + result (or result reference)
- `retrieval`: query + results metadata (doc_id/score), content optional

OTel GenAI semantic conventions can guide attribute naming and what “good instrumentation” captures, but ContextForge should not require any specific vendor’s fields. citeturn0search10turn0search6turn0search14

---

## 5. Instrumentation contract: normalize events → trace steps

> **Formal specifications:**
> - [specs/foundation/007-otel-ingestion.md](specs/foundation/007-otel-ingestion.md) — OTel/OpenInference import
> - [specs/foundation/008-instrumentor-interface.md](specs/foundation/008-instrumentor-interface.md) — Instrumentor pattern

ContextForge provides multiple instrumentation mechanisms. All produce conformant ContextForge traces.

### 5.1 Instrumentor pattern (Monkey-patching)

Following OpenInference conventions, instrumentors patch framework functions at import time:

```python
from contextforge.instrumentation import LangChainInstrumentor

LangChainInstrumentor().instrument()
# All LangChain calls are now traced automatically
```

Instrumentors MUST:
- Provide `instrument()` and `uninstrument()` methods
- Store original functions for restoration
- Be safe for async + concurrency
- Support configuration for trace destination

### 5.2 Callback handler pattern

For frameworks with callback systems:

```python
from contextforge.callbacks import ContextForgeHandler

handler = ContextForgeHandler()
chain.invoke(input, config={"callbacks": [handler]})
```

### 5.3 OTel/OpenInference ingestion

For existing instrumented code:

```bash
contextforge collect --otlp-port 4317 --eval evals.yaml
```

### 5.4 Design constraints (all methods)

All instrumentation methods SHOULD:
- be safe for async + concurrency
- avoid global state
- support partial tracing (some runtimes won't provide everything)
- support redaction hooks (PII, secrets)
- attach stable correlation IDs (span_id / step_id mapping)

### 5.5 Fidelity tiers

Instrumentation MAY declare a "fidelity level":

- **Level A (Full):** llm_call + retrieval + tool_call + memory + state transitions
- **Level B (Core):** llm_call + tool_call (+ basic outcome)
- **Level C (Minimal):** only final output + outcome

**Guideline:** graders MUST declare what fidelity they require, and runners MUST warn (not crash) if a trace is missing optional fields.

This keeps the ecosystem inclusive: frameworks can start with Level B and still benefit.

---

## 6. Replay is a first-class spec feature

CI-safe evaluation requires deterministic replays. OpenAI’s evaluation guidance strongly emphasizes continuous evaluation, regression checks, and growing datasets over time. citeturn0search1turn0search5

### 6.1 Tool replay contract
ContextForge MUST support a replay layer where tool calls can be:
- **recorded** (request + response + metadata)
- **replayed** (same response returned deterministically)

Replay modes:
- `strict`: tool signature must match (tool name + args canonicalization)
- `lenient`: allow minor non-semantic differences (future)

### 6.2 Canonicalization guidelines (important)
To make replay compatible across frameworks, tool calls SHOULD be canonicalized:
- stable tool name
- JSON-serializable args
- sorted keys
- normalized floats if needed
- redacted secrets replaced by tokens (e.g., `"api_key": "<redacted>"`)

This prevents “framework differences” from breaking replay.

---

## 7. Evaluation configuration must be declarative and portable

Users should define **what to evaluate**, not how the trace is stored.

### 7.1 Eval config schema (YAML)
Recommended shape:

```yaml
suite: "checkout_agent"
tasks:
  - id: "refund_request"
    dataset: "datasets/refund.jsonl"
graders:
  - budget:
      max_tokens: 5000
      max_tool_calls: 10
  - tool_schema:
      allowlist: ["search", "db_query", "email_send"]
  - loops:
      max_repeats: 3
  - trajectory_judge:
      backend: "ollama"
      model: "llama3.1"
      rubric: "rubrics/decision_quality.md"
      temperature: 0.0
reporters:
  - junit
  - markdown
```

### 7.2 Why declarative configs matter
- portable across repos and teams
- can be used in CI/CD
- can be diffed and reviewed like code

This mirrors “test before you ship” evaluation workflows used by common eval platforms. citeturn0search0turn0search2

---

## 8. Grader best practices (portable by design)

### 8.1 Grader MUST declare required signals
Each grader MUST define:
- required step types (e.g., needs `retrieval`)
- required fields (e.g., needs `retrieval.results[*].score`)
- whether it is deterministic

Example (conceptual):

```python
class RetrievalFitnessGrader(Grader):
    requires = {
        "step_types": {"retrieval"},
        "fields": {"steps[].results[].score"}
    }
    deterministic = True
```

### 8.2 Evidence is not optional
Every grader result SHOULD include evidence pointers:
- step_ids referenced
- excerpts (redacted)
- thresholds used
- why it failed

This is critical for debugging multi-step runs, which is a core theme in agent observability guidance. citeturn0search12turn0search28

---

## 9. LLM-as-judge: portability + reproducibility rules

LLM judges are useful for decision-quality scoring, but they are nondeterministic. Best practice is to combine automated (LLM judge) with deterministic checks and targeted human review. citeturn0search12turn0search8

### 9.1 Judge backend interface
ContextForge SHOULD define a backend-neutral judge interface:

- `backend`: `"ollama" | "openai_compat" | "http"`
- `model`: string
- `params`: temperature/top_p/seed where supported
- `rubric`: markdown file
- `input`: trace slice + question

### 9.2 Reproducibility requirements (MUST)
When using judges, the system MUST store:
- rubric version (hash)
- prompt template version (hash)
- filled judge prompt
- judge backend + model id
- judge params
- raw judge output + parsed score

This enables regression tracking and “continuous evaluation” over time. citeturn0search1turn0search5

---

## 10. Multi-agent compatibility guidelines

Multi-agent systems add complexity: multiple roles, message passing, shared state. Evaluation guidance for multi-agent systems emphasizes unique architectures and additional considerations beyond single-agent runs. citeturn0search20turn0search28

### 10.1 Trace representation
The trace SHOULD support:
- `actor` / `role` per step (e.g., `"planner"`, `"executor"`)
- optional `conversation_id` / `thread_id`
- `parent_step_id` for nested calls

### 10.2 Grader portability rule
Graders MUST not assume:
- a single agent
- a single linear chain
- a single tool router

Instead, graders should operate on:
- subsets by role
- aggregated metrics across actors
- conversation threads

---

## 11. Versioning & backward compatibility

To keep third-party graders working:

### 11.1 Trace spec evolution rules
- Additive changes only in minor versions
- Never rename fields without aliasing
- Introduce new step types without breaking old ones

### 11.2 Capability negotiation
Runners SHOULD expose trace capabilities (derived from what was captured):

```json
{
  "capabilities": {
    "retrieval": true,
    "memory": false,
    "tool_replay": true,
    "multi_agent": true
  }
}
```

Graders can then:
- run normally
- downgrade
- or skip with a clear message

---

## 12. Integration patterns (4 levels)

ContextForge provides four integration levels, from zero-code to full control:

### 12.1 Level 1: Zero-Code (OTel Ingestion)

For teams with existing OpenTelemetry/OpenInference instrumentation:

```bash
# Collect traces from existing OpenTelemetry pipeline
contextforge collect --otlp-port 4317 --eval evals.yaml
```

No code changes required.

### 12.2 Level 2: One-Line Instrumentation

Add auto-instrumentation with a single line:

```python
from contextforge.instrumentation import LangChainInstrumentor

LangChainInstrumentor().instrument()

# Existing LangChain code works unchanged - all calls traced
from langchain_openai import ChatOpenAI
llm = ChatOpenAI()
response = llm.invoke("Hello!")  # Automatically traced
```

Or via environment variable (no code changes):
```bash
CONTEXTFORGE_INSTRUMENT_LANGCHAIN=true python my_agent.py
```

### 12.3 Level 3: Callback Handler

For frameworks with callback systems:

```python
from contextforge.callbacks import ContextForgeHandler

handler = ContextForgeHandler()
chain.invoke(input, config={"callbacks": [handler]})
```

### 12.4 Level 4: Explicit Tracer API

For custom agents or when you need full control:

```python
from context_forge import Tracer

with Tracer.run(task="refund_request") as t:
    t.user_input("I want a refund")
    out = llm.generate(prompt)
    t.llm_call(prompt=prompt, output=out)
    res = tool(args)
    t.tool_call("db_query", args, res)
    t.final_output(out)
```

**Design principle:** If a user ever feels they are "writing trace JSON," treat it as a UX bug. Users should use the highest-level integration that works for their setup.

---

## 13. Recommended “agnostic-first” roadmap

To ensure compatibility grows rather than fractures:

1. **Freeze the minimal trace spec + grader result format** early
2. Ship **Generic Tracer** + **record/replay** before fancy adapters
3. Add **one adapter at a time** (LangGraph/LangChain/etc.)
4. Add OTel export/import once the trace is stable
5. Grow domain packs (creative, finance, support) as separate packages

This mirrors the standard industry flow: start with curated examples, then add regression testing and continuous evaluation loops as systems mature. citeturn0search2turn0search1

---

## 14. Practical checklist for “framework neutrality”

A compatibility review for any new feature should answer:

- Does this require a specific framework object? (If yes → reject)
- Can this be expressed as trace steps? (If yes → accept)
- Does it degrade gracefully with missing signals? (If no → redesign)
- Can it be replayed deterministically in CI? (If no → redesign)
- Does it preserve user privacy (redaction hooks)? (If no → redesign)

---

## Appendix A: Terminology alignment (optional)

Where helpful, ContextForge MAY align naming with:
- OTel GenAI semantic conventions (attributes and spans) citeturn0search10turn0search14
- common “run/step” models used in tracing platforms (LLM call, tool call, node run) citeturn0search2turn0search0

But ContextForge MUST remain independent and not require any vendor SDK.