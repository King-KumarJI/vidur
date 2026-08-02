"""
VIDUR Core - ML Prediction
Submodule: Quality Trend Predictor
Purpose: Predict the trajectory of a project's health score across
successive inspection runs, per Chapter VII ("predicts ... quality
trends") and the Real AI/ML/DL/NLP Upgrade amendment ("Add
scikit-learn. Train an actual model on accumulated historical
health-score/findings data pulled from Memory"). Trains a scikit-learn
LinearRegression on the project's own history of health scores (run
index -> health score), optionally enriched with a paired history of
per-run finding counts as a second feature when the caller supplies
one, and projects the next run's score. Persistence of that history
between runs remains the responsibility of the caller (the Memory
module), matching the precedent set by InspectionSnapshot in the
Inspection Engine.
"""

from typing import List, Optional, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression

from app.core.ml_prediction.enums import TrendDirection
from app.core.ml_prediction.models import QualityTrendPrediction

#: Minimum absolute slope (health-score points per run) required to
#: classify the trend as IMPROVING/DEGRADING rather than STABLE.
STABLE_SLOPE_THRESHOLD = 0.5

MIN_HEALTH_SCORE = 0.0
MAX_HEALTH_SCORE = 100.0

#: Fewer than this many data points (history + current run) means
#: there is nothing to train a trend model on yet - cold start.
MIN_TRAINING_POINTS = 2


class QualityTrendPredictor:
    """Trains a scikit-learn `LinearRegression` on
    `historical_health_scores + [current_health_score]` (run index ->
    health score) and projects the next run's score. When the caller
    also supplies a paired `historical_finding_counts` series plus the
    current run's `current_finding_count`, the finding-count trend is
    folded in as a second regression feature - its own next value is
    itself forecast from its own trend first, since the true future
    finding count is not yet known at prediction time."""

    def predict(
        self,
        current_health_score: float,
        historical_health_scores: Optional[List[float]] = None,
        historical_finding_counts: Optional[List[int]] = None,
        current_finding_count: Optional[int] = None,
    ) -> QualityTrendPrediction:
        scores = list(historical_health_scores or []) + [current_health_score]
        data_points_used = len(scores)

        if data_points_used < MIN_TRAINING_POINTS:
            return QualityTrendPrediction(
                direction=TrendDirection.UNKNOWN,
                current_health_score=current_health_score,
                projected_next_health_score=current_health_score,
                slope_per_run=0.0,
                data_points_used=data_points_used,
                summary=(
                    "No prior health-score history was supplied, so a quality "
                    "trend model cannot yet be trained; this is the project's "
                    "first recorded score."
                ),
            )

        finding_counts = self._aligned_finding_counts(
            historical_health_scores, historical_finding_counts, current_finding_count
        )

        slope, projected_raw = self._fit_and_project(scores, finding_counts)
        projected_next = round(min(max(projected_raw, MIN_HEALTH_SCORE), MAX_HEALTH_SCORE), 2)
        direction = self._classify(slope)

        findings_clause = (
            ", with finding-count history as a second model feature" if finding_counts else ""
        )
        summary = (
            f"Health score trend is {direction.value} "
            f"({slope:+.2f} point(s) per run over {data_points_used} data point(s){findings_clause}); "
            f"next run projected at {projected_next:.2f} by a trained linear regression model."
        )

        return QualityTrendPrediction(
            direction=direction,
            current_health_score=current_health_score,
            projected_next_health_score=projected_next,
            slope_per_run=round(slope, 4),
            data_points_used=data_points_used,
            summary=summary,
        )

    @staticmethod
    def _aligned_finding_counts(
        historical_health_scores: Optional[List[float]],
        historical_finding_counts: Optional[List[int]],
        current_finding_count: Optional[int],
    ) -> Optional[List[int]]:
        """Return the per-run finding-count series aligned to `scores`
        (history followed by the current run, same order as the health
        scores), or None when the caller did not supply a complete,
        matching series. The finding-count feature is only ever used
        when it is genuinely available and aligned - never fabricated
        to fill a gap."""
        if historical_finding_counts is None or current_finding_count is None:
            return None
        expected_history_length = len(historical_health_scores or [])
        if len(historical_finding_counts) != expected_history_length:
            return None
        return list(historical_finding_counts) + [current_finding_count]

    @staticmethod
    def _fit_and_project(
        scores: List[float], finding_counts: Optional[List[int]]
    ) -> Tuple[float, float]:
        sample_count = len(scores)
        indices = np.arange(sample_count, dtype=float).reshape(-1, 1)
        target = np.array(scores, dtype=float)

        if finding_counts is not None:
            features = np.column_stack(
                [indices.flatten(), np.array(finding_counts, dtype=float)]
            )
        else:
            features = indices

        model = LinearRegression()
        model.fit(features, target)
        slope = float(model.coef_[0])

        next_index = float(sample_count)
        if finding_counts is not None:
            next_finding_count = QualityTrendPredictor._forecast_next(finding_counts)
            next_features = [[next_index, next_finding_count]]
        else:
            next_features = [[next_index]]

        projected = float(model.predict(next_features)[0])
        return slope, projected

    @staticmethod
    def _forecast_next(series: List[int]) -> float:
        """Extrapolate `series`'s own trend one step forward with its
        own scikit-learn `LinearRegression`, for use as a forecast
        input feature (the true future value is not yet known)."""
        indices = np.arange(len(series), dtype=float).reshape(-1, 1)
        target = np.array(series, dtype=float)
        model = LinearRegression()
        model.fit(indices, target)
        return float(model.predict([[float(len(series))]])[0])

    @staticmethod
    def _classify(slope: float) -> TrendDirection:
        if slope >= STABLE_SLOPE_THRESHOLD:
            return TrendDirection.IMPROVING
        if slope <= -STABLE_SLOPE_THRESHOLD:
            return TrendDirection.DEGRADING
        return TrendDirection.STABLE
