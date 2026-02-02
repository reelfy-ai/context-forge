# Trace Models

The trace module defines the canonical schema for capturing agent execution.

## TraceRun

The top-level container for a complete agent execution trace.

::: context_forge.core.trace.TraceRun
    options:
      show_root_heading: true
      members:
        - add_step
        - get_steps_by_type
        - get_llm_calls
        - get_tool_calls
        - total_tokens
        - total_tool_calls
        - to_json

## Step Types

All steps inherit from `BaseStep` and are discriminated by `step_type`.

### BaseStep

::: context_forge.core.trace.BaseStep

### LLMCallStep

::: context_forge.core.trace.LLMCallStep

### ToolCallStep

::: context_forge.core.trace.ToolCallStep

### RetrievalStep

::: context_forge.core.trace.RetrievalStep

### MemoryReadStep

::: context_forge.core.trace.MemoryReadStep

### MemoryWriteStep

::: context_forge.core.trace.MemoryWriteStep

### UserInputStep

::: context_forge.core.trace.UserInputStep

### FinalOutputStep

::: context_forge.core.trace.FinalOutputStep

### InterruptStep

::: context_forge.core.trace.InterruptStep

### StateChangeStep

::: context_forge.core.trace.StateChangeStep