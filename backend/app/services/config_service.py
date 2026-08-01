"""
VIDUR Services
Submodule: Config Service
Purpose: Orchestration logic for the Core Configuration module's
routes. Thin read-through over the existing `settings` and
`feature_flags` singletons - no new state, no persistence.
"""

from typing import Optional

from app.config.feature_flags import FeatureFlagRegistry, feature_flags
from app.config.settings import Settings, settings


class ConfigService:
    """Read-only access to application identity and feature flag
    state for the API Layer."""

    def __init__(
        self,
        app_settings: Optional[Settings] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
    ) -> None:
        self._settings = app_settings or settings
        self._feature_flags = feature_flag_registry or feature_flags

    def app_info(self) -> dict:
        return {
            "app_name": self._settings.APP_NAME,
            "app_full_name": self._settings.APP_FULL_NAME,
            "app_version": self._settings.APP_VERSION,
            "constitution_version": self._settings.CONSTITUTION_VERSION,
            "environment": self._settings.ENVIRONMENT,
            "debug": self._settings.DEBUG,
        }

    def feature_flag_state(self) -> dict:
        return {"flags": self._feature_flags.all_flags()}
