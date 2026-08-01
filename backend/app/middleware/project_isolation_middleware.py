"""
VIDUR Middleware
Submodule: Project Isolation Middleware
Purpose: Extracts and validates the Project ID from every inbound HTTP
request, binding it to the request-scoped context before the request
reaches any route handler. Enforces Article 21 of the VIDUR
Constitution: every operation must verify the active Project ID
before execution.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config.settings import settings
from app.core.project_isolation import (
    InvalidProjectIdError,
    reset_current_project_id,
    set_current_project_id,
    validate_project_id_format,
)

# Routes that do not require an active project context (health checks,
# project registration/listing itself, global (non-project-scoped)
# application configuration, API docs).
_EXEMPT_PATH_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    f"{settings.API_V1_PREFIX}/projects",
    f"{settings.API_V1_PREFIX}/config",
)


class ProjectIsolationMiddleware(BaseHTTPMiddleware):
    """Binds the request's Project ID to the isolation context for the
    lifetime of the request, and rejects requests missing a valid one
    unless the path is explicitly exempt."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not settings.ENFORCE_PROJECT_ISOLATION:
            return await call_next(request)

        if request.url.path.startswith(_EXEMPT_PATH_PREFIXES):
            return await call_next(request)

        raw_project_id = request.headers.get(settings.DEFAULT_PROJECT_ID_HEADER)

        if not raw_project_id:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "missing_project_id",
                    "message": (
                        "Request is missing the required "
                        f"'{settings.DEFAULT_PROJECT_ID_HEADER}' header."
                    ),
                },
            )

        try:
            project_id = validate_project_id_format(raw_project_id)
        except InvalidProjectIdError as exc:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_project_id", "message": str(exc)},
            )

        token = set_current_project_id(project_id)
        try:
            response = await call_next(request)
        finally:
            reset_current_project_id(token)

        response.headers[settings.DEFAULT_PROJECT_ID_HEADER] = project_id
        return response
