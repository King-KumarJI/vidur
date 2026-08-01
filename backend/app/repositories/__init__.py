"""
VIDUR Repositories Package.

Single import surface for data-access logic that talks to
`app.db.mongodb` / `app.db.chromadb` directly. Per Article 21, no
route or service may import a Mongo/Chroma client outside this layer
(or `app.memory`, which already owns its own project-isolated
persistence for analysis-history records). Today the only direct
database access the API Layer itself performs is the connectivity
health check, since every other module's persistence is already
handled by the Memory module's engine.
"""

from app.repositories.db_health_repository import DatabaseHealthRepository

__all__ = ["DatabaseHealthRepository"]
