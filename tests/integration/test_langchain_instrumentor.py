"""Integration tests for LangChainInstrumentor.

Tests T030, T032, T032a:
- LangChainInstrumentor with actual LangChain components
- Multiple instrumentors (FR-009a)
- Context manager auto-uninstrument
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from context_forge.core.trace import LLMCallStep, ToolCallStep, UserInputStep, FinalOutputStep
from context_forge.instrumentation import LangChainInstrumentor

# Check if LangChain is available
try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.outputs import LLMResult, Generation, ChatGeneration
    from langchain_core.tools import tool

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestLangChainInstrumentorIntegration:
    """Integration tests for LangChainInstrumentor (T030)."""

    def test_instrumentor_inherits_from_base_callback_handler(self):
        """Callback handler inherits from LangChain BaseCallbackHandler."""
        instrumentor = LangChainInstrumentor()
        instrumentor.instrument()

        handler = instrumentor.get_callback_handler()
        assert isinstance(handler, BaseCallbackHandler)

        instrumentor.uninstrument()

    def test_callback_handler_captures_llm_call(self):
        """Callback handler captures LLM calls."""
        instrumentor = LangChainInstrumentor()
        instrumentor.instrument()

        handler = instrumentor.get_callback_handler()
        run_id = uuid4()

        # Simulate LLM start
        handler.on_chat_model_start(
            serialized={},
            messages=[[HumanMessage(content="Hello")]],
            run_id=run_id,
            parent_run_id=None,
        )

        # Create mock LLM response
        mock_message = MagicMock()
        mock_message.content = "Hello! How can I help?"
        mock_message.usage_metadata = MagicMock()
        mock_message.usage_metadata.input_tokens = 10
        mock_message.usage_metadata.output_tokens = 8
        mock_message.usage_metadata.total_tokens = 18

        mock_generation = MagicMock()
        mock_generation.text = None
        mock_generation.message = mock_message

        mock_response = MagicMock()
        mock_response.generations = [[mock_generation]]
        mock_response.llm_output = {"model_name": "gpt-4"}

        # Simulate LLM end
        handler.on_llm_end(
            response=mock_response,
            run_id=run_id,
            parent_run_id=None,
        )

        traces = instrumentor.get_traces()
        assert len(traces) == 1

        llm_steps = [s for s in traces[0].steps if isinstance(s, LLMCallStep)]
        assert len(llm_steps) == 1

        llm_step = llm_steps[0]
        assert llm_step.model == "gpt-4"
        assert llm_step.output == "Hello! How can I help?"
        assert llm_step.tokens_in == 10
        assert llm_step.tokens_out == 8
        assert llm_step.tokens_total == 18

        instrumentor.uninstrument()

    def test_callback_handler_captures_tool_call(self):
        """Callback handler captures tool calls."""
        instrumentor = LangChainInstrumentor()
        instrumentor.instrument()

        handler = instrumentor.get_callback_handler()
        run_id = uuid4()

        # Simulate tool start
        handler.on_tool_start(
            serialized={"name": "calculator"},
            input_str="2+2",
            run_id=run_id,
            parent_run_id=None,
            inputs={"expression": "2+2"},
        )

        # Simulate tool end
        handler.on_tool_end(
            output="4",
            run_id=run_id,
            parent_run_id=None,
            name="calculator",
        )

        traces = instrumentor.get_traces()
        assert len(traces) == 1

        tool_steps = [s for s in traces[0].steps if isinstance(s, ToolCallStep)]
        assert len(tool_steps) == 1

        tool_step = tool_steps[0]
        assert tool_step.tool_name == "calculator"
        assert tool_step.arguments == {"expression": "2+2"}
        assert tool_step.result == "4"
        assert tool_step.success is True

        instrumentor.uninstrument()

    def test_callback_handler_captures_chain_flow(self):
        """Callback handler captures chain start/end as user input/final output."""
        instrumentor = LangChainInstrumentor()
        instrumentor.instrument()

        handler = instrumentor.get_callback_handler()
        chain_run_id = uuid4()
        llm_run_id = uuid4()

        # Simulate chain start (top-level)
        handler.on_chain_start(
            serialized={},
            inputs={"input": "What is 2+2?"},
            run_id=chain_run_id,
            parent_run_id=None,
        )

        # Simulate nested LLM call
        handler.on_chat_model_start(
            serialized={},
            messages=[[HumanMessage(content="What is 2+2?")]],
            run_id=llm_run_id,
            parent_run_id=chain_run_id,
        )

        mock_message = MagicMock()
        mock_message.content = "2+2 equals 4"

        mock_generation = MagicMock()
        mock_generation.text = None
        mock_generation.message = mock_message

        mock_response = MagicMock()
        mock_response.generations = [[mock_generation]]
        mock_response.llm_output = {}

        handler.on_llm_end(
            response=mock_response,
            run_id=llm_run_id,
            parent_run_id=chain_run_id,
        )

        # Simulate chain end
        handler.on_chain_end(
            outputs={"output": "The answer is 4"},
            run_id=chain_run_id,
            parent_run_id=None,
        )

        # Trace should be finalized
        traces = instrumentor.get_traces()
        assert len(traces) == 1

        trace = traces[0]
        user_inputs = [s for s in trace.steps if isinstance(s, UserInputStep)]
        final_outputs = [s for s in trace.steps if isinstance(s, FinalOutputStep)]

        assert len(user_inputs) == 1
        assert user_inputs[0].content == "What is 2+2?"

        assert len(final_outputs) == 1
        assert final_outputs[0].content == "The answer is 4"

        instrumentor.uninstrument()

    def test_callback_handler_captures_tool_error(self):
        """Callback handler captures failed tool calls."""
        instrumentor = LangChainInstrumentor()
        instrumentor.instrument()

        handler = instrumentor.get_callback_handler()
        run_id = uuid4()

        # Simulate tool start
        handler.on_tool_start(
            serialized={"name": "api_call"},
            input_str="url=https://example.com",
            run_id=run_id,
            parent_run_id=None,
        )

        # Simulate tool error
        handler.on_tool_error(
            error=ConnectionError("Connection timeout"),
            run_id=run_id,
            parent_run_id=None,
            name="api_call",
        )

        traces = instrumentor.get_traces()
        tool_steps = [s for s in traces[0].steps if isinstance(s, ToolCallStep)]

        assert len(tool_steps) == 1
        assert tool_steps[0].success is False
        assert "Connection timeout" in tool_steps[0].error

        instrumentor.uninstrument()


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestContextManagerAutoUninstrument:
    """Tests for context manager auto-uninstrument (T032a)."""

    def test_context_manager_activates_and_deactivates(self):
        """Context manager properly activates and deactivates instrumentor."""
        with LangChainInstrumentor() as instrumentor:
            assert instrumentor.is_active is True
            handler = instrumentor.get_callback_handler()
            assert handler is not None

        assert instrumentor.is_active is False

    def test_context_manager_saves_traces_on_exit(self):
        """Context manager saves traces when output_path is configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with LangChainInstrumentor(output_path=tmpdir) as instrumentor:
                handler = instrumentor.get_callback_handler()
                run_id = uuid4()

                # Simulate a simple chain
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

            # After exit, traces should be saved
            trace_files = list(Path(tmpdir).glob("trace-*.json"))
            assert len(trace_files) == 1

            with open(trace_files[0]) as f:
                data = json.load(f)
            assert "steps" in data
            assert len(data["steps"]) >= 1

    def test_context_manager_handles_exception(self):
        """Context manager properly uninstruments even on exception."""
        instrumentor = LangChainInstrumentor()

        with pytest.raises(ValueError):
            with instrumentor:
                assert instrumentor.is_active is True
                raise ValueError("Test error")

        assert instrumentor.is_active is False

    def test_multiple_context_managers_sequential(self):
        """Multiple context managers can be used sequentially."""
        with LangChainInstrumentor() as inst1:
            handler1 = inst1.get_callback_handler()
            run_id = uuid4()
            handler1.on_chain_start(
                serialized={},
                inputs={"input": "first"},
                run_id=run_id,
                parent_run_id=None,
            )
            handler1.on_chain_end(
                outputs={"output": "first result"},
                run_id=run_id,
                parent_run_id=None,
            )
            traces1 = inst1.get_traces()

        with LangChainInstrumentor() as inst2:
            handler2 = inst2.get_callback_handler()
            run_id = uuid4()
            handler2.on_chain_start(
                serialized={},
                inputs={"input": "second"},
                run_id=run_id,
                parent_run_id=None,
            )
            handler2.on_chain_end(
                outputs={"output": "second result"},
                run_id=run_id,
                parent_run_id=None,
            )
            traces2 = inst2.get_traces()

        assert len(traces1) == 1
        assert len(traces2) == 1
        # They should be different traces
        assert traces1[0].run_id != traces2[0].run_id


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestMultipleInstrumentors:
    """Tests for multiple instrumentors (T032)."""

    def test_multiple_instrumentors_raise_error(self):
        """Calling instrument() twice on same instrumentor raises error."""
        from context_forge.exceptions import InstrumentorAlreadyActiveError

        instrumentor = LangChainInstrumentor()
        instrumentor.instrument()

        with pytest.raises(InstrumentorAlreadyActiveError):
            instrumentor.instrument()

        instrumentor.uninstrument()

    def test_separate_instrumentors_independent(self):
        """Different instrumentor instances are independent."""
        inst1 = LangChainInstrumentor(agent_name="agent1")
        inst2 = LangChainInstrumentor(agent_name="agent2")

        inst1.instrument()
        inst2.instrument()

        handler1 = inst1.get_callback_handler()
        handler2 = inst2.get_callback_handler()

        # Record to handler1 only
        run_id = uuid4()
        handler1.on_chain_start(
            serialized={},
            inputs={"input": "test"},
            run_id=run_id,
            parent_run_id=None,
        )
        handler1.on_chain_end(
            outputs={"output": "result"},
            run_id=run_id,
            parent_run_id=None,
        )

        # inst1 should have traces, inst2 should not
        traces1 = inst1.get_traces()
        traces2 = inst2.get_traces()

        assert len(traces1) == 1
        assert len(traces2) == 0

        inst1.uninstrument()
        inst2.uninstrument()


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestFrameworkVersionDetection:
    """Tests for framework version detection."""

    def test_framework_name(self):
        """Instrumentor reports correct framework name."""
        instrumentor = LangChainInstrumentor()
        assert instrumentor.framework == "langchain"

    def test_framework_version_detected(self):
        """Instrumentor detects LangChain version."""
        instrumentor = LangChainInstrumentor()
        version = instrumentor.framework_version
        # Version should be a string like "0.3.0" or similar
        assert version is not None
        assert isinstance(version, str)
        assert "." in version  # Version contains dots

    def test_agent_info_in_trace(self):
        """Agent info includes framework details in trace."""
        instrumentor = LangChainInstrumentor(
            agent_name="test-agent",
            agent_version="1.0.0",
        )
        instrumentor.instrument()

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

        traces = instrumentor.get_traces()
        assert len(traces) == 1

        agent_info = traces[0].agent_info
        assert agent_info.name == "test-agent"
        assert agent_info.version == "1.0.0"
        assert agent_info.framework == "langchain"
        assert agent_info.framework_version is not None

        instrumentor.uninstrument()
