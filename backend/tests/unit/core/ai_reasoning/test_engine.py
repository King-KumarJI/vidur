"""Unit tests for app.core.ai_reasoning.engine."""

import pytest

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.ai_reasoning.engine import AIReasoningEngine
from app.core.ai_reasoning.exceptions import InvalidReasoningInputError, ReasoningDisabledError
from app.core.inspection_engine.engine import InspectionEngine
from app.core.inspection_engine.models import InspectionReport
from app.core.project_isolation.exceptions import InvalidProjectIdError


def _enabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_AI_REASONING=True))


def _disabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_AI_REASONING=False))


def _inspection_report(tmp_path, project_id: str = "demo-project") -> InspectionReport:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("# TODO: cleanup\nx = 1\n")
    (pkg / "b.py").write_text("from pkg import a\n")
    return InspectionEngine().run(project_id, str(tmp_path))


def test_run_raises_when_feature_flag_disabled(tmp_path):
    report = _inspection_report(tmp_path)
    engine = AIReasoningEngine(feature_flag_registry=_disabled_registry())
    with pytest.raises(ReasoningDisabledError):
        engine.run("demo-project", report)


def test_run_raises_for_invalid_project_id(tmp_path):
    report = _inspection_report(tmp_path)
    engine = AIReasoningEngine(feature_flag_registry=_enabled_registry())
    with pytest.raises(InvalidProjectIdError):
        engine.run("!!invalid!!", report)


def test_run_raises_for_mismatched_project(tmp_path):
    report = _inspection_report(tmp_path, project_id="project-a")
    engine = AIReasoningEngine(feature_flag_registry=_enabled_registry())
    with pytest.raises(InvalidReasoningInputError):
        engine.run("project-b", report)


def test_run_produces_reasoning_report(tmp_path):
    report = _inspection_report(tmp_path)
    engine = AIReasoningEngine(feature_flag_registry=_enabled_registry())

    reasoning = engine.run("demo-project", report)

    assert reasoning.project_id == "demo-project"
    assert reasoning.recommendations
    codes = {hypothesis.finding_code for hypothesis in reasoning.debugging_hypotheses}
    assert "FORBIDDEN_MARKER_TODO" in codes


def test_run_normalizes_project_id_case(tmp_path):
    report = _inspection_report(tmp_path)
    engine = AIReasoningEngine(feature_flag_registry=_enabled_registry())

    reasoning = engine.run("Demo-Project", report)

    assert reasoning.project_id == "demo-project"
