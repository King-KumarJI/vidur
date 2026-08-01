"""
VIDUR Core - ML Prediction
Submodule: Failure Probability Predictor
Purpose: Predict an overall probability of project quality breakdown,
per Chapter VII ("predicts failure probability"), as a weighted
combination of regression risk, technical debt, drift churn, and the
current health-score deficit. Deliberately reuses the other
predictors' outputs rather than re-deriving its own signal, per
Article 31-32 (reuse before rewriting).
"""

from typing import List

from app.core.ml_prediction.enums import RiskLevel
from app.core.ml_prediction.models import (
    FailureProbabilityPrediction,
    ProjectFeatureVector,
    RegressionRiskPrediction,
    TechnicalDebtEstimate,
)

#: Blend weights for the four contributing signals (sum to 1.0).
#: Regression risk is weighted highest because it is the most direct
#: predictor of a near-term failure; health-score deficit is weighted
#: lowest because it is already a lagging aggregate of past findings.
REGRESSION_RISK_WEIGHT = 0.4
TECHNICAL_DEBT_WEIGHT = 0.25
CHURN_WEIGHT = 0.15
HEALTH_DEFICIT_WEIGHT = 0.2

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


class FailureProbabilityPredictor:
    """Combines regression risk, technical debt, drift churn, and
    health-score deficit into a single FailureProbabilityPrediction."""

    def predict(
        self,
        feature_vector: ProjectFeatureVector,
        regression_risk: RegressionRiskPrediction,
        technical_debt: TechnicalDebtEstimate,
    ) -> FailureProbabilityPrediction:
        churn_component = min(feature_vector.drift_churn_ratio, 1.0)
        health_deficit_component = max(0.0, (100.0 - feature_vector.health_score) / 100.0)
        debt_component = technical_debt.debt_score / 100.0

        probability = round(
            (regression_risk.probability * REGRESSION_RISK_WEIGHT)
            + (debt_component * TECHNICAL_DEBT_WEIGHT)
            + (churn_component * CHURN_WEIGHT)
            + (health_deficit_component * HEALTH_DEFICIT_WEIGHT),
            4,
        )
        probability = min(max(probability, 0.0), 1.0)
        risk_level = _classify(probability)

        factors = self._contributing_factors(
            regression_risk, debt_component, churn_component, health_deficit_component
        )
        summary = (
            f"Predicted overall failure probability {probability:.0%} ({risk_level.value}), "
            "combining regression risk, technical debt, drift churn, and health-score deficit."
        )

        return FailureProbabilityPrediction(
            probability=probability,
            risk_level=risk_level,
            contributing_factors=factors,
            summary=summary,
        )

    @staticmethod
    def _contributing_factors(
        regression_risk: RegressionRiskPrediction,
        debt_component: float,
        churn_component: float,
        health_deficit_component: float,
    ) -> List[str]:
        factors: List[str] = []
        if regression_risk.probability >= 0.3:
            factors.append(f"Regression risk probability is {regression_risk.probability:.0%}.")
        if debt_component >= 0.3:
            factors.append(f"Technical debt score is {debt_component * 100:.1f}/100.")
        if churn_component >= 0.3:
            factors.append(f"Drift churn ratio is {churn_component:.2f}.")
        if health_deficit_component >= 0.3:
            factors.append(f"Health score deficit is {health_deficit_component:.0%} below full health.")
        return factors
