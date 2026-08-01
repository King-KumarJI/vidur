"""
VIDUR Core - ML Prediction
Submodule: Regression Risk Predictor
Purpose: Predict the probability that the current inspection run's
changes introduce a regression, per Chapter VII ("predicts regression
probability"). No historical labeled defect data is persisted yet (the
Memory module has not been built), so a trained classifier cannot be
fit; instead this uses a deterministic logistic-style scoring function
over engineered features - transparent and reproducible, matching the
rule-based precedent set by AI Reasoning's DebuggingAssistant and the
from-scratch statistical technique in NLP's SemanticSimilarityReasoner.
Advisory only (Article 10-11, Chapter VII ML): never blocks or replaces
deterministic Inspection Engine validation.
"""

import math
from typing import List

from app.core.ml_prediction.enums import RiskLevel
from app.core.ml_prediction.models import ProjectFeatureVector, RegressionRiskPrediction

#: Reference scales: a feature at or above its reference value is
#: treated as maximally contributing on that axis before the sigmoid
#: is applied. Each normalized component is capped at COMPONENT_CAP so
#: no single extreme feature alone saturates the model.
CHURN_REFERENCE = 1.0
SEVERITY_DENSITY_REFERENCE = 5.0
COMPLEXITY_REFERENCE = 20.0
DEPENDENCY_RISK_REFERENCE = 5.0
COMPONENT_CAP = 2.0

#: Logistic model weights. Churn (files changed since the previous
#: inspection) dominates because regressions are, by definition,
#: introduced by change; a project with zero drift cannot regress in
#: this run regardless of how complex or risky its existing code is.
BIAS = -2.0
CHURN_WEIGHT = 3.0
SEVERITY_DENSITY_WEIGHT = 1.5
COMPLEXITY_WEIGHT = 1.0
DEPENDENCY_WEIGHT = 1.5

CRITICAL_PROBABILITY_THRESHOLD = 0.75
HIGH_PROBABILITY_THRESHOLD = 0.5
MODERATE_PROBABILITY_THRESHOLD = 0.25


def _classify(probability: float) -> RiskLevel:
    if probability >= CRITICAL_PROBABILITY_THRESHOLD:
        return RiskLevel.CRITICAL
    if probability >= HIGH_PROBABILITY_THRESHOLD:
        return RiskLevel.HIGH
    if probability >= MODERATE_PROBABILITY_THRESHOLD:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


class RegressionRiskPredictor:
    """Scores a ProjectFeatureVector into a RegressionRiskPrediction."""

    def predict(self, feature_vector: ProjectFeatureVector) -> RegressionRiskPrediction:
        churn_component = min(feature_vector.drift_churn_ratio / CHURN_REFERENCE, COMPONENT_CAP)
        severity_component = min(
            feature_vector.severity_weighted_density / SEVERITY_DENSITY_REFERENCE, COMPONENT_CAP
        )
        complexity_component = min(
            feature_vector.average_cyclomatic_complexity / COMPLEXITY_REFERENCE, COMPONENT_CAP
        )
        dependency_component = min(
            feature_vector.max_dependency_risk / DEPENDENCY_RISK_REFERENCE, COMPONENT_CAP
        )

        z = (
            BIAS
            + (CHURN_WEIGHT * churn_component)
            + (SEVERITY_DENSITY_WEIGHT * severity_component)
            + (COMPLEXITY_WEIGHT * complexity_component)
            + (DEPENDENCY_WEIGHT * dependency_component)
        )
        probability = round(1.0 / (1.0 + math.exp(-z)), 4)

        factors = self._contributing_factors(
            feature_vector, churn_component, severity_component, complexity_component, dependency_component
        )
        risk_level = _classify(probability)
        summary = (
            f"Predicted regression probability {probability:.0%} ({risk_level.value}) "
            f"for this run, based on {feature_vector.file_count} inspected file(s)."
        )

        return RegressionRiskPrediction(
            probability=probability,
            risk_level=risk_level,
            contributing_factors=factors,
            summary=summary,
        )

    @staticmethod
    def _contributing_factors(
        feature_vector: ProjectFeatureVector,
        churn_component: float,
        severity_component: float,
        complexity_component: float,
        dependency_component: float,
    ) -> List[str]:
        factors: List[str] = []
        if churn_component >= 0.3:
            factors.append(
                f"File churn ratio since previous inspection is {feature_vector.drift_churn_ratio:.2f}."
            )
        if severity_component >= 0.3:
            factors.append(
                f"Severity-weighted finding density is {feature_vector.severity_weighted_density:.2f} per file."
            )
        if complexity_component >= 0.3:
            factors.append(
                f"Average max cyclomatic complexity is {feature_vector.average_cyclomatic_complexity:.2f}."
            )
        if dependency_component >= 0.3:
            factors.append(
                f"Highest dependency blast-radius risk score is {feature_vector.max_dependency_risk:.2f}."
            )
        return factors
