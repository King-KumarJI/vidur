"""
VIDUR Core - Project Isolation Package.

Single import surface for project context binding, validation, and
resource-name derivation. Enforces Article 21 (Absolute Project
Isolation) of the VIDUR Constitution.
"""

from app.core.project_isolation.context import (
    get_current_project_id,
    project_scope,
    reset_current_project_id,
    set_current_project_id,
)
from app.core.project_isolation.exceptions import (
    CrossProjectAccessError,
    InvalidProjectIdError,
    ProjectContextNotSetError,
    ProjectIsolationError,
    ProjectNotRegisteredError,
)
from app.core.project_isolation.resource_naming import (
    chromadb_collection_name,
    mongodb_database_name,
)
from app.core.project_isolation.validator import validate_project_id_format

__all__ = [
    "get_current_project_id",
    "set_current_project_id",
    "reset_current_project_id",
    "project_scope",
    "validate_project_id_format",
    "mongodb_database_name",
    "chromadb_collection_name",
    "ProjectIsolationError",
    "ProjectContextNotSetError",
    "InvalidProjectIdError",
    "ProjectNotRegisteredError",
    "CrossProjectAccessError",
]
