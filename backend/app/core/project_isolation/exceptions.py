"""
VIDUR Core - Project Isolation
Submodule: Exceptions
Purpose: Exception types enforcing Article 21 (Absolute Project
Isolation) of the VIDUR Constitution.
"""


class ProjectIsolationError(Exception):
    """Base class for all project isolation violations."""


class ProjectContextNotSetError(ProjectIsolationError):
    """Raised when an operation requiring a Project ID executes
    without one bound to the current context."""


class InvalidProjectIdError(ProjectIsolationError):
    """Raised when a supplied Project ID fails format validation."""


class ProjectNotRegisteredError(ProjectIsolationError):
    """Raised when a syntactically valid Project ID does not
    correspond to a known, registered project."""


class CrossProjectAccessError(ProjectIsolationError):
    """Raised when an operation attempts to access resources
    belonging to a Project ID other than the active one."""
