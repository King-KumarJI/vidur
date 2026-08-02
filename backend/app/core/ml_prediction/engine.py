"""
VIDUR Core - ML Prediction
Submodule: Engine
Purpose: Orchestrates a full ML Prediction run over a completed
Inspection Engine InspectionReport (and, when available, its paired AI
Reasoning ReasoningReport) - feature extraction, high-risk module
identification, regression-risk, technical-debt, quality-trend, and
failure-probability prediction - into a single MLPredictionReport.
Enforces the MAJOR_ML_RISK_PREDICTION feature flag (Article 41-44: this
entire module is a Major/advanced capability, ships disabled by
default) and Article 21 (Absolute Project Isolation) by requiring and
binding a valid Project ID for the duration of the run.
"""

from typing import List, Optional

from app.config.feature_flags import FeatureFlag, FeatureFlagRegistry, feature_flags
from app.config.logging_config import get_logger
from app.core.ai_reasoning.models import ReasoningReport
from app.core.inspection_engine.models import InspectionReport
from app.core.ml_prediction.exceptions import (
    InvalidPredictionInputError,
    MLPredictionDisabledError,
    MLPredictionError,
)
from app.core.ml_prediction.failure_probability_predictor import FailureProbabilityPredictor
from app.core.ml_prediction.feature_extractor import FeatureExtractor
from app.core.ml_prediction.high_risk_module_identifier import HighRiskModuleIdentifier
from app.core.ml_prediction.models import MLPredictionReport
from app.core.ml_prediction.quality_trend_predictor import QualityTrendPredictor
from app.core.ml_prediction.regression_risk_predictor import RegressionRiskPredictor
from app.core.ml_prediction.report_generator import MLPredictionReportGenerator
from app.core.ml_prediction.technical_debt_estimator import TechnicalDebtEstimator
from app.core.project_isolation import project_scope, validate_project_id_format
from app.core.project_isolation.exceptions import ProjectIsolationError

logger = get_logger("ml_prediction.engine")


class MLPredictionEngine:
    """Top-level orchestrator for a single ML Prediction run over an
    InspectionReport."""

    def __init__(
        self,
        feature_extractor: Optional[FeatureExtractor] = None,
        high_risk_module_identifier: Optional[HighRiskModuleIdentifier] = None,
        regression_risk_predictor: Optional[RegressionRiskPredictor] = None,
        technical_debt_estimator: Optional[TechnicalDebtEstimator] = None,
        quality_trend_predictor: Optional[QualityTrendPredictor] = None,
        failure_probability_predictor: Optional[FailureProbabilityPredictor] = None,
        report_generator: Optional[MLPredictionReportGenerator] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
    ) -> None:
        self._feature_extractor = feature_extractor or FeatureExtractor()
        self._high_risk_module_identifier = high_risk_module_identifier or HighRiskModuleIdentifier()
        self._regression_risk_predictor = regression_risk_predictor or RegressionRiskPredictor()
        self._technical_debt_estimator = technical_debt_estimator or TechnicalDebtEstimator()
        self._quality_trend_predictor = quality_trend_predictor or QualityTrendPredictor()
        self._failure_probability_predictor = (
            failure_probability_predictor or FailureProbabilityPredictor()
        )
        self._report_generator = report_generator or MLPredictionReportGenerator()
        self._feature_flags = feature_flag_registry or feature_flags

    def run(
        self,
        project_id: str,
        inspection_report: InspectionReport,
        reasoning_report: Optional[ReasoningReport] = None,
        historical_health_scores: Optional[List[float]] = None,
        historical_finding_counts: Optional[List[int]] = None,
    ) -> MLPredictionReport:
        """Run ML prediction over `inspection_report` (optionally
        enriched by `reasoning_report`'s dependency-impact data, a
        caller-supplied `historical_health_scores` series, and a
        paired `historical_finding_counts` series used to train the
        QualityTrendPredictor's scikit-learn model), scoped to
        `project_id`.

        Raises MLPredictionDisabledError if MAJOR_ML_RISK_PREDICTION is
        disabled, InvalidProjectIdError if `project_id` fails format
        validation, InvalidPredictionInputError if `inspection_report`
        or `reasoning_report` belongs to a different project, and
        MLPredictionError wrapping any other unexpected failure
        encountered mid-run.
        """
        if not self._feature_flags.is_enabled(FeatureFlag.MAJOR_ML_RISK_PREDICTION):
            raise MLPredictionDisabledError(
                "ML prediction was requested but the MAJOR_ML_RISK_PREDICTION "
                "feature flag is disabled."
            )

        normalized_project_id = validate_project_id_format(project_id)
        if inspection_report.project_id != normalized_project_id:
            raise InvalidPredictionInputError(
                f"InspectionReport belongs to project "
                f"'{inspection_report.project_id}', not '{normalized_project_id}'."
            )
        if reasoning_report is not None and reasoning_report.project_id != normalized_project_id:
            raise InvalidPredictionInputError(
                f"ReasoningReport belongs to project "
                f"'{reasoning_report.project_id}', not '{normalized_project_id}'."
            )

        logger.info(
            "ML prediction started for project_id=%s root=%s",
            normalized_project_id,
            inspection_report.root_path,
        )

        with project_scope(normalized_project_id):
            try:
                report = self._execute(
                    normalized_project_id,
                    inspection_report,
                    reasoning_report,
                    historical_health_scores,
                    historical_finding_counts,
                )
            except (MLPredictionError, ProjectIsolationError):
                raise
            except Exception as exc:  # prediction stages must never crash a whole run
                logger.error(
                    "ML prediction failed for project_id=%s root=%s: %s",
                    normalized_project_id,
                    inspection_report.root_path,
                    exc,
                )
                raise MLPredictionError(
                    f"ML prediction run failed for project '{normalized_project_id}': {exc}"
                ) from exc

        logger.info(
            "ML prediction completed for project_id=%s failure_probability=%.4f",
            normalized_project_id,
            report.failure_probability.probability,
        )
        return report

    def _execute(
        self,
        project_id: str,
        inspection_report: InspectionReport,
        reasoning_report: Optional[ReasoningReport],
        historical_health_scores: Optional[List[float]],
        historical_finding_counts: Optional[List[int]] = None,
    ) -> MLPredictionReport:
        feature_vector = self._feature_extractor.extract(inspection_report, reasoning_report)
        module_risk_scores = self._high_risk_module_identifier.identify(
            inspection_report.file_metrics,
            inspection_report.findings,
            reasoning_report.dependency_assessments if reasoning_report is not None else None,
        )
        regression_risk = self._regression_risk_predictor.predict(feature_vector)
        technical_debt = self._technical_debt_estimator.estimate(feature_vector)
        quality_trend = self._quality_trend_predictor.predict(
            inspection_report.health_score,
            historical_health_scores,
            historical_finding_counts,
            current_finding_count=len(inspection_report.findings),
        )
        failure_probability = self._failure_probability_predictor.predict(
            feature_vector, regression_risk, technical_debt
        )

        return self._report_generator.generate(
            project_id=project_id,
            root_path=inspection_report.root_path,
            feature_vector=feature_vector,
            module_risk_scores=module_risk_scores,
            regression_risk=regression_risk,
            technical_debt=technical_debt,
            quality_trend=quality_trend,
            failure_probability=failure_probability,
        )
