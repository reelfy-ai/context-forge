# Tracer API

Explicit trace capture for custom agents (Level 4 integration).

## Overview

The Tracer provides programmatic control over trace capture when auto-instrumentation isn't suitable.

```python
from context_forge.instrumentation import Tracer

with Tracer.run(run_id="my-run", agent_name="MyAgent") as tracer:
    tracer.user_input("Hello!")
    tracer.llm_call(model="gpt-4", messages=[...], response="Hi there!")
    tracer.tool_call(name="search", args={"q": "weather"}, result={...})
    tracer.memory_write(namespace=["user"], key="prefs", data={...})

trace = tracer.get_trace()
trace.save("trace.json")
```

## Tracer

::: context_forge.instrumentation.tracer.Tracer
    options:
      show_root_heading: true
      members:
        - run
        - user_input
        - llm_call
        - tool_call
        - retrieval
        - memory_read
        - memory_write
        - error
        - final_output
        - get_trace
        - save