"""
VIDUR API Layer
Submodule: Router Aggregation
Purpose: Combine every v1 route module into a single `APIRouter`,
mounted by `app.main` under `settings.API_V1_PREFIX`. The DB module's
`health` router is mounted separately by `app.main` at the top-level
`/health` prefix, since it must match
`ProjectIsolationMiddleware`'s `/health` exemption rather than the
versioned API prefix.
"""

from fastapi import APIRouter

from app.api.v1.routes import (
    ai_reasoning,
    config,
    deep_learning_vision,
    inspection,
    memory,
    ml_prediction,
    nlp,
    projects,
    specs,
)

api_router = APIRouter()

api_router.include_router(config.router)
api_router.include_router(projects.router)
api_router.include_router(inspection.router)
api_router.include_router(ai_reasoning.router)
api_router.include_router(nlp.router)
api_router.include_router(ml_prediction.router)
api_router.include_router(deep_learning_vision.router)
api_router.include_router(memory.router)
api_router.include_router(specs.router)
