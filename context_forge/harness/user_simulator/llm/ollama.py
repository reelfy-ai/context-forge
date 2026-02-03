"""Ollama client for user simulation LLM calls."""

from typing import Optional

import httpx
from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    """Configuration for Ollama LLM client."""

    base_url: str = "http://localhost:11434"
    model: str = "llama3.2"
    temperature: float = 0.7
    max_tokens: int = 500
    timeout: float = 60.0


class OllamaClient:
    """Async client for Ollama API.

    Used by LLMUserSimulator to generate simulated user responses.

    Example usage:
        async with OllamaClient() as client:
            response = await client.generate(
                prompt="What should the user say next?",
                system="You are simulating a user named Sarah...",
            )
    """

    def __init__(self, config: Optional[OllamaConfig] = None):
        """Initialize the Ollama client.

        Args:
            config: Configuration for Ollama connection
        """
        self._config = config or OllamaConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OllamaClient":
        """Enter async context manager."""
        self._client = httpx.AsyncClient(timeout=self._config.timeout)
        return self

    async def __aexit__(self, *args) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
    ) -> str:
        """Generate a response from Ollama.

        Args:
            prompt: User prompt to send
            system: Optional system prompt

        Returns:
            Generated text response
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.post(
            f"{self._config.base_url}/api/chat",
            json={
                "model": self._config.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self._config.temperature,
                    "num_predict": self._config.max_tokens,
                },
            },
        )
        response.raise_for_status()

        data = response.json()
        return data["message"]["content"]

    async def check_health(self) -> bool:
        """Check if Ollama is available.

        Returns:
            True if Ollama is reachable and responding
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            response = await self._client.get(f"{self._config.base_url}/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    async def list_models(self) -> list[str]:
        """List available models.

        Returns:
            List of model names available in Ollama
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.get(f"{self._config.base_url}/api/tags")
        response.raise_for_status()

        data = response.json()
        return [model["name"] for model in data.get("models", [])]
