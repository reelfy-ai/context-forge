# Grader Base Classes

Base classes for all ContextForge graders.

## GraderResult

The result returned by all graders.

::: context_forge.graders.base.GraderResult
    options:
      members:
        - errors
        - warnings
        - to_dict
        - format_report
        - print_report

## Evidence

Proof of what was evaluated by a grader.

::: context_forge.graders.base.Evidence

## Severity

::: context_forge.graders.base.Severity

## Grader

Abstract base class for all graders.

::: context_forge.graders.base.Grader
    options:
      members:
        - grade
        - validate_trace
        - check_required_steps