"""
VIDUR Schemas
Submodule: Config
Purpose: Response shapes for the Core Configuration module's routes -
non-secret application identity and the resolved state of every
registered feature flag.
"""

from typing import Dict

from pydantic import BaseModel, ConfigDict


class AppInfoResponse(BaseModel):
    """Non-secret application identity, sourced from
    `app.config.settings.settings`."""

    model_config = ConfigDict(extra="forbid")

    app_name: str
    app_full_name: str
    app_version: str
    constitution_version: str
    environment: str
    debug: bool


class FeatureFlagsResponse(BaseModel):
    """Resolved state of every registered feature flag, sourced from
    `app.config.feature_flags.feature_flags`."""

    model_config = ConfigDict(extra="forbid")

    flags: Dict[str, bool]
