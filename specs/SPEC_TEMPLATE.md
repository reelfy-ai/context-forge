# Spec NNN: [Title]

**Status:** Draft | Under Review | Approved | Implemented
**Author:** [name]
**Created:** YYYY-MM-DD
**Last Updated:** YYYY-MM-DD
**Depends On:** [spec IDs, e.g., 001, 003]
**Blocks:** [spec IDs that depend on this]

---

## 1. Problem Statement

[What problem does this solve? What failure modes does it address?]

### 1.1 Current Limitations

[What is missing or broken without this?]

### 1.2 Target Users

[Who benefits from this spec? Agent developers, grader authors, framework integrators, etc.]

---

## 2. Solution Overview

[High-level approach. 2-3 paragraphs max.]

### 2.1 Design Principles

- [Principle 1]
- [Principle 2]
- [Principle 3]

### 2.2 Non-Goals

- [What this spec explicitly does NOT cover]
- [Scope boundaries]

---

## 3. Detailed Design

### 3.1 Data Structures

```python
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class ExampleModel:
    """Description of the model."""
    required_field: str
    optional_field: Optional[str] = None
```

### 3.2 API Surface

```python
class ExampleInterface:
    """Description of the interface."""

    def required_method(self, arg: str) -> Result:
        """
        Description of what this method does.

        Args:
            arg: Description of argument

        Returns:
            Description of return value

        Raises:
            ExampleError: When something goes wrong
        """
        ...
```

### 3.3 Behavior Specification

**Invariants:**
- [Invariant 1: something that must always be true]
- [Invariant 2]

**Edge Cases:**
- [Edge case 1]: [Expected behavior]
- [Edge case 2]: [Expected behavior]

**Error Handling:**
- [Error condition 1]: [How it should be handled]
- [Error condition 2]: [How it should be handled]

---

## 4. Examples

### 4.1 Basic Usage

```python
# Minimal working example
from context_forge import Example

example = Example()
result = example.do_something("input")
print(result)
```

### 4.2 Advanced Usage

```python
# Complex scenario example with multiple features
from context_forge import Example, Config

config = Config(
    option_a=True,
    option_b="value"
)
example = Example(config)
result = example.do_complex_thing(
    input="data",
    options={"key": "value"}
)
```

### 4.3 Error Cases

```python
# Expected error handling
from context_forge import Example, ExampleError

try:
    example = Example()
    example.do_invalid_thing(None)
except ExampleError as e:
    print(f"Expected error: {e}")
```

---

## 5. Integration Points

### 5.1 Dependencies

[What this spec consumes from other specs]

| Spec | What We Use |
|------|-------------|
| 001-trace-schema | `TraceStep`, `TraceRun` models |
| 003-grader-interface | `Grader` base class |

### 5.2 Consumers

[What other specs depend on this]

| Spec | What They Use |
|------|---------------|
| 030-budget-grader | `GraderResult` format |
| 051-junit-reporter | `GraderResult.evidence` |

### 5.3 Configuration

```yaml
# Relevant eval config sections
example:
  option_a: true
  option_b: "value"
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

- [ ] Test case 1: [Description]
- [ ] Test case 2: [Description]
- [ ] Test case 3: [Description]

### 6.2 Integration Tests

- [ ] Integration test 1: [Description]
- [ ] Integration test 2: [Description]

### 6.3 CI Requirements

- [ ] Tests must be deterministic (no network calls, seeded randomness)
- [ ] Tests must pass with tool replay enabled
- [ ] Tests must complete in < X seconds

---

## 7. Open Questions

- [ ] **Q1:** [Unresolved design question]
- [ ] **Q2:** [Alternative approach to consider]
- [ ] **Q3:** [Clarification needed from stakeholders]

---

## 8. Alternatives Considered

### 8.1 [Alternative A]

**Description:** [What this alternative would look like]

**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Why Rejected:** [Reason for not choosing this approach]

### 8.2 [Alternative B]

**Description:** [What this alternative would look like]

**Why Rejected:** [Reason for not choosing this approach]

---

## 9. Implementation Checklist

- [ ] Data structures implemented in `context_forge/[module].py`
- [ ] Public API implemented
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Spec status changed to "Implemented"

---

## 10. References

- [Link to ARCHITECTURE.md section](../ARCHITECTURE.md#section)
- [Link to related spec](./NNN-related-spec.md)
- [External reference or prior art](https://example.com)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| YYYY-MM-DD | [name] | Initial draft |
