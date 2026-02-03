"""Simple evaluation API for ContextForge.

This module provides high-level functions for common evaluation patterns,
hiding the complexity of instrumentors, adapters, and graders.

Two usage levels:

Level 2 (Simple): Single-turn evaluation with minimal setup
    from context_forge.evaluation import evaluate_agent

    result = evaluate_agent(
        graph=my_graph,
        message="I work from home now",
        store=my_store,
    )
    result.print_report()

Level 3 (Simulation): Multi-turn with personas and scenarios
    from context_forge import SimulationRunner, LangGraphAdapter, Persona
    # ... full control over simulation
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from context_forge.core.trace import TraceRun
from context_forge.graders import GraderResult, HybridMemoryHygieneGrader
from context_forge.graders.base import Evidence
from context_forge.instrumentation import LangGraphInstrumentor


@dataclass
class EvaluationResult:
    """Result from a simple evaluation run.

    Combines the agent's response with grader results for easy inspection.

    Attributes:
        response: The agent's final response
        trace: The captured trace (for debugging)
        grader_results: Results from each grader that was run
        passed: True if all graders passed
    """
    response: Any
    trace: TraceRun
    grader_results: list[GraderResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all graders passed."""
        return all(r.passed for r in self.grader_results)

    @property
    def score(self) -> float:
        """Average score across all graders."""
        if not self.grader_results:
            return 1.0
        return sum(r.score for r in self.grader_results) / len(self.grader_results)

    @property
    def errors(self) -> list[Evidence]:
        """All errors from all graders."""
        errors = []
        for r in self.grader_results:
            errors.extend(r.errors)
        return errors

    def print_report(self, verbose: bool = False) -> None:
        """Print a combined report of all grader results."""
        print("\n" + "=" * 60)
        print("EVALUATION REPORT")
        print("=" * 60)

        status = "PASSED" if self.passed else "FAILED"
        print(f"\nOverall: {status} (score: {self.score:.2f})")
        print(f"Response: {str(self.response)[:100]}...")

        for result in self.grader_results:
            result.print_report(verbose=verbose)


def evaluate_agent(
    graph,
    message: str,
    store=None,
    user_id: str = "eval_user",
    session_id: str = "eval_session",
    graders: Optional[list[str]] = None,
    llm_model: str = "llama3.2",
    print_result: bool = True,
) -> EvaluationResult:
    """Evaluate a LangGraph agent with a single message.

    This is the simplest way to evaluate your agent. It:
    1. Instruments the agent to capture traces
    2. Runs your message through the agent
    3. Grades the trace with specified graders
    4. Returns a combined result

    Args:
        graph: Your compiled LangGraph graph
        message: The user message to send
        store: Optional LangGraph store (for memory operations)
        user_id: User ID for the session
        session_id: Session ID for the conversation
        graders: List of grader names to run. Default: ["memory_hygiene"]
                 Available: "memory_hygiene", "memory_corruption"
        llm_model: Ollama model for LLM-based graders
        print_result: Whether to print the report automatically

    Returns:
        EvaluationResult with response, trace, and grader results

    Example:
        from context_forge.evaluation import evaluate_agent
        from langgraph.store.memory import InMemoryStore
        from my_agent import build_graph

        store = InMemoryStore()
        # ... populate store with user profile ...

        graph = build_graph(store=store)
        result = evaluate_agent(
            graph=graph,
            message="I switched to working from home",
            store=store,
        )

        if not result.passed:
            print("Agent failed evaluation!")
            for error in result.errors:
                print(f"  - {error.description}")
    """
    graders = graders or ["memory_hygiene"]

    # Set up instrumentation
    instrumentor = LangGraphInstrumentor(
        agent_name="evaluated_agent",
        agent_version="1.0.0",
    )
    instrumentor.instrument()

    try:
        # Build initial state
        initial_state = {
            "user_id": user_id,
            "session_id": session_id,
            "message": message,
            "messages": [],
            "turn_count": 0,
            "user_profile": None,  # Will be loaded from store
            "response": None,
        }

        # Add store config if provided
        config = {}
        if store is not None:
            config["configurable"] = {"store": store}

        # Run the agent
        result = graph.invoke(initial_state, config=config)
        response = result.get("response", result)

        # Get the trace
        traces = instrumentor.get_traces()
        if not traces:
            raise RuntimeError("No trace captured. Is the graph using LangChain components?")
        trace = traces[0]

        # Run graders
        grader_results = []
        for grader_name in graders:
            grader_result = _run_grader(grader_name, trace, llm_model)
            grader_results.append(grader_result)

        # Build result
        eval_result = EvaluationResult(
            response=response,
            trace=trace,
            grader_results=grader_results,
        )

        if print_result:
            eval_result.print_report()

        return eval_result

    finally:
        instrumentor.uninstrument()


def evaluate_trace(
    trace: TraceRun,
    graders: Optional[list[str]] = None,
    llm_model: str = "llama3.2",
    print_result: bool = True,
) -> EvaluationResult:
    """Evaluate an existing trace.

    Use this when you already have a trace (e.g., loaded from a file)
    and just want to run graders on it.

    Args:
        trace: The trace to evaluate
        graders: List of grader names to run
        llm_model: Ollama model for LLM-based graders
        print_result: Whether to print the report automatically

    Returns:
        EvaluationResult with grader results

    Example:
        from context_forge.evaluation import evaluate_trace
        from context_forge import TraceRun
        import json

        with open("my_trace.json") as f:
            trace = TraceRun.model_validate(json.load(f))

        result = evaluate_trace(trace)
    """
    graders = graders or ["memory_hygiene"]

    grader_results = []
    for grader_name in graders:
        grader_result = _run_grader(grader_name, trace, llm_model)
        grader_results.append(grader_result)

    eval_result = EvaluationResult(
        response=None,
        trace=trace,
        grader_results=grader_results,
    )

    if print_result:
        eval_result.print_report()

    return eval_result


def _run_grader(grader_name: str, trace: TraceRun, llm_model: str) -> GraderResult:
    """Run a grader by name."""
    from context_forge.graders import MemoryCorruptionGrader
    from context_forge.graders.judges.backends import OllamaBackend

    if grader_name == "memory_hygiene":
        # Check if Ollama is available
        try:
            backend = OllamaBackend(model=llm_model)
            if backend.is_available():
                grader = HybridMemoryHygieneGrader(llm_backend=backend)
            else:
                # Fall back to deterministic only
                grader = HybridMemoryHygieneGrader()
        except Exception:
            grader = HybridMemoryHygieneGrader()
        return grader.grade(trace)

    elif grader_name == "memory_corruption":
        grader = MemoryCorruptionGrader()
        return grader.grade(trace)

    else:
        raise ValueError(
            f"Unknown grader: {grader_name}. "
            f"Available: memory_hygiene, memory_corruption"
        )
