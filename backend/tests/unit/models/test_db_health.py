"""Unit tests for app.models.db_health.DatabaseHealthReport."""

from datetime import datetime, timezone

from app.models.db_health import DatabaseHealthReport

_NOW = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)


def test_healthy_is_true_only_when_both_stores_connected():
    assert DatabaseHealthReport(mongodb_connected=True, chromadb_connected=True, checked_at=_NOW).healthy is True
    assert DatabaseHealthReport(mongodb_connected=True, chromadb_connected=False, checked_at=_NOW).healthy is False
    assert DatabaseHealthReport(mongodb_connected=False, chromadb_connected=True, checked_at=_NOW).healthy is False


def test_to_dict_serializes_all_fields():
    report = DatabaseHealthReport(mongodb_connected=True, chromadb_connected=True, checked_at=_NOW)

    assert report.to_dict() == {
        "mongodb_connected": True,
        "chromadb_connected": True,
        "healthy": True,
        "checked_at": _NOW.isoformat(),
    }
