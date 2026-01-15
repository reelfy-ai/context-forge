#!/usr/bin/env python3
"""
Example 03: Multi-Agent Tracing

This example shows how to trace a multi-agent system where
different agents (actors) collaborate on a task.

Run: python examples/basic/03_multi_agent.py
"""

from context_forge import Tracer


def main():
    """Demonstrate tracing a multi-agent system."""

    print("=== Multi-Agent Tracing Example ===\n")

    with Tracer.run(
        task="flight_booking",
        agent_name="travel-assistant"
    ) as t:

        # User request
        t.user_input("Book me a flight to Paris next week")

        # Planner agent decides the approach
        t.llm_call(
            model="gpt-4",
            output="I'll search for flights and find the best option.",
            actor="planner",  # Specify which agent is acting
            usage={"input_tokens": 80, "output_tokens": 25, "total_tokens": 105}
        )

        # Executor agent performs the search
        t.tool_call(
            tool="flight_search",
            args={"destination": "Paris", "date_range": "next_week"},
            result={
                "flights": [
                    {"id": "FL123", "price": 450, "airline": "Air France"},
                    {"id": "FL456", "price": 380, "airline": "Delta"},
                ]
            },
            actor="executor",  # Different agent
            latency_ms=500
        )

        # Planner reviews results
        t.llm_call(
            model="gpt-4",
            output="Found 2 flights. The Delta flight at $380 is the best value.",
            actor="planner",
            usage={"input_tokens": 150, "output_tokens": 40, "total_tokens": 190}
        )

        # Executor books the flight
        t.tool_call(
            tool="book_flight",
            args={"flight_id": "FL456"},
            result={"confirmation": "CONF789", "status": "booked"},
            actor="executor",
            latency_ms=800
        )

        # Final response
        t.llm_call(
            model="gpt-4",
            output="I've booked your Delta flight to Paris for $380. Confirmation: CONF789",
            actor="planner",
            usage={"input_tokens": 100, "output_tokens": 30, "total_tokens": 130}
        )

        t.final_output("Flight booked! Confirmation: CONF789")

    trace = t.trace

    print(f"Trace ID: {trace.run_id}")
    print(f"Multi-agent: {trace.capabilities.get('multi_agent')}")

    print("\n=== Agent Activity ===")
    agent_steps = {}
    for step in trace.steps:
        actor = step.actor or "system"
        if actor not in agent_steps:
            agent_steps[actor] = []
        agent_steps[actor].append(step.step_type.value)

    for actor, steps in agent_steps.items():
        print(f"  {actor}: {len(steps)} steps - {steps}")

    print("\n=== Full Step Sequence ===")
    for step in trace.steps:
        actor = step.actor or "system"
        print(f"  [{step.step_id}] ({actor}) {step.step_type.value}")


if __name__ == "__main__":
    main()
