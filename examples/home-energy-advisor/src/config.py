"""Configuration loader for agents and tools."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents."""
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


class Settings(BaseSettings):
    """Application settings from environment variables."""

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENWEATHER_API_KEY: str = ""
    NREL_API_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


class AgentConfig:
    """Configuration for a single agent."""

    def __init__(self, data: dict[str, Any]):
        self.model: str = data.get("model", "llama3.2")
        self.temperature: float = data.get("temperature", 0.7)
        self.recursion_limit: int = data.get("recursion_limit", 10)
        self.confidence_threshold: float = data.get("confidence_threshold", 0.7)
        self.turn_threshold: int = data.get("turn_threshold", 10)
        self.max_turns_before_summary: int = data.get("max_turns_before_summary", 20)


class AppConfig:
    """Full application configuration from YAML files + environment."""

    def __init__(self, config_dir: str | Path = "./config"):
        config_dir = Path(config_dir)
        agents_data = _load_yaml(config_dir / "agents.yaml")
        tools_data = _load_yaml(config_dir / "tools.yaml")

        self.advisor = AgentConfig(agents_data.get("advisor", {}))
        self.analyzer = AgentConfig(agents_data.get("analyzer", {}))
        self.memorizer = AgentConfig(agents_data.get("memorizer", {}))

        self.tools_mode: str = tools_data.get("mode", "mock")
        self.tools: dict[str, Any] = {
            k: v for k, v in tools_data.items() if k != "mode"
        }

        self.settings = Settings()


# Module-level singleton (lazily initialized)
_config: AppConfig | None = None


def get_config(config_dir: str | Path = "./config") -> AppConfig:
    """Get or create the application configuration."""
    global _config
    if _config is None:
        _config = AppConfig(config_dir)
    return _config


def reset_config() -> None:
    """Reset config singleton (useful for testing)."""
    global _config
    _config = None
