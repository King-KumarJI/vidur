"""Unit tests for app.core.nlp.consistency_checker."""

from typing import Dict, Set

from app.core.nlp.consistency_checker import ConsistencyChecker
from app.core.nlp.models import DocumentedIntent, ImplementedIntent, RequirementStatement


class _StubLinguisticAnalyzer:
    """Deterministic double for LinguisticAnalyzer: returns a
    preconfigured keyword set per exact input text, so the checker's
    exact-match-then-linguistic-fallback logic can be tested without
    depending on spaCy's specific lemmatization choices."""

    def __init__(self, keyword_map: Dict[str, Set[str]]) -> None:
        self._keyword_map = keyword_map

    def extract_keywords(self, text: str) -> Set[str]:
        return self._keyword_map.get(text, set())


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


def test_check_does_not_flag_paraphrased_requirement_via_real_linguistic_fallback():
    # Exact-match keyword overlap is only 1/4 ("incoming") because
    # "requests" (documented, plural) and "validate" (documented) don't
    # exact-match "request" and "validates" (implemented) - the real
    # spaCy-backed LinguisticAnalyzer lemmatizes both sides to the same
    # {validate, incoming, request} and rescues the claim.
    documented = DocumentedIntent(
        requirement_statements=[
            RequirementStatement(
                text="The system should validate incoming requests",
                source_path="README.md",
                line=3,
                keywords=["system", "validate", "incoming", "requests"],
            )
        ]
    )
    implemented = ImplementedIntent(
        analyzed_file_count=1,
        file_text_blobs={"app/validator.py": "validates incoming request payloads"},
    )

    findings = ConsistencyChecker().check(documented, implemented)
    assert not any(f.code == "REQUIREMENT_NOT_TRACEABLE" for f in findings)


def test_check_rescues_requirement_via_stubbed_linguistic_overlap():
    documented = DocumentedIntent(
        requirement_statements=[
            RequirementStatement(
                text="paraphrased claim",
                source_path="README.md",
                line=1,
                keywords=["totally", "different", "wording"],
            )
        ]
    )
    implemented = ImplementedIntent(
        analyzed_file_count=1,
        file_text_blobs={"app/x.py": "unrelated corpus text"},
    )
    stub = _StubLinguisticAnalyzer(
        {
            "paraphrased claim": {"concept"},
            "unrelated corpus text": {"concept", "other"},
        }
    )

    findings = ConsistencyChecker(linguistic_analyzer=stub).check(documented, implemented)
    assert not any(f.code == "REQUIREMENT_NOT_TRACEABLE" for f in findings)


def test_check_still_flags_requirement_when_linguistic_overlap_also_insufficient():
    documented = DocumentedIntent(
        requirement_statements=[
            RequirementStatement(
                text="paraphrased claim",
                source_path="README.md",
                line=1,
                keywords=["totally", "different", "wording"],
            )
        ]
    )
    implemented = ImplementedIntent(
        analyzed_file_count=1,
        file_text_blobs={"app/x.py": "unrelated corpus text"},
    )
    stub = _StubLinguisticAnalyzer(
        {
            "paraphrased claim": {"concept"},
            "unrelated corpus text": {"something", "else"},
        }
    )

    findings = ConsistencyChecker(linguistic_analyzer=stub).check(documented, implemented)
    assert any(f.code == "REQUIREMENT_NOT_TRACEABLE" for f in findings)


def test_check_does_not_flag_paraphrased_feature_via_stubbed_linguistic_overlap():
    documented = DocumentedIntent(declared_features=["push alerts"])
    implemented = ImplementedIntent(
        analyzed_file_count=1,
        file_text_blobs={"app/notify.py": "sends mobile notifications"},
    )
    stub = _StubLinguisticAnalyzer(
        {
            "push alerts": {"notification"},
            "sends mobile notifications": {"notification", "mobile"},
        }
    )

    findings = ConsistencyChecker(linguistic_analyzer=stub).check(documented, implemented)
    assert not any(f.code == "FEATURE_NOT_TRACEABLE" for f in findings)


def test_check_skips_linguistic_fallback_when_corpus_has_no_blobs():
    documented = DocumentedIntent(
        requirement_statements=[
            RequirementStatement(
                text="paraphrased claim",
                source_path="README.md",
                line=1,
                keywords=["totally", "different", "wording"],
            )
        ]
    )
    implemented = ImplementedIntent(analyzed_file_count=0, file_text_blobs={})
    stub = _StubLinguisticAnalyzer({"paraphrased claim": {"concept"}})

    findings = ConsistencyChecker(linguistic_analyzer=stub).check(documented, implemented)
    assert any(f.code == "REQUIREMENT_NOT_TRACEABLE" for f in findings)
