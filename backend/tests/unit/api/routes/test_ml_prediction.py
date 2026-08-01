"""Route tests for /api/v1/ml-prediction, including the
MAJOR_ML_RISK_PREDICTION feature-flag-disabled path (Article 41-44:
ships disabled by default, mapped to HTTP 403)."""

from app.api.v1.dependencies import get_ml_prediction_service
from app.core.ml_prediction.exceptions import MLPredictionDisabledError
from app.main import app


class _StubService:
    def __init__(self, report=None, error=None) -> None:
        self.report = report
        self.error = error
        self.calls = []

    async def run(self, project_id, root_path, include_reasoning=True):
        self.calls.append((project_id, root_path, include_reasoning))
        if self.error:
            raise self.error
        return self.report


def test_run_ml_prediction_maps_disabled_feature_flag_to_403(client, project_headers):
    stub = _StubService(
        error=MLPredictionDisabledError(
            "ML prediction was requested but the MAJOR_ML_RISK_PREDICTION feature flag is disabled."
        )
    )
    app.dependency_overrides[get_ml_prediction_service] = lambda: stub

    response = client.post("/api/v1/ml-prediction/run", json={"root_path": "/tmp/demo"}, headers=project_headers)

    assert response.status_code == 403
    assert response.json()["error"] == "MLPredictionDisabledError"


def test_run_ml_prediction_without_project_id_header_returns_400(client):
    response = client.post("/api/v1/ml-prediction/run", json={"root_path": "/tmp/demo"})
    assert response.status_code == 400


def test_run_ml_prediction_passes_include_reasoning_flag(client, project_headers):
    stub = _StubService(error=MLPredictionDisabledError("disabled"))
    app.dependency_overrides[get_ml_prediction_service] = lambda: stub

    client.post(
        "/api/v1/ml-prediction/run",
        json={"root_path": "/tmp/demo", "include_reasoning": False},
        headers=project_headers,
    )

    assert stub.calls == [("demo-project", "/tmp/demo", False)]
