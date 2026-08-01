"""
VIDUR Repositories
Submodule: Database Health Repository
Purpose: Data-access logic wrapping the MongoDB and ChromaDB clients'
own connectivity checks (`app.db.mongodb.client.ping`,
`app.db.chromadb.client.ping`), combined into a single
DatabaseHealthReport. Never touches a Mongo/Chroma client outside
`app.db`, per Article 21.
"""

from app.core.inspection_engine.models import utc_now
from app.db import chroma_ping, mongo_ping
from app.models.db_health import DatabaseHealthReport


class DatabaseHealthRepository:
    """Reads live connectivity status from the shared MongoDB and
    ChromaDB clients."""

    async def check(self) -> DatabaseHealthReport:
        """Return the current connectivity status of both data
        stores. Never raises: an unreachable or uninitialized client
        is reported as `connected=False` rather than propagating a
        DatabaseError, since this check exists to answer "is it up?"."""
        mongodb_connected = await mongo_ping()
        chromadb_connected = chroma_ping()
        return DatabaseHealthReport(
            mongodb_connected=mongodb_connected,
            chromadb_connected=chromadb_connected,
            checked_at=utc_now(),
        )
