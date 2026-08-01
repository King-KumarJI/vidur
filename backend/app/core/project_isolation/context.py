"""
VIDUR Core - Project Isolation
Submodule: Context
Purpose: Request-scoped, isolated project context management using
contextvars. Guarantees that every operation can identify and verify
its active Project ID, per Article 21 of the VIDUR Constitution.
"""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Optional

from app.core.project_isolation.exceptions import ProjectContextNotSetError

_current_project_id: "ContextVar[Optional[str]]" = ContextVar(
    "vidur_current_project_id", default=None
)


def set_current_project_id(project_id: str) -> Token:
    """Bind a project ID to the current execution context.

    Returns a Token that must be passed to `reset_current_project_id`
    to restore the previous context value.
    """
    if not project_id or not project_id.strip():
        raise ValueError("project_id must be a non-empty string")
    return _current_project_id.set(project_id)


def reset_current_project_id(token: Token) -> None:
    """Restore the project context to its state before the matching
    `set_current_project_id` call."""
    _current_project_id.reset(token)


def get_current_project_id(required: bool = True) -> Optional[str]:
    """Return the Project ID bound to the current execution context.

    If `required` is True (default) and no project is bound, raises
    ProjectContextNotSetError instead of silently returning None. This
    enforces Article 21: every operation must verify the active
    Project ID before execution.
    """
    project_id = _current_project_id.get()
    if project_id is None and required:
        raise ProjectContextNotSetError(
            "No active Project ID is bound to the current context. "
            "Every operation must run within a project-scoped context."
        )
    return project_id


@contextmanager
def project_scope(project_id: str) -> Iterator[str]:
    """Context manager that binds `project_id` for the duration of the
    `with` block and guarantees cleanup, even on exception."""
    token = set_current_project_id(project_id)
    try:
        yield project_id
    finally:
        reset_current_project_id(token)
