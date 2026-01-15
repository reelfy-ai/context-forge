#!/usr/bin/env python3
"""
Example: Budget Grader

This example shows how to use the BudgetGrader to enforce
token and tool call limits on agent traces.

Run: python examples/graders/budget_grader.py
"""

from context_forge import Tracer
from context_forge.graders import BudgetGrader, GraderResult


def create_sample_trace():
    """Create a sample trace to evaluate."""
    with Tracer.run(task="sample_task") as t:
        t.user_input("Do something")

        # Simulate multiple LLM calls with varying token usage
        for i in range(3):
            t.llm_call(
                model="gpt-4",
                output=f"Response {i}",
                usage={
                    "input_tokens": 100 + (i * 50),
                    "output_tokens": 50 + (i * 20),
                    "total_tokens": 150 + (i * 70)
                }
            )

        # Simulate tool calls
        for i in range(5):
            t.tool_call(
                tool="some_tool",
                args={"param": i},
                result={"success": True}
            )

        t.final_output("Done!")

    return t.trace


def main():
    """Demonstrate budget grader usage."""

    print("=== Budget Grader Example ===\n")

    # Create a sample trace
    trace = create_sample_trace()

    print(f"Trace summary:")
    print(f"  Total tokens: {trace.budgets.tokens_total}")
    print(f"  Tool calls: {trace.budgets.tool_calls_total}")

    # Test 1: Grader with generous limits (should pass)
    print("\n--- Test 1: Generous limits ---")
    grader1 = BudgetGrader(config={
        "max_tokens": 10000,
        "max_tool_calls": 20
    })

    result1: GraderResult = grader1(trace)

    print(f"Passed: {result1.passed}")
    print(f"Score: {result1.score}")
    print(f"Summary: {result1.summary}")

    # Test 2: Grader with strict limits (should fail)
    print("\n--- Test 2: Strict limits ---")
    grader2 = BudgetGrader(config={
        "max_tokens": 200,
        "max_tool_calls": 3
    })

    result2: GraderResult = grader2(trace)

    print(f"Passed: {result2.passed}")
    print(f"Score: {result2.score}")
    print(f"Summary: {result2.summary}")

    # Show evidence for the failed case
    if not result2.passed:
        print("\nEvidence:")
        for evidence in result2.evidence:
            print(f"  - {evidence.description}")
            if evidence.data:
                print(f"    Data: {evidence.data}")

    # Test 3: Custom score components
    print("\n--- Test 3: Score breakdown ---")
    grader3 = BudgetGrader(config={
        "max_tokens": 500,  # Will exceed
        "max_tool_calls": 10  # Will pass
    })

    result3: GraderResult = grader3(trace)

    print(f"Overall passed: {result3.passed}")
    print(f"Overall score: {result3.score}")
    print(f"Sub-scores:")
    for name, score in result3.scores.items():
        status = "✓" if score >= 0.5 else "✗"
        print(f"  {status} {name}: {score}")


if __name__ == "__main__":
    main()
