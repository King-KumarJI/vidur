"""
VIDUR Core - ML Prediction
Submodule: Exceptions
Purpose: Exception types for the ML Prediction pipeline (feature
extraction, regression-risk/technical-debt/quality-trend/failure-
probability prediction, and high-risk module identification built on
top of Inspection Engine and AI Reasoning output).
"""


class MLPredictionError(Exception):
    """Base class for all ML Prediction errors."""


class MLPredictionDisabledError(MLPredictionError):
    """Raised when a prediction run is requested while the
    MAJOR_ML_RISK_PREDICTION feature flag is disabled."""


class InvalidPredictionInputError(MLPredictionError):
    """Raised when the input supplied to the ML Prediction pipeline is
    missing data required to predict from it (for example, an
    InspectionReport or ReasoningReport belonging to a different
    project than the one the prediction run was scoped to)."""
