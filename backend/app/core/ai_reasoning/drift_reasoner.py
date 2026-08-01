"""
VIDUR Core - AI Reasoning
Submodule: Drift Reasoner
Purpose: Interpret Inspection Engine drift findings (files added,
removed, modified since the previous snapshot) into an overall churn
assessment, cross-referenced against dependency-impact data to flag
drifted files that also carry a significant blast radius.
"""

from typing import List, Optional, Set

from app.core.ai_reasoning.enums import ChurnLevel
from app.core.ai_reasoning.models import DependencyImpactAssessment, DriftInsight
from app.core.inspection_engine.enums import FindingCategory
from app.core.inspection_engine.models import Finding

#: Fraction of total inspected files that must have drifted before the
#: run is classified as HIGH / MODERATE churn. Anything below MODERATE
#: but with at least one drift finding is LOW.
HIGH_CHURN_RATIO = 0.3
MODERATE_CHURN_RATIO = 0.1

#: Minimum dependency risk score (see DependencyReasoner) for a
#: drifted, non-removed file to be flagged as high-impact drift.
HIGH_IMPACT_RISK_THRESHOLD = 2.0


class DriftReasoner:
    """Derives a single DriftInsight from a run's drift-category
    findings and its dependency-impact assessments."""

    def reason(
        self,
        findings: List[Finding],
        dependency_assessments: List[DependencyImpactAssessment],
        total_files: int,
    ) -> Optional[DriftInsight]:
        """Return a DriftInsight, or None if the run has no drift
        findings (for example, a project's first-ever inspection, which
        has nothing to diff against)."""
        drift_findings = [f for f in findings if f.category is FindingCategory.DRIFT]
        if not drift_findings:
            return None

        added = [f for f in drift_findings if f.code == "FILE_ADDED"]
        removed = [f for f in drift_findings if f.code == "FILE_REMOVED"]
        modified = [f for f in drift_findings if f.code == "FILE_MODIFIED"]

        churn_ratio = len(drift_findings) / max(total_files, 1)
        churn_level = self._classify_churn(churn_ratio)

        risk_by_file = {assessment.file_path: assessment.risk_score for assessment in dependency_assessments}
        high_impact_files: Set[str] = set()
        # A removed file's impact can no longer be measured against the
        # current dependency graph (it is gone), so any removal is
        # treated as high-impact on its own.
        high_impact_files.update(f.file_path for f in removed if f.file_path is not None)
        for finding in added + modified:
            if finding.file_path is None:
                continue
            if risk_by_file.get(finding.file_path, 0.0) >= HIGH_IMPACT_RISK_THRESHOLD:
                high_impact_files.add(finding.file_path)

        summary = (
            f"{len(drift_findings)} of {total_files} files drifted since the "
            f"previous inspection ({len(added)} added, {len(removed)} removed, "
            f"{len(modified)} modified), classified as {churn_level.value} churn."
        )
        if high_impact_files:
            summary += (
                f" {len(high_impact_files)} drifted file(s) also carry a "
                "significant dependency blast radius and warrant priority review."
            )

        return DriftInsight(
            churn_level=churn_level,
            added_count=len(added),
            removed_count=len(removed),
            modified_count=len(modified),
            high_impact_files=sorted(high_impact_files),
            summary=summary,
        )

    @staticmethod
    def _classify_churn(ratio: float) -> ChurnLevel:
        if ratio >= HIGH_CHURN_RATIO:
            return ChurnLevel.HIGH
        if ratio >= MODERATE_CHURN_RATIO:
            return ChurnLevel.MODERATE
        return ChurnLevel.LOW
