"""
VIDUR - Memory
Submodule: Exceptions
Purpose: Exception types for the Memory module (persistent storage and
recall of VIDUR's own analysis history - inspection, AI reasoning,
NLP, ML prediction, and deep learning vision reports - per project).

The base error is named `MemoryModuleError` rather than the
`<Module>Error` convention used elsewhere (e.g. `MLPredictionError`,
`NLPError`) because `MemoryError` is a Python builtin (raised on
out-of-memory conditions); reusing that name here would shadow it for
every caller that imports this module's exceptions.
"""


class MemoryModuleError(Exception):
    """Base class for all Memory module errors."""


class MemoryDisabledError(MemoryModuleError):
    """Raised when a memory operation is requested while the
    MINOR_PROJECT_MEMORY feature flag is disabled."""


class InvalidMemoryQueryError(MemoryModuleError):
    """Raised when a semantic recall query is missing data required to
    run it (for example, an empty or whitespace-only query_text)."""


class MemoryPersistenceError(MemoryModuleError):
    """Raised when the underlying MongoDB record store or ChromaDB
    semantic index fails to persist or retrieve a memory record."""
