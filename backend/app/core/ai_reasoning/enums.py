"""
VIDUR Core - AI Reasoning
Submodule: Enums
Purpose: Shared enumerations used across the AI Reasoning pipeline for
recommendation priority, insight category, correlation basis, and
drift churn level.
"""

from enum import Enum


class RecommendationPriority(str, Enum):
    """Priority of a single Recommendation, ordered low to high."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        """Numeric weight used to sort recommendations. Higher is more
        urgent."""
        return {
            RecommendationPriority.LOW: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.HIGH: 3,
            RecommendationPriority.CRITICAL: 4,
        }[self]


class InsightCategory(str, Enum):
    """Classification of which reasoning stage produced an insight or
    recommendation."""

    ISSUE_CORRELATION = "issue_correlation"
    DEPENDENCY_IMPACT = "dependency_impact"
    DEBUGGING_ASSISTANCE = "debugging_assistance"
    DRIFT_SIGNIFICANCE = "drift_significance"


class CorrelationBasis(str, Enum):
    """The shared signal that grouped a set of findings together."""

    SAME_FILE = "same_file"
    SAME_CODE = "same_code"


class ChurnLevel(str, Enum):
    """Coarse classification of how much a project's file inventory
    changed between two inspections."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
