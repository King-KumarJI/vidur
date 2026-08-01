"""
VIDUR Core - Deep Learning Vision Package.

Single import surface for running a Deep Learning Vision comparison
between two caller-supplied VisualSnapshots: pixel-level image diffing,
layout structural diffing, layout consistency checking, and visual
regression detection, aggregated into a single VisualComparisonReport.
Analysis-only - this module never captures screenshots or drives a
browser itself, and depends on nothing beyond the Python standard
library. Ships disabled by default behind the
MAJOR_DEEP_LEARNING_VISUAL_INSPECTION feature flag (Article 41-44).
"""

from app.core.deep_learning_vision.engine import DeepLearningVisionEngine
from app.core.deep_learning_vision.enums import (
    ComparisonVerdict,
    LayoutChangeType,
    LayoutConsistencyIssueType,
    VisualRiskLevel,
)
from app.core.deep_learning_vision.exceptions import (
    DeepLearningVisionDisabledError,
    DeepLearningVisionError,
    ImageDimensionMismatchError,
    InvalidComparisonInputError,
    InvalidImageDataError,
    InvalidLayoutDataError,
)
from app.core.deep_learning_vision.layout_consistency_checker import LayoutConsistencyChecker
from app.core.deep_learning_vision.layout_diff_analyzer import LayoutDiffAnalyzer
from app.core.deep_learning_vision.models import (
    BoundingBox,
    LayoutConsistencyIssue,
    LayoutDiffResult,
    LayoutElement,
    LayoutElementChange,
    LayoutSnapshot,
    PixelDiffRegion,
    PixelDiffResult,
    PixelImage,
    VisualComparisonReport,
    VisualRegressionFinding,
    VisualSnapshot,
)
from app.core.deep_learning_vision.pixel_diff_analyzer import PixelDiffAnalyzer
from app.core.deep_learning_vision.report_generator import VisualComparisonReportGenerator
from app.core.deep_learning_vision.visual_regression_detector import VisualRegressionDetector

__all__ = [
    "DeepLearningVisionEngine",
    "PixelDiffAnalyzer",
    "LayoutDiffAnalyzer",
    "LayoutConsistencyChecker",
    "VisualRegressionDetector",
    "VisualComparisonReportGenerator",
    "VisualRiskLevel",
    "LayoutChangeType",
    "LayoutConsistencyIssueType",
    "ComparisonVerdict",
    "BoundingBox",
    "PixelImage",
    "LayoutElement",
    "LayoutSnapshot",
    "VisualSnapshot",
    "PixelDiffRegion",
    "PixelDiffResult",
    "LayoutElementChange",
    "LayoutDiffResult",
    "LayoutConsistencyIssue",
    "VisualRegressionFinding",
    "VisualComparisonReport",
    "DeepLearningVisionError",
    "DeepLearningVisionDisabledError",
    "InvalidImageDataError",
    "InvalidLayoutDataError",
    "ImageDimensionMismatchError",
    "InvalidComparisonInputError",
]
