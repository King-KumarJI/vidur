"""
VIDUR Schemas
Submodule: Health
Purpose: Response shape for the DB module's connectivity health-check
route. Mirrors `app.models.db_health.DatabaseHealthReport.to_dict()`.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatabaseHealthResponse(BaseModel):
    """Combined MongoDB/ChromaDB connectivity status."""

    model_config = ConfigDict(extra="forbid")

    mongodb_connected: bool
    chromadb_connected: bool
    healthy: bool
    checked_at: datetime
