"""
VIDUR Core - Deep Learning Vision
Submodule: Enums
Purpose: Shared enumerations used across the Deep Learning Vision
pipeline for risk classification, layout change classification, and
overall comparison verdicts.
"""

from enum import Enum


class VisualRiskLevel(str, Enum):
    """Coarse classification of a visual finding's severity, ordered
    low to high. Used for pixel-diff results, layout-diff results,
    layout consistency issues, and individual findings alike so every
    result in a report reads on the same scale (mirrors
    ml_prediction.enums.RiskLevel)."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        """Numeric weight used to sort/compare by risk level. Higher is
        more severe."""
        return {
            VisualRiskLevel.LOW: 1,
            VisualRiskLevel.MODERATE: 2,
            VisualRiskLevel.HIGH: 3,
            VisualRiskLevel.CRITICAL: 4,
        }[self]


class LayoutChangeType(str, Enum):
    """Kind of structural change detected for a single layout element
    between a baseline and current LayoutSnapshot."""

    ADDED = "added"
    REMOVED = "removed"
    MOVED = "moved"
    RESIZED = "resized"
    MODIFIED = "modified"


class LayoutConsistencyIssueType(str, Enum):
    """Kind of intra-snapshot layout consistency problem detected on a
    single LayoutSnapshot, independent of any baseline comparison."""

    OVERLAPPING_ELEMENTS = "overlapping_elements"
    OFF_CANVAS_ELEMENT = "off_canvas_element"
    ZERO_SIZE_ELEMENT = "zero_size_element"
    DUPLICATE_ELEMENT_ID = "duplicate_element_id"


class ComparisonVerdict(str, Enum):
    """Overall outcome of a single visual comparison run."""

    MATCH = "match"
    MINOR_DIFFERENCE = "minor_difference"
    REGRESSION = "regression"


class EmbeddingComparisonMethod(str, Enum):
    """Which technique produced an ImageEmbeddingComparisonResult.
    CLIP is the primary path (real pretrained vision model, inference
    only); CLASSICAL_FALLBACK is used automatically whenever OpenCLIP/
    torch cannot be imported or the model fails to load, per CLAUDE.md's
    "Real AI/ML/DL/NLP Upgrade" Deep Learning Vision clause."""

    CLIP = "clip"
    CLASSICAL_FALLBACK = "classical_fallback"
