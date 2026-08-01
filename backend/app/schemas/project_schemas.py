"""
VIDUR Schemas
Submodule: Project Isolation
Purpose: Request/response shapes for the Project Isolation module's
routes - Project ID format validation and derivation of a project's
isolated resource names. Mirrors the capabilities already implemented
in `app.core.project_isolation` (validator, resource_naming); no
project registry exists yet, so these routes are pure, side-effect-
free validation/derivation, not persistence.
"""

from pydantic import BaseModel, ConfigDict, Field


class ProjectIdRequest(BaseModel):
    """A single, caller-supplied Project ID to validate."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(..., min_length=1, description="Candidate Project ID to validate.")


class ProjectValidationResponse(BaseModel):
    """Result of validating and normalizing a Project ID."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(..., description="The normalized (lower-cased, stripped) Project ID.")
    valid: bool


class ProjectResourcesResponse(BaseModel):
    """The isolated MongoDB database name and ChromaDB collection name
    deterministically derived from a valid Project ID."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    mongodb_database: str
    chromadb_collection: str
