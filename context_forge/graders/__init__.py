"""ContextForge Graders - Evaluate agent trajectories.

Graders analyze traces to detect behavioral issues that output-only
evaluation would miss.

Two types of evaluation:
- Deterministic (MemoryCorruptionGrader): Checks INVARIANTS that are always wrong
- LLM Judges (MemoryHygieneJudge): SEMANTIC evaluation requiring understanding
- Hybrid: Combines both for comprehensive analysis

Usage:
    from context_forge.graders import HybridMemoryHygieneGrader
    from context_forge.graders.judges.backends import OllamaBackend

    # Full evaluation (recommended)
    grader = HybridMemoryHygieneGrader(
        llm_backend=OllamaBackend(model="llama3.2")
    )
    result = grader.grade(trace)

    if not result.passed:
        for error in result.errors:
            print(f"Issue: {error.description}")
"""

from context_forge.graders.base import Evidence, Grader, GraderResult, Severity
from context_forge.graders.deterministic import MemoryCorruptionGrader
from context_forge.graders.hybrid import HybridMemoryHygieneGrader
from context_forge.graders.judges import LLMJudge, MemoryHygieneJudge

__all__ = [
    # Base classes
    "Grader",
    "GraderResult",
    "Evidence",
    "Severity",
    # Deterministic graders (invariant checks)
    "MemoryCorruptionGrader",
    # LLM judges (semantic evaluation)
    "LLMJudge",
    "MemoryHygieneJudge",
    # Hybrid graders (recommended)
    "HybridMemoryHygieneGrader",
]
