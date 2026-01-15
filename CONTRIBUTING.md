

# Contributing to ContextForge

First of all: **thank you** for considering a contribution to ContextForge.  
This project exists to make agentic AI systems **observable, testable, and reliable** — and that only works with a strong community.

This document explains **how to contribute**, **what standards we expect**, and **how decisions are made**.

---

## 1. Project philosophy (read this first)

ContextForge is **infrastructure**, not a demo.

That means we optimize for:
- long-term stability
- clear contracts
- framework neutrality
- reproducibility
- debuggability

We intentionally move slower on features and faster on correctness.

If a contribution makes the system:
- harder to reason about
- coupled to a specific framework
- harder to reproduce in CI

…it will likely be rejected.

---

## 2. What we welcome

We actively welcome contributions in the following areas:

### ✅ Core framework
- Trace spec improvements (backward compatible)
- Tracer API enhancements (no breaking changes)
- Deterministic graders
- Replay / record infrastructure
- CLI improvements
- Documentation and examples

### ✅ Adapters (framework integrations)
- LangGraph
- LangChain
- AutoGen
- CrewAI
- smolagents
- Custom runtimes

Adapters **must not** leak framework objects into graders.

### ✅ Graders
- Context engineering graders
- Tool orchestration graders
- Memory hygiene graders
- Budget / efficiency graders
- Domain-specific graders (via domain packs)

### ✅ Domain packs
- Creative AI
- Finance & compliance
- Support automation
- Healthcare / regulated domains

Domain packs must live outside the core logic.

---

## 3. What we do NOT accept

To keep ContextForge usable and neutral, we do **not** accept:

- ❌ Framework-specific logic inside graders
- ❌ Hard dependencies on proprietary SaaS platforms
- ❌ Eval logic that depends on UI state or chat history alone
- ❌ “Prompt-only” evaluation tools
- ❌ Breaking changes without a migration path

---

## 4. Contribution types & guidelines

### 4.1 Bug reports
Please include:
- ContextForge version / commit hash
- Python version
- Minimal reproducible example
- Expected vs actual behavior
- Trace excerpts (redacted if needed)

---

### 4.2 Feature requests
Good feature requests:
- describe a real failure mode
- explain why existing graders are insufficient
- show how the feature remains framework-agnostic

Bad feature requests:
- depend on a specific agent framework
- assume a specific LLM vendor
- optimize only for demos

---

### 4.3 Code contributions (general rules)

- One feature or fix per PR
- Include tests where applicable
- Keep public APIs minimal
- Prefer composition over inheritance
- Prefer explicitness over magic

If you’re unsure, open a discussion or draft PR early.

---

## 5. Trace spec contributions (very important)

The **trace spec is the backbone** of ContextForge.

### Rules:
- Backward compatibility is mandatory
- Additive changes only in minor versions
- Never remove or rename fields without aliasing
- New step types must degrade gracefully

Every trace spec change must include:
- rationale
- example trace
- impact analysis for existing graders

---

## 6. Writing adapters (framework integrations)

Adapters are responsible for **normalizing runtime events**.

### Adapter rules:
- Do NOT expose framework-native objects downstream
- Do NOT require changes to user agent logic
- Support async + concurrency
- Provide redaction hooks (PII, secrets)
- Emit best-effort traces (partial is better than nothing)

Adapters should declare a **fidelity level**:
- Level A: full tracing (LLM, tools, retrieval, memory)
- Level B: core tracing (LLM + tools)
- Level C: minimal (final output only)

Graders must be able to handle missing optional signals.

---

## 7. Writing graders (portable by design)

Graders must operate **only on traces**.

### Required properties of a grader:
- Deterministic unless explicitly declared otherwise
- Stateless (no hidden global state)
- Side-effect free
- Clear failure evidence

### Grader checklist:
- What step types are required?
- What fields are required?
- What happens if data is missing?
- Can this run in CI deterministically?

### Example grader contract (conceptual):

```python
class MyGrader(Grader):
    requires = {
        "step_types": {"llm_call", "tool_call"},
        "fields": {"steps[].tool", "steps[].usage.tokens"}
    }
    deterministic = True
```

If a grader depends on LLM judges, it must:
- declare non-determinism
- store judge inputs and outputs
- support local backends (Ollama)

---

## 8. Domain packs

Domain packs extend ContextForge without bloating the core.

### Rules:
- No core imports from domain packs
- Register via plugin mechanism
- Provide clear documentation and examples
- Include rubrics as versioned artifacts

Recommended structure:

```
context_forge_domains_<name>/
  graders/
  rubrics/
  tasks/
  README.md
```

---

## 9. Testing & CI expectations

All contributions should aim to be:
- CI-safe
- deterministic
- reproducible

Tests should:
- avoid network calls
- use replayed tool calls
- assert grader outputs and evidence

If a feature cannot be tested deterministically, explain why.

---

## 10. Versioning & compatibility

ContextForge follows semantic versioning.

- **PATCH**: bug fixes
- **MINOR**: backward-compatible additions
- **MAJOR**: breaking changes (rare and deliberate)

Breaking changes require:
- migration guide
- deprecation period
- explicit approval from maintainers

---

## 11. Code style & tooling

- Python 3.10+
- Type hints required for public APIs
- Prefer Pydantic or dataclasses for models
- Black / Ruff formatting
- No heavy runtime dependencies in core

---

## 12. Governance & decision-making

ContextForge is currently:
- maintainer-led
- consensus-seeking

We value:
- thoughtful design discussion
- real-world failure reports
- long-term maintainability

Maintainers may reject technically correct code if it harms clarity or neutrality.

---

## 13. Code of conduct

Be respectful.

We welcome contributors from:
- open source
- academia
- startups
- enterprises
- creative industries

Harassment, gatekeeping, or dismissive behavior is not tolerated.

---

## 14. How to write a spec

ContextForge follows **Spec-Driven Development**. New features start as specifications.

### Spec process
1. Copy `specs/SPEC_TEMPLATE.md` to the appropriate directory
2. Use numbering convention: `NNN-descriptive-name.md`
3. Fill all sections, marking open questions with `[ ]`
4. Submit PR with `spec-draft` label
5. Address review feedback
6. Once approved, implementation can begin

### Spec locations
- `specs/foundation/` — Core contracts (trace, grader, config)
- `specs/instrumentation/` — Tracer and adapters
- `specs/harness/` — Execution infrastructure
- `specs/graders/` — Individual grader specs
- `specs/reports/` — Reporter specs
- `specs/cli/` — CLI specs

See [specs/README.md](specs/README.md) for full process documentation.

---

## 15. Final note

ContextForge is building **evaluation infrastructure for the next generation of AI systems**.

If your contribution helps:
- surface hidden failures
- make agents more reliable
- reduce demo-driven engineering

…it belongs here.

We’re glad you’re contributing.