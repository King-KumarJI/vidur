"""
VIDUR Core - Deep Learning Vision
Submodule: Report Generator
Purpose: Assemble the outputs of every comparison stage (pixel diff,
layout diff, layout consistency, and visual regression detection) into
a single VisualComparisonReport. Reuses Inspection Engine's `utc_now`
helper for timestamping rather than redefining it (Article 31-32).
"""

from datetime import datetime
from typing import List, Optional

from app.core.deep_learning_vision.enums import ComparisonVerdict
from app.core.deep_learning_vision.models import (
    ImageEmbeddingComparisonResult,
    LayoutConsistencyIssue,
    LayoutDiffResult,
    PixelDiffResult,
    VisualComparisonReport,
    VisualRegressionFinding,
)
from app.core.inspection_engine.models import utc_now

_VERDICT_SUMMARY = {
    ComparisonVerdict.MATCH: "No meaningful visual differences were detected.",
    ComparisonVerdict.MINOR_DIFFERENCE: "Minor visual differences were detected.",
    ComparisonVerdict.REGRESSION: "A visual regression was detected.",
}


class VisualComparisonReportGenerator:
    """Builds the final VisualComparisonReport for a completed
    comparison run."""

    def generate(
        self,
        *,
        project_id: str,
        baseline_label: str,
        current_label: str,
        embedding_diff: Optional[ImageEmbeddingComparisonResult],
        pixel_diff: Optional[PixelDiffResult],
        layout_diff: Optional[LayoutDiffResult],
        consistency_issues: List[LayoutConsistencyIssue],
        findings: List[VisualRegressionFinding],
        verdict: ComparisonVerdict,
        generated_at: Optional[datetime] = None,
    ) -> VisualComparisonReport:
        """Assemble the final VisualComparisonReport for one comparison
        run between `baseline_label` and `current_label`."""
        data_sources = []
        if embedding_diff is not None:
            data_sources.append("real-screenshot embedding data")
        if pixel_diff is not None:
            data_sources.append("pixel data")
        if layout_diff is not None:
            data_sources.append("layout data")

        summary = (
            f"{_VERDICT_SUMMARY[verdict]} Comparing '{baseline_label}' to '{current_label}': "
            f"{len(findings)} finding(s) across {' and '.join(data_sources) or 'no data'}."
        )

        return VisualComparisonReport(
            project_id=project_id,
            baseline_label=baseline_label,
            current_label=current_label,
            generated_at=generated_at or utc_now(),
            embedding_diff=embedding_diff,
            pixel_diff=pixel_diff,
            layout_diff=layout_diff,
            consistency_issues=consistency_issues,
            findings=findings,
            verdict=verdict,
            summary=summary,
        )
