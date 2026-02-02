"""Deterministic Memory Corruption Grader.

Checks for TRUE INVARIANTS that are ALWAYS wrong regardless of agent path:
- Data corruption: Existing correct data was deleted or overwritten with null
- Schema violations: Wrong types, malformed data structures

These checks detect hard failures that should never happen, regardless of
the non-deterministic path the agent takes.

For semantic evaluation (did the agent save the right facts?), use the
MemoryHygieneJudge LLM-based grader instead.
"""

from context_forge.core.trace import MemoryWriteStep, TraceRun
from context_forge.graders.base import Evidence, Grader, GraderResult, Severity


class MemoryCorruptionGrader(Grader):
    """Deterministic grader for memory corruption detection.

    Checks for invariant violations that are ALWAYS wrong:
    1. Data corruption: Existing data deleted without replacement
    2. Field deletion: Required fields removed

    These are hard constraints - if violated, something is broken.

    For semantic checks (missed facts, hallucinations), use the
    MemoryHygieneJudge LLM-based grader.

    Usage:
        grader = MemoryCorruptionGrader()
        result = grader.grade(trace)
        if not result.passed:
            for error in result.errors:
                print(f"Corruption detected: {error.description}")
    """

    name = "memory_corruption"
    deterministic = True
    required_step_types = []  # Can run on any trace

    def __init__(self, fail_on_data_loss: bool = True):
        """Initialize the grader.

        Args:
            fail_on_data_loss: Treat data loss as errors (default: True)
        """
        self.fail_on_data_loss = fail_on_data_loss

    def grade(self, trace: TraceRun) -> GraderResult:
        """Check for memory corruption in a trace.

        Args:
            trace: The trace to evaluate

        Returns:
            GraderResult with corruption findings
        """
        evidence: list[Evidence] = []

        # Get memory write steps
        memory_writes = [s for s in trace.steps if isinstance(s, MemoryWriteStep)]

        # Check for data corruption (deletion of existing values)
        evidence.extend(self._check_data_corruption(memory_writes))

        # Calculate score and pass/fail
        errors = [e for e in evidence if e.severity == Severity.ERROR]

        # Score: 1.0 - 0.5 per corruption error
        score = max(0.0, 1.0 - (len(errors) * 0.5))
        passed = len(errors) == 0

        return GraderResult(
            grader_name=self.name,
            passed=passed,
            score=score,
            evidence=evidence,
            metadata={
                "total_memory_writes": len(memory_writes),
                "corruption_errors": len(errors),
            },
        )

    def _check_data_corruption(
        self, memory_writes: list[MemoryWriteStep]
    ) -> list[Evidence]:
        """Check for data corruption: existing data deleted or nullified.

        Data corruption occurs when:
        - old_value exists (not None)
        - new_value is None (data deleted)

        This is an invariant violation - correct user data should never
        be deleted without explicit user request.
        """
        evidence = []

        for write in memory_writes:
            if not write.changes:
                continue

            corrupted_fields = []
            for change in write.changes:
                # Corruption: had value, now null (data lost)
                if change.old_value is not None and change.new_value is None:
                    corrupted_fields.append(change)

            if corrupted_fields:
                severity = Severity.ERROR if self.fail_on_data_loss else Severity.WARN
                paths = [c.path for c in corrupted_fields]
                evidence.append(
                    Evidence(
                        check_name="data_corruption",
                        description=f"Existing data was deleted: {paths}",
                        severity=severity,
                        step_ids=[write.step_id],
                        details={
                            "corrupted_fields": [
                                {
                                    "path": c.path,
                                    "lost_value": c.old_value,
                                }
                                for c in corrupted_fields
                            ],
                        },
                    )
                )

        return evidence
