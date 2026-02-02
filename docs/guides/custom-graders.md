# Writing Custom Graders

This guide shows how to create custom graders for your specific evaluation needs.

## Overview

ContextForge provides two types of graders:

1. **Deterministic Graders**: Rule-based, fast, reproducible
2. **LLM Judges**: Semantic understanding, slower, may vary between runs

## Creating a Deterministic Grader

Deterministic graders implement exact rules and produce identical results on repeated runs.

### Basic Structure

```python
from context_forge.graders.base import Grader, GraderResult, Evidence, Severity
from context_forge.core.trace import TraceRun, ToolCallStep

class ToolBudgetGrader(Grader):
    """Checks that tool calls stay within budget."""

    name = "tool_budget"
    deterministic = True
    required_step_types = ["tool_call"]

    def __init__(self, max_tool_calls: int = 10):
        self.max_tool_calls = max_tool_calls

    def grade(self, trace: TraceRun) -> GraderResult:
        # Validate required steps exist
        self.check_required_steps(trace)

        # Count tool calls
        tool_calls = [s for s in trace.steps if isinstance(s, ToolCallStep)]
        count = len(tool_calls)

        evidence = []
        passed = count <= self.max_tool_calls

        if not passed:
            evidence.append(Evidence(
                check_name="tool_budget_exceeded",
                description=f"Used {count} tool calls, limit is {self.max_tool_calls}",
                severity=Severity.ERROR,
                details={"count": count, "limit": self.max_tool_calls},
            ))
        else:
            evidence.append(Evidence(
                check_name="tool_budget_ok",
                description=f"Used {count}/{self.max_tool_calls} tool calls",
                severity=Severity.INFO,
            ))

        # Score: 1.0 if within budget, decreasing as we exceed
        score = min(1.0, self.max_tool_calls / max(count, 1))

        return GraderResult(
            grader_name=self.name,
            passed=passed,
            score=score,
            evidence=evidence,
        )
```

### Using Your Grader

```python
grader = ToolBudgetGrader(max_tool_calls=5)
result = grader.grade(trace)
result.print_report()
```

## Creating an LLM Judge

LLM judges use language models for semantic evaluation.

### Basic Structure

```python
from context_forge.graders.judges.base import LLMJudge, LLMBackend
from context_forge.graders.base import GraderResult, Evidence, Severity
from context_forge.core.trace import TraceRun
from pydantic import BaseModel, Field

# Define the expected output schema
class ToneEvaluation(BaseModel):
    is_professional: bool = Field(description="Whether the tone is professional")
    issues: list[str] = Field(default_factory=list, description="Specific tone issues")
    score: float = Field(ge=0.0, le=1.0, description="Professionalism score")

class ToneJudge(LLMJudge):
    """Evaluates whether agent responses maintain professional tone."""

    name = "tone_judge"
    required_step_types = ["final_output"]

    def _build_prompt(self, trace: TraceRun) -> str:
        # Extract final outputs
        outputs = [s for s in trace.steps if s.step_type == "final_output"]
        output_text = "\n".join(s.content for s in outputs)

        return f"""Evaluate if this response maintains a professional tone:

{output_text}

Check for:
- Appropriate formality
- No slang or casual language
- Clear and respectful communication
"""

    def _parse_response(self, response: str, trace: TraceRun) -> GraderResult:
        # Parse LLM response into structured format
        # (In practice, use complete_structured() for reliable parsing)
        pass

    def grade(self, trace: TraceRun) -> GraderResult:
        prompt = self._build_prompt(trace)

        # Use structured output for reliable parsing
        evaluation = self.backend.complete_structured(
            prompt=prompt,
            response_model=ToneEvaluation,
            temperature=self.temperature,
        )

        evidence = []
        for issue in evaluation.issues:
            evidence.append(Evidence(
                check_name="tone_issue",
                description=issue,
                severity=Severity.WARN,
            ))

        return GraderResult(
            grader_name=self.name,
            passed=evaluation.is_professional,
            score=evaluation.score,
            evidence=evidence,
            metadata={
                "llm": {
                    "model_id": self.backend.model_id,
                    "temperature": self.temperature,
                    "prompt": prompt,
                }
            },
        )
```

### Using Your LLM Judge

```python
from context_forge.graders.judges.backends import OllamaBackend

judge = ToneJudge(backend=OllamaBackend(model="llama3.2"))
result = judge.grade(trace)
result.print_report()
```

## Best Practices

### 1. Use Evidence Liberally

Evidence items explain why a grader passed or failed. Always include:

- What was checked
- What was found
- Why it matters

```python
Evidence(
    check_name="specific_check_name",  # Machine-readable identifier
    description="Human-readable explanation",
    severity=Severity.ERROR,  # ERROR, WARN, or INFO
    step_ids=["step-1", "step-2"],  # Which steps were examined
    details={"key": "value"},  # Structured data for debugging
)
```

### 2. Validate Required Steps

Always call `check_required_steps()` at the start of `grade()`:

```python
def grade(self, trace: TraceRun) -> GraderResult:
    self.check_required_steps(trace)  # Raises if missing
    # ... rest of grading logic
```

### 3. Include Reproducibility Metadata

For LLM judges, always include the prompt and model info in metadata:

```python
return GraderResult(
    # ...
    metadata={
        "llm": {
            "model_id": self.backend.model_id,
            "temperature": self.temperature,
            "prompt": prompt,
        }
    },
)
```

### 4. Use Pydantic Models for Structured Output

Define Pydantic models for LLM output to ensure reliable parsing:

```python
class MyEvaluation(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)

# Use with Ollama's structured output
result = backend.complete_structured(
    prompt=prompt,
    response_model=MyEvaluation,
)
```

### 5. Handle Errors Gracefully

LLM judges may fail due to connection issues or parsing errors:

```python
try:
    evaluation = self.backend.complete_structured(...)
except (ValidationError, ValueError) as e:
    return GraderResult(
        grader_name=self.name,
        passed=True,  # Don't fail on LLM error
        score=0.5,
        evidence=[
            Evidence(
                check_name="llm_error",
                description=f"LLM evaluation failed: {e}",
                severity=Severity.WARN,
            )
        ],
    )
```

## Combining Graders

Use multiple graders together for comprehensive evaluation:

```python
graders = [
    ToolBudgetGrader(max_tool_calls=10),
    HybridMemoryHygieneGrader(llm_backend=backend),
    ToneJudge(backend=backend),
]

for grader in graders:
    result = grader.grade(trace)
    result.print_report()
    if not result.passed:
        print(f"Failed: {grader.name}")
```

## Next Steps

- See [API Reference: Graders](../api/graders/base.md) for complete API documentation
- See [Memory Hygiene Grader](../api/graders/memory-hygiene.md) for a production example