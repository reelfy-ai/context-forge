"""Ollama backend for LLM judges.

Provides local LLM execution via Ollama. This is the primary backend
for ContextForge, enabling evaluation without sending data to cloud APIs.

Supports structured output via JSON schema - pass a Pydantic model
to get validated, typed responses.

Uses the official Ollama Python SDK for cleaner, more maintainable code.
"""

import logging
from typing import TypeVar

import ollama
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OllamaBackend:
    """Ollama backend for local LLM execution with structured output support.

    Usage:
        backend = OllamaBackend(model="llama3.2")

        # Basic completion (returns string)
        response = backend.complete("Evaluate this trace...")

        # Structured output with Pydantic model (returns validated object)
        result = backend.complete_structured(
            prompt="Evaluate this trace...",
            response_model=MemoryHygieneEvaluation,
        )

    Requires Ollama to be running at localhost:11434 (default).
    """

    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        """Initialize the Ollama backend.

        Args:
            model: Ollama model to use (e.g., "llama3.2", "mistral")
            host: Ollama host URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.host = host
        self.timeout = timeout
        self._client = ollama.Client(host=host, timeout=timeout)

    @property
    def model_id(self) -> str:
        """The model identifier."""
        return f"ollama/{self.model}"

    def complete(
        self,
        prompt: str,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        """Generate a completion using Ollama.

        Args:
            prompt: The prompt to complete
            temperature: Sampling temperature (0.0 for deterministic)
            json_mode: If True, enforce JSON output format

        Returns:
            The model's response text

        Raises:
            ollama.ResponseError: If the request fails
            ValueError: If Ollama is not running
        """
        try:
            response = self._client.generate(
                model=self.model,
                prompt=prompt,
                format="json" if json_mode else None,
                options={"temperature": temperature},
            )
            return response.get("response", "")

        except ollama.ResponseError as e:
            logger.error(f"Ollama request failed: {e}")
            raise

        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                logger.error(f"Failed to connect to Ollama at {self.host}: {e}")
                raise ValueError(
                    f"Cannot connect to Ollama at {self.host}. "
                    "Is Ollama running? Start it with: ollama serve"
                ) from e
            raise

    def complete_structured(
        self,
        prompt: str,
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        """Generate a structured completion with Pydantic validation.

        Uses Ollama's structured output feature to enforce a JSON schema,
        then validates with Pydantic for type safety.

        Args:
            prompt: The prompt to complete
            response_model: Pydantic model class for the response
            temperature: Sampling temperature (0.0 for deterministic)

        Returns:
            Validated Pydantic model instance

        Raises:
            ollama.ResponseError: If the request fails
            pydantic.ValidationError: If response doesn't match schema
            ValueError: If Ollama connection fails
        """
        # Get JSON schema from Pydantic model
        schema = response_model.model_json_schema()

        try:
            response = self._client.generate(
                model=self.model,
                prompt=prompt,
                format=schema,  # Ollama enforces this schema
                options={"temperature": temperature},
            )
            response_text = response.get("response", "")

            # Parse and validate with Pydantic
            return response_model.model_validate_json(response_text)

        except ollama.ResponseError as e:
            logger.error(f"Ollama request failed: {e}")
            raise

        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                logger.error(f"Failed to connect to Ollama at {self.host}: {e}")
                raise ValueError(
                    f"Cannot connect to Ollama at {self.host}. "
                    "Is Ollama running? Start it with: ollama serve"
                ) from e
            raise

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available.

        Returns:
            True if Ollama is accessible and model is pulled
        """
        try:
            response = self._client.list()
            # SDK returns ListResponse with .models attribute containing Model objects
            model_names = [m.model.split(":")[0] for m in response.models]
            return self.model.split(":")[0] in model_names
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"OllamaBackend(model={self.model!r}, host={self.host!r})"
