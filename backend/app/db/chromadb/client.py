"""
VIDUR Database Layer
Submodule: ChromaDB Client
Purpose: Manage the lifecycle of the ChromaDB connection and expose
per-project isolated vector collections, per Article 21 of the VIDUR
Constitution.
"""

from typing import Optional

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings

from app.config.logging_config import get_logger
from app.config.settings import settings
from app.core.project_isolation import chromadb_collection_name
from app.db.exceptions import DatabaseConnectionError, DatabaseNotInitializedError

logger = get_logger("db.chromadb")

_client: Optional[ClientAPI] = None


def connect_to_chroma() -> None:
    """Initialize the shared ChromaDB client. Call once at application
    startup. Idempotent."""
    global _client
    if _client is not None:
        return

    try:
        _client = chromadb.HttpClient(
            host=settings.CHROMADB_HOST,
            port=settings.CHROMADB_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _client.heartbeat()
        logger.info("ChromaDB connection established")
    except Exception as exc:  # chromadb raises varied exception types
        _client = None
        logger.error("ChromaDB connection failed: %s", exc)
        raise DatabaseConnectionError(f"Unable to connect to ChromaDB: {exc}") from exc


def close_chroma_connection() -> None:
    """Release the shared ChromaDB client reference. Call once at
    application shutdown. Idempotent."""
    global _client
    _client = None
    logger.info("ChromaDB connection released")


def get_chroma_client() -> ClientAPI:
    """Return the shared ChromaDB client. Raises if not yet connected."""
    if _client is None:
        raise DatabaseNotInitializedError(
            "ChromaDB client is not initialized. Call connect_to_chroma() at startup."
        )
    return _client


def get_project_collection(project_id: str) -> Collection:
    """Return the isolated ChromaDB collection handle for `project_id`,
    creating it if it does not yet exist.

    Enforces Article 21: every vector operation is scoped to exactly
    one project's own collection, derived deterministically from the
    validated project_id.
    """
    client = get_chroma_client()
    collection_name = chromadb_collection_name(project_id)
    return client.get_or_create_collection(name=collection_name)


def ping() -> bool:
    """Health check: returns True if the ChromaDB server responds."""
    try:
        client = get_chroma_client()
        client.heartbeat()
        return True
    except Exception:
        return False
