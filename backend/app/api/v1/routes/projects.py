"""
VIDUR API Layer
Module: Project Isolation
Purpose: Project ID validation and isolated-resource-name derivation
routes. Exempted from `ProjectIsolationMiddleware`'s Project ID
requirement (`_EXEMPT_PATH_PREFIXES` already lists this prefix) since
these routes exist to validate/derive a Project ID before it can be
used as the active one, per Article 21.
"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_project_service
from app.schemas.project_schemas import (
    ProjectIdRequest,
    ProjectResourcesResponse,
    ProjectValidationResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Project Isolation"])


@router.post("/validate", response_model=ProjectValidationResponse, summary="Validate a Project ID's format")
def validate_project_id(
    body: ProjectIdRequest, service: ProjectService = Depends(get_project_service)
) -> ProjectValidationResponse:
    return ProjectValidationResponse.model_validate(service.validate(body.project_id))


@router.get(
    "/{project_id}/resources",
    response_model=ProjectResourcesResponse,
    summary="Derive a Project ID's isolated resource names",
)
def get_project_resources(
    project_id: str, service: ProjectService = Depends(get_project_service)
) -> ProjectResourcesResponse:
    return ProjectResourcesResponse.model_validate(service.resource_names(project_id))
