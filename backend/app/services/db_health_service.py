"""
VIDUR Services
Submodule: DB Health Service
Purpose: Orchestration logic for the DB module's connectivity
health-check route. Delegates data access to
`app.repositories.DatabaseHealthRepository`; routes never call a
repository directly.
"""

from typing import Optional

from app.models.db_health import DatabaseHealthReport
from app.repositories.db_health_repository import DatabaseHealthRepository


class DBHealthService:
    """Reports combined MongoDB/ChromaDB connectivity status."""

    def __init__(self, repository: Optional[DatabaseHealthRepository] = None) -> None:
        self._repository = repository or DatabaseHealthRepository()

    async def check(self) -> DatabaseHealthReport:
        return await self._repository.check()
