"""Unit tests for app.memory.models."""

from datetime import datetime, timezone

from app.memory.enums import MemoryRecordType
from app.memory.models import MemoryRecallMatch, MemoryRecord, MemorySemanticMatch


def _record(**overrides) -> MemoryRecord:
    defaults = dict(
        record_id="rec-1",
        project_id="demo-project",
        record_type=MemoryRecordType.INSPECTION,
        recorded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        summary="Inspection run summary.",
        payload={"health_score": 88.5},
        health_score=88.5,
    )
    defaults.update(overrides)
    return MemoryRecord(**defaults)


def test_memory_record_to_dict_serializes_all_fields():
    record = _record()
    result = record.to_dict()

    assert result["record_id"] == "rec-1"
    assert result["project_id"] == "demo-project"
    assert result["record_type"] == "inspection"
    assert result["recorded_at"] == "2026-01-01T00:00:00+00:00"
    assert result["summary"] == "Inspection run summary."
    assert result["payload"] == {"health_score": 88.5}
    assert result["health_score"] == 88.5


def test_memory_record_health_score_defaults_to_none():
    record = _record(health_score=None)
    assert record.to_dict()["health_score"] is None


def test_memory_semantic_match_to_dict():
    match = MemorySemanticMatch(record_id="rec-1", similarity_score=0.75)
    assert match.to_dict() == {"record_id": "rec-1", "similarity_score": 0.75}


def test_memory_recall_match_to_dict_embeds_full_record():
    record = _record()
    match = MemoryRecallMatch(record=record, similarity_score=0.9)

    result = match.to_dict()

    assert result["similarity_score"] == 0.9
    assert result["record"] == record.to_dict()
