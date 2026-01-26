"""CLI entry point for the Home Energy Advisor agent."""

import argparse
import json
import sys
import uuid

from src.agents.advisor import build_advisor_graph
from src.config import get_config


def run_query(query: str, user_id: str, trace: bool = False, output: str | None = None) -> str:
    """Run a single query through the advisor agent.

    Args:
        query: The user's energy question.
        user_id: User identifier for profile loading.
        trace: Whether to capture trace data.
        output: File path to write trace output.

    Returns:
        The agent's response text.
    """
    session_id = str(uuid.uuid4())
    graph = build_advisor_graph()

    result = graph.invoke({
        "user_id": user_id,
        "session_id": session_id,
        "message": query,
        "messages": [],
        "turn_count": 0,
        "user_profile": None,
        "weather_data": None,
        "rate_data": None,
        "solar_estimate": None,
        "retrieved_docs": [],
        "tool_observations": [],
        "response": None,
        "extracted_facts": [],
        "should_memorize": False,
    })

    response = result.get("response", "No response generated.")

    if trace and output:
        trace_data = {
            "session_id": session_id,
            "user_id": user_id,
            "query": query,
            "response": response,
            "tool_observations": result.get("tool_observations", []),
            "turn_count": result.get("turn_count", 0),
        }
        with open(output, "w") as f:
            json.dump(trace_data, f, indent=2, default=str)

    return response


def interactive_mode(user_id: str):
    """Run the advisor in interactive mode with a conversation loop."""
    print("Home Energy Advisor (type 'quit' or 'exit' to stop)")
    print("-" * 50)

    graph = build_advisor_graph()
    session_id = str(uuid.uuid4())
    messages = []
    turn_count = 0

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        turn_count += 1
        result = graph.invoke({
            "user_id": user_id,
            "session_id": session_id,
            "message": user_input,
            "messages": messages,
            "turn_count": turn_count - 1,
            "user_profile": None,
            "weather_data": None,
            "rate_data": None,
            "solar_estimate": None,
            "retrieved_docs": [],
            "tool_observations": [],
            "response": None,
            "extracted_facts": [],
            "should_memorize": False,
        })

        response = result.get("response", "I couldn't generate a response.")
        messages = result.get("messages", [])
        turn_count = result.get("turn_count", turn_count)

        print(f"\nAdvisor: {response}")


def main():
    """Parse arguments and run the advisor."""
    parser = argparse.ArgumentParser(description="Home Energy Advisor Agent")
    parser.add_argument("--query", "-q", type=str, help="Single query to process")
    parser.add_argument("--user-id", "-u", type=str, default="default_user", help="User ID for profile")
    parser.add_argument("--trace", action="store_true", help="Enable trace capture")
    parser.add_argument("--output", "-o", type=str, help="Output file for trace data")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")

    args = parser.parse_args()

    if args.query:
        response = run_query(args.query, args.user_id, args.trace, args.output)
        print(response)
    elif args.interactive:
        interactive_mode(args.user_id)
    else:
        # Default to interactive mode
        interactive_mode(args.user_id)


if __name__ == "__main__":
    main()
