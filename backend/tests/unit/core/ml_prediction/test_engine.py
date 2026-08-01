"""Unit tests for app.core.ml_prediction.engine."""

import pytest

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.ai_reasoning.engine import AIReasoningEngine
from app.core.inspection_engine.engine import InspectionEngine
from app.core.inspection_engine.models import InspectionReport
from app.core.ml_prediction.engine import MLPredictionEngine
from app.core.ml_prediction.exceptions import InvalidPredictionInputError, MLPredictionDisabledError
from app.core.project_isolation.exceptions import InvalidProjectIdError


def _enabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MAJOR_ML_RISK_PREDICTION=True))


def _disabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MAJOR_ML_RISK_PREDICTION=False))


def _inspection_report(tmp_path, project_id: str = "demo-project") -> InspectionReport:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("x = 1\n")
    (pkg / "b.py").write_text("from pkg import a\n")
    return InspectionEngine().run(project_id, str(tmp_path))


def test_run_raises_when_feature_flag_disabled(tmp_path):
    report = _inspection_report(tmp_path)
    engine = MLPredictionEngine(feature_flag_registry=_disabled_registry())
    with pytest.raises(MLPredictionDisabledError):
        engine.run("demo-project", report)


def test_run_raises_for_invalid_project_id(tmp_path):
    report = _inspection_report(tmp_path)
    engine = MLPredictionEngine(feature_flag_registry=_enabled_registry())
    with pytest.raises(InvalidProjectIdError):
        engine.run("!!invalid!!", report)


def test_run_raises_for_mismatched_inspection_report(tmp_path):
    report = _inspection_report(tmp_path, project_id="project-a")
    engine = MLPredictionEngine(feature_flag_registry=_enabled_registry())
    with pytest.raises(InvalidPredictionInputError):
        engine.run("project-b", report)


def test_run_raises_for_mismatched_reasoning_report(tmp_path):
    report = _inspection_report(tmp_path, project_id="demo-project")
    reasoning_registry = FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_AI_REASONING=True))
    reasoning_report = AIReasoningEngine(feature_flag_registry=reasoning_registry).run(
        "demo-project", report
    )
    # Manually construct a mismatched-project reasoning report to exercise the guard.
    mismatched = reasoning_report.__class__(
        project_id="other-project",
        root_path=reasoning_report.root_path,
        generated_at=reasoning_report.generated_at,
    )

    engine = MLPredictionEngine(feature_flag_registry=_enabled_registry())
    with pytest.raises(InvalidPredictionInputError):
        engine.run("demo-project", report, mismatched)


def test_run_produces_ml_prediction_report_without_reasoning_report(tmp_path):
    report = _inspection_report(tmp_path)
    engine = MLPredictionEngine(feature_flag_registry=_enabled_registry())

    prediction = engine.run("demo-project", report)

    assert prediction.project_id == "demo-project"
    assert prediction.feature_vector.file_count == len(report.files)
    assert prediction.regression_risk is not None
    assert prediction.technical_debt is not None
    assert prediction.quality_trend is not None
    assert prediction.failure_probability is not None


def test_run_produces_ml_prediction_report_with_reasoning_report(tmp_path):
    report = _inspection_report(tmp_path)
    reasoning_registry = FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_AI_REASONING=True))
    reasoning_report = AIReasoningEngine(feature_flag_registry=reasoning_registry).run(
        "demo-project", report
    )

    engine = MLPredictionEngine(feature_flag_registry=_enabled_registry())
    prediction = engine.run("demo-project", report, reasoning_report)

    assert prediction.project_id == "demo-project"


def test_run_uses_historical_health_scores_for_quality_trend(tmp_path):
    report = _inspection_report(tmp_path)
    engine = MLPredictionEngine(feature_flag_registry=_enabled_registry())

    prediction = engine.run("demo-project", report, historical_health_scores=[50.0, 60.0, 70.0])

    assert prediction.quality_trend.data_points_used == 4


def test_run_normalizes_project_id_case(tmp_path):
    report = _inspection_report(tmp_path)
    engine = MLPredictionEngine(feature_flag_registry=_enabled_registry())

    prediction = engine.run("Demo-Project", report)

    assert prediction.project_id == "demo-project"
