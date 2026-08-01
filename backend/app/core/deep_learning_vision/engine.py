"""
VIDUR Core - Deep Learning Vision
Submodule: Engine
Purpose: Orchestrates a full Deep Learning Vision comparison run
between two caller-supplied VisualSnapshots - pixel diff, layout diff,
layout consistency checking, and visual regression detection - into a
single VisualComparisonReport. Enforces the
MAJOR_DEEP_LEARNING_VISUAL_INSPECTION feature flag (Article 41-44: this
entire module is a Major/advanced capability, ships disabled by
default) and Article 21 (Absolute Project Isolation) by requiring and
binding a valid Project ID for the duration of the run. This module is
analysis-only: it never captures screenshots or drives a browser
itself, it only compares whatever image/layout data the caller
supplies.
"""

from typing import List, Optional

from app.config.feature_flags import FeatureFlag, FeatureFlagRegistry, feature_flags
from app.config.logging_config import get_logger
from app.core.deep_learning_vision.exceptions import (
    DeepLearningVisionDisabledError,
    DeepLearningVisionError,
    InvalidComparisonInputError,
)
from app.core.deep_learning_vision.layout_consistency_checker import LayoutConsistencyChecker
from app.core.deep_learning_vision.layout_diff_analyzer import LayoutDiffAnalyzer
from app.core.deep_learning_vision.models import (
    LayoutConsistencyIssue,
    LayoutDiffResult,
    PixelDiffResult,
    VisualComparisonReport,
    VisualSnapshot,
)
from app.core.deep_learning_vision.pixel_diff_analyzer import PixelDiffAnalyzer
from app.core.deep_learning_vision.report_generator import VisualComparisonReportGenerator
from app.core.deep_learning_vision.visual_regression_detector import VisualRegressionDetector
from app.core.project_isolation import project_scope, validate_project_id_format
from app.core.project_isolation.exceptions import ProjectIsolationError

logger = get_logger("deep_learning_vision.engine")


class DeepLearningVisionEngine:
    """Top-level orchestrator for a single visual comparison run
    between a baseline and current VisualSnapshot."""

    def __init__(
        self,
        pixel_diff_analyzer: Optional[PixelDiffAnalyzer] = None,
        layout_diff_analyzer: Optional[LayoutDiffAnalyzer] = None,
        layout_consistency_checker: Optional[LayoutConsistencyChecker] = None,
        visual_regression_detector: Optional[VisualRegressionDetector] = None,
        report_generator: Optional[VisualComparisonReportGenerator] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
    ) -> None:
        self._pixel_diff_analyzer = pixel_diff_analyzer or PixelDiffAnalyzer()
        self._layout_diff_analyzer = layout_diff_analyzer or LayoutDiffAnalyzer()
        self._layout_consistency_checker = layout_consistency_checker or LayoutConsistencyChecker()
        self._visual_regression_detector = visual_regression_detector or VisualRegressionDetector()
        self._report_generator = report_generator or VisualComparisonReportGenerator()
        self._feature_flags = feature_flag_registry or feature_flags

    def run(
        self,
        project_id: str,
        baseline: VisualSnapshot,
        current: VisualSnapshot,
        canvas_width: Optional[int] = None,
        canvas_height: Optional[int] = None,
    ) -> VisualComparisonReport:
        """Compare `baseline` against `current`, scoped to
        `project_id`.

        Raises DeepLearningVisionDisabledError if
        MAJOR_DEEP_LEARNING_VISUAL_INSPECTION is disabled,
        InvalidProjectIdError if `project_id` fails format validation,
        InvalidComparisonInputError if `baseline`/`current` belong to a
        different project or are not comparable (mismatched
        image/layout presence, or neither snapshot supplies any data),
        and DeepLearningVisionError wrapping any other unexpected
        failure encountered mid-run.
        """
        if not self._feature_flags.is_enabled(FeatureFlag.MAJOR_DEEP_LEARNING_VISUAL_INSPECTION):
            raise DeepLearningVisionDisabledError(
                "Visual comparison was requested but the "
                "MAJOR_DEEP_LEARNING_VISUAL_INSPECTION feature flag is disabled."
            )

        normalized_project_id = validate_project_id_format(project_id)
        if baseline.project_id != normalized_project_id:
            raise InvalidComparisonInputError(
                f"Baseline VisualSnapshot belongs to project "
                f"'{baseline.project_id}', not '{normalized_project_id}'."
            )
        if current.project_id != normalized_project_id:
            raise InvalidComparisonInputError(
                f"Current VisualSnapshot belongs to project "
                f"'{current.project_id}', not '{normalized_project_id}'."
            )

        logger.info(
            "Visual comparison started for project_id=%s baseline=%s current=%s",
            normalized_project_id,
            baseline.label,
            current.label,
        )

        with project_scope(normalized_project_id):
            try:
                report = self._execute(normalized_project_id, baseline, current, canvas_width, canvas_height)
            except (DeepLearningVisionError, ProjectIsolationError):
                raise
            except Exception as exc:  # comparison stages must never crash a whole run
                logger.error(
                    "Visual comparison failed for project_id=%s baseline=%s current=%s: %s",
                    normalized_project_id,
                    baseline.label,
                    current.label,
                    exc,
                )
                raise DeepLearningVisionError(
                    f"Visual comparison run failed for project '{normalized_project_id}': {exc}"
                ) from exc

        logger.info(
            "Visual comparison completed for project_id=%s verdict=%s",
            normalized_project_id,
            report.verdict.value,
        )
        return report

    def _execute(
        self,
        project_id: str,
        baseline: VisualSnapshot,
        current: VisualSnapshot,
        canvas_width: Optional[int],
        canvas_height: Optional[int],
    ) -> VisualComparisonReport:
        pixel_diff: Optional[PixelDiffResult] = None
        if baseline.image is not None and current.image is not None:
            pixel_diff = self._pixel_diff_analyzer.compare(baseline.image, current.image)
        elif (baseline.image is None) != (current.image is None):
            raise InvalidComparisonInputError(
                "Both baseline and current must supply image data, or both must omit it."
            )

        layout_diff: Optional[LayoutDiffResult] = None
        if baseline.layout is not None and current.layout is not None:
            layout_diff = self._layout_diff_analyzer.compare(baseline.layout, current.layout)
        elif (baseline.layout is None) != (current.layout is None):
            raise InvalidComparisonInputError(
                "Both baseline and current must supply layout data, or both must omit it."
            )

        if pixel_diff is None and layout_diff is None:
            raise InvalidComparisonInputError(
                "At least one of image or layout data must be supplied on both snapshots."
            )

        consistency_issues: List[LayoutConsistencyIssue] = []
        if current.layout is not None:
            consistency_issues = self._layout_consistency_checker.check(
                current.layout, canvas_width, canvas_height
            )

        findings, verdict = self._visual_regression_detector.detect(
            pixel_diff, layout_diff, consistency_issues
        )

        return self._report_generator.generate(
            project_id=project_id,
            baseline_label=baseline.label,
            current_label=current.label,
            pixel_diff=pixel_diff,
            layout_diff=layout_diff,
            consistency_issues=consistency_issues,
            findings=findings,
            verdict=verdict,
        )
