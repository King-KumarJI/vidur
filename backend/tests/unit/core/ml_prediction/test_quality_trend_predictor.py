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


def test_predict_uses_finding_count_history_when_aligned_and_current_supplied():
    prediction = QualityTrendPredictor().predict(
        current_health_score=90.0,
        historical_health_scores=[60.0, 70.0, 80.0],
        historical_finding_counts=[9, 6, 3],
        current_finding_count=0,
    )
    assert "finding-count history" in prediction.summary
    assert prediction.direction == TrendDirection.IMPROVING
    assert prediction.data_points_used == 4


def test_predict_falls_back_to_health_scores_only_when_finding_counts_mismatched():
    prediction = QualityTrendPredictor().predict(
        current_health_score=90.0,
        historical_health_scores=[60.0, 70.0, 80.0],
        historical_finding_counts=[9, 6],  # one short of the health-score history
        current_finding_count=0,
    )
    assert "finding-count history" not in prediction.summary
    assert prediction.direction == TrendDirection.IMPROVING


def test_predict_falls_back_to_health_scores_only_when_current_finding_count_missing():
    prediction = QualityTrendPredictor().predict(
        current_health_score=90.0,
        historical_health_scores=[60.0, 70.0, 80.0],
        historical_finding_counts=[9, 6, 3],
        current_finding_count=None,
    )
    assert "finding-count history" not in prediction.summary


def test_predict_with_finding_counts_still_clamps_projected_score():
    prediction = QualityTrendPredictor().predict(
        current_health_score=99.0,
        historical_health_scores=[10.0, 40.0, 70.0],
        historical_finding_counts=[30, 20, 10],
        current_finding_count=2,
    )
    assert 0.0 <= prediction.projected_next_health_score <= 100.0


def test_predict_cold_start_with_only_current_run_ignores_finding_counts():
    prediction = QualityTrendPredictor().predict(
        current_health_score=85.0,
        historical_health_scores=None,
        historical_finding_counts=None,
        current_finding_count=4,
    )
    assert prediction.direction == TrendDirection.UNKNOWN
    assert prediction.data_points_used == 1
    assert prediction.projected_next_health_score == 85.0


def test_predict_realistic_synthetic_history_produces_sane_stable_trend():
    # A project bouncing around a stable baseline should not be
    # reported as strongly improving or degrading.
    prediction = QualityTrendPredictor().predict(
        current_health_score=81.5,
        historical_health_scores=[80.0, 82.0, 79.5, 81.0, 80.5],
    )
    assert prediction.direction == TrendDirection.STABLE
    assert 0.0 <= prediction.projected_next_health_score <= 100.0
    assert prediction.data_points_used == 6
