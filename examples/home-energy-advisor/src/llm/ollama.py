"""Ollama LLM and embeddings wrappers."""

from langchain_ollama import ChatOllama, OllamaEmbeddings

from src.config import get_config


def get_llm(agent_name: str = "advisor") -> ChatOllama:
    """Get a ChatOllama instance configured for the specified agent.

    Args:
        agent_name: One of "advisor", "analyzer", "memorizer"
    """
    config = get_config()
    agent_config = getattr(config, agent_name, config.advisor)

    return ChatOllama(
        model=agent_config.model,
        temperature=agent_config.temperature,
        base_url=config.settings.OLLAMA_BASE_URL,
    )


def get_embeddings() -> OllamaEmbeddings:
    """Get OllamaEmbeddings instance for nomic-embed-text."""
    config = get_config()

    return OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=config.settings.OLLAMA_BASE_URL,
    )
