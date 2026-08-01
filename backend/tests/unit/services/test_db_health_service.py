"""Unit tests for app.services.db_health_service."""

import asyncio
from datetime import datetime, timezone

from app.models.db_health import DatabaseHealthReport
from app.services.db_health_service import DBHealthService


class _StubRepository:
    def __init__(self, report: DatabaseHealthReport) -> None:
        self.report = report

    async def check(self) -> DatabaseHealthReport:
        return self.report


def test_check_delegates_to_repository():
    report = DatabaseHealthReport(
        mongodb_connected=True, chromadb_connected=False, checked_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    service = DBHealthService(repository=_StubRepository(report))

    result = asyncio.run(service.check())

    assert result is report
