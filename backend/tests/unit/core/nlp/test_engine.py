"""Unit tests for app.core.nlp.engine."""

import pytest

from app.config.feature_flags import FeatureFlagRegistry, FeatureFlagSettings
from app.core.nlp.engine import NLPEngine
from app.core.nlp.exceptions import NLPDisabledError
from app.core.project_isolation.exceptions import InvalidProjectIdError


def _registry(minor=True, major=False) -> FeatureFlagRegistry:
    return FeatureFlagRegistry(
        overrides=FeatureFlagSettings(
            MINOR_REQUIREMENT_CONSISTENCY=minor,
            MAJOR_ADVANCED_NLP_DOCUMENT_REASONING=major,
        )
    )


def _write_project(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Demo\n\n## Features\n\n- Email notifications\n\nThe system must send a welcome email.\n"
    )
    (tmp_path / "requirements.txt").write_text("requests==2.32.0\n")
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mailer.py").write_text(
        '"""Sends the welcome email."""\nimport requests\n\ndef send_welcome_email():\n    pass\n'
    )


def test_run_raises_when_feature_flag_disabled(tmp_path):
    _write_project(tmp_path)
    engine = NLPEngine(feature_flag_registry=_registry(minor=False))
    with pytest.raises(NLPDisabledError):
        engine.run("demo-project", str(tmp_path))


def test_run_raises_for_invalid_project_id(tmp_path):
    _write_project(tmp_path)
    engine = NLPEngine(feature_flag_registry=_registry())
    with pytest.raises(InvalidProjectIdError):
        engine.run("!!invalid!!", str(tmp_path))


def test_run_produces_nlp_report(tmp_path):
    _write_project(tmp_path)
    engine = NLPEngine(feature_flag_registry=_registry())

    report = engine.run("demo-project", str(tmp_path))

    assert report.project_id == "demo-project"
    assert report.documented_intent.project_title == "Demo"
    assert "requests" in report.implemented_intent.imported_third_party_packages
    assert report.semantic_similarity_results == []


def test_run_includes_semantic_results_when_major_flag_enabled(tmp_path):
    _write_project(tmp_path)
    engine = NLPEngine(feature_flag_registry=_registry(major=True))

    report = engine.run("demo-project", str(tmp_path))

    assert report.semantic_similarity_results != []


def test_run_normalizes_project_id_case(tmp_path):
    _write_project(tmp_path)
    engine = NLPEngine(feature_flag_registry=_registry())

    report = engine.run("Demo-Project", str(tmp_path))

    assert report.project_id == "demo-project"
