"""
VIDUR Services
Submodule: Project Service
Purpose: Orchestration logic for the Project Isolation module's
routes. Wraps `app.core.project_isolation` validation and resource-
name derivation - no persistence, since no project registry exists
yet (Article 38: not building beyond what is approved/requested).
"""

from app.core.project_isolation import (
    chromadb_collection_name,
    mongodb_database_name,
    validate_project_id_format,
)


class ProjectService:
    """Validates Project IDs and derives their isolated resource
    names, per Article 21."""

    def validate(self, project_id: str) -> dict:
        normalized = validate_project_id_format(project_id)
        return {"project_id": normalized, "valid": True}

    def resource_names(self, project_id: str) -> dict:
        normalized = validate_project_id_format(project_id)
        return {
            "project_id": normalized,
            "mongodb_database": mongodb_database_name(normalized),
            "chromadb_collection": chromadb_collection_name(normalized),
        }
