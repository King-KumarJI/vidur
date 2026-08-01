"""Route tests for /api/v1/memory."""

from datetime import datetime, timezone

from app.api.v1.dependencies import get_memory_service
from app.main import app
from app.memory.enums import MemoryRecordType
from app.memory.models import MemoryRecallMatch, MemoryRecord

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _StubService:
    def __init__(self, matches=None, records=None, health_scores=None) -> None:
        self.matches = matches or []
        self.records = records or []
        self.health_scores = health_scores or []
        self.recall_calls = []
        self.history_calls = []
        self.trend_calls = []

    async def recall(self, project_id, query_text, top_k, record_type):
        self.recall_calls.append((project_id, query_text, top_k, record_type))
        return self.matches

    async def history(self, project_id, record_type, limit):
        self.history_calls.append((project_id, record_type, limit))
        return self.records

    async def health_score_trend(self, project_id, record_types, limit):
        self.trend_calls.append((project_id, record_types, limit))
        return self.health_scores


def _record() -> MemoryRecord:
    return MemoryRecord(
        record_id="rec-1",
        project_id="demo-project",
        record_type=MemoryRecordType.INSPECTION,
        recorded_at=_NOW,
        summary="A completed inspection run.",
        payload={"health_score": 90.0},
        health_score=90.0,
    )


def test_recall_without_project_id_header_returns_400(client):
    response = client.post("/api/v1/memory/recall", json={"query_text": "inspection"})
    assert response.status_code == 400


def test_recall_returns_hydrated_matches(client, project_headers):
    stub = _StubService(matches=[MemoryRecallMatch(record=_record(), similarity_score=0.87)])
    app.dependency_overrides[get_memory_service] = lambda: stub

    response = client.post(
        "/api/v1/memory/recall", json={"query_text": "inspection", "top_k": 3}, headers=project_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["similarity_score"] == 0.87
    assert body[0]["record"]["record_id"] == "rec-1"
    assert stub.recall_calls == [("demo-project", "inspection", 3, None)]


def test_get_memory_history(client, project_headers):
    stub = _StubService(records=[_record()])
    app.dependency_overrides[get_memory_service] = lambda: stub

    response = client.get(
        "/api/v1/memory/history", params={"record_type": "inspection", "limit": 5}, headers=project_headers
    )

    assert response.status_code == 200
    assert response.json()["records"][0]["record_id"] == "rec-1"
    assert stub.history_calls == [("demo-project", "inspection", 5)]


def test_get_health_score_trend(client, project_headers):
    stub = _StubService(health_scores=[70.0, 80.0, 90.0])
    app.dependency_overrides[get_memory_service] = lambda: stub

    response = client.get(
        "/api/v1/memory/health-score-trend",
        params=[("record_types", "inspection"), ("record_types", "ml_prediction")],
        headers=project_headers,
    )

    assert response.status_code == 200
    assert response.json()["health_scores"] == [70.0, 80.0, 90.0]
    assert stub.trend_calls == [("demo-project", ["inspection", "ml_prediction"], None)]
