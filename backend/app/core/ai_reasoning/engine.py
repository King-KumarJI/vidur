"""
VIDUR Core - AI Reasoning
Submodule: Engine
Purpose: Orchestrates a full AI reasoning run over an Inspection
Engine InspectionReport - issue correlation, dependency-impact
reasoning, debugging assistance, and drift reasoning - into a single
ReasoningReport. Enforces the MINOR_AI_REASONING feature flag and
Article 21 (Absolute Project Isolation) by requiring and binding a
valid Project ID for the duration of the run.
"""

from typing import Optional

from app.config.feature_flags import FeatureFlag, FeatureFlagRegistry, feature_flags
from app.config.logging_config import get_logger
from app.core.ai_reasoning.debug_assistant import DebuggingAssistant
from app.core.ai_reasoning.dependency_reasoner import DependencyReasoner
from app.core.ai_reasoning.drift_reasoner import DriftReasoner
from app.core.ai_reasoning.exceptions import (
    AIReasoningError,
    InvalidReasoningInputError,
    ReasoningDisabledError,
)
from app.core.ai_reasoning.issue_correlator import IssueCorrelator
from app.core.ai_reasoning.models import ReasoningReport
from app.core.ai_reasoning.recommendation_engine import RecommendationEngine
from app.core.ai_reasoning.report_generator import ReasoningReportGenerator
from app.core.inspection_engine.models import InspectionReport
from app.core.project_isolation import project_scope, validate_project_id_format
from app.core.project_isolation.exceptions import ProjectIsolationError

logger = get_logger("ai_reasoning.engine")


class AIReasoningEngine:
    """Top-level orchestrator for a single AI reasoning run over an
    InspectionReport."""

    def __init__(
        self,
        issue_correlator: Optional[IssueCorrelator] = None,
        dependency_reasoner: Optional[DependencyReasoner] = None,
        debugging_assistant: Optional[DebuggingAssistant] = None,
        drift_reasoner: Optional[DriftReasoner] = None,
        recommendation_engine: Optional[RecommendationEngine] = None,
        report_generator: Optional[ReasoningReportGenerator] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
    ) -> None:
        self._issue_correlator = issue_correlator or IssueCorrelator()
        self._dependency_reasoner = dependency_reasoner or DependencyReasoner()
        self._debugging_assistant = debugging_assistant or DebuggingAssistant()
        self._drift_reasoner = drift_reasoner or DriftReasoner()
        self._recommendation_engine = recommendation_engine or RecommendationEngine()
        self._report_generator = report_generator or ReasoningReportGenerator()
        self._feature_flags = feature_flag_registry or feature_flags

    def run(self, project_id: str, inspection_report: InspectionReport) -> ReasoningReport:
        """Run AI reasoning over `inspection_report`, scoped to
        `project_id`.

        Raises ReasoningDisabledError if MINOR_AI_REASONING is
        disabled, InvalidProjectIdError if `project_id` fails format
        validation, InvalidReasoningInputError if `inspection_report`
        belongs to a different project, and AIReasoningError wrapping
        any other unexpected failure encountered mid-run.
        """
        if not self._feature_flags.is_enabled(FeatureFlag.MINOR_AI_REASONING):
            raise ReasoningDisabledError(
                "AI reasoning was requested but the MINOR_AI_REASONING "
                "feature flag is disabled."
            )

        normalized_project_id = validate_project_id_format(project_id)
        if inspection_report.project_id != normalized_project_id:
            raise InvalidReasoningInputError(
                f"InspectionReport belongs to project "
                f"'{inspection_report.project_id}', not '{normalized_project_id}'."
            )

        logger.info(
            "AI reasoning started for project_id=%s root=%s",
            normalized_project_id,
            inspection_report.root_path,
        )

        with project_scope(normalized_project_id):
            try:
                report = self._execute(normalized_project_id, inspection_report)
            except (AIReasoningError, ProjectIsolationError):
                raise
            except Exception as exc:  # reasoning stages must never crash a whole run
                logger.error(
                    "AI reasoning failed for project_id=%s root=%s: %s",
                    normalized_project_id,
                    inspection_report.root_path,
                    exc,
                )
                raise AIReasoningError(
                    f"AI reasoning run failed for project '{normalized_project_id}': {exc}"
                ) from exc

        logger.info(
            "AI reasoning completed for project_id=%s recommendations=%d",
            normalized_project_id,
            len(report.recommendations),
        )
        return report

    def _execute(self, project_id: str, inspection_report: InspectionReport) -> ReasoningReport:
        findings = inspection_report.findings
        total_files = len(inspection_report.files)

        correlation_groups = self._issue_correlator.correlate(findings)
        dependency_assessments = self._dependency_reasoner.assess(
            inspection_report.files, findings
        )
        debugging_hypotheses = self._debugging_assistant.generate(findings)
        drift_insight = self._drift_reasoner.reason(findings, dependency_assessments, total_files)

        recommendations = self._recommendation_engine.build(
            correlation_groups, dependency_assessments, debugging_hypotheses, drift_insight
        )

        return self._report_generator.generate(
            project_id=project_id,
            root_path=inspection_report.root_path,
            correlation_groups=correlation_groups,
            dependency_assessments=dependency_assessments,
            debugging_hypotheses=debugging_hypotheses,
            drift_insight=drift_insight,
            recommendations=recommendations,
        )
