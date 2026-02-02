"""Integration tests for LangGraphInstrumentor.

Tests:
- LangGraphInstrumentor captures LLM calls (inherited)
- LangGraphInstrumentor captures memory operations via store patching
- Unified trace contains both LLM and memory steps
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from context_forge.core.trace import (
    LLMCallStep,
    MemoryReadStep,
    MemoryWriteStep,
    ToolCallStep,
)
from context_forge.instrumentation import LangGraphInstrumentor

# Check if LangGraph is available
try:
    from langgraph.store.base import BaseStore
    from langgraph.store.memory import InMemoryStore

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

# Check if LangChain is available (needed for callback tests)
try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.messages import HumanMessage

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
class TestLangGraphInstrumentorStorePatching:
    """Tests for BaseStore method patching."""

    def test_instrumentor_patches_store_methods(self):
        """Instrumentor patches BaseStore methods when activated."""
        original_get = BaseStore.get
        original_put = BaseStore.put

        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        # Methods should be patched
        assert BaseStore.get is not original_get
        assert BaseStore.put is not original_put

        instrumentor.uninstrument()

        # Methods should be restored
        assert BaseStore.get is original_get
        assert BaseStore.put is original_put

    def test_store_get_captured(self):
        """Store.get() is captured as MemoryReadStep."""
        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        store = InMemoryStore()

        # Put something first
        store.put(("users",), "user123", {"name": "Alice"})

        # Get it back - this should be traced
        result = store.get(("users",), "user123")

        traces = instrumentor.get_traces()
        assert len(traces) == 1

        memory_reads = [s for s in traces[0].steps if isinstance(s, MemoryReadStep)]
        assert len(memory_reads) >= 1

        # Find the get operation (not the search from put)
        get_step = next(
            (s for s in memory_reads if s.query.get("key") == "user123"), None
        )
        assert get_step is not None
        assert get_step.query["namespace"] == ("users",)
        assert len(get_step.results) == 1

        instrumentor.uninstrument()

    def test_store_put_captured(self):
        """Store.put() is captured as MemoryWriteStep."""
        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        store = InMemoryStore()
        store.put(("profiles",), "profile1", {"email": "test@example.com"})

        traces = instrumentor.get_traces()
        assert len(traces) == 1

        memory_writes = [s for s in traces[0].steps if isinstance(s, MemoryWriteStep)]
        assert len(memory_writes) == 1

        write_step = memory_writes[0]
        assert write_step.entity_type == "profiles"
        assert write_step.operation == "add"
        assert write_step.entity_id == "profile1"
        assert write_step.data == {"email": "test@example.com"}

        instrumentor.uninstrument()

    def test_store_delete_captured(self):
        """Store.delete() is captured as MemoryWriteStep with operation=delete."""
        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        store = InMemoryStore()
        store.put(("cache",), "key1", {"value": "data"})
        store.delete(("cache",), "key1")

        traces = instrumentor.get_traces()
        memory_writes = [s for s in traces[0].steps if isinstance(s, MemoryWriteStep)]

        # Should have put and delete
        assert len(memory_writes) == 2

        delete_step = next(s for s in memory_writes if s.operation == "delete")
        assert delete_step.entity_type == "cache"
        assert delete_step.entity_id == "key1"

        instrumentor.uninstrument()

    def test_store_search_captured(self):
        """Store.search() is captured as MemoryReadStep."""
        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        store = InMemoryStore()
        store.put(("docs",), "doc1", {"title": "First"})
        store.put(("docs",), "doc2", {"title": "Second"})

        # Search for documents
        results = store.search(("docs",), limit=10)

        traces = instrumentor.get_traces()
        memory_reads = [s for s in traces[0].steps if isinstance(s, MemoryReadStep)]

        # Should have search operations
        search_steps = [s for s in memory_reads if "namespace_prefix" in str(s.query)]
        assert len(search_steps) >= 1

        instrumentor.uninstrument()


@pytest.mark.skipif(
    not (LANGGRAPH_AVAILABLE and LANGCHAIN_AVAILABLE),
    reason="LangGraph or LangChain not installed",
)
class TestLangGraphInstrumentorUnifiedTrace:
    """Tests for unified trace with LLM + memory operations."""

    def test_inherits_from_langchain_instrumentor(self):
        """LangGraphInstrumentor inherits from LangChainInstrumentor."""
        from context_forge.instrumentation import LangChainInstrumentor

        instrumentor = LangGraphInstrumentor()
        assert isinstance(instrumentor, LangChainInstrumentor)

    def test_callback_handler_captures_llm_calls(self):
        """Callback handler captures LLM calls (inherited behavior)."""
        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        handler = instrumentor.get_callback_handler()
        assert isinstance(handler, BaseCallbackHandler)

        # Simulate an LLM call
        run_id = uuid4()
        handler.on_chat_model_start(
            serialized={},
            messages=[[HumanMessage(content="Hello")]],
            run_id=run_id,
            parent_run_id=None,
        )

        mock_message = MagicMock()
        mock_message.content = "Hello! How can I help?"
        mock_generation = MagicMock()
        mock_generation.text = None
        mock_generation.message = mock_message
        mock_response = MagicMock()
        mock_response.generations = [[mock_generation]]
        mock_response.llm_output = {"model_name": "gpt-4"}

        handler.on_llm_end(
            response=mock_response,
            run_id=run_id,
            parent_run_id=None,
        )

        traces = instrumentor.get_traces()
        llm_steps = [s for s in traces[0].steps if isinstance(s, LLMCallStep)]
        assert len(llm_steps) == 1

        instrumentor.uninstrument()

    def test_unified_trace_has_both_llm_and_memory(self):
        """Single trace contains both LLM calls and memory operations."""
        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        # Get callback handler for LLM calls
        handler = instrumentor.get_callback_handler()

        # Create a store for memory operations
        store = InMemoryStore()

        # Simulate memory read (recall user profile)
        store.put(("users",), "user1", {"name": "Alice"})
        profile = store.get(("users",), "user1")

        # Simulate LLM call
        run_id = uuid4()
        handler.on_chat_model_start(
            serialized={},
            messages=[[HumanMessage(content="What's my name?")]],
            run_id=run_id,
            parent_run_id=None,
        )

        mock_message = MagicMock()
        mock_message.content = "Your name is Alice!"
        mock_generation = MagicMock()
        mock_generation.text = None
        mock_generation.message = mock_message
        mock_response = MagicMock()
        mock_response.generations = [[mock_generation]]
        mock_response.llm_output = {}

        handler.on_llm_end(
            response=mock_response,
            run_id=run_id,
            parent_run_id=None,
        )

        # Simulate memory write (update profile)
        store.put(("users",), "user1", {"name": "Alice", "last_query": "What's my name?"})

        # Get the unified trace
        traces = instrumentor.get_traces()
        assert len(traces) == 1

        trace = traces[0]

        # Should have LLM steps
        llm_steps = [s for s in trace.steps if isinstance(s, LLMCallStep)]
        assert len(llm_steps) == 1

        # Should have memory read steps
        read_steps = [s for s in trace.steps if isinstance(s, MemoryReadStep)]
        assert len(read_steps) >= 1

        # Should have memory write steps
        write_steps = [s for s in trace.steps if isinstance(s, MemoryWriteStep)]
        assert len(write_steps) >= 1

        instrumentor.uninstrument()

    def test_framework_property(self):
        """Framework property returns 'langgraph'."""
        instrumentor = LangGraphInstrumentor()
        assert instrumentor.framework == "langgraph"

    def test_framework_version_detected(self):
        """Framework version is detected from langgraph package."""
        instrumentor = LangGraphInstrumentor()
        version = instrumentor.framework_version
        assert version is not None
        assert isinstance(version, str)


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
class TestLangGraphInstrumentorContextManager:
    """Tests for context manager usage."""

    def test_context_manager_patches_and_unpatches(self):
        """Context manager properly patches and restores store methods."""
        original_get = BaseStore.get

        with LangGraphInstrumentor() as instrumentor:
            assert BaseStore.get is not original_get
            store = InMemoryStore()
            store.put(("test",), "key", {"data": "value"})

        assert BaseStore.get is original_get

    def test_context_manager_saves_traces(self):
        """Context manager saves traces when output_path configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LangGraphInstrumentor(output_path=tmpdir) as instrumentor:
                store = InMemoryStore()
                store.put(("test",), "key", {"data": "value"})

                # Simulate chain end to finalize trace
                handler = instrumentor.get_callback_handler()
                run_id = uuid4()
                handler.on_chain_start(
                    serialized={},
                    inputs={"input": "test"},
                    run_id=run_id,
                    parent_run_id=None,
                )
                handler.on_chain_end(
                    outputs={"output": "result"},
                    run_id=run_id,
                    parent_run_id=None,
                )

            # Traces should be saved
            trace_files = list(Path(tmpdir).glob("trace-*.json"))
            assert len(trace_files) >= 1

            with open(trace_files[0]) as f:
                data = json.load(f)

            # Should have memory write step
            memory_writes = [s for s in data["steps"] if s["step_type"] == "memory_write"]
            assert len(memory_writes) >= 1


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
class TestLangGraphInstrumentorAsync:
    """Tests for async store method patching."""

    @pytest.mark.asyncio
    async def test_async_store_get_captured(self):
        """Async store.aget() is captured."""
        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        store = InMemoryStore()
        await store.aput(("async_test",), "key1", {"value": "async_data"})
        result = await store.aget(("async_test",), "key1")

        traces = instrumentor.get_traces()
        memory_reads = [s for s in traces[0].steps if isinstance(s, MemoryReadStep)]
        assert len(memory_reads) >= 1

        instrumentor.uninstrument()

    @pytest.mark.asyncio
    async def test_async_store_put_captured(self):
        """Async store.aput() is captured."""
        instrumentor = LangGraphInstrumentor()
        instrumentor.instrument()

        store = InMemoryStore()
        await store.aput(("async_profiles",), "p1", {"name": "Bob"})

        traces = instrumentor.get_traces()
        memory_writes = [s for s in traces[0].steps if isinstance(s, MemoryWriteStep)]
        assert len(memory_writes) == 1
        assert memory_writes[0].entity_type == "async_profiles"

        instrumentor.uninstrument()
