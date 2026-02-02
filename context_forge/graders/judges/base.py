"""Base class for LLM-based judges.

LLM judges evaluate semantic aspects of traces that require
natural language understanding. They are marked as non-deterministic
and include full reproducibility metadata.

Supports structured output with Pydantic models for reliable parsing.
"""

from abc import abstractmethod
from typing import Any, Optional, Protocol, TypeVar

from pydantic import BaseModel

from context_forge.core.trace import TraceRun
from context_forge.graders.base import Grader, GraderResult

T = TypeVar("T", bound=BaseModel)


class LLMBackend(Protocol):
    """Protocol for LLM backends (Ollama, OpenAI, etc.)."""

    @property
    def model_id(self) -> str:
        """The model identifier."""
        ...

    def complete(self, prompt: str, temperature: float = 0.0) -> str:
        """Generate a completion for the given prompt.

        Args:
            prompt: The prompt to complete
            temperature: Sampling temperature (0.0 for deterministic)

        Returns:
            The model's response text
        """
        ...

    def complete_structured(
        self,
        prompt: str,
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        """Generate a structured completion with Pydantic validation.

        Args:
            prompt: The prompt to complete
            response_model: Pydantic model class for the response
            temperature: Sampling temperature (0.0 for deterministic)

        Returns:
            Validated Pydantic model instance
        """
        ...


class LLMJudge(Grader):
    """Base class for LLM-based judges.

    LLM judges use language models to evaluate aspects of traces that
    require semantic understanding. Unlike deterministic graders, they:
    - Are marked as non-deterministic
    - Include full reproducibility metadata (prompt, response, model)
    - Support configurable backends (Ollama, OpenAI, etc.)

    Subclasses must implement:
    - _build_prompt(): Construct the evaluation prompt
    - _parse_response(): Parse the LLM response into a GraderResult

    Usage:
        class MyJudge(LLMJudge):
            def _build_prompt(self, trace):
                return f"Evaluate this trace: {trace}"

            def _parse_response(self, response, trace):
                return GraderResult(...)

        judge = MyJudge(backend=OllamaBackend(model="llama3.2"))
        result = judge.grade(trace)
    """

    name = "llm_judge"
    deterministic = False  # LLM outputs can vary

    def __init__(
        self,
        backend: LLMBackend,
        temperature: float = 0.0,
    ):
        """Initialize the judge with an LLM backend.

        Args:
            backend: LLM backend to use for evaluation
            temperature: Sampling temperature (default 0.0 for consistency)
        """
        self.backend = backend
        self.temperature = temperature

    def grade(self, trace: TraceRun) -> GraderResult:
        """Evaluate a trace using the LLM.

        Args:
            trace: The trace to evaluate

        Returns:
            GraderResult with LLM evaluation and reproducibility metadata
        """
        # Build prompt
        prompt = self._build_prompt(trace)

        # Call LLM
        response = self.backend.complete(prompt, temperature=self.temperature)

        # Parse response into result
        result = self._parse_response(response, trace)

        # Add reproducibility metadata
        if result.metadata is None:
            result.metadata = {}

        result.metadata.update({
            "llm": {
                "model_id": self.backend.model_id,
                "temperature": self.temperature,
                "prompt": prompt,
                "raw_response": response,
            }
        })

        return result

    @abstractmethod
    def _build_prompt(self, trace: TraceRun) -> str:
        """Construct the evaluation prompt for the LLM.

        Args:
            trace: The trace to evaluate

        Returns:
            The prompt string to send to the LLM
        """
        pass

    @abstractmethod
    def _parse_response(self, response: str, trace: TraceRun) -> GraderResult:
        """Parse the LLM response into a GraderResult.

        Args:
            response: Raw LLM response text
            trace: The original trace (for context)

        Returns:
            GraderResult with parsed findings
        """
        pass
