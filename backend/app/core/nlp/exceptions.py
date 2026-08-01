"""
VIDUR Core - NLP
Submodule: Exceptions
Purpose: Exception types for the NLP pipeline (document discovery,
documented/implemented intent extraction, and requirement-to-
implementation consistency checking).
"""


class NLPError(Exception):
    """Base class for all NLP module errors."""


class NLPDisabledError(NLPError):
    """Raised when NLP analysis is requested while the
    MINOR_REQUIREMENT_CONSISTENCY feature flag is disabled."""


class InvalidNLPInputError(NLPError):
    """Raised when the input supplied to the NLP pipeline is invalid or
    insufficient to run analysis on (for example, a project root that
    does not resolve to an inspectable directory)."""


class DocumentReadError(NLPError):
    """Raised when a discovered document (README, dependency manifest,
    or Python source file) cannot be read as UTF-8 text."""
