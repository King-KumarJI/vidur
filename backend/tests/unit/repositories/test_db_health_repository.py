"""Unit tests for app.repositories.db_health_repository.

`mongo_ping`/`chroma_ping` are monkeypatched directly on the
repository module (where they are imported as bound names), rather
than on `app.db`, so no real MongoDB/ChromaDB client is touched.
"""

import asyncio

from app.repositories import db_health_repository as repository_module
from app.repositories.db_health_repository import DatabaseHealthRepository


async def _true() -> bool:
    return True


async def _false() -> bool:
    return False


def test_check_reports_both_stores_connected(monkeypatch):
    monkeypatch.setattr(repository_module, "mongo_ping", _true)
    monkeypatch.setattr(repository_module, "chroma_ping", lambda: True)

    report = asyncio.run(DatabaseHealthRepository().check())

    assert report.mongodb_connected is True
    assert report.chromadb_connected is True
    assert report.healthy is True


def test_check_reports_partial_connectivity_as_unhealthy(monkeypatch):
    monkeypatch.setattr(repository_module, "mongo_ping", _false)
    monkeypatch.setattr(repository_module, "chroma_ping", lambda: True)

    report = asyncio.run(DatabaseHealthRepository().check())

    assert report.mongodb_connected is False
    assert report.chromadb_connected is True
    assert report.healthy is False
