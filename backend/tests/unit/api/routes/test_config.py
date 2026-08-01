"""Route tests for /api/v1/config (exempt from ProjectIsolationMiddleware)."""

from app.api.v1.dependencies import get_config_service
from app.main import app


class _StubService:
    def app_info(self) -> dict:
        return {
            "app_name": "VIDUR",
            "app_full_name": "Virtual Intelligent Development Understanding & Reasoning",
            "app_version": "0.1.0",
            "constitution_version": "1.0",
            "environment": "development",
            "debug": False,
        }

    def feature_flag_state(self) -> dict:
        return {"flags": {"MINOR_PROJECT_INSPECTION": True, "MAJOR_ML_RISK_PREDICTION": False}}


def test_get_app_info_requires_no_project_id_header(client):
    app.dependency_overrides[get_config_service] = lambda: _StubService()

    response = client.get("/api/v1/config/info")

    assert response.status_code == 200
    assert response.json()["app_name"] == "VIDUR"


def test_get_feature_flags(client):
    app.dependency_overrides[get_config_service] = lambda: _StubService()

    response = client.get("/api/v1/config/feature-flags")

    assert response.status_code == 200
    assert response.json()["flags"]["MAJOR_ML_RISK_PREDICTION"] is False
