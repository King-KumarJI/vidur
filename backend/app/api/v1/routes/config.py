"""
VIDUR API Layer
Module: Core Configuration
Purpose: Non-secret application identity and feature-flag state
routes. Global, not project-scoped data, so this router's prefix is
exempted from `ProjectIsolationMiddleware`'s Project ID requirement
(see `_EXEMPT_PATH_PREFIXES` in `app.middleware.project_isolation_middleware`).
"""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_config_service
from app.schemas.config_schemas import AppInfoResponse, FeatureFlagsResponse
from app.services.config_service import ConfigService

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/info", response_model=AppInfoResponse, summary="Get application identity")
def get_app_info(service: ConfigService = Depends(get_config_service)) -> AppInfoResponse:
    return AppInfoResponse.model_validate(service.app_info())


@router.get("/feature-flags", response_model=FeatureFlagsResponse, summary="Get resolved feature flag state")
def get_feature_flags(service: ConfigService = Depends(get_config_service)) -> FeatureFlagsResponse:
    return FeatureFlagsResponse.model_validate(service.feature_flag_state())
