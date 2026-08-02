"""
VIDUR Core Configuration
Module: Core Configuration
Submodule: Feature Flags
Purpose: Centralized feature flag registry controlling Minor vs Major
project capabilities, per Articles 41-44 of the VIDUR Constitution.

Major Project capabilities must exist in the codebase, compile, and
integrate, but remain disabled until explicitly activated here or via
environment variables. Activation requires no architectural change.
"""

from enum import Enum
from functools import lru_cache
from typing import Dict, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlag(str, Enum):
    """Registry of all VIDUR feature flags.

    MINOR_* flags represent the ~90% baseline capability set.
    MAJOR_* flags represent the ~10% advanced capability set that ships
    disabled by default (Article 41).
    """

    # --- Minor Project (baseline, enabled by default) ---
    MINOR_PROJECT_INSPECTION = "MINOR_PROJECT_INSPECTION"
    MINOR_AI_REASONING = "MINOR_AI_REASONING"
    MINOR_REQUIREMENT_CONSISTENCY = "MINOR_REQUIREMENT_CONSISTENCY"
    MINOR_ARCHITECTURE_CONSISTENCY = "MINOR_ARCHITECTURE_CONSISTENCY"
    MINOR_PROJECT_MEMORY = "MINOR_PROJECT_MEMORY"
    MINOR_BASIC_ANALYTICS = "MINOR_BASIC_ANALYTICS"

    # --- Major Project (advanced, disabled by default) ---
    MAJOR_DEEP_LEARNING_VISUAL_INSPECTION = "MAJOR_DEEP_LEARNING_VISUAL_INSPECTION"
    MAJOR_ML_RISK_PREDICTION = "MAJOR_ML_RISK_PREDICTION"
    MAJOR_IOT_ENVIRONMENTAL_ANALYTICS = "MAJOR_IOT_ENVIRONMENTAL_ANALYTICS"
    MAJOR_ADVANCED_NLP_DOCUMENT_REASONING = "MAJOR_ADVANCED_NLP_DOCUMENT_REASONING"
    MAJOR_PREDICTIVE_DASHBOARDS = "MAJOR_PREDICTIVE_DASHBOARDS"


# Default state for every flag. Minor flags default True, Major flags
# default False, in accordance with Article 41 and Article 42.
_DEFAULT_FLAG_STATE: Dict["FeatureFlag", bool] = {
    FeatureFlag.MINOR_PROJECT_INSPECTION: True,
    FeatureFlag.MINOR_AI_REASONING: True,
    FeatureFlag.MINOR_REQUIREMENT_CONSISTENCY: True,
    FeatureFlag.MINOR_ARCHITECTURE_CONSISTENCY: True,
    FeatureFlag.MINOR_PROJECT_MEMORY: True,
    FeatureFlag.MINOR_BASIC_ANALYTICS: True,
    FeatureFlag.MAJOR_DEEP_LEARNING_VISUAL_INSPECTION: True,
    FeatureFlag.MAJOR_ML_RISK_PREDICTION: False,
    FeatureFlag.MAJOR_IOT_ENVIRONMENTAL_ANALYTICS: True,
    FeatureFlag.MAJOR_ADVANCED_NLP_DOCUMENT_REASONING: False,
    FeatureFlag.MAJOR_PREDICTIVE_DASHBOARDS: False,
}


class FeatureFlagSettings(BaseSettings):
    """Environment-driven overrides for feature flags.

    Any flag can be overridden via an environment variable of the same
    name (e.g. MAJOR_ML_RISK_PREDICTION=true) without code changes,
    satisfying Article 44 (Activation Law).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MINOR_PROJECT_INSPECTION: bool = True
    MINOR_AI_REASONING: bool = True
    MINOR_REQUIREMENT_CONSISTENCY: bool = True
    MINOR_ARCHITECTURE_CONSISTENCY: bool = True
    MINOR_PROJECT_MEMORY: bool = True
    MINOR_BASIC_ANALYTICS: bool = True

    MAJOR_DEEP_LEARNING_VISUAL_INSPECTION: bool = True
    MAJOR_ML_RISK_PREDICTION: bool = False
    MAJOR_IOT_ENVIRONMENTAL_ANALYTICS: bool = True
    MAJOR_ADVANCED_NLP_DOCUMENT_REASONING: bool = False
    MAJOR_PREDICTIVE_DASHBOARDS: bool = False


class FeatureFlagRegistry:
    """Centralized, read-through feature flag registry.

    All Major Project functionality must be checked through this
    registry exclusively (Article 42). No module may bypass it.
    """

    def __init__(self, overrides: Optional[FeatureFlagSettings] = None) -> None:
        self._overrides = overrides or FeatureFlagSettings()

    def is_enabled(self, flag: FeatureFlag) -> bool:
        """Return whether a given feature flag is currently active."""
        return bool(getattr(self._overrides, flag.value, _DEFAULT_FLAG_STATE.get(flag, False)))

    def all_flags(self) -> Dict[str, bool]:
        """Return the resolved state of every registered flag."""
        return {flag.value: self.is_enabled(flag) for flag in FeatureFlag}


@lru_cache
def get_feature_flags() -> FeatureFlagRegistry:
    """Return a cached singleton FeatureFlagRegistry instance."""
    return FeatureFlagRegistry()


feature_flags = get_feature_flags()
