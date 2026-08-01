"""
VIDUR Internal Domain Models
Submodule: Database Health Report
Purpose: Combined MongoDB/ChromaDB connectivity status. Owned by the
API Layer because neither `app.db.mongodb.client` nor
`app.db.chromadb.client` (each of which only exposes an independent
`ping()`) nor any `app.core.*` engine produces a combined view of both
- there is no existing engine return type to reuse here.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass(frozen=True)
class DatabaseHealthReport:
    """Point-in-time connectivity status for both isolated data stores
    VIDUR depends on (Article 21: MongoDB per-project databases,
    ChromaDB per-project collections)."""

    mongodb_connected: bool
    chromadb_connected: bool
    checked_at: datetime

    @property
    def healthy(self) -> bool:
        return self.mongodb_connected and self.chromadb_connected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mongodb_connected": self.mongodb_connected,
            "chromadb_connected": self.chromadb_connected,
            "healthy": self.healthy,
            "checked_at": self.checked_at.isoformat(),
        }
