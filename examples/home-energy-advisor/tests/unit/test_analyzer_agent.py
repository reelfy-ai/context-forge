"""Tests for the Analyzer agent (create_agent-based tool calling)."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from src.agents.analyzer import build_analyzer, invoke_analyzer


@tool
def mock_get_weather(location: str) -> str:
    """Get weather forecast for a location."""
    return '{"temp_f": 72, "cloud_cover": 25, "solar_hours": 6.5}'


@tool
def mock_get_rates(utility: str, schedule: str) -> str:
    """Get utility rate schedule."""
    return '{"peak_rate": 0.49, "off_peak_rate": 0.30, "peak_hours": "16-21"}'


@tool
def mock_get_solar(lat: float, lon: float, capacity_kw: float) -> str:
    """Estimate solar production."""
    return '{"daily_kwh": 30.8, "solar_hours": 6.5}'


class TestAnalyzerBuild:
    """Tests for building the Analyzer agent."""

    def test_build_analyzer_returns_runnable(self):
        """build_analyzer returns a LangGraph Runnable."""
        from src.agents.analyzer import build_analyzer

        with patch("src.agents.analyzer.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.bind_tools = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            analyzer = build_analyzer(tools=[mock_get_weather, mock_get_rates])
            assert analyzer is not None
            assert hasattr(analyzer, "invoke")

    def test_build_analyzer_with_no_tools(self):
        """build_analyzer works with empty tool list."""
        from src.agents.analyzer import build_analyzer

        with patch("src.agents.analyzer.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.bind_tools = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            analyzer = build_analyzer(tools=[])
            assert analyzer is not None


class TestAnalyzerInvocation:
    """Tests for invoking the Analyzer agent."""

    @patch("src.agents.analyzer.create_agent")
    @patch("src.agents.analyzer.get_llm")
    def test_analyzer_processes_query(self, mock_get_llm, mock_create_agent):
        """Analyzer processes a query and returns messages with tool observations."""
        from src.agents.analyzer import invoke_analyzer

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Mock the compiled agent graph
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="How much solar will I produce today?"),
                AIMessage(content="Let me check the weather."),
                ToolMessage(content='{"temp_f": 72, "solar_hours": 6.5}', name="mock_get_weather", tool_call_id="call_1"),
                AIMessage(content="Based on weather data, solar production will be good today with 6.5 solar hours."),
            ]
        }
        mock_create_agent.return_value = mock_agent

        result = invoke_analyzer(
            query="How much solar will I produce today?",
            tools=[mock_get_weather],
            context={"location": {"zip_code": "94102"}},
        )

        assert "messages" in result
        assert "tool_observations" in result
        assert len(result["tool_observations"]) == 1
        assert result["tool_observations"][0]["tool"] == "mock_get_weather"

    @patch("src.agents.analyzer.create_agent")
    @patch("src.agents.analyzer.get_llm")
    def test_analyzer_no_tool_calls(self, mock_get_llm, mock_create_agent):
        """Analyzer can respond without calling any tools."""
        from src.agents.analyzer import invoke_analyzer

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="How do solar panels work?"),
                AIMessage(content="Solar panels generate electricity from sunlight."),
            ]
        }
        mock_create_agent.return_value = mock_agent

        result = invoke_analyzer(
            query="How do solar panels work?",
            tools=[mock_get_weather],
            context={},
        )

        assert result["tool_observations"] == []
        assert len(result["messages"]) == 2

    @patch("src.agents.analyzer.create_agent")
    @patch("src.agents.analyzer.get_llm")
    def test_analyzer_multiple_tool_calls(self, mock_get_llm, mock_create_agent):
        """Analyzer handles multiple tool calls in a session."""
        from src.agents.analyzer import invoke_analyzer

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="Optimize my EV charging"),
                AIMessage(content="I'll check weather and rates."),
                ToolMessage(content='{"solar_hours": 6.5}', name="mock_get_weather", tool_call_id="call_1"),
                ToolMessage(content='{"peak_rate": 0.49}', name="mock_get_rates", tool_call_id="call_2"),
                AIMessage(content="Based on both data sources, charge after 9 PM."),
            ]
        }
        mock_create_agent.return_value = mock_agent

        result = invoke_analyzer(
            query="Optimize my EV charging",
            tools=[mock_get_weather, mock_get_rates],
            context={},
        )

        assert len(result["tool_observations"]) == 2
        assert result["tool_observations"][0]["tool"] == "mock_get_weather"
        assert result["tool_observations"][1]["tool"] == "mock_get_rates"
