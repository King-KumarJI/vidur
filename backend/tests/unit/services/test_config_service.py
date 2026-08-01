"""Unit tests for app.services.config_service."""

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.config.settings import Settings
from app.services.config_service import ConfigService


def _settings() -> Settings:
    return Settings(
        SECRET_KEY="test-only-secret-key-do-not-use",
        MONGODB_URI="mongodb://localhost:27017",
        APP_NAME="VIDUR-TEST",
        ENVIRONMENT="development",
    )


def test_app_info_reflects_injected_settings():
    service = ConfigService(app_settings=_settings())

    info = service.app_info()

    assert info["app_name"] == "VIDUR-TEST"
    assert info["environment"] == "development"
    assert "constitution_version" in info


def test_feature_flag_state_reflects_injected_registry():
    registry = FeatureFlagRegistry(overrides=FeatureFlagSettings(MAJOR_ML_RISK_PREDICTION=True))
    service = ConfigService(feature_flag_registry=registry)

    state = service.feature_flag_state()

    assert state["flags"]["MAJOR_ML_RISK_PREDICTION"] is True
    assert state["flags"]["MINOR_PROJECT_INSPECTION"] is True
