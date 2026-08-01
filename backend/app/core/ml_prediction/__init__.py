"""
VIDUR Core - ML Prediction Package.

Single import surface for running ML Prediction over a completed
Inspection Engine InspectionReport (and, when available, its paired AI
Reasoning ReasoningReport): feature extraction, high-risk module
identification, and regression-risk/technical-debt/quality-trend/
failure-probability prediction, aggregated into a single
MLPredictionReport. Ships disabled by default behind the
MAJOR_ML_RISK_PREDICTION feature flag (Article 41-44).
"""

from app.core.ml_prediction.engine import MLPredictionEngine
from app.core.ml_prediction.enums import RiskLevel, TrendDirection
from app.core.ml_prediction.exceptions import (
    InvalidPredictionInputError,
    MLPredictionDisabledError,
    MLPredictionError,
)
from app.core.ml_prediction.failure_probability_predictor import FailureProbabilityPredictor
from app.core.ml_prediction.feature_extractor import FeatureExtractor
from app.core.ml_prediction.high_risk_module_identifier import HighRiskModuleIdentifier
from app.core.ml_prediction.models import (
    FailureProbabilityPrediction,
    MLPredictionReport,
    ModuleRiskScore,
    ProjectFeatureVector,
    QualityTrendPrediction,
    RegressionRiskPrediction,
    TechnicalDebtEstimate,
)
from app.core.ml_prediction.quality_trend_predictor import QualityTrendPredictor
from app.core.ml_prediction.regression_risk_predictor import RegressionRiskPredictor
from app.core.ml_prediction.report_generator import MLPredictionReportGenerator
from app.core.ml_prediction.technical_debt_estimator import TechnicalDebtEstimator

__all__ = [
    "MLPredictionEngine",
    "FeatureExtractor",
    "HighRiskModuleIdentifier",
    "RegressionRiskPredictor",
    "TechnicalDebtEstimator",
    "QualityTrendPredictor",
    "FailureProbabilityPredictor",
    "MLPredictionReportGenerator",
    "RiskLevel",
    "TrendDirection",
    "ProjectFeatureVector",
    "ModuleRiskScore",
    "RegressionRiskPrediction",
    "TechnicalDebtEstimate",
    "QualityTrendPrediction",
    "FailureProbabilityPrediction",
    "MLPredictionReport",
    "MLPredictionError",
    "MLPredictionDisabledError",
    "InvalidPredictionInputError",
]
