"""Tool implementations for the Home Energy Advisor."""

from src.tools.rates import get_utility_rates
from src.tools.solar import get_solar_estimate
from src.tools.weather import get_weather_forecast


class ToolError(Exception):
    """Error raised when a tool call fails."""

    def __init__(self, tool_name: str, message: str, retry_after: int | None = None):
        self.tool_name = tool_name
        self.message = message
        self.retry_after = retry_after
        super().__init__(f"[{tool_name}] {message}")


def get_tool_list() -> list:
    """Return the list of @tool-decorated functions for create_agent."""
    return [get_weather_forecast, get_utility_rates, get_solar_estimate]


__all__ = ["get_tool_list", "get_weather_forecast", "get_utility_rates", "get_solar_estimate", "ToolError"]
