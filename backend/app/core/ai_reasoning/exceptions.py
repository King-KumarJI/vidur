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
