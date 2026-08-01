"""
VIDUR Core - ML Prediction
Submodule: Enums
Purpose: Shared enumerations used across the ML Prediction pipeline for
risk classification and quality-trend direction.
"""

from enum import Enum


class RiskLevel(str, Enum):
    """Coarse classification of a predicted risk score, ordered low to
    high. Used for regression risk, technical debt, failure
    probability, and per-module risk scores alike so every prediction
    in a report reads on the same scale."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        """Numeric weight used to sort/filter by risk level. Higher is
        more severe."""
        return {
            RiskLevel.LOW: 1,
            RiskLevel.MODERATE: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }[self]


class TrendDirection(str, Enum):
    """Direction of a project's predicted health-score trend across
    successive inspection runs."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    UNKNOWN = "unknown"
