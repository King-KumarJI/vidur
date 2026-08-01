"""
VIDUR Core - Project Isolation
Submodule: Resource Naming
Purpose: Deterministic, collision-safe derivation of isolated resource
names (MongoDB database, ChromaDB collection) from a Project ID, per
Article 21 of the VIDUR Constitution.
"""

from app.config.settings import settings
from app.core.project_isolation.validator import validate_project_id_format


def mongodb_database_name(project_id: str) -> str:
    """Return the isolated MongoDB database name for `project_id`."""
    normalized = validate_project_id_format(project_id)
    return f"{settings.MONGODB_DB_PREFIX}{normalized}"


def chromadb_collection_name(project_id: str) -> str:
    """Return the isolated ChromaDB collection name for `project_id`."""
    normalized = validate_project_id_format(project_id)
    return f"{settings.CHROMADB_COLLECTION_PREFIX}{normalized}"
