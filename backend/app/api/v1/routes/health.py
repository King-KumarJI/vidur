"""
VIDUR API Layer
Module: DB
Purpose: Connectivity health-check route for the MongoDB and ChromaDB
clients underlying every project-isolated data store. Mounted at the
top-level `/health` prefix (not under the versioned `/api/v1` prefix)
so it matches the `/health` exemption `ProjectIsolationMiddleware`
already grants - a connectivity check is not itself a project-scoped
operation.
"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_db_health_service
from app.schemas.health_schemas import DatabaseHealthResponse
from app.services.db_health_service import DBHealthService

router = APIRouter(tags=["Health"])


@router.get("", response_model=DatabaseHealthResponse, summary="Check MongoDB/ChromaDB connectivity")
async def check_database_health(
    service: DBHealthService = Depends(get_db_health_service),
) -> DatabaseHealthResponse:
    report = await service.check()
    return DatabaseHealthResponse.model_validate(report.to_dict())
