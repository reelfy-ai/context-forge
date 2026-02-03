"""Memory Hygiene Judge - LLM-based semantic evaluation.

Layer 2 of the hybrid Memory Hygiene Grader. Uses an LLM to evaluate:
- Did the user provide new facts about themselves?
- Do those facts contradict stored memory?
- Was memory appropriately updated?

These semantic checks require natural language understanding.

Uses Ollama's structured output feature for reliable JSON parsing.
"""

import json
import logging
from typing import Any

from pydantic import ValidationError

from context_forge.core.trace import (
    MemoryReadStep,
    MemoryWriteStep,
    TraceRun,
    UserInputStep,
)
from context_forge.graders.base import Evidence, GraderResult, Severity
from context_forge.graders.judges.base import LLMBackend, LLMJudge
from context_forge.graders.judges.models import MemoryHygieneEvaluation

logger = logging.getLogger(__name__)


MEMORY_HYGIENE_PROMPT_TEMPLATE = '''You are evaluating an AI agent's memory management.

## Task
Analyze whether the agent correctly identified and saved ONLY facts the user explicitly stated.

## Current Memory (what the agent knew at session start)
{memory_state}

## User Messages (what the user said during the session)
{user_messages}

## Memory Changes (field-level differences, old_value -> new_value)
{memory_writes}

## Step-by-Step Evaluation

### Step 1: List user-stated facts
Read the user messages carefully. What concrete facts did the user explicitly state about themselves?
- Only include facts the user ACTUALLY said
- Example: If user says "I have a Tesla Model 3", that's a user fact
- Example: If user says "When should I charge?", that contains NO facts about themselves

### Step 2: Check each memory change
For EACH field in "Memory Changes", ask:
- Did the user explicitly state this information? If yes → correct save
- Did the user NOT mention this at all? If the agent invented it → HALLUCINATION
- Was existing correct data deleted or overwritten incorrectly? → data loss

### Step 3: Check for missed facts
For each user-stated fact from Step 1, was it saved to memory? If not → missed fact

## What IS a hallucination (flag these!)
- Agent saves "user plans to buy solar" but user never mentioned solar → HALLUCINATION
- Agent saves "user prefers morning charging" but user never stated a preference → HALLUCINATION
- Agent saves ANY new semantic content that the user did not explicitly state → HALLUCINATION

## What is NOT a hallucination (ignore these)
- Timestamp/metadata changes (updated_at, created_at, IDs)
- Preserving existing data that was already in memory
- Reformatting user's words (e.g., "12kW" saved as "12000W")

## Critical Rule
If the agent writes NEW information to memory that the user did NOT say, that is a hallucination.
The agent should ONLY save facts the user explicitly stated.

Evaluate the memory management and provide your assessment.'''


class MemoryHygieneJudge(LLMJudge):
    """LLM-based judge for memory hygiene semantic evaluation.

    Evaluates whether the agent correctly identified user facts and
    updated memory appropriately. Catches issues that rule-based
    checks cannot detect:
    - User stated new fact but it wasn't saved
    - Agent saved something user didn't say (hallucination)
    - Contradictions between user statements and memory updates

    Uses Pydantic models for structured output validation.

    Usage:
        from context_forge.graders.judges.backends import OllamaBackend

        judge = MemoryHygieneJudge(backend=OllamaBackend(model="llama3.2"))
        result = judge.grade(trace)

        if not result.passed:
            print("Issues found:")
            for evidence in result.errors:
                print(f"  - {evidence.description}")
    """

    name = "memory_hygiene_judge"
    required_step_types = ["user_input"]

    def _build_prompt(self, trace: TraceRun) -> str:
        """Build the evaluation prompt from trace data.

        Extracts user inputs, memory reads, and memory writes from
        the trace and formats them for LLM evaluation.
        """
        # Extract relevant steps
        user_inputs = [s for s in trace.steps if isinstance(s, UserInputStep)]
        memory_reads = [s for s in trace.steps if isinstance(s, MemoryReadStep)]
        memory_writes = [s for s in trace.steps if isinstance(s, MemoryWriteStep)]

        # Format memory state (from reads)
        if memory_reads:
            memory_state = self._format_memory_state(memory_reads)
        else:
            memory_state = "No memory was read at session start."

        # Format user messages
        if user_inputs:
            user_messages = self._format_user_messages(user_inputs)
        else:
            user_messages = "No user messages in this session."

        # Format memory writes
        if memory_writes:
            memory_writes_text = self._format_memory_writes(memory_writes)
        else:
            memory_writes_text = "No memory updates were made."

        # Build prompt
        prompt = MEMORY_HYGIENE_PROMPT_TEMPLATE.format(
            memory_state=memory_state,
            user_messages=user_messages,
            memory_writes=memory_writes_text,
        )
        return prompt

    def _format_memory_state(self, memory_reads: list[MemoryReadStep]) -> str:
        """Format memory read results for the prompt."""
        parts = []
        for i, read in enumerate(memory_reads, 1):
            if read.results:
                # Pretty print the results
                results_str = json.dumps(read.results, indent=2, default=str)
                parts.append(f"Read {i}:\n{results_str}")
            else:
                parts.append(f"Read {i}: (empty)")
        return "\n\n".join(parts)

    def _format_user_messages(self, user_inputs: list[UserInputStep]) -> str:
        """Format user input messages for the prompt."""
        parts = []
        for i, inp in enumerate(user_inputs, 1):
            parts.append(f"Message {i}: {inp.content}")
        return "\n".join(parts)

    def _format_memory_writes(self, memory_writes: list[MemoryWriteStep]) -> str:
        """Format memory writes for the prompt."""
        parts = []
        for i, write in enumerate(memory_writes, 1):
            if write.changes:
                changes_str = "\n".join(
                    f"  - {c.path}: {c.old_value} -> {c.new_value}"
                    for c in write.changes
                )
                parts.append(f"Write {i} (to {write.namespace}):\n{changes_str}")
            else:
                parts.append(f"Write {i}: {write.data}")
        return "\n\n".join(parts)

    def grade(self, trace: TraceRun) -> GraderResult:
        """Evaluate a trace using structured LLM output.

        Overrides base class to use complete_structured for reliable parsing.

        Args:
            trace: The trace to evaluate

        Returns:
            GraderResult with LLM evaluation
        """
        prompt = self._build_prompt(trace)

        try:
            # Use structured output - Ollama enforces the schema
            evaluation = self.backend.complete_structured(
                prompt=prompt,
                response_model=MemoryHygieneEvaluation,
                temperature=self.temperature,
            )

            # Convert to GraderResult
            evidence = self._evaluation_to_evidence(evaluation)
            result = GraderResult(
                grader_name=self.name,
                passed=evaluation.passed,
                score=evaluation.score,
                evidence=evidence,
            )

            # Add reproducibility metadata
            result.metadata = {
                "llm": {
                    "model_id": self.backend.model_id,
                    "temperature": self.temperature,
                    "prompt": prompt,
                }
            }

            return result

        except (ValidationError, ValueError) as e:
            logger.warning(f"Structured output failed: {e}")

            # Fallback: return a warning result
            return GraderResult(
                grader_name=self.name,
                passed=True,  # Don't fail just because of LLM error
                score=0.5,
                evidence=[
                    Evidence(
                        check_name="llm_error",
                        description=f"LLM evaluation failed: {e}",
                        severity=Severity.WARN,
                    )
                ],
                metadata={
                    "llm": {
                        "model_id": self.backend.model_id,
                        "temperature": self.temperature,
                        "prompt": prompt,
                        "error": str(e),
                    }
                },
            )

    def _parse_response(self, response: str, trace: TraceRun) -> GraderResult:
        """Parse LLM response (not used with structured output).

        This method is kept for compatibility but the grade() method
        uses complete_structured() instead.
        """
        # This shouldn't be called when using structured output
        raise NotImplementedError(
            "MemoryHygieneJudge uses structured output via grade() method"
        )

    def _evaluation_to_evidence(
        self, evaluation: MemoryHygieneEvaluation
    ) -> list[Evidence]:
        """Convert a validated evaluation to evidence items."""
        evidence: list[Evidence] = []

        # Missed facts (ERROR)
        for item in evaluation.facts_missed:
            evidence.append(
                Evidence(
                    check_name="missed_fact",
                    description=f"User stated '{item.fact}' but it was not saved",
                    severity=Severity.ERROR,
                    details={
                        "fact": item.fact,
                        "should_have_updated": item.should_have_updated,
                    },
                )
            )

        # Hallucinations (ERROR)
        for item in evaluation.hallucinations:
            evidence.append(
                Evidence(
                    check_name="hallucination",
                    description=f"Agent saved '{item.saved}' which user did not state",
                    severity=Severity.ERROR,
                    details={
                        "saved": item.saved,
                        "reason": item.reason,
                    },
                )
            )

        # Data loss (ERROR)
        for item in evaluation.data_incorrectly_lost:
            evidence.append(
                Evidence(
                    check_name="incorrect_data_loss",
                    description=f"Field '{item.field}' was incorrectly overwritten",
                    severity=Severity.ERROR,
                    details={
                        "field": item.field,
                        "old_value": item.old_value,
                        "reason": item.reason,
                    },
                )
            )

        # Correctly saved facts (INFO - positive feedback)
        for item in evaluation.facts_correctly_saved:
            evidence.append(
                Evidence(
                    check_name="correct_save",
                    description=f"Correctly saved: '{item.fact}'",
                    severity=Severity.INFO,
                    details={
                        "fact": item.fact,
                        "saved_as": item.saved_as,
                    },
                )
            )

        # Summary (INFO)
        evidence.append(
            Evidence(
                check_name="llm_summary",
                description=evaluation.summary,
                severity=Severity.INFO,
                details={
                    "user_facts_count": len(evaluation.user_facts_stated),
                    "correctly_saved_count": len(evaluation.facts_correctly_saved),
                    "missed_count": len(evaluation.facts_missed),
                    "hallucinations_count": len(evaluation.hallucinations),
                },
            )
        )

        return evidence
