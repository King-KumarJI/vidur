"""Unit tests for app.core.nlp.consistency_checker."""

from app.core.nlp.consistency_checker import ConsistencyChecker
from app.core.nlp.models import DocumentedIntent, ImplementedIntent, RequirementStatement


def test_check_flags_declared_but_unused_dependency():
    documented = DocumentedIntent(declared_dependencies=["fastapi", "requests"])
    implemented = ImplementedIntent(
        analyzed_file_count=1, imported_third_party_packages=["requests"]
    )

    findings = ConsistencyChecker().check(documented, implemented)

    codes = [(f.code, f.message) for f in findings if f.code == "DECLARED_DEPENDENCY_UNUSED"]
    assert any("fastapi" in message for _, message in codes)
    assert not any("requests" in message for _, message in codes)


def test_check_flags_undeclared_dependency_used():
    documented = DocumentedIntent(declared_dependencies=["fastapi"])
    implemented = ImplementedIntent(
        analyzed_file_count=1, imported_third_party_packages=["fastapi", "requests"]
    )

    findings = ConsistencyChecker().check(documented, implemented)

    undeclared = [f for f in findings if f.code == "UNDECLARED_DEPENDENCY_USED"]
    assert len(undeclared) == 1
    assert "requests" in undeclared[0].message


def test_check_resolves_known_distribution_aliases():
    documented = DocumentedIntent(declared_dependencies=["python-dotenv", "pydantic-settings"])
    implemented = ImplementedIntent(
        analyzed_file_count=1,
        imported_third_party_packages=["dotenv", "pydantic_settings"],
    )

    findings = ConsistencyChecker().check(documented, implemented)
    assert [f for f in findings if f.category.value == "dependency_consistency"] == []


def test_check_skips_dependency_findings_when_no_manifest_declared():
    documented = DocumentedIntent(declared_dependencies=[])
    implemented = ImplementedIntent(
        analyzed_file_count=1, imported_third_party_packages=["requests"]
    )

    findings = ConsistencyChecker().check(documented, implemented)
    assert findings == []


def test_check_flags_untraceable_requirement_statement():
    documented = DocumentedIntent(
        requirement_statements=[
            RequirementStatement(
                text="The system must archive audit logs",
                source_path="README.md",
                line=5,
                keywords=["system", "archive", "audit", "logs"],
            )
        ]
    )
    implemented = ImplementedIntent(
        analyzed_file_count=1,
        file_text_blobs={"app/unrelated.py": "greeting hello world"},
    )

    findings = ConsistencyChecker().check(documented, implemented)
    assert any(f.code == "REQUIREMENT_NOT_TRACEABLE" for f in findings)


def test_check_does_not_flag_traceable_requirement_statement():
    documented = DocumentedIntent(
        requirement_statements=[
            RequirementStatement(
                text="The system must archive audit logs",
                source_path="README.md",
                line=5,
                keywords=["system", "archive", "audit", "logs"],
            )
        ]
    )
    implemented = ImplementedIntent(
        analyzed_file_count=1,
        file_text_blobs={"app/audit.py": "archive audit logs to storage"},
    )

    findings = ConsistencyChecker().check(documented, implemented)
    assert not any(f.code == "REQUIREMENT_NOT_TRACEABLE" for f in findings)


def test_check_flags_untraceable_feature():
    documented = DocumentedIntent(declared_features=["Real-time push notifications"])
    implemented = ImplementedIntent(
        analyzed_file_count=1,
        file_text_blobs={"app/unrelated.py": "greeting hello world"},
    )

    findings = ConsistencyChecker().check(documented, implemented)
    assert any(f.code == "FEATURE_NOT_TRACEABLE" for f in findings)
