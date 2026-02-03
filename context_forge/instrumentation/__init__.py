"""Instrumentation module for ContextForge.

This module provides multiple levels of trace capture:
- Level 2: Auto-instrumentation via Instrumentor().instrument()
- Level 3: Callback handlers for per-call control
- Level 4: Explicit Tracer API for custom agents
"""

from context_forge.instrumentation.base import (
    BaseInstrumentor,
    RedactionConfig,
)
from context_forge.instrumentation.instrumentors.langchain import LangChainInstrumentor
from context_forge.instrumentation.instrumentors.langgraph import LangGraphInstrumentor

__all__ = [
    # Base classes
    "BaseInstrumentor",
    "RedactionConfig",
    # Framework instrumentors
    "LangChainInstrumentor",
    "LangGraphInstrumentor",
]
