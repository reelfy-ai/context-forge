"""LLM backends for ContextForge judges.

Backends provide the connection to LLM providers. Ollama is the
primary/default backend for local execution.
"""

from context_forge.graders.judges.backends.ollama import OllamaBackend

__all__ = ["OllamaBackend"]
