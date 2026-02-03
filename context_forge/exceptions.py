"""Custom exceptions for ContextForge.

This module implements T025: Custom exceptions.
"""


class ContextForgeError(Exception):
    """Base exception for all ContextForge errors."""

    pass


class TraceValidationError(ContextForgeError):
    """Raised when trace validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message)


class InstrumentationError(ContextForgeError):
    """Raised when instrumentation fails."""

    pass


class InstrumentorAlreadyActiveError(InstrumentationError):
    """Raised when trying to instrument when already instrumented."""

    pass


class InstrumentorNotActiveError(InstrumentationError):
    """Raised when trying to uninstrument when not instrumented."""

    pass


class SpanConversionError(ContextForgeError):
    """Raised when span conversion fails."""

    def __init__(self, message: str, span_id: str | None = None):
        self.span_id = span_id
        super().__init__(message)


class TracerError(ContextForgeError):
    """Raised when tracer operations fail."""

    pass


class TracerNotActiveError(TracerError):
    """Raised when trying to record steps without an active tracer."""

    pass
