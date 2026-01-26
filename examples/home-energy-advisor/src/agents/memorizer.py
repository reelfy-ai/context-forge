"""Memorizer agent: learning subgraph for fact extraction and profile updates."""

from langgraph.graph import END, StateGraph

from src.core.state import MemorizerState
from src.nodes.memorize_apply import memorize_apply_node
from src.nodes.memorize_extract import memorize_extract_node
from src.nodes.memorize_summarize import memorize_summarize_node


def build_memorizer_graph() -> StateGraph:
    """Build the Memorizer learning subgraph.

    Flow: Extract → Apply → Summarize → END

    - Extract: LLM analyzes conversation for new user facts
    - Apply: Filters by confidence, updates profile, refreshes timestamps
    - Summarize: Compresses old turns into ProfileNote
    """
    graph = StateGraph(MemorizerState)

    graph.add_node("extract", memorize_extract_node)
    graph.add_node("apply", memorize_apply_node)
    graph.add_node("summarize", memorize_summarize_node)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "apply")
    graph.add_edge("apply", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()
