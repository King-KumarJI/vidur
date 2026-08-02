"""
VIDUR Core - Specs Package.

Single import surface for Specs telemetry ingestion and storage
(Personal / Computer / Calendar / Environmental metrics, per CLAUDE.md's
Specs Module section) and manual deadline entries, scoped to a
project's own isolated MongoDB database via the project-isolation + db
pattern (Article 21). Gated by the MAJOR_IOT_ENVIRONMENTAL_ANALYTICS
feature flag (Article 41-44), disabled by default as Major-Project
advanced infrastructure.

Scope (explicit, user-directed): storage and ingestion only. No ML
prediction and no local agent live in this package yet.
"""

from app.core.specs.enums import MetricStatus
from app.core.specs.exceptions import (
    InvalidSpecsPayloadError,
    SpecsDisabledError,
    SpecsModuleError,
    SpecsPersistenceError,
)
from app.core.specs.models import (
    CalendarSnapshot,
    ComputerMetrics,
    Deadline,
    EnvironmentalMetrics,
    MetricReading,
    PersonalMetrics,
    SpecsSnapshot,
)
from app.core.specs.storage import SpecsStorage

__all__ = [
    "MetricStatus",
    "SpecsModuleError",
    "SpecsDisabledError",
    "InvalidSpecsPayloadError",
    "SpecsPersistenceError",
    "MetricReading",
    "PersonalMetrics",
    "ComputerMetrics",
    "EnvironmentalMetrics",
    "SpecsSnapshot",
    "Deadline",
    "CalendarSnapshot",
    "SpecsStorage",
]
