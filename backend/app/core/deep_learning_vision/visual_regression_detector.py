"""
VIDUR Core - Deep Learning Vision
Submodule: Visual Regression Detector
Purpose: Turn the outputs of the Pixel Diff Analyzer, Layout Diff
Analyzer, and Layout Consistency Checker into a single, human-readable
list of VisualRegressionFinding entries plus an overall
ComparisonVerdict (per Chapter VII "visual regression detection").
Advisory only (Article 10-11): never blocks or auto-modifies anything,
it only reports.
"""

from collections import defaultdict
from typing import List, Optional, Tuple

from app.core.deep_learning_vision.enums import ComparisonVerdict, LayoutChangeType, VisualRiskLevel
from app.core.deep_learning_vision.models import (
    LayoutConsistencyIssue,
    LayoutDiffResult,
    PixelDiffResult,
    VisualRegressionFinding,
)

#: A pixel diff or layout diff at or above this risk level produces a
#: finding; anything below is treated as noise (anti-aliasing jitter,
#: incidental single-element drift) and omitted.
MINIMUM_REPORTED_RISK_LEVEL = VisualRiskLevel.MODERATE

REGRESSION_VERDICT_THRESHOLD = VisualRiskLevel.HIGH.weight
MINOR_DIFFERENCE_VERDICT_THRESHOLD = VisualRiskLevel.MODERATE.weight

_NON_REMOVAL_CHANGE_TYPES: Tuple[LayoutChangeType, ...] = (
    LayoutChangeType.ADDED,
    LayoutChangeType.MOVED,
    LayoutChangeType.RESIZED,
    LayoutChangeType.MODIFIED,
)


class VisualRegressionDetector:
    """Derives findings and an overall verdict from comparison
    results."""

    def detect(
        self,
        pixel_diff: Optional[PixelDiffResult],
        layout_diff: Optional[LayoutDiffResult],
        consistency_issues: List[LayoutConsistencyIssue],
    ) -> Tuple[List[VisualRegressionFinding], ComparisonVerdict]:
        findings: List[VisualRegressionFinding] = []
        findings.extend(self._pixel_diff_findings(pixel_diff))
        findings.extend(self._layout_diff_findings(layout_diff))
        findings.extend(self._consistency_findings(consistency_issues))

        # The verdict is driven by each finding's own (possibly
        # escalated) risk level - e.g. a single REMOVED element is
        # always surfaced as HIGH regardless of the overall
        # layout_diff.risk_level - rather than by the three input
        # results' aggregate risk levels directly.
        overall_weight = max([finding.risk_level.weight for finding in findings] + [0])
        verdict = self._classify_verdict(overall_weight)
        return findings, verdict

    @staticmethod
    def _classify_verdict(overall_weight: int) -> ComparisonVerdict:
        if overall_weight >= REGRESSION_VERDICT_THRESHOLD:
            return ComparisonVerdict.REGRESSION
        if overall_weight >= MINOR_DIFFERENCE_VERDICT_THRESHOLD:
            return ComparisonVerdict.MINOR_DIFFERENCE
        return ComparisonVerdict.MATCH

    @staticmethod
    def _pixel_diff_findings(pixel_diff: Optional[PixelDiffResult]) -> List[VisualRegressionFinding]:
        if pixel_diff is None or pixel_diff.risk_level.weight < MINIMUM_REPORTED_RISK_LEVEL.weight:
            return []
        return [
            VisualRegressionFinding(
                category="pixel_diff",
                risk_level=pixel_diff.risk_level,
                message=(
                    f"{pixel_diff.changed_pixel_count} of {pixel_diff.total_pixel_count} pixels "
                    f"changed ({pixel_diff.diff_ratio:.1%}) across {len(pixel_diff.regions)} "
                    f"region(s)."
                ),
            )
        ]

    @staticmethod
    def _layout_diff_findings(layout_diff: Optional[LayoutDiffResult]) -> List[VisualRegressionFinding]:
        if layout_diff is None:
            return []

        findings: List[VisualRegressionFinding] = []

        # Every removal is reported individually: an element disappearing
        # is a concrete, actionable regression regardless of how many
        # other elements changed in the same run.
        for change in layout_diff.changes_of_type(LayoutChangeType.REMOVED):
            findings.append(
                VisualRegressionFinding(
                    category="layout_diff",
                    risk_level=VisualRiskLevel.HIGH,
                    message=change.detail,
                    element_id=change.element_id,
                )
            )

        if layout_diff.risk_level.weight < MINIMUM_REPORTED_RISK_LEVEL.weight:
            return findings

        counts_by_type = defaultdict(int)
        for change in layout_diff.changes:
            if change.change_type in _NON_REMOVAL_CHANGE_TYPES:
                counts_by_type[change.change_type] += 1

        for change_type in _NON_REMOVAL_CHANGE_TYPES:
            count = counts_by_type.get(change_type, 0)
            if count > 0:
                findings.append(
                    VisualRegressionFinding(
                        category="layout_diff",
                        risk_level=layout_diff.risk_level,
                        message=f"{count} element(s) were {change_type.value} between baseline and current layout.",
                    )
                )

        return findings

    @staticmethod
    def _consistency_findings(
        consistency_issues: List[LayoutConsistencyIssue],
    ) -> List[VisualRegressionFinding]:
        return [
            VisualRegressionFinding(
                category="layout_consistency",
                risk_level=issue.risk_level,
                message=issue.detail,
                element_id=issue.element_ids[0] if issue.element_ids else None,
            )
            for issue in consistency_issues
        ]
