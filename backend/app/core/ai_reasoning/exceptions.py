"""
VIDUR Core - AI Reasoning
Submodule: Exceptions
Purpose: Exception types for the AI Reasoning pipeline (issue
correlation, dependency-impact reasoning, debugging assistance, and
drift-significance reasoning built on top of Inspection Engine output).
"""


class AIReasoningError(Exception):
    """Base class for all AI Reasoning errors."""


class ReasoningDisabledError(AIReasoningError):
    """Raised when reasoning is requested while the MINOR_AI_REASONING
    feature flag is disabled."""


class InvalidReasoningInputError(AIReasoningError):
    """Raised when the InspectionReport (or other input) supplied to
    the reasoning pipeline is missing data required to reason about
    it (for example, a report from a different project than the one
    the reasoning run was scoped to)."""


class OllamaUnavailableError(AIReasoningError):
    """Raised when the local Ollama service cannot be reached, times
    out, or responds with a non-success status or an unexpected
    response shape. Callers should treat this as a signal to fall
    back to rule-based reasoning (Article 10-11: additive, never a
    hard replacement), not as a fatal error."""


class OllamaResponseParsingError(AIReasoningError):
    """Raised when Ollama was reached and responded, but its response
    could not be parsed into at least one valid structured
    recommendation. Callers should treat this the same as
    OllamaUnavailableError: fall back to rule-based reasoning."""
