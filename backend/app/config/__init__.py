"""
VIDUR Core Configuration Package.

Exposes the application settings singleton, the feature flag registry,
and the logging configuration entry point as the single import surface
for all other modules.
"""

from app.config.feature_flags import FeatureFlag, feature_flags
from app.config.logging_config import configure_logging, get_logger
from app.config.settings import settings

__all__ = [
    "settings",
    "feature_flags",
    "FeatureFlag",
    "configure_logging",
    "get_logger",
]
