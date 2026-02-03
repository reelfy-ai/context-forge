"""Integration test configuration — requires running Ollama instance."""

import os
import tempfile

import httpx
import pytest
from dotenv import load_dotenv

from src.config import AppConfig, reset_config
from src.core.models import Equipment, Household, Location, Preferences, UserProfile

# Load .env so API key skip markers can check os.environ
load_dotenv()


def _ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _model_available(model: str = "llama3.2") -> bool:
    """Check if the required model is pulled in Ollama."""
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if resp.status_code != 200:
            return False
        models = resp.json().get("models", [])
        return any(m.get("name", "").startswith(model.split(":")[0]) for m in models)
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


# Skip markers
ollama_required = pytest.mark.skipif(
    not _ollama_available(),
    reason="Ollama is not running at localhost:11434",
)

model_required = pytest.mark.skipif(
    not _model_available(),
    reason="Required model (llama3.2) not available in Ollama",
)

api_keys_available = pytest.mark.skipif(
    not os.environ.get("OPENWEATHER_API_KEY") or not os.environ.get("NREL_API_KEY"),
    reason="API keys not configured (OPENWEATHER_API_KEY, NREL_API_KEY)",
)


@pytest.fixture(autouse=True)
def _reset_config_integration():
    """Reset config between integration tests."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def tmp_data_dir():
    """Temporary data directory for profile persistence tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_tools_config(tmp_path):
    """Create a config directory with tools in mock mode."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    agents_yaml = config_dir / "agents.yaml"
    agents_yaml.write_text("""
advisor:
  model: llama3.2
  temperature: 0.7

analyzer:
  model: llama3.2
  temperature: 0.3
  recursion_limit: 10

memorizer:
  model: llama3.2
  temperature: 0.2
  confidence_threshold: 0.7
  turn_threshold: 10
  max_turns_before_summary: 20
""")

    tools_yaml = config_dir / "tools.yaml"
    tools_yaml.write_text("""
mode: mock

weather:
  provider: openweathermap
  endpoint: https://api.openweathermap.org/data/2.5
  api_key_env: OPENWEATHER_API_KEY

rates:
  provider: nrel
  endpoint: https://developer.nrel.gov/api/utility_rates/v3
  api_key_env: NREL_API_KEY

solar:
  provider: nrel_pvwatts
  endpoint: https://developer.nrel.gov/api/pvwatts/v8
  api_key_env: NREL_API_KEY
""")

    return str(config_dir)


@pytest.fixture
def integration_config(mock_tools_config):
    """Set up config with mock tools for integration tests."""
    reset_config()
    import src.config as config_module
    config_module._config = AppConfig(config_dir=mock_tools_config)
    yield config_module._config
    reset_config()


@pytest.fixture
def demo_profile():
    """Demo user profile for integration tests."""
    return UserProfile(
        user_id="integration_test_user",
        equipment=Equipment(
            solar_capacity_kw=7.5,
            ev_model="Tesla Model 3",
            ev_battery_kwh=75.0,
            has_battery_storage=True,
            battery_capacity_kwh=13.5,
            heating_type="heat_pump",
            cooling_type="mini_split",
        ),
        preferences=Preferences(
            budget_priority="high",
            comfort_priority="medium",
            green_priority="high",
        ),
        household=Household(
            work_schedule="9-5 weekdays",
            occupants=4,
            typical_usage_pattern="evening_heavy",
        ),
        location=Location(
            lat=37.7749,
            lon=-122.4194,
            zip_code="94102",
            utility_provider="PG&E",
            rate_schedule="E-TOU-C",
        ),
    )


@pytest.fixture
def live_tools_config(tmp_path):
    """Create a config directory with tools in live mode (real API calls)."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    agents_yaml = config_dir / "agents.yaml"
    agents_yaml.write_text("""
advisor:
  model: llama3.2
  temperature: 0.7

analyzer:
  model: llama3.2
  temperature: 0.3
  recursion_limit: 10

memorizer:
  model: llama3.2
  temperature: 0.2
  confidence_threshold: 0.7
  turn_threshold: 10
  max_turns_before_summary: 20
""")

    tools_yaml = config_dir / "tools.yaml"
    tools_yaml.write_text("""
mode: live

weather:
  provider: openweathermap
  endpoint: https://api.openweathermap.org/data/2.5
  api_key_env: OPENWEATHER_API_KEY

rates:
  provider: nrel
  endpoint: https://developer.nrel.gov/api/utility_rates/v3
  api_key_env: NREL_API_KEY

solar:
  provider: nrel_pvwatts
  endpoint: https://developer.nrel.gov/api/pvwatts/v8
  api_key_env: NREL_API_KEY
""")

    return str(config_dir)


@pytest.fixture
def live_config(live_tools_config):
    """Set up config with live tools for API integration tests."""
    reset_config()
    import src.config as config_module
    config_module._config = AppConfig(config_dir=live_tools_config)
    yield config_module._config
    reset_config()
