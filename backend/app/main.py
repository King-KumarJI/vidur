"""
VIDUR Backend Application
Purpose: FastAPI application factory - wires together configuration,
logging, project-isolation middleware, CORS, the versioned API router,
domain exception handlers, and the MongoDB/ChromaDB connection
lifecycle. This is the single ASGI entry point for the whole backend
(run via `uvicorn app.main:app`).
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.error_handlers import register_exception_handlers
from app.api.v1.router import api_router
from app.api.v1.routes.health import router as health_router
from app.config.logging_config import configure_logging, get_logger
from app.config.settings import settings
from app.db.chromadb.client import close_chroma_connection, connect_to_chroma
from app.db.exceptions import DatabaseConnectionError
from app.db.mongodb.client import close_mongo_connection, connect_to_mongo
from app.middleware import ProjectIsolationMiddleware

configure_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Connect to MongoDB/ChromaDB at startup and disconnect at
    shutdown. A data store that is unreachable at startup is logged
    and skipped rather than raised: VIDUR is a watchdog over other
    projects' code, not a database-dependent CRUD app, so routes that
    do not touch persistence (inspection, reasoning, NLP, and Deep
    Learning Vision runs with Memory disabled, Config, and Project
    Isolation) must stay usable even when a data store is down."""
    logger.info("%s starting up (version=%s)", settings.APP_NAME, settings.APP_VERSION)

    try:
        await connect_to_mongo()
    except DatabaseConnectionError as exc:
        logger.warning("MongoDB unavailable at startup, continuing without it: %s", exc)

    try:
        connect_to_chroma()
    except DatabaseConnectionError as exc:
        logger.warning("ChromaDB unavailable at startup, continuing without it: %s", exc)

    yield

    await close_mongo_connection()
    close_chroma_connection()
    logger.info("%s shut down", settings.APP_NAME)


def create_app() -> FastAPI:
    """Build and fully configure the VIDUR FastAPI application."""
    app = FastAPI(
        title=settings.APP_FULL_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Starlette runs the *last*-added middleware first, so
    # ProjectIsolationMiddleware is added before CORSMiddleware: CORS
    # (including preflight OPTIONS requests) must be handled before a
    # request can be rejected for a missing/invalid Project ID header.
    app.add_middleware(ProjectIsolationMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router, prefix="/health")
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
