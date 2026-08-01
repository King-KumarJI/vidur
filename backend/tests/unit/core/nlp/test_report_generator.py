"""Unit tests for app.core.nlp.report_generator."""

from app.core.nlp.models import DocumentedIntent, ImplementedIntent
from app.core.nlp.report_generator import NLPReportGenerator


def test_generate_builds_nlp_report():
    report = NLPReportGenerator().generate(
        project_id="demo-project",
        root_path="/tmp/demo",
        documented_intent=DocumentedIntent(),
        implemented_intent=ImplementedIntent(),
        consistency_findings=[],
        semantic_similarity_results=[],
    )

    assert report.project_id == "demo-project"
    assert report.root_path == "/tmp/demo"
    assert report.generated_at is not None
    assert report.to_dict()["project_id"] == "demo-project"
