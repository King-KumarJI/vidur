"""
VIDUR Core - Inspection Engine
Submodule: Enums
Purpose: Shared enumerations used across the inspection pipeline for
finding severity, finding category, and inspection lifecycle status.
"""

from enum import Enum


class Severity(str, Enum):
    """Severity of a single inspection finding, ordered low to high."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        """Numeric weight used by health score aggregation. Higher is
        more severe."""
        return {
            Severity.INFO: 1,
            Severity.WARNING: 3,
            Severity.ERROR: 7,
            Severity.CRITICAL: 15,
        }[self]


class FindingCategory(str, Enum):
    """Classification of what an inspection finding is about."""

    SYNTAX = "syntax"
    CODE_QUALITY = "code_quality"
    DEPENDENCY = "dependency"
    ARCHITECTURE = "architecture"
    DRIFT = "drift"


class InspectionStatus(str, Enum):
    """Lifecycle status of a single inspection run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
