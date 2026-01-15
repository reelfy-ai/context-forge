#!/usr/bin/env python3
"""
Example 02: Tool Call Tracing

This example shows how to trace an agent that uses tools.

Run: python examples/basic/02_tool_calls.py
"""

from context_forge import Tracer


def simulate_weather_api(city: str) -> dict:
    """Simulate a weather API call."""
    # In real usage, this would call an actual API
    return {"temp_c": 22, "condition": "sunny", "city": city}


def main():
    """Demonstrate tracing an agent with tool calls."""

    print("=== Tool Call Tracing Example ===\n")

    with Tracer.run(
        task="weather_query",
        agent_name="weather-bot",
        toolset=["weather_api", "geocode"]
    ) as t:

        # User asks about weather
        t.user_input("What's the weather in Paris?")

        # First LLM call - decides to use a tool
        t.llm_call(
            model="gpt-4",
            output="",
            tool_calls=[{"name": "weather_api", "args": {"city": "Paris"}}],
            finish_reason="tool_calls",
            usage={"input_tokens": 50, "output_tokens": 20, "total_tokens": 70}
        )

        # Execute the tool
        weather_result = simulate_weather_api("Paris")

        # Record the tool call
        tool_step_id = t.tool_call(
            tool="weather_api",
            args={"city": "Paris"},
            result=weather_result,
            latency_ms=150
        )
        print(f"Tool call recorded as step {tool_step_id}")

        # Second LLM call - generates response with tool result
        final_response = f"The weather in Paris is {weather_result['condition']}, {weather_result['temp_c']}°C."

        t.llm_call(
            model="gpt-4",
            output=final_response,
            finish_reason="stop",
            usage={"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}
        )

        t.final_output(final_response)

    # Inspect the trace
    trace = t.trace

    print(f"\nTrace ID: {trace.run_id}")
    print(f"Total steps: {len(trace.steps)}")
    print(f"Tool calls: {trace.budgets.tool_calls_total}")
    print(f"Total tokens: {trace.budgets.tokens_total}")

    print("\n=== Capabilities ===")
    for cap, enabled in trace.capabilities.items():
        if enabled:
            print(f"  ✓ {cap}")

    print("\n=== Step Sequence ===")
    for step in trace.steps:
        step_info = f"  [{step.step_id}] {step.step_type.value}"
        if step.step_type.value == "tool_call":
            step_info += f" -> {step.data.get('tool')}"
        print(step_info)


if __name__ == "__main__":
    main()
