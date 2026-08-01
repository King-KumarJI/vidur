"""
VIDUR Internal Domain Models Package.

Single import surface for internal domain entities that are not
already produced by a `backend/app/core/*` or `backend/app/memory`
engine. Most API Layer responses serialize an engine's own report
dataclasses directly (each engine's models remain the single source of
truth for its own content, per Article 31-32 reuse); this package only
holds entities the API Layer itself owns, such as combined database
connectivity status.
"""

from app.models.db_health import DatabaseHealthReport

__all__ = ["DatabaseHealthReport"]
