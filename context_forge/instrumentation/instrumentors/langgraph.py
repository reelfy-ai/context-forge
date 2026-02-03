"""LangGraph instrumentor for ContextForge.

Provides unified instrumentation for LangGraph agents, capturing:
- LLM calls (via LangChain callbacks)
- Tool calls (via LangChain callbacks)
- Memory operations (via BaseStore patching)

All events are captured in a single unified trace.
"""

import functools
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
import uuid

from context_forge.core.trace import MemoryReadStep, MemoryWriteStep
from context_forge.core.types import FieldChange
from context_forge.instrumentation.base import RedactionConfig
from context_forge.instrumentation.instrumentors.langchain import LangChainInstrumentor


def compute_field_changes(
    old_value: dict[str, Any] | None,
    new_value: dict[str, Any],
    prefix: str = "$",
) -> list[FieldChange]:
    """Compute field-level changes between two dictionaries using JSON paths.

    Model-agnostic diff computation that works with any data structure.

    Args:
        old_value: Previous value (None if new record)
        new_value: New value being written
        prefix: JSON path prefix (default "$" for root)

    Returns:
        List of FieldChange objects representing each changed field
    """
    changes: list[FieldChange] = []
    old_value = old_value or {}

    # Get all keys from both old and new
    all_keys = set(old_value.keys()) | set(new_value.keys())

    for key in all_keys:
        old_val = old_value.get(key)
        new_val = new_value.get(key)
        path = f"{prefix}.{key}"

        # Both are dicts - recurse
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            changes.extend(compute_field_changes(old_val, new_val, path))
        # Values differ
        elif old_val != new_val:
            changes.append(
                FieldChange(
                    path=path,
                    old_value=old_val,
                    new_value=new_val,
                )
            )

    return changes

logger = logging.getLogger(__name__)

# Track whether LangGraph is available
try:
    from langgraph.store.base import BaseStore

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    BaseStore = None  # type: ignore
    _LANGGRAPH_AVAILABLE = False


class LangGraphInstrumentor(LangChainInstrumentor):
    """Combined instrumentor for LangGraph agents.

    Captures LLM calls, tool calls, AND memory operations in a single
    unified trace. Extends LangChainInstrumentor with BaseStore patching.

    Usage:
        # One-liner instrumentation
        instrumentor = LangGraphInstrumentor().instrument()
        handler = instrumentor.get_callback_handler()

        # Run your LangGraph agent
        result = graph.invoke(input, config={"callbacks": [handler]})

        # Get unified trace with everything
        traces = instrumentor.get_traces()

    Or with context manager:
        with LangGraphInstrumentor(output_path="./traces") as inst:
            handler = inst.get_callback_handler()
            result = graph.invoke(input, config={"callbacks": [handler]})
        # Trace saved with LLM calls + tool calls + memory ops
    """

    def __init__(
        self,
        agent_name: str = "langgraph_agent",
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
        # Store original methods for restoration
        self._original_store_methods: dict[str, Callable] = {}
        self._langgraph_version: Optional[str] = None

    @property
    def framework(self) -> str:
        return "langgraph"

    @property
    def framework_version(self) -> Optional[str]:
        if self._langgraph_version is None:
            try:
                from importlib.metadata import version

                self._langgraph_version = version("langgraph")
            except Exception:
                pass
        return self._langgraph_version

    def _install_hooks(self) -> None:
        """Install both LangChain callbacks and BaseStore patches."""
        # Install LangChain callback hooks (LLM, tools, retriever)
        super()._install_hooks()

        # Install BaseStore patches (memory operations)
        if _LANGGRAPH_AVAILABLE:
            self._patch_store_methods()
            logger.debug("LangGraph store methods patched")
        else:
            logger.warning(
                "LangGraph not available, memory operations will not be traced. "
                "Install with: pip install langgraph"
            )

    def _remove_hooks(self) -> None:
        """Remove both LangChain callbacks and BaseStore patches."""
        # Remove BaseStore patches first
        if _LANGGRAPH_AVAILABLE:
            self._unpatch_store_methods()
            logger.debug("LangGraph store methods unpatched")

        # Remove LangChain callback hooks
        super()._remove_hooks()

    def _patch_store_methods(self) -> None:
        """Patch BaseStore methods to capture memory operations."""
        if not _LANGGRAPH_AVAILABLE or BaseStore is None:
            return

        # Store originals
        self._original_store_methods = {
            "get": BaseStore.get,
            "put": BaseStore.put,
            "delete": BaseStore.delete,
            "search": BaseStore.search,
            "aget": BaseStore.aget,
            "aput": BaseStore.aput,
            "adelete": BaseStore.adelete,
            "asearch": BaseStore.asearch,
        }

        # Create patched methods
        instrumentor = self  # Capture for closures

        @functools.wraps(self._original_store_methods["get"])
        def traced_get(
            store_self,
            namespace: tuple[str, ...],
            key: str,
            *,
            refresh_ttl: bool | None = None,
        ):
            start_time = time.perf_counter()
            result = instrumentor._original_store_methods["get"](
                store_self, namespace, key, refresh_ttl=refresh_ttl
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            instrumentor._record_memory_read(
                query={"namespace": namespace, "key": key},
                results=[result.value] if result else [],
                latency_ms=latency_ms,
            )
            return result

        @functools.wraps(self._original_store_methods["put"])
        def traced_put(
            store_self,
            namespace: tuple[str, ...],
            key: str,
            value: dict[str, Any],
            index=None,
            *,
            ttl=None,
        ):
            # Get current value BEFORE write (for diff computation)
            old_item = None
            try:
                old_item = instrumentor._original_store_methods["get"](
                    store_self, namespace, key
                )
            except Exception:
                pass  # No existing value

            old_value = old_item.value if old_item else None

            start_time = time.perf_counter()
            # Handle the NOT_PROVIDED sentinel
            kwargs = {}
            if ttl is not None:
                kwargs["ttl"] = ttl
            result = instrumentor._original_store_methods["put"](
                store_self, namespace, key, value, index, **kwargs
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Compute field-level changes
            changes = compute_field_changes(old_value, value)

            instrumentor._record_memory_write(
                namespace=list(namespace),
                key=key,
                operation="add",
                data=value,
                changes=changes,
                latency_ms=latency_ms,
            )
            return result

        @functools.wraps(self._original_store_methods["delete"])
        def traced_delete(store_self, namespace: tuple[str, ...], key: str):
            # Get current value BEFORE delete (for diff computation)
            old_item = None
            try:
                old_item = instrumentor._original_store_methods["get"](
                    store_self, namespace, key
                )
            except Exception:
                pass

            old_value = old_item.value if old_item else None

            start_time = time.perf_counter()
            result = instrumentor._original_store_methods["delete"](
                store_self, namespace, key
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Compute changes (all fields become None)
            changes = []
            if old_value:
                changes = compute_field_changes(old_value, {})

            instrumentor._record_memory_write(
                namespace=list(namespace),
                key=key,
                operation="delete",
                data={},
                changes=changes,
                latency_ms=latency_ms,
            )
            return result

        @functools.wraps(self._original_store_methods["search"])
        def traced_search(
            store_self,
            namespace_prefix: tuple[str, ...],
            /,
            *,
            query: str | None = None,
            filter: dict[str, Any] | None = None,
            limit: int = 10,
            offset: int = 0,
            refresh_ttl: bool | None = None,
        ):
            start_time = time.perf_counter()
            results = instrumentor._original_store_methods["search"](
                store_self,
                namespace_prefix,
                query=query,
                filter=filter,
                limit=limit,
                offset=offset,
                refresh_ttl=refresh_ttl,
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            instrumentor._record_memory_read(
                query={
                    "namespace_prefix": namespace_prefix,
                    "query": query,
                    "filter": filter,
                },
                results=[r.value for r in results],
                latency_ms=latency_ms,
            )
            return results

        # Async versions
        @functools.wraps(self._original_store_methods["aget"])
        async def traced_aget(
            store_self,
            namespace: tuple[str, ...],
            key: str,
            *,
            refresh_ttl: bool | None = None,
        ):
            start_time = time.perf_counter()
            result = await instrumentor._original_store_methods["aget"](
                store_self, namespace, key, refresh_ttl=refresh_ttl
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            instrumentor._record_memory_read(
                query={"namespace": namespace, "key": key},
                results=[result.value] if result else [],
                latency_ms=latency_ms,
            )
            return result

        @functools.wraps(self._original_store_methods["aput"])
        async def traced_aput(
            store_self,
            namespace: tuple[str, ...],
            key: str,
            value: dict[str, Any],
            index=None,
            *,
            ttl=None,
        ):
            # Get current value BEFORE write (for diff computation)
            old_item = None
            try:
                old_item = await instrumentor._original_store_methods["aget"](
                    store_self, namespace, key
                )
            except Exception:
                pass  # No existing value

            old_value = old_item.value if old_item else None

            start_time = time.perf_counter()
            kwargs = {}
            if ttl is not None:
                kwargs["ttl"] = ttl
            result = await instrumentor._original_store_methods["aput"](
                store_self, namespace, key, value, index, **kwargs
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Compute field-level changes
            changes = compute_field_changes(old_value, value)

            instrumentor._record_memory_write(
                namespace=list(namespace),
                key=key,
                operation="add",
                data=value,
                changes=changes,
                latency_ms=latency_ms,
            )
            return result

        @functools.wraps(self._original_store_methods["adelete"])
        async def traced_adelete(store_self, namespace: tuple[str, ...], key: str):
            # Get current value BEFORE delete (for diff computation)
            old_item = None
            try:
                old_item = await instrumentor._original_store_methods["aget"](
                    store_self, namespace, key
                )
            except Exception:
                pass

            old_value = old_item.value if old_item else None

            start_time = time.perf_counter()
            result = await instrumentor._original_store_methods["adelete"](
                store_self, namespace, key
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Compute changes (all fields become None)
            changes = []
            if old_value:
                changes = compute_field_changes(old_value, {})

            instrumentor._record_memory_write(
                namespace=list(namespace),
                key=key,
                operation="delete",
                data={},
                changes=changes,
                latency_ms=latency_ms,
            )
            return result

        @functools.wraps(self._original_store_methods["asearch"])
        async def traced_asearch(
            store_self,
            namespace_prefix: tuple[str, ...],
            /,
            *,
            query: str | None = None,
            filter: dict[str, Any] | None = None,
            limit: int = 10,
            offset: int = 0,
            refresh_ttl: bool | None = None,
        ):
            start_time = time.perf_counter()
            results = await instrumentor._original_store_methods["asearch"](
                store_self,
                namespace_prefix,
                query=query,
                filter=filter,
                limit=limit,
                offset=offset,
                refresh_ttl=refresh_ttl,
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            instrumentor._record_memory_read(
                query={
                    "namespace_prefix": namespace_prefix,
                    "query": query,
                    "filter": filter,
                },
                results=[r.value for r in results],
                latency_ms=latency_ms,
            )
            return results

        # Apply patches
        BaseStore.get = traced_get
        BaseStore.put = traced_put
        BaseStore.delete = traced_delete
        BaseStore.search = traced_search
        BaseStore.aget = traced_aget
        BaseStore.aput = traced_aput
        BaseStore.adelete = traced_adelete
        BaseStore.asearch = traced_asearch

    def _unpatch_store_methods(self) -> None:
        """Restore original BaseStore methods."""
        if not _LANGGRAPH_AVAILABLE or BaseStore is None:
            return

        for method_name, original_method in self._original_store_methods.items():
            setattr(BaseStore, method_name, original_method)

        self._original_store_methods.clear()

    def _record_memory_read(
        self,
        query: str | dict[str, Any],
        results: list[Any],
        latency_ms: Optional[int] = None,
    ) -> None:
        """Record a memory read operation to the current trace."""
        try:
            trace = self._get_current_trace()
            step = MemoryReadStep(
                step_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                query=query,
                results=results,
                match_count=len(results),
                latency_ms=latency_ms,
            )
            trace.add_step(step)
        except Exception as e:
            logger.debug(f"Failed to record memory read: {e}")

    def _record_memory_write(
        self,
        namespace: list[str],
        key: str,
        operation: str,
        data: dict[str, Any],
        changes: list[FieldChange] | None = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        """Record a memory write operation to the current trace.

        Args:
            namespace: Storage namespace as list (e.g., ["profiles", "user_123"])
            key: Storage key within the namespace
            operation: Operation type ("add", "delete")
            data: The complete data being written
            changes: Field-level changes with JSON paths (model-agnostic)
            latency_ms: Operation latency in milliseconds
        """
        try:
            trace = self._get_current_trace()

            # Find the most recent tool call to link as trigger
            triggered_by = None
            for step in reversed(trace.steps):
                if step.step_type == "tool_call":
                    triggered_by = step.step_id
                    break

            step = MemoryWriteStep(
                step_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                namespace=namespace,
                key=key,
                operation=operation,  # type: ignore[arg-type]
                data=data,
                changes=changes,
                triggered_by_step_id=triggered_by,
                # Legacy field for backward compatibility
                entity_type="/".join(namespace),
                entity_id=key,
            )
            trace.add_step(step)
        except Exception as e:
            logger.debug(f"Failed to record memory write: {e}")
