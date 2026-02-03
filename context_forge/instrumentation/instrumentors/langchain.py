"""LangChain instrumentor for ContextForge.

This module implements:
- T039: LangChainInstrumentor
- T040: LangChain callback hooks for LLM, Tool, Retriever
- T041: Token usage capture from LangChain callbacks
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Sequence
from uuid import UUID

from context_forge.core.trace import (
    FinalOutputStep,
    LLMCallStep,
    RetrievalStep,
    ToolCallStep,
    UserInputStep,
)
from context_forge.core.types import RetrievalResult
from context_forge.instrumentation.base import BaseInstrumentor, RedactionConfig

logger = logging.getLogger(__name__)

# Try to import LangChain's BaseCallbackHandler for proper inheritance
try:
    from langchain_core.callbacks import BaseCallbackHandler

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    BaseCallbackHandler = object  # type: ignore
    _LANGCHAIN_AVAILABLE = False

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler


class LangChainInstrumentor(BaseInstrumentor):
    """Auto-instrumentor for LangChain/LangGraph agents.

    Provides one-line instrumentation for LangChain-based agents
    by installing a global callback handler.

    Usage:
        LangChainInstrumentor().instrument()
        # ... your LangChain code runs normally ...
        # All LLM calls, tool calls, and retrievals are captured

    Or with context manager:
        with LangChainInstrumentor(output_path="./traces") as instrumentor:
            chain.invoke({"input": "hello"})
        # Traces saved automatically
    """

    def __init__(
        self,
        agent_name: str = "langchain_agent",
        agent_version: Optional[str] = None,
        output_path: Optional[str | Path] = None,
        redaction_config: Optional[RedactionConfig] = None,
    ):
        super().__init__(
            agent_name=agent_name,
            agent_version=agent_version,
            output_path=output_path,
            redaction_config=redaction_config,
        )
        self._handler: Optional["ContextForgeCallbackHandler"] = None
        self._original_handlers: list[Any] = []
        self._framework_version: Optional[str] = None

    @property
    def framework(self) -> str:
        return "langchain"

    @property
    def framework_version(self) -> Optional[str]:
        if self._framework_version is None:
            try:
                import langchain_core

                self._framework_version = getattr(langchain_core, "__version__", None)
            except ImportError:
                pass
        return self._framework_version

    def _install_hooks(self) -> None:
        """Install LangChain callback handler globally."""
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is required for LangChainInstrumentor. "
                "Install it with: pip install langchain-core"
            )

        # Create our callback handler
        self._handler = ContextForgeCallbackHandler(instrumentor=self)
        logger.debug("LangChain instrumentor handler ready")

    def _remove_hooks(self) -> None:
        """Remove LangChain callback handler."""
        self._handler = None

    def get_callback_handler(self) -> "ContextForgeCallbackHandler":
        """Get the callback handler for explicit use.

        Useful when you want to pass the handler explicitly:
            handler = instrumentor.get_callback_handler()
            chain.invoke(input, config={"callbacks": [handler]})

        Returns:
            The ContextForgeCallbackHandler instance
        """
        if self._handler is None:
            if not _LANGCHAIN_AVAILABLE:
                raise ImportError(
                    "LangChain is required for LangChainInstrumentor. "
                    "Install it with: pip install langchain-core"
                )
            self._handler = ContextForgeCallbackHandler(instrumentor=self)
        return self._handler


class ContextForgeCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """LangChain callback handler that captures trace events.

    Implements LangChain's callback interface to capture LLM calls,
    tool executions, and retrieval operations.

    Inherits from langchain_core.callbacks.BaseCallbackHandler when
    LangChain is installed, ensuring compatibility with LangChain/LangGraph.
    """

    def __init__(self, instrumentor: LangChainInstrumentor):
        # Call parent __init__ if we're inheriting from BaseCallbackHandler
        if _LANGCHAIN_AVAILABLE and hasattr(super(), "__init__"):
            super().__init__()
        self._instrumentor = instrumentor
        self._run_id_to_step_id: dict[str, str] = {}
        self._run_id_to_start_time: dict[str, float] = {}
        self._run_id_to_input: dict[str, Any] = {}
        self._run_id_to_model: dict[str, str] = {}
        self._run_id_to_tool_name: dict[str, str] = {}
        self._run_id_to_node: dict[str, str | None] = {}
        self._parent_run_id_map: dict[str, str] = {}

    def _extract_node_name(self, tags: list[str] | None, metadata: dict[str, Any] | None) -> str | None:
        """Extract LangGraph node name from tags or metadata.

        LangGraph tags often include patterns like:
        - 'graph:step:recommend'
        - 'langgraph:step:2'
        - 'seq:step:1'

        Metadata may include 'langgraph_node' or 'node' keys.
        """
        # Check metadata first
        if metadata:
            if "langgraph_node" in metadata:
                return metadata["langgraph_node"]
            if "node" in metadata:
                return metadata["node"]

        # Parse tags for node name
        if tags:
            for tag in tags:
                # Look for LangGraph step patterns
                if tag.startswith("graph:step:"):
                    return tag.split(":")[-1]
                if tag.startswith("langgraph_step:"):
                    return tag.split(":")[-1]
            # Also check for plain node names in tags
            # LangGraph sometimes includes node names directly
            for tag in tags:
                if not tag.startswith(("seq:", "graph:", "langgraph")):
                    # Could be a node name
                    return tag

        return None

    def _get_step_id(self, run_id: UUID) -> str:
        """Get or create step ID for a run ID."""
        run_id_str = str(run_id)
        if run_id_str not in self._run_id_to_step_id:
            self._run_id_to_step_id[run_id_str] = str(uuid.uuid4())
        return self._run_id_to_step_id[run_id_str]

    def _get_parent_step_id(self, parent_run_id: Optional[UUID]) -> Optional[str]:
        """Get parent step ID if parent run exists."""
        if parent_run_id is None:
            return None
        return self._run_id_to_step_id.get(str(parent_run_id))

    # LLM Callbacks
    def _extract_model_name(self, serialized: dict[str, Any]) -> str:
        """Extract model name from serialized LLM config."""
        # Try kwargs first (most common)
        kwargs = serialized.get("kwargs", {})
        if "model_name" in kwargs:
            return kwargs["model_name"]
        if "model" in kwargs:
            return kwargs["model"]

        # Try id field (e.g., ["langchain", "chat_models", "openai", "ChatOpenAI"])
        id_list = serialized.get("id", [])
        if id_list and len(id_list) > 0:
            # Use the last non-class identifier
            return id_list[-1]

        # Try name field
        if "name" in serialized:
            return serialized["name"]

        return "unknown"

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts."""
        run_id_str = str(run_id)
        self._run_id_to_start_time[run_id_str] = time.perf_counter()
        self._run_id_to_input[run_id_str] = prompts[0] if len(prompts) == 1 else prompts
        self._run_id_to_model[run_id_str] = self._extract_model_name(serialized)
        self._run_id_to_node[run_id_str] = self._extract_node_name(tags, metadata)

        if parent_run_id:
            self._parent_run_id_map[run_id_str] = str(parent_run_id)

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chat model starts."""
        run_id_str = str(run_id)
        self._run_id_to_start_time[run_id_str] = time.perf_counter()
        self._run_id_to_model[run_id_str] = self._extract_model_name(serialized)
        self._run_id_to_node[run_id_str] = self._extract_node_name(tags, metadata)

        # Convert messages to serializable format
        formatted_messages = []
        for msg_list in messages:
            for msg in msg_list:
                if hasattr(msg, "type") and hasattr(msg, "content"):
                    formatted_messages.append({"role": msg.type, "content": msg.content})
                elif isinstance(msg, dict):
                    formatted_messages.append(msg)

        self._run_id_to_input[run_id_str] = formatted_messages

        if parent_run_id:
            self._parent_run_id_map[run_id_str] = str(parent_run_id)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM ends."""
        run_id_str = str(run_id)
        step_id = self._get_step_id(run_id)

        # Calculate latency
        start_time = self._run_id_to_start_time.pop(run_id_str, None)
        latency_ms = None
        if start_time:
            latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Get input, model, and node
        input_data = self._run_id_to_input.pop(run_id_str, "")
        model = self._run_id_to_model.pop(run_id_str, "unknown")
        node_name = self._run_id_to_node.pop(run_id_str, None)

        # Try to get model from response if not captured from start
        if model == "unknown" and hasattr(response, "llm_output") and response.llm_output:
            model = response.llm_output.get("model_name", model)

        # Extract output and token usage
        output = ""
        tokens_in = None
        tokens_out = None
        tokens_total = None

        if hasattr(response, "generations") and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    # Try to extract text output
                    if hasattr(gen, "text") and gen.text is not None:
                        output = gen.text
                    elif hasattr(gen, "message") and gen.message is not None:
                        if hasattr(gen.message, "content") and gen.message.content is not None:
                            output = gen.message.content
                        else:
                            output = str(gen.message)

                    # Extract token usage from message
                    if hasattr(gen, "message") and gen.message is not None:
                        if hasattr(gen.message, "usage_metadata") and gen.message.usage_metadata is not None:
                            usage = gen.message.usage_metadata
                            if hasattr(usage, "input_tokens"):
                                tokens_in = usage.input_tokens
                            if hasattr(usage, "output_tokens"):
                                tokens_out = usage.output_tokens
                            if hasattr(usage, "total_tokens"):
                                tokens_total = usage.total_tokens

        # Also check llm_output for token usage
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            if token_usage:
                tokens_in = tokens_in or token_usage.get("prompt_tokens")
                tokens_out = tokens_out or token_usage.get("completion_tokens")
                tokens_total = tokens_total or token_usage.get("total_tokens")

        # Build metadata with node info
        step_metadata = None
        if node_name:
            step_metadata = {"node": node_name}

        # Create step
        step = LLMCallStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=self._get_parent_step_id(parent_run_id),
            metadata=step_metadata,
            model=model,
            input=input_data,
            output=output,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tokens_total=tokens_total,
            latency_ms=latency_ms,
        )

        trace = self._instrumentor._get_current_trace()
        trace.add_step(step)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM errors."""
        run_id_str = str(run_id)
        self._run_id_to_start_time.pop(run_id_str, None)
        self._run_id_to_input.pop(run_id_str, None)
        self._run_id_to_model.pop(run_id_str, None)
        self._run_id_to_node.pop(run_id_str, None)
        logger.debug(f"LLM error: {error}")

    # Tool Callbacks
    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        inputs: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when tool starts."""
        run_id_str = str(run_id)
        self._run_id_to_start_time[run_id_str] = time.perf_counter()
        self._run_id_to_input[run_id_str] = inputs or {"input": input_str}
        self._run_id_to_node[run_id_str] = self._extract_node_name(tags, metadata)

        # Extract tool name from serialized
        tool_name = serialized.get("name", "unknown_tool")
        if tool_name == "unknown_tool":
            # Try id field (e.g., ["langchain", "tools", "MyTool"])
            id_list = serialized.get("id", [])
            if id_list:
                tool_name = id_list[-1]
        self._run_id_to_tool_name[run_id_str] = tool_name

        if parent_run_id:
            self._parent_run_id_map[run_id_str] = str(parent_run_id)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when tool ends."""
        run_id_str = str(run_id)
        step_id = self._get_step_id(run_id)

        # Calculate latency
        start_time = self._run_id_to_start_time.pop(run_id_str, None)
        latency_ms = None
        if start_time:
            latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Get input/arguments, tool name, and node
        arguments = self._run_id_to_input.pop(run_id_str, {})
        tool_name = self._run_id_to_tool_name.pop(run_id_str, None)
        node_name = self._run_id_to_node.pop(run_id_str, None)
        if not tool_name:
            tool_name = kwargs.get("name", "unknown_tool")

        # Convert output to serializable format
        result = output
        if hasattr(output, "content"):
            result = output.content
        elif not isinstance(output, (str, int, float, bool, list, dict, type(None))):
            result = str(output)

        # Build metadata with node info
        step_metadata = None
        if node_name:
            step_metadata = {"node": node_name}

        step = ToolCallStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=self._get_parent_step_id(parent_run_id),
            metadata=step_metadata,
            tool_name=tool_name,
            arguments=arguments if isinstance(arguments, dict) else {"input": arguments},
            result=result,
            latency_ms=latency_ms,
            success=True,
        )

        trace = self._instrumentor._get_current_trace()
        trace.add_step(step)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when tool errors."""
        run_id_str = str(run_id)
        step_id = self._get_step_id(run_id)

        start_time = self._run_id_to_start_time.pop(run_id_str, None)
        latency_ms = None
        if start_time:
            latency_ms = int((time.perf_counter() - start_time) * 1000)

        arguments = self._run_id_to_input.pop(run_id_str, {})
        tool_name = self._run_id_to_tool_name.pop(run_id_str, None)
        node_name = self._run_id_to_node.pop(run_id_str, None)
        if not tool_name:
            tool_name = kwargs.get("name", "unknown_tool")

        # Build metadata with node info
        step_metadata = None
        if node_name:
            step_metadata = {"node": node_name}

        step = ToolCallStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=self._get_parent_step_id(parent_run_id),
            metadata=step_metadata,
            tool_name=tool_name,
            arguments=arguments if isinstance(arguments, dict) else {"input": arguments},
            result=None,
            latency_ms=latency_ms,
            success=False,
            error=str(error),
        )

        trace = self._instrumentor._get_current_trace()
        trace.add_step(step)

    # Retriever Callbacks
    def on_retriever_start(
        self,
        serialized: dict[str, Any],
        query: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when retriever starts."""
        run_id_str = str(run_id)
        self._run_id_to_start_time[run_id_str] = time.perf_counter()
        self._run_id_to_input[run_id_str] = query

        if parent_run_id:
            self._parent_run_id_map[run_id_str] = str(parent_run_id)

    def on_retriever_end(
        self,
        documents: Sequence[Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when retriever ends."""
        run_id_str = str(run_id)
        step_id = self._get_step_id(run_id)

        start_time = self._run_id_to_start_time.pop(run_id_str, None)
        latency_ms = None
        if start_time:
            latency_ms = int((time.perf_counter() - start_time) * 1000)

        query = self._run_id_to_input.pop(run_id_str, "")

        # Convert documents to RetrievalResult
        results = []
        for doc in documents:
            content = ""
            doc_metadata: dict[str, Any] = {}
            score = None

            if hasattr(doc, "page_content"):
                content = doc.page_content
            elif isinstance(doc, str):
                content = doc
            else:
                content = str(doc)

            if hasattr(doc, "metadata"):
                doc_metadata = doc.metadata
                score = doc_metadata.pop("score", None) if isinstance(doc_metadata, dict) else None

            results.append(RetrievalResult(content=content, score=score, metadata=doc_metadata or None))

        step = RetrievalStep(
            step_id=step_id,
            timestamp=datetime.now(timezone.utc),
            parent_step_id=self._get_parent_step_id(parent_run_id),
            query=query,
            results=results,
            match_count=len(results),
            latency_ms=latency_ms,
        )

        trace = self._instrumentor._get_current_trace()
        trace.add_step(step)

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when retriever errors."""
        run_id_str = str(run_id)
        self._run_id_to_start_time.pop(run_id_str, None)
        self._run_id_to_input.pop(run_id_str, None)
        logger.debug(f"Retriever error: {error}")

    # Chain callbacks (for user input / final output tracking)
    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain starts."""
        # Only record as user input if this is a top-level chain
        if parent_run_id is None:
            step_id = self._get_step_id(run_id)

            # Extract user input from inputs
            content = ""
            if "input" in inputs:
                content = str(inputs["input"])
            elif "question" in inputs:
                content = str(inputs["question"])
            elif len(inputs) == 1:
                content = str(list(inputs.values())[0])
            else:
                content = str(inputs)

            step = UserInputStep(
                step_id=step_id,
                timestamp=datetime.now(timezone.utc),
                content=content,
            )

            trace = self._instrumentor._get_current_trace()
            trace.add_step(step)

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain ends."""
        # Only record as final output if this is a top-level chain
        if parent_run_id is None:
            step_id = str(uuid.uuid4())

            # Extract output
            content: Any = ""
            if "output" in outputs:
                content = outputs["output"]
            elif "result" in outputs:
                content = outputs["result"]
            elif "answer" in outputs:
                content = outputs["answer"]
            elif len(outputs) == 1:
                content = list(outputs.values())[0]
            else:
                content = outputs

            step = FinalOutputStep(
                step_id=step_id,
                timestamp=datetime.now(timezone.utc),
                content=content,
            )

            trace = self._instrumentor._get_current_trace()
            trace.add_step(step)

            # Finalize the trace
            self._instrumentor._finalize_current_trace()

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Called when chain errors."""
        logger.debug(f"Chain error: {error}")
