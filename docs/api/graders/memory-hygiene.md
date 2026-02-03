# Memory Hygiene Evaluation

Evaluates agent memory management through two complementary approaches.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EVALUATION LAYERS                        │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: INVARIANTS (MemoryCorruptionGrader)               │
│  - Data corruption: Existing data deleted/nullified         │
│  → Fast, deterministic, always runs                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: SEMANTIC (MemoryHygieneJudge)                     │
│  - Missed facts: User said X, not saved                     │
│  - Hallucinations: Agent saved Y, user never said           │
│  → LLM-based, understands meaning                           │
└─────────────────────────────────────────────────────────────┘
```

## Why Two Layers?

**Deterministic checks are context-blind**: They can't know if "no memory write" is a problem (maybe nothing needed saving) or if "redundant write" is wasteful (maybe confirming data).

**LLM judges understand semantics**: They can compare what the user actually said to what was saved, catching issues that require understanding.

| Issue Type | MemoryCorruptionGrader | MemoryHygieneJudge |
|------------|------------------------|-------------------|
| Data deleted | ✅ Catches | N/A |
| User fact not saved | ❌ Can't detect | ✅ Catches |
| Agent invented fact | ❌ Can't detect | ✅ Catches |

## MemoryCorruptionGrader (Deterministic)

Checks for **invariants** - things that are ALWAYS wrong regardless of agent path.

::: context_forge.graders.deterministic.memory_corruption.MemoryCorruptionGrader
    options:
      show_root_heading: true
      members:
        - grade

### What It Checks

- **Data corruption**: Existing non-null value overwritten with null

### What It Does NOT Check

- Missed facts (semantic - use LLM judge)
- Hallucinations (semantic - use LLM judge)
- Redundant writes (context-dependent - not always wrong)

## HybridMemoryHygieneGrader (Recommended)

Combines corruption detection with semantic evaluation.

::: context_forge.graders.hybrid.HybridMemoryHygieneGrader
    options:
      show_root_heading: true
      members:
        - grade

### Usage

```python
from context_forge.graders import HybridMemoryHygieneGrader
from context_forge.graders.judges.backends import OllamaBackend

# Full evaluation (recommended)
grader = HybridMemoryHygieneGrader(
    llm_backend=OllamaBackend(model="llama3.2")
)
result = grader.grade(trace)

# View results
result.print_report()

# Without LLM (corruption detection only)
grader = HybridMemoryHygieneGrader()  # No llm_backend
result = grader.grade(trace)  # Only checks for data corruption
```

### Evaluation Flow

1. **Run corruption check** (always)
2. **If corruption found**: Skip LLM, fail immediately
3. **If no corruption**: Run LLM semantic evaluation
4. **Combine results**: Both must pass for overall pass
