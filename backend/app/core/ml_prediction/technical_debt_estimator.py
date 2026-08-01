"""
VIDUR Core - ML Prediction
Submodule: Technical Debt Estimator
Purpose: Predict a 0-100 technical debt score and an estimated
remediation effort in hours, per Chapter VII ("predicts technical
debt"), from a project's complexity, docstring coverage, and
code-quality finding density.
"""

from typing import List

from app.core.ml_prediction.enums import RiskLevel
from app.core.ml_prediction.models import ProjectFeatureVector, TechnicalDebtEstimate

#: A max cyclomatic complexity at or above this value contributes the
#: full complexity penalty.
COMPLEXITY_REFERENCE = 20.0
MAX_COMPLEXITY_PENALTY = 40.0

#: Docstring coverage below 100% contributes proportionally to the
#: documentation-debt penalty, up to this maximum.
MAX_DOCSTRING_PENALTY = 30.0

#: Findings-per-file density at or above this value contributes the
#: full code-quality penalty.
FINDING_DENSITY_REFERENCE = 0.5
MAX_FINDING_DENSITY_PENALTY = 30.0

#: Heuristic remediation cost for a file carrying the maximum possible
#: debt score (100): roughly a day-and-a-half's worth of cleanup spread
#: across an hour and a half per file.
HOURS_PER_FILE_AT_MAX_DEBT = 1.5

CRITICAL_DEBT_THRESHOLD = 75.0
HIGH_DEBT_THRESHOLD = 50.0
MODERATE_DEBT_THRESHOLD = 25.0


def _classify(debt_score: float) -> RiskLevel:
    if debt_score >= CRITICAL_DEBT_THRESHOLD:
        return RiskLevel.CRITICAL
    if debt_score >= HIGH_DEBT_THRESHOLD:
        return RiskLevel.HIGH
    if debt_score >= MODERATE_DEBT_THRESHOLD:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


class TechnicalDebtEstimator:
    """Scores a ProjectFeatureVector into a TechnicalDebtEstimate."""

    def estimate(self, feature_vector: ProjectFeatureVector) -> TechnicalDebtEstimate:
        complexity_penalty = min(
            feature_vector.average_cyclomatic_complexity / COMPLEXITY_REFERENCE, 1.0
        ) * MAX_COMPLEXITY_PENALTY

        docstring_gap = max(0.0, 1.0 - feature_vector.average_docstring_coverage)
        docstring_penalty = docstring_gap * MAX_DOCSTRING_PENALTY

        finding_density_penalty = min(
            feature_vector.finding_density / FINDING_DENSITY_REFERENCE, 1.0
        ) * MAX_FINDING_DENSITY_PENALTY

        debt_score = round(
            min(complexity_penalty + docstring_penalty + finding_density_penalty, 100.0), 2
        )
        remediation_hours = round(
            (debt_score / 100.0) * feature_vector.file_count * HOURS_PER_FILE_AT_MAX_DEBT, 1
        )

        risk_level = _classify(debt_score)
        factors = self._contributing_factors(
            feature_vector, complexity_penalty, docstring_penalty, finding_density_penalty
        )
        summary = (
            f"Predicted technical debt score {debt_score:.1f}/100 ({risk_level.value}), "
            f"estimated at {remediation_hours:.1f} remediation hour(s) across "
            f"{feature_vector.file_count} file(s)."
        )

        return TechnicalDebtEstimate(
            debt_score=debt_score,
            risk_level=risk_level,
            estimated_remediation_hours=remediation_hours,
            contributing_factors=factors,
            summary=summary,
        )

    @staticmethod
    def _contributing_factors(
        feature_vector: ProjectFeatureVector,
        complexity_penalty: float,
        docstring_penalty: float,
        finding_density_penalty: float,
    ) -> List[str]:
        factors: List[str] = []
        if complexity_penalty >= MAX_COMPLEXITY_PENALTY * 0.3:
            factors.append(
                f"Average max cyclomatic complexity is {feature_vector.average_cyclomatic_complexity:.2f}."
            )
        if docstring_penalty >= MAX_DOCSTRING_PENALTY * 0.3:
            factors.append(
                f"Average docstring coverage is only {feature_vector.average_docstring_coverage:.0%}."
            )
        if finding_density_penalty >= MAX_FINDING_DENSITY_PENALTY * 0.3:
            factors.append(
                f"Finding density is {feature_vector.finding_density:.2f} findings per file."
            )
        return factors
