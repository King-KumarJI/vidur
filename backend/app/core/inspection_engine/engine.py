"""
VIDUR Core - Inspection Engine
Submodule: Engine
Purpose: Orchestrates a full project inspection run - file scanning,
code analysis, dependency analysis, architecture validation, and
drift detection - into a single InspectionReport. Enforces the
MINOR_PROJECT_INSPECTION feature flag and Article 21 (Absolute
Project Isolation) by requiring and binding a valid Project ID for
the duration of the run.
"""

from datetime import datetime
from typing import List, Optional

from app.config.feature_flags import FeatureFlag, FeatureFlagRegistry, feature_flags
from app.config.logging_config import get_logger
from app.core.inspection_engine.architecture_validator import ArchitectureValidator
from app.core.inspection_engine.code_analyzer import PythonCodeAnalyzer
from app.core.inspection_engine.dependency_analyzer import DependencyAnalyzer
from app.core.inspection_engine.drift_detector import DriftDetector
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.exceptions import InspectionDisabledError, InspectionEngineError
from app.core.inspection_engine.file_scanner import ProjectFileScanner
from app.core.inspection_engine.models import Finding, FileMetrics, InspectionReport, InspectionSnapshot, utc_now
from app.core.inspection_engine.report_generator import InspectionReportGenerator
from app.core.project_isolation import project_scope, validate_project_id_format
from app.core.project_isolation.exceptions import ProjectIsolationError

logger = get_logger("inspection_engine.engine")


class InspectionEngine:
    """Top-level orchestrator for a single project inspection run."""

    def __init__(
        self,
        file_scanner: Optional[ProjectFileScanner] = None,
        code_analyzer: Optional[PythonCodeAnalyzer] = None,
        dependency_analyzer: Optional[DependencyAnalyzer] = None,
        architecture_validator: Optional[ArchitectureValidator] = None,
        drift_detector: Optional[DriftDetector] = None,
        report_generator: Optional[InspectionReportGenerator] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
    ) -> None:
        self._file_scanner = file_scanner or ProjectFileScanner()
        self._code_analyzer = code_analyzer or PythonCodeAnalyzer()
        self._dependency_analyzer = dependency_analyzer or DependencyAnalyzer()
        self._architecture_validator = architecture_validator or ArchitectureValidator()
        self._drift_detector = drift_detector or DriftDetector()
        self._report_generator = report_generator or InspectionReportGenerator()
        self._feature_flags = feature_flag_registry or feature_flags

    def run(
        self,
        project_id: str,
        root_path: str,
        previous_snapshot: Optional[InspectionSnapshot] = None,
    ) -> InspectionReport:
        """Run a full inspection of `root_path` scoped to `project_id`.

        Raises InspectionDisabledError if MINOR_PROJECT_INSPECTION is
        disabled, InvalidProjectIdError if `project_id` fails format
        validation, InvalidInspectionTargetError if `root_path` is not
        an inspectable directory, and InspectionEngineError wrapping
        any other unexpected failure encountered mid-run.
        """
        if not self._feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_INSPECTION):
            raise InspectionDisabledError(
                "Inspection was requested but the MINOR_PROJECT_INSPECTION "
                "feature flag is disabled."
            )

        normalized_project_id = validate_project_id_format(project_id)
        started_at = utc_now()
        logger.info("Inspection started for project_id=%s root=%s", normalized_project_id, root_path)

        with project_scope(normalized_project_id):
            try:
                report = self._execute(normalized_project_id, root_path, started_at, previous_snapshot)
            except (InspectionEngineError, ProjectIsolationError):
                raise
            except Exception as exc:  # analyzers must never crash a whole inspection run
                logger.error(
                    "Inspection failed for project_id=%s root=%s: %s",
                    normalized_project_id,
                    root_path,
                    exc,
                )
                raise InspectionEngineError(
                    f"Inspection run failed for project '{normalized_project_id}': {exc}"
                ) from exc

        logger.info(
            "Inspection completed for project_id=%s health_score=%s findings=%d",
            normalized_project_id,
            report.health_score,
            len(report.findings),
        )
        return report

    def _execute(
        self,
        project_id: str,
        root_path: str,
        started_at: datetime,
        previous_snapshot: Optional[InspectionSnapshot],
    ) -> InspectionReport:
        files = self._file_scanner.scan(root_path)

        findings: List[Finding] = []
        file_metrics: List[FileMetrics] = []
        for record in files:
            if record.extension != "py":
                continue
            metrics, analyzer_findings = self._code_analyzer.analyze(
                record.absolute_path, record.relative_path
            )
            file_metrics.append(metrics)
            findings.extend(analyzer_findings)

        findings.extend(self._dependency_analyzer.find_findings(files))
        findings.extend(self._architecture_validator.validate(files))

        completed_at = utc_now()
        snapshot = self._report_generator.build_snapshot(project_id, root_path, files, completed_at)
        findings.extend(self._drift_detector.detect(previous_snapshot, snapshot))

        return self._report_generator.generate(
            project_id=project_id,
            root_path=root_path,
            status=InspectionStatus.COMPLETED,
            started_at=started_at,
            files=files,
            file_metrics=file_metrics,
            findings=findings,
            completed_at=completed_at,
            snapshot=snapshot,
        )
