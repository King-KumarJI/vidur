"""
VIDUR Core - Project Isolation
Submodule: Validator
Purpose: Format validation for Project IDs, per Article 21 of the
VIDUR Constitution.
"""

import re

from app.core.project_isolation.exceptions import InvalidProjectIdError

# Project IDs are constrained to a DNS/DB-safe slug: lowercase
# alphanumeric plus hyphen/underscore, 3-63 characters. This keeps
# derived MongoDB database names and ChromaDB collection names valid.
_PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,61}[a-z0-9]$")


def validate_project_id_format(project_id: str) -> str:
    """Validate that `project_id` matches the required slug format.

    Returns the normalized (lower-cased, stripped) project_id on
    success. Raises InvalidProjectIdError on failure.
    """
    if not isinstance(project_id, str):
        raise InvalidProjectIdError(
            f"project_id must be a string, got {type(project_id).__name__}"
        )

    normalized = project_id.strip().lower()

    if not _PROJECT_ID_PATTERN.match(normalized):
        raise InvalidProjectIdError(
            "project_id must be 3-63 characters, lowercase alphanumeric "
            "with hyphens/underscores only, and must not start or end "
            f"with a separator. Received: {project_id!r}"
        )

    return normalized
