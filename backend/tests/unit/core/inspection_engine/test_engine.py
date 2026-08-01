"""Unit tests for app.core.inspection_engine.engine."""

import pytest

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.inspection_engine.engine import InspectionEngine
from app.core.inspection_engine.enums import InspectionStatus
from app.core.inspection_engine.exceptions import InspectionDisabledError
from app.core.project_isolation.exceptions import InvalidProjectIdError


def _enabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_PROJECT_INSPECTION=True))


def _disabled_registry() -> FeatureFlagRegistry:
    return FeatureFlagRegistry(overrides=FeatureFlagSettings(MINOR_PROJECT_INSPECTION=False))


def test_run_raises_when_feature_flag_disabled(tmp_path):
    engine = InspectionEngine(feature_flag_registry=_disabled_registry())
    with pytest.raises(InspectionDisabledError):
        engine.run("demo-project", str(tmp_path))


def test_run_raises_for_invalid_project_id(tmp_path):
    engine = InspectionEngine(feature_flag_registry=_enabled_registry())
    with pytest.raises(InvalidProjectIdError):
        engine.run("!!invalid!!", str(tmp_path))


def test_run_produces_completed_report(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text('"""Module."""\n\n\ndef add(a, b):\n    """Add."""\n    return a + b\n')

    engine = InspectionEngine(feature_flag_registry=_enabled_registry())
    report = engine.run("demo-project", str(tmp_path))

    assert report.status is InspectionStatus.COMPLETED
    assert report.project_id == "demo-project"
    assert len(report.files) == 2
    assert len(report.file_metrics) == 2
    assert report.health_score == 100.0
    assert report.snapshot is not None


def test_run_detects_findings_across_analyzers(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("# TODO: cleanup\nx = 1\n")

    engine = InspectionEngine(feature_flag_registry=_enabled_registry())
    report = engine.run("demo-project", str(tmp_path))

    codes = {finding.code for finding in report.findings}
    assert "FORBIDDEN_MARKER_TODO" in codes
    assert "MISSING_INIT_FILE" in codes
    assert report.health_score < 100.0


def test_run_with_previous_snapshot_reports_drift(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    engine = InspectionEngine(feature_flag_registry=_enabled_registry())
    first_report = engine.run("demo-project", str(tmp_path))

    (tmp_path / "b.py").write_text("y = 2\n")
    second_report = engine.run(
        "demo-project", str(tmp_path), previous_snapshot=first_report.snapshot
    )

    drift_findings = [f for f in second_report.findings if f.code == "FILE_ADDED"]
    assert len(drift_findings) == 1
    assert drift_findings[0].file_path == "b.py"


def test_run_normalizes_project_id_case(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    engine = InspectionEngine(feature_flag_registry=_enabled_registry())

    report = engine.run("Demo-Project", str(tmp_path))

    assert report.project_id == "demo-project"
