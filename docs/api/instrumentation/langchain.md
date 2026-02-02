# LangChain Instrumentation

Auto-instrumentation for LangChain applications (Level 2 integration).

## Overview

The LangChain instrumentor automatically captures traces from LangChain chains and agents.

```python
from context_forge.instrumentation import LangChainInstrumentor

# One-line instrumentation
instrumentor = LangChainInstrumentor(output_path="./traces")
instrumentor.instrument()

# Run your LangChain code - traces are captured automatically
chain = LLMChain(llm=llm, prompt=prompt)
result = chain.invoke({"input": "Hello"})

# Cleanup
instrumentor.uninstrument()
```

## LangChainInstrumentor

::: context_forge.instrumentation.instrumentors.langchain.LangChainInstrumentor
    options:
      show_root_heading: true
      members:
        - instrument
        - uninstrument

## LangGraphInstrumentor

Auto-instrumentation for LangGraph with memory store patching.

::: context_forge.instrumentation.instrumentors.langgraph.LangGraphInstrumentor
    options:
      show_root_heading: true
      members:
        - instrument
        - uninstrument