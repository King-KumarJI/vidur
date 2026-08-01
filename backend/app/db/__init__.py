"""
VIDUR Database Layer Package.

Single import surface for MongoDB and ChromaDB lifecycle management
and per-project isolated resource access. All access must go through
this layer so that Article 21 (Absolute Project Isolation) is
enforced consistently.
"""

from app.db.chromadb import close_chroma_connection, connect_to_chroma, get_chroma_client
from app.db.chromadb import get_project_collection
from app.db.chromadb import ping as chroma_ping
from app.db.exceptions import DatabaseConnectionError, DatabaseError, DatabaseNotInitializedError
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_mongo_client
from app.db.mongodb import get_project_database
from app.db.mongodb import ping as mongo_ping

__all__ = [
    "connect_to_mongo",
    "close_mongo_connection",
    "get_mongo_client",
    "get_project_database",
    "mongo_ping",
    "connect_to_chroma",
    "close_chroma_connection",
    "get_chroma_client",
    "get_project_collection",
    "chroma_ping",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseNotInitializedError",
]
