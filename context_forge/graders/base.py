"""Base classes for ContextForge graders.

This module implements the core grader interface that all graders
(deterministic and LLM judges) must implement.

Key design principles:
- Graders operate ONLY on traces, never on framework objects
- Results include evidence with step_ids for traceability
- Deterministic graders are stateless and reproducible
- LLM judges include full reproducibility metadata
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from context_forge.core.trace import TraceRun


class Severity(str, Enum):
    """Severity level for evidence items."""

    INFO = "info"       # Informational, not a problem
    WARN = "warn"       # Potential issue, doesn't fail the grader
    ERROR = "error"     # Definite issue, fails the grader


@dataclass
class Evidence:
    """Proof of what was evaluated by a grader.

    Every grader result must include evidence explaining what was
    checked and why the result was pass/fail.

    Attributes:
        check_name: Name of the specific check (e.g., "redundant_write")
        description: Human-readable explanation of the finding
        severity: How serious this finding is
        step_ids: Which trace steps were examined
        details: Additional structured data about the finding
    """

    check_name: str
    description: str
    severity: Severity = Severity.INFO
    step_ids: list[str] = field(default_factory=list)
    details: Optional[dict[str, Any]] = None


@dataclass
class GraderResult:
    """Result from any grader (deterministic or LLM judge).

    Attributes:
        grader_name: Name of the grader that produced this result
        passed: Whether the trace passed all checks
        score: Numeric score from 0.0 (worst) to 1.0 (best)
        evidence: List of evidence items explaining the result
        timestamp: When the grading was performed
        metadata: Additional grader-specific data (LLM judges add prompt/response)
    """

    grader_name: str
    passed: bool
    score: float
    evidence: list[Evidence] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self):
        """Validate score is in valid range."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")

    @property
    def errors(self) -> list[Evidence]:
        """Get all evidence items with ERROR severity."""
        return [e for e in self.evidence if e.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Evidence]:
        """Get all evidence items with WARN severity."""
        return [e for e in self.evidence if e.severity == Severity.WARN]

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "grader_name": self.grader_name,
            "passed": self.passed,
            "score": self.score,
            "evidence": [
                {
                    "check_name": e.check_name,
                    "description": e.description,
                    "severity": e.severity.value,
                    "step_ids": e.step_ids,
                    "details": e.details,
                }
                for e in self.evidence
            ],
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def format_report(self, verbose: bool = False) -> str:
        """Format the grader result as a human-readable report.

        Args:
            verbose: Include additional details and metadata

        Returns:
            Formatted string report
        """
        lines = []

        # Header
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"GRADER REPORT: {self.grader_name}")
        lines.append("=" * 60)

        # Result summary
        status = "PASSED" if self.passed else "FAILED"
        status_icon = "[OK]" if self.passed else "[FAIL]"
        lines.append("")
        lines.append(f"Result: {status_icon} {status}")
        lines.append(f"Score:  {self.score:.2f} / 1.00")

        # Errors (always show)
        errors = self.errors
        if errors:
            lines.append("")
            lines.append(f"ERRORS ({len(errors)}):")
            for e in errors:
                lines.append(f"  [ERROR] {e.check_name}")
                lines.append(f"          {e.description}")
                if verbose and e.details:
                    for k, v in e.details.items():
                        lines.append(f"          {k}: {v}")

        # Warnings (always show)
        warnings = self.warnings
        if warnings:
            lines.append("")
            lines.append(f"WARNINGS ({len(warnings)}):")
            for e in warnings:
                lines.append(f"  [WARN]  {e.check_name}")
                lines.append(f"          {e.description}")

        # Info items (show summary only, or all if verbose)
        info_items = [e for e in self.evidence if e.severity == Severity.INFO]
        if info_items:
            # Always show the summary if present
            summary = next(
                (e for e in info_items if e.check_name == "llm_summary"),
                None,
            )
            if summary:
                lines.append("")
                lines.append("SUMMARY:")
                lines.append(f"  {summary.description}")

            # Show correct saves
            correct_saves = [e for e in info_items if e.check_name == "correct_save"]
            if correct_saves:
                lines.append("")
                lines.append(f"CORRECTLY SAVED ({len(correct_saves)}):")
                for e in correct_saves:
                    lines.append(f"  [OK] {e.description}")

            # Verbose: show all info items
            if verbose:
                other_info = [
                    e for e in info_items
                    if e.check_name not in ("llm_summary", "correct_save")
                ]
                if other_info:
                    lines.append("")
                    lines.append("ADDITIONAL INFO:")
                    for e in other_info:
                        lines.append(f"  [{e.check_name}] {e.description}")

        lines.append("")
        lines.append("-" * 60)

        return "\n".join(lines)

    def print_report(self, verbose: bool = False) -> None:
        """Print the grader result as a human-readable report.

        Args:
            verbose: Include additional details and metadata
        """
        print(self.format_report(verbose=verbose))

    def __str__(self) -> str:
        """Short string representation."""
        status = "PASSED" if self.passed else "FAILED"
        return f"GraderResult({self.grader_name}: {status}, score={self.score:.2f})"


class Grader(ABC):
    """Base class for all graders.

    Graders evaluate traces and return structured results with evidence.
    All graders must implement the `grade` method.

    Attributes:
        name: Human-readable name for this grader
        deterministic: Whether this grader produces identical results on repeated runs
        required_step_types: Step types this grader needs to function
    """

    name: str = "base_grader"
    deterministic: bool = True
    required_step_types: list[str] = []

    @abstractmethod
    def grade(self, trace: TraceRun) -> GraderResult:
        """Evaluate a trace and return a grading result.

        Args:
            trace: The trace to evaluate

        Returns:
            GraderResult with pass/fail, score, and evidence
        """
        pass

    def validate_trace(self, trace: TraceRun) -> list[str]:
        """Check if trace has required step types.

        Args:
            trace: The trace to validate

        Returns:
            List of missing step types (empty if all present)
        """
        present_types = {step.step_type for step in trace.steps}
        missing = [st for st in self.required_step_types if st not in present_types]
        return missing

    def check_required_steps(self, trace: TraceRun) -> None:
        """Validate trace has required step types, raising if not.

        Call this at the start of grade() to fail fast on invalid traces.

        Args:
            trace: The trace to validate

        Raises:
            ValueError: If required step types are missing
        """
        missing = self.validate_trace(trace)
        if missing:
            raise ValueError(
                f"Grader '{self.name}' requires step types {self.required_step_types}, "
                f"but trace is missing: {missing}"
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, deterministic={self.deterministic})"
