"""
VIDUR Core - ML Prediction
Submodule: Report Generator
Purpose: Assemble the outputs of every prediction stage (feature
extraction, high-risk module identification, regression risk,
technical debt, quality trend, and failure probability) into a single
MLPredictionReport.
"""

from datetime import datetime
from typing import List, Optional

from app.core.inspection_engine.models import utc_now
from app.core.ml_prediction.models import (
    FailureProbabilityPrediction,
    MLPredictionReport,
    ModuleRiskScore,
    ProjectFeatureVector,
    QualityTrendPrediction,
    RegressionRiskPrediction,
    TechnicalDebtEstimate,
)


class MLPredictionReportGenerator:
    """Builds the final MLPredictionReport for a completed prediction
    run."""

    def generate(
        self,
        *,
        project_id: str,
        root_path: str,
        feature_vector: ProjectFeatureVector,
        module_risk_scores: List[ModuleRiskScore],
        regression_risk: RegressionRiskPrediction,
        technical_debt: TechnicalDebtEstimate,
        quality_trend: QualityTrendPrediction,
        failure_probability: FailureProbabilityPrediction,
        generated_at: Optional[datetime] = None,
    ) -> MLPredictionReport:
        """Assemble the final MLPredictionReport for one prediction
        run."""
        return MLPredictionReport(
            project_id=project_id,
            root_path=root_path,
            generated_at=generated_at or utc_now(),
            feature_vector=feature_vector,
            module_risk_scores=module_risk_scores,
            regression_risk=regression_risk,
            technical_debt=technical_debt,
            quality_trend=quality_trend,
            failure_probability=failure_probability,
        )
