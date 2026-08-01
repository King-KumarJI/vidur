"""
VIDUR Core - Inspection Engine
Submodule: Drift Detector
Purpose: Compare two InspectionSnapshots of the same project to
surface structural drift - files added, removed, or modified since
the previous inspection run.
"""

from typing import List, Optional

from app.core.inspection_engine.enums import FindingCategory, Severity
from app.core.inspection_engine.models import Finding, InspectionSnapshot


class DriftDetector:
    """Detects file-level drift between a previous and a current
    InspectionSnapshot of the same project."""

    def detect(
        self,
        previous: Optional[InspectionSnapshot],
        current: InspectionSnapshot,
    ) -> List[Finding]:
        """Return one Finding per added, removed, or modified file
        between `previous` and `current`. Returns an empty list when
        `previous` is None (first-ever inspection: nothing to diff)."""
        if previous is None:
            return []

        findings: List[Finding] = []
        previous_paths = set(previous.files)
        current_paths = set(current.files)

        for added_path in sorted(current_paths - previous_paths):
            findings.append(
                Finding(
                    category=FindingCategory.DRIFT,
                    severity=Severity.INFO,
                    code="FILE_ADDED",
                    message=f"File added since previous inspection: {added_path}",
                    file_path=added_path,
                    line=None,
                )
            )

        for removed_path in sorted(previous_paths - current_paths):
            findings.append(
                Finding(
                    category=FindingCategory.DRIFT,
                    severity=Severity.WARNING,
                    code="FILE_REMOVED",
                    message=f"File removed since previous inspection: {removed_path}",
                    file_path=removed_path,
                    line=None,
                )
            )

        for shared_path in sorted(previous_paths & current_paths):
            previous_record = previous.files[shared_path]
            current_record = current.files[shared_path]
            if previous_record.content_hash != current_record.content_hash:
                findings.append(
                    Finding(
                        category=FindingCategory.DRIFT,
                        severity=Severity.INFO,
                        code="FILE_MODIFIED",
                        message=f"File modified since previous inspection: {shared_path}",
                        file_path=shared_path,
                        line=None,
                    )
                )

        return findings
