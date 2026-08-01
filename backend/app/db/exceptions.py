"""
VIDUR Database Layer
Submodule: Exceptions
Purpose: Exception types for MongoDB and ChromaDB connection
lifecycle and access failures.
"""


class DatabaseError(Exception):
    """Base class for all VIDUR database-layer errors."""


class DatabaseConnectionError(DatabaseError):
    """Raised when a database connection cannot be established."""


class DatabaseNotInitializedError(DatabaseError):
    """Raised when a database client is accessed before its
    connect_* lifecycle function has been called."""
