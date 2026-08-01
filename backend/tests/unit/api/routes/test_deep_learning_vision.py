"""Route tests for /api/v1/deep-learning-vision, including the
MAJOR_DEEP_LEARNING_VISUAL_INSPECTION feature-flag-disabled path
(Article 41-44: ships disabled by default, mapped to HTTP 403)."""

from datetime import datetime, timezone

from app.api.v1.dependencies import get_deep_learning_vision_service
from app.core.deep_learning_vision.enums import ComparisonVerdict
from app.core.deep_learning_vision.exceptions import DeepLearningVisionDisabledError
from app.core.deep_learning_vision.models import VisualComparisonReport
from app.main import app

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

_BODY = {
    "baseline": {"label": "before"},
    "current": {"label": "after"},
}


class _StubService:
    def __init__(self, report=None, error=None) -> None:
        self.report = report
        self.error = error

    async def run(self, project_id, baseline, current, canvas_width=None, canvas_height=None):
        if self.error:
            raise self.error
        return self.report


def test_compare_maps_disabled_feature_flag_to_403(client, project_headers):
    stub = _StubService(
        error=DeepLearningVisionDisabledError(
            "Visual comparison was requested but the MAJOR_DEEP_LEARNING_VISUAL_INSPECTION feature flag is disabled."
        )
    )
    app.dependency_overrides[get_deep_learning_vision_service] = lambda: stub

    response = client.post("/api/v1/deep-learning-vision/compare", json=_BODY, headers=project_headers)

    assert response.status_code == 403
    assert response.json()["error"] == "DeepLearningVisionDisabledError"


def test_compare_without_project_id_header_returns_400(client):
    response = client.post("/api/v1/deep-learning-vision/compare", json=_BODY)
    assert response.status_code == 400


def test_compare_returns_serialized_report(client, project_headers):
    report = VisualComparisonReport(
        project_id="demo-project",
        baseline_label="before",
        current_label="after",
        generated_at=_NOW,
        verdict=ComparisonVerdict.MATCH,
        summary="No visual differences detected.",
    )
    app.dependency_overrides[get_deep_learning_vision_service] = lambda: _StubService(report=report)

    response = client.post("/api/v1/deep-learning-vision/compare", json=_BODY, headers=project_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "match"
    assert body["summary"] == "No visual differences detected."
