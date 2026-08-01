"""Unit tests for app.core.ai_reasoning.report_generator."""

from app.core.ai_reasoning.report_generator import ReasoningReportGenerator


def test_generate_builds_reasoning_report():
    report = ReasoningReportGenerator().generate(
        project_id="demo-project",
        root_path="/tmp/demo",
        correlation_groups=[],
        dependency_assessments=[],
        debugging_hypotheses=[],
        drift_insight=None,
        recommendations=[],
    )

    assert report.project_id == "demo-project"
    assert report.root_path == "/tmp/demo"
    assert report.generated_at is not None
    assert report.to_dict()["project_id"] == "demo-project"
