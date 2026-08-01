"""Unit tests for app.memory.semantic_index.

Exercised against an in-memory fake standing in for a chromadb
Collection, since no live ChromaDB server is available in this
environment. MemorySemanticIndex accepts an injectable
`collection_provider` for exactly this purpose.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from app.memory.enums import MemoryRecordType
from app.memory.exceptions import MemoryPersistenceError
from app.memory.models import MemoryRecord
from app.memory.semantic_index import MemorySemanticIndex

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FakeChromaCollection:
    """Deterministic stand-in for a chromadb Collection: documents that
    contain the query text (case-insensitive) score a distance of 0.0,
    everything else scores 1.0, so ranking is unambiguous in tests."""

    def __init__(self, fail: bool = False) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}
        self._fail = fail

    def upsert(self, ids: List[str], documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        if self._fail:
            raise RuntimeError("simulated chroma failure")
        for record_id, document, metadata in zip(ids, documents, metadatas):
            self._items[record_id] = {"document": document, "metadata": metadata}

    def query(self, query_texts: List[str], n_results: int, where: Optional[Dict[str, Any]] = None):
        if self._fail:
            raise RuntimeError("simulated chroma failure")
        query_text = query_texts[0].lower()
        candidates = []
        for record_id, item in self._items.items():
            if where and not all(item["metadata"].get(k) == v for k, v in where.items()):
                continue
            distance = 0.0 if query_text in item["document"].lower() else 1.0
            candidates.append((record_id, distance))
        candidates.sort(key=lambda pair: pair[1])
        candidates = candidates[:n_results]
        return {
            "ids": [[record_id for record_id, _ in candidates]],
            "distances": [[distance for _, distance in candidates]],
        }


def _index(fail: bool = False) -> MemorySemanticIndex:
    collections: Dict[str, _FakeChromaCollection] = {}

    def provider(project_id: str) -> _FakeChromaCollection:
        return collections.setdefault(project_id, _FakeChromaCollection(fail=fail))

    return MemorySemanticIndex(collection_provider=provider)


def _record(record_id: str, summary: str, record_type=MemoryRecordType.INSPECTION) -> MemoryRecord:
    return MemoryRecord(
        record_id=record_id,
        project_id="demo-project",
        record_type=record_type,
        recorded_at=_NOW,
        summary=summary,
        payload={},
        health_score=None,
    )


def test_index_and_query_returns_best_match_first():
    index = _index()
    index.index(_record("rec-1", "authentication module regression found"))
    index.index(_record("rec-2", "unrelated formatting cleanup"))

    matches = index.query("demo-project", "authentication", top_k=5)

    assert matches[0].record_id == "rec-1"
    assert matches[0].similarity_score == 1.0


def test_query_respects_top_k():
    index = _index()
    index.index(_record("rec-1", "authentication issue"))
    index.index(_record("rec-2", "authentication issue too"))
    index.index(_record("rec-3", "authentication issue as well"))

    matches = index.query("demo-project", "authentication issue", top_k=2)

    assert len(matches) == 2


def test_query_filters_by_record_type():
    index = _index()
    index.index(_record("rec-1", "risk finding", record_type=MemoryRecordType.INSPECTION))
    index.index(_record("rec-2", "risk finding", record_type=MemoryRecordType.ML_PREDICTION))

    matches = index.query("demo-project", "risk finding", record_type=MemoryRecordType.ML_PREDICTION)

    assert [match.record_id for match in matches] == ["rec-2"]


def test_query_with_no_matches_returns_empty_list():
    index = _index()
    assert index.query("demo-project", "anything") == []


def test_index_wraps_underlying_errors():
    index = _index(fail=True)
    with pytest.raises(MemoryPersistenceError):
        index.index(_record("rec-1", "summary"))


def test_query_wraps_underlying_errors():
    index = _index(fail=True)
    with pytest.raises(MemoryPersistenceError):
        index.query("demo-project", "summary")
