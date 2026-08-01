"""
VIDUR Core - Inspection Engine
Submodule: Report Generator
Purpose: Assemble the outputs of every analyzer stage (file inventory,
code metrics, findings) plus the computed health score into a single
InspectionReport, and derive the InspectionSnapshot used for future
drift detection.
"""

from datetime import datetime
from typing import List, Optional

from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.health_score import HealthScoreCalculator
from app.core.inspection_engine.models import (
    Finding,
    FileMetrics,
    FileRecord,
    InspectionReport,
    InspectionSnapshot,
    utc_now,
)


class InspectionReportGenerator:
    """Builds the final InspectionReport and InspectionSnapshot for a
    completed (or failed) inspection run."""

    def __init__(self, health_score_calculator: Optional[HealthScoreCalculator] = None) -> None:
        self._health_score_calculator = health_score_calculator or HealthScoreCalculator()

    def build_snapshot(
        self,
        project_id: str,
        root_path: str,
        files: List[FileRecord],
        generated_at: Optional[datetime] = None,
    ) -> InspectionSnapshot:
        """Build the file-inventory snapshot for the current run."""
        return InspectionSnapshot(
            project_id=project_id,
            root_path=root_path,
            generated_at=generated_at or utc_now(),
            files={record.relative_path: record for record in files},
        )

    def generate(
        self,
        *,
        project_id: str,
        root_path: str,
        status: InspectionStatus,
        started_at: datetime,
        files: List[FileRecord],
        file_metrics: List[FileMetrics],
        findings: List[Finding],
        completed_at: Optional[datetime] = None,
        snapshot: Optional[InspectionSnapshot] = None,
    ) -> InspectionReport:
        """Assemble the final InspectionReport for one inspection run."""
        resolved_completed_at = completed_at or utc_now()
        resolved_snapshot = snapshot or self.build_snapshot(
            project_id, root_path, files, resolved_completed_at
        )
        health_score = self._health_score_calculator.calculate(findings, len(files))

        return InspectionReport(
            project_id=project_id,
            root_path=root_path,
            status=status,
            started_at=started_at,
            completed_at=resolved_completed_at,
            files=files,
            file_metrics=file_metrics,
            findings=findings,
            health_score=health_score,
            snapshot=resolved_snapshot,
        )
