"""Unit tests for app.core.ml_prediction.quality_trend_predictor."""

from app.core.ml_prediction.enums import TrendDirection
from app.core.ml_prediction.quality_trend_predictor import QualityTrendPredictor


def test_predict_unknown_with_no_history():
    prediction = QualityTrendPredictor().predict(90.0, None)
    assert prediction.direction == TrendDirection.UNKNOWN
    assert prediction.data_points_used == 1
    assert prediction.projected_next_health_score == 90.0


def test_predict_improving_trend():
    prediction = QualityTrendPredictor().predict(90.0, [60.0, 70.0, 80.0])
    assert prediction.direction == TrendDirection.IMPROVING
    assert prediction.slope_per_run > 0.0
    assert prediction.data_points_used == 4


def test_predict_degrading_trend():
    prediction = QualityTrendPredictor().predict(60.0, [90.0, 80.0, 70.0])
    assert prediction.direction == TrendDirection.DEGRADING
    assert prediction.slope_per_run < 0.0


def test_predict_stable_trend_for_flat_history():
    prediction = QualityTrendPredictor().predict(80.0, [80.0, 80.0, 80.0])
    assert prediction.direction == TrendDirection.STABLE
    assert abs(prediction.slope_per_run) < 0.01


def test_predict_projected_score_clamped_to_valid_range():
    prediction = QualityTrendPredictor().predict(99.0, [10.0, 40.0, 70.0])
    assert 0.0 <= prediction.projected_next_health_score <= 100.0
