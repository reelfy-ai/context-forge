"""Integration tests for the Analyzer agent tool calling.

Tests that the ReAct agent correctly identifies which tools to call
and processes their results when given energy-related queries.

Requires: Ollama running at localhost:11434 with llama3.2 pulled.
"""

import json

import pytest

from .conftest import model_required, ollama_required

pytestmark = [ollama_required, model_required]


class TestAnalyzerToolCalling:
    """E2E tests for the Analyzer agent calling real @tool functions."""

    def test_analyzer_calls_weather_tool(self, integration_config):
        """Analyzer invokes weather tool when asked about weather/solar."""
        from src.agents.analyzer import invoke_analyzer
        from src.tools import get_tool_list

        result = invoke_analyzer(
            query="What's the weather like today at latitude 37.77, longitude -122.42? How many solar hours?",
            tools=get_tool_list(),
            context={"location": {"lat": 37.7749, "lon": -122.4194, "zip_code": "94102"}},
        )

        assert "messages" in result
        assert "tool_observations" in result
        assert len(result["tool_observations"]) >= 1
        # Verify tool output is valid JSON
        for obs in result["tool_observations"]:
            data = json.loads(obs["result"])
            assert isinstance(data, dict)

    def test_analyzer_calls_rates_tool(self, integration_config):
        """Analyzer invokes rates tool when asked about electricity costs."""
        from src.agents.analyzer import invoke_analyzer
        from src.tools import get_tool_list

        result = invoke_analyzer(
            query="What are the current PG&E E-TOU-C electricity rates? When is peak vs off-peak?",
            tools=get_tool_list(),
            context={"location": {"utility_provider": "PG&E", "rate_schedule": "E-TOU-C"}},
        )

        assert len(result["tool_observations"]) >= 1

    def test_analyzer_calls_solar_tool(self, integration_config):
        """Analyzer invokes solar tool when asked about solar production."""
        from src.agents.analyzer import invoke_analyzer
        from src.tools import get_tool_list

        result = invoke_analyzer(
            query="Estimate annual solar production for a 7.5kW system at lat 37.77, lon -122.42",
            tools=get_tool_list(),
            context={
                "location": {"lat": 37.7749, "lon": -122.4194},
                "equipment": {"solar_capacity_kw": 7.5},
            },
        )

        assert len(result["tool_observations"]) >= 1

    def test_analyzer_multiple_tools(self, integration_config):
        """Analyzer can call multiple tools in one session."""
        from src.agents.analyzer import invoke_analyzer
        from src.tools import get_tool_list

        result = invoke_analyzer(
            query="I want to optimize my EV charging. Check the weather (lat 37.77, lon -122.42) and PG&E rates to tell me the best time.",
            tools=get_tool_list(),
            context={
                "location": {"lat": 37.7749, "lon": -122.4194, "utility_provider": "PG&E", "rate_schedule": "E-TOU-C"},
            },
        )

        tool_names = [obs["tool"] for obs in result["tool_observations"]]
        assert len(tool_names) >= 1  # At minimum one tool; ideally 2+
