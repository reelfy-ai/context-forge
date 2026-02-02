"""Hybrid graders that combine deterministic and LLM-based evaluation.

Hybrid graders leverage the strengths of both approaches:
- Deterministic: Fast, cheap, catches invariant violations (corruption)
- LLM Judge: Semantic understanding, catches meaning-related issues
"""

from typing import Optional

from context_forge.core.trace import TraceRun
from context_forge.graders.base import Evidence, Grader, GraderResult, Severity
from context_forge.graders.deterministic.memory_corruption import MemoryCorruptionGrader
from context_forge.graders.judges.base import LLMBackend
from context_forge.graders.judges.memory_hygiene_judge import MemoryHygieneJudge


class HybridMemoryHygieneGrader(Grader):
    """Hybrid grader combining corruption detection and semantic evaluation.

    Layer 1 - Deterministic (MemoryCorruptionGrader):
    Checks for INVARIANTS that are always wrong:
    - Data corruption: Existing data deleted without replacement

    Layer 2 - LLM Judge (MemoryHygieneJudge):
    Checks for SEMANTIC issues requiring understanding:
    - Missed facts: User stated something, agent didn't save it
    - Hallucinations: Agent saved something user never said
    - Contradictions: Saved data conflicts with user statements

    The deterministic layer catches hard failures (corruption).
    The LLM layer catches semantic failures (wrong understanding).

    Usage:
        # With LLM (recommended - full semantic analysis)
        from context_forge.graders.judges.backends import OllamaBackend

        grader = HybridMemoryHygieneGrader(
            llm_backend=OllamaBackend(model="llama3.2")
        )
        result = grader.grade(trace)

        # Without LLM (only corruption detection)
        grader = HybridMemoryHygieneGrader()
        result = grader.grade(trace)  # Only checks for data corruption
    """

    name = "hybrid_memory_hygiene"
    deterministic = False  # Because LLM layer is non-deterministic

    def __init__(
        self,
        llm_backend: Optional[LLMBackend] = None,
        skip_llm_on_corruption: bool = True,
        llm_temperature: float = 0.0,
    ):
        """Initialize the hybrid grader.

        Args:
            llm_backend: Optional LLM backend for semantic checks.
                         If None, only corruption detection runs.
            skip_llm_on_corruption: If True, skip LLM when corruption
                         is detected (saves tokens, corruption is fatal).
            llm_temperature: Temperature for LLM calls (0.0 recommended).
        """
        self.llm_backend = llm_backend
        self.skip_llm_on_corruption = skip_llm_on_corruption

        # Layer 1: Corruption detection (invariants)
        self.corruption_grader = MemoryCorruptionGrader()

        # Layer 2: Semantic evaluation (understanding)
        self.llm_judge: Optional[MemoryHygieneJudge] = None
        if llm_backend:
            self.llm_judge = MemoryHygieneJudge(
                backend=llm_backend,
                temperature=llm_temperature,
            )

    def grade(self, trace: TraceRun) -> GraderResult:
        """Run hybrid evaluation on a trace.

        1. Run corruption detection (always)
        2. Run LLM judge (if configured and no corruption found)
        3. Combine results

        Args:
            trace: The trace to evaluate

        Returns:
            Combined GraderResult from both layers
        """
        all_evidence: list[Evidence] = []

        # Layer 1: Corruption detection
        corruption_result = self.corruption_grader.grade(trace)
        all_evidence.extend(corruption_result.evidence)

        # Add layer marker
        all_evidence.append(
            Evidence(
                check_name="layer_1_complete",
                description=f"Corruption check: {'PASSED' if corruption_result.passed else 'FAILED'} (score: {corruption_result.score:.2f})",
                severity=Severity.INFO,
            )
        )

        # Layer 2: LLM Semantic Judge (if configured)
        llm_result: Optional[GraderResult] = None

        if self.llm_judge:
            # Skip LLM if corruption detected (corruption is fatal)
            if self.skip_llm_on_corruption and not corruption_result.passed:
                all_evidence.append(
                    Evidence(
                        check_name="layer_2_skipped",
                        description="Semantic evaluation skipped: data corruption detected",
                        severity=Severity.INFO,
                    )
                )
            else:
                try:
                    llm_result = self.llm_judge.grade(trace)
                    all_evidence.extend(llm_result.evidence)

                    all_evidence.append(
                        Evidence(
                            check_name="layer_2_complete",
                            description=f"Semantic evaluation: {'PASSED' if llm_result.passed else 'FAILED'} (score: {llm_result.score:.2f})",
                            severity=Severity.INFO,
                        )
                    )
                except Exception as e:
                    all_evidence.append(
                        Evidence(
                            check_name="layer_2_error",
                            description=f"Semantic evaluation failed: {e}",
                            severity=Severity.WARN,
                        )
                    )

        # Combine results
        combined_result = self._combine_results(
            corruption_result, llm_result, all_evidence
        )
        return combined_result

    def _combine_results(
        self,
        corruption_result: GraderResult,
        llm_result: Optional[GraderResult],
        all_evidence: list[Evidence],
    ) -> GraderResult:
        """Combine corruption and semantic results into final result.

        Scoring:
        - If LLM ran: average of both scores
        - If LLM didn't run: corruption score only

        Passing:
        - Must pass BOTH layers to pass overall
        - Corruption failure is fatal (always fails)
        """
        if llm_result:
            # Both layers ran - combine
            combined_score = (corruption_result.score + llm_result.score) / 2
            combined_passed = corruption_result.passed and llm_result.passed

            # Merge metadata
            metadata = {
                "corruption": corruption_result.metadata,
                "semantic": llm_result.metadata,
                "layers_run": ["corruption", "semantic"],
            }
        else:
            # Only corruption check ran
            combined_score = corruption_result.score
            combined_passed = corruption_result.passed

            metadata = {
                "corruption": corruption_result.metadata,
                "layers_run": ["corruption"],
            }

        return GraderResult(
            grader_name=self.name,
            passed=combined_passed,
            score=combined_score,
            evidence=all_evidence,
            metadata=metadata,
        )
