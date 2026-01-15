#!/usr/bin/env python3
"""
Example 01: Simple Trace

This example shows the basic usage of the Tracer API to capture
an agent's trajectory.

Run: python examples/basic/01_simple_trace.py
"""

# NOTE: This is illustrative code. The context_forge package
# is not yet implemented. This shows the intended API.

from context_forge import Tracer


def main():
    """Demonstrate basic tracing of a simple agent interaction."""

    print("=== Simple Trace Example ===\n")

    # Create a trace using the context manager
    with Tracer.run(task="simple_qa", agent_name="demo-agent") as t:

        # Record user input
        t.user_input("What is 2 + 2?")

        # Simulate an LLM call
        # In real usage, you'd call your actual LLM here
        response = "2 + 2 equals 4."

        t.llm_call(
            model="gpt-4",
            output=response,
            usage={"input_tokens": 10, "output_tokens": 8, "total_tokens": 18}
        )

        # Record the final output
        t.final_output(response)

    # Access the completed trace
    trace = t.trace

    print(f"Trace ID: {trace.run_id}")
    print(f"Steps: {len(trace.steps)}")
    print(f"Outcome: {trace.outcome.status}")
    print(f"Total tokens: {trace.budgets.tokens_total}")

    print("\n=== Step Details ===")
    for step in trace.steps:
        print(f"  [{step.step_id}] {step.step_type.value}")

    print("\n=== Trace JSON (first 500 chars) ===")
    import json
    trace_json = json.dumps(trace.to_dict(), indent=2)
    print(trace_json[:500] + "...")


if __name__ == "__main__":
    main()
