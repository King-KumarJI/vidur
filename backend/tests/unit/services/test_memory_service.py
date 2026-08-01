"""Unit tests for app.services.memory_service.

Exercises MemoryService's thin pass-through to MemoryEngine plus its
own `record_type` string -> enum validation, against a stub
MemoryEngine.
"""

import asyncio
from datetime import datetime, timezone
from typing import List

import pytest

from app.memory.enums import MemoryRecordType
from app.memory.exceptions import InvalidMemoryQueryError
from app.memory.models import MemoryRecallMatch, MemoryRecord
from app.services.memory_service import MemoryService

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubMemoryEngine:
    def __init__(self) -> None:
        self.recall_calls: List[tuple] = []
        self.history_calls: List[tuple] = []
        self.trend_calls: List[tuple] = []

    async def recall(self, project_id, query_text, top_k, record_type):
        self.recall_calls.append((project_id, query_text, top_k, record_type))
        record = MemoryRecord(
            record_id="rec-1",
            project_id=project_id,
            record_type=MemoryRecordType.INSPECTION,
            recorded_at=_NOW,
            summary="stub",
            payload={},
        )
        return [MemoryRecallMatch(record=record, similarity_score=0.9)]

    async def history(self, project_id, record_type, limit):
        self.history_calls.append((project_id, record_type, limit))
        return []

    async def health_score_trend(self, project_id, record_types, limit):
        self.trend_calls.append((project_id, record_types, limit))
        return [70.0, 80.0]


def test_recall_parses_record_type_and_delegates():
    engine = _StubMemoryEngine()
    service = MemoryService(engine=engine)

    matches = asyncio.run(service.recall("demo-project", "query", 5, "inspection"))

    assert engine.recall_calls == [("demo-project", "query", 5, MemoryRecordType.INSPECTION)]
    assert matches[0].similarity_score == 0.9


def test_recall_raises_for_invalid_record_type():
    service = MemoryService(engine=_StubMemoryEngine())
    with pytest.raises(InvalidMemoryQueryError):
        asyncio.run(service.recall("demo-project", "query", 5, "not-a-real-type"))


def test_history_passes_none_record_type_through():
    engine = _StubMemoryEngine()
    service = MemoryService(engine=engine)

    asyncio.run(service.history("demo-project", None, 10))

    assert engine.history_calls == [("demo-project", None, 10)]


def test_health_score_trend_parses_multiple_record_types():
    engine = _StubMemoryEngine()
    service = MemoryService(engine=engine)

    scores = asyncio.run(service.health_score_trend("demo-project", ["inspection", "ml_prediction"], None))

    assert engine.trend_calls == [
        ("demo-project", [MemoryRecordType.INSPECTION, MemoryRecordType.ML_PREDICTION], None)
    ]
    assert scores == [70.0, 80.0]


def test_health_score_trend_passes_none_when_no_record_types_given():
    engine = _StubMemoryEngine()
    service = MemoryService(engine=engine)

    asyncio.run(service.health_score_trend("demo-project", None, 5))

    assert engine.trend_calls == [("demo-project", None, 5)]
