"""
VIDUR Database Layer
Submodule: MongoDB Client
Purpose: Manage the lifecycle of the MongoDB connection and expose
per-project isolated database handles, per Article 21 of the VIDUR
Constitution.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.config.logging_config import get_logger
from app.config.settings import settings
from app.core.project_isolation import mongodb_database_name
from app.db.exceptions import DatabaseConnectionError, DatabaseNotInitializedError

logger = get_logger("db.mongodb")

_client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo() -> None:
    """Initialize the shared MongoDB client. Call once at application
    startup. Idempotent."""
    global _client
    if _client is not None:
        return

    try:
        _client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
            serverSelectionTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
        )
        await _client.admin.command("ping")
        logger.info("MongoDB connection established")
    except PyMongoError as exc:
        _client = None
        logger.error("MongoDB connection failed: %s", exc)
        raise DatabaseConnectionError(f"Unable to connect to MongoDB: {exc}") from exc


async def close_mongo_connection() -> None:
    """Close the shared MongoDB client. Call once at application
    shutdown. Idempotent."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")


def get_mongo_client() -> AsyncIOMotorClient:
    """Return the shared MongoDB client. Raises if not yet connected."""
    if _client is None:
        raise DatabaseNotInitializedError(
            "MongoDB client is not initialized. Call connect_to_mongo() at startup."
        )
    return _client


def get_project_database(project_id: str) -> AsyncIOMotorDatabase:
    """Return the isolated MongoDB database handle for `project_id`.

    Enforces Article 21: every database access is scoped to exactly
    one project's own database, derived deterministically from the
    validated project_id.
    """
    client = get_mongo_client()
    db_name = mongodb_database_name(project_id)
    return client[db_name]


async def ping() -> bool:
    """Health check: returns True if the MongoDB server responds."""
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        return True
    except (PyMongoError, DatabaseNotInitializedError):
        return False
