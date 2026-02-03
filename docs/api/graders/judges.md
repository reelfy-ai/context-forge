# LLM Judges

LLM-based semantic evaluation for agent behavior.

## Overview

LLM judges provide semantic understanding that rule-based graders cannot:

- **Missed Facts**: User stated something but agent didn't save it
- **Hallucinations**: Agent saved something user never said
- **Contradictions**: Agent's response contradicts known facts

## LLMJudge Base Class

::: context_forge.graders.judges.base.LLMJudge
    options:
      show_root_heading: true

## MemoryHygieneJudge

::: context_forge.graders.judges.memory_hygiene_judge.MemoryHygieneJudge
    options:
      show_root_heading: true
      members:
        - grade

## LLM Backends

### OllamaBackend

Local LLM execution via Ollama with structured output support.

::: context_forge.graders.judges.backends.ollama.OllamaBackend
    options:
      show_root_heading: true
      members:
        - complete
        - complete_structured
        - is_available
        - model_id

## Evaluation Models

Pydantic models for structured LLM output.

::: context_forge.graders.judges.models.MemoryHygieneEvaluation
    options:
      show_root_heading: true