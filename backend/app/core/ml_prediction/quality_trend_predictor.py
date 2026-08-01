"""
VIDUR Core - ML Prediction
Submodule: Quality Trend Predictor
Purpose: Predict the trajectory of a project's health score across
successive inspection runs, per Chapter VII ("predicts ... quality
trends"), using ordinary least-squares regression over a caller-
supplied history of prior health scores. Persistence of that history
between runs is the responsibility of the caller (the future Memory
module), matching the precedent set by InspectionSnapshot in the
Inspection Engine.
"""

from typing import List, Optional

from app.core.ml_prediction.enums import TrendDirection
from app.core.ml_prediction.models import QualityTrendPrediction

#: Minimum absolute slope (health-score points per run) required to
#: classify the trend as IMPROVING/DEGRADING rather than STABLE.
STABLE_SLOPE_THRESHOLD = 0.5

MIN_HEALTH_SCORE = 0.0
MAX_HEALTH_SCORE = 100.0


class QualityTrendPredictor:
    """Fits a least-squares trend line to `historical_health_scores +
    [current_health_score]` and projects the next run's score."""

    def predict(
        self,
        current_health_score: float,
        historical_health_scores: Optional[List[float]] = None,
    ) -> QualityTrendPrediction:
        series = list(historical_health_scores or []) + [current_health_score]
        data_points_used = len(series)

        if data_points_used < 2:
            return QualityTrendPrediction(
                direction=TrendDirection.UNKNOWN,
                current_health_score=current_health_score,
                projected_next_health_score=current_health_score,
                slope_per_run=0.0,
                data_points_used=data_points_used,
                summary=(
                    "No prior health-score history was supplied, so a quality "
                    "trend cannot yet be predicted; this is the project's first "
                    "recorded score."
                ),
            )

        slope = self._least_squares_slope(series)
        projected_next = round(
            min(max(current_health_score + slope, MIN_HEALTH_SCORE), MAX_HEALTH_SCORE), 2
        )
        direction = self._classify(slope)

        summary = (
            f"Health score trend is {direction.value} "
            f"({slope:+.2f} point(s) per run over {data_points_used} data point(s)); "
            f"next run projected at {projected_next:.2f}."
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
    def _least_squares_slope(series: List[float]) -> float:
        n = len(series)
        x_mean = (n - 1) / 2.0
        y_mean = sum(series) / n
        numerator = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(series))
        denominator = sum((index - x_mean) ** 2 for index in range(n))
        if denominator == 0.0:
            return 0.0
        return numerator / denominator

    @staticmethod
    def _classify(slope: float) -> TrendDirection:
        if slope >= STABLE_SLOPE_THRESHOLD:
            return TrendDirection.IMPROVING
        if slope <= -STABLE_SLOPE_THRESHOLD:
            return TrendDirection.DEGRADING
        return TrendDirection.STABLE
