"""Unit tests for app.core.nlp.semantic_reasoner."""

from app.core.nlp.models import DocumentedIntent, ImplementedIntent, RequirementStatement
from app.core.nlp.semantic_reasoner import SemanticSimilarityReasoner


def test_reason_matches_claim_to_most_similar_file():
    documented = DocumentedIntent(
        declared_features=["User authentication with JWT tokens"],
        requirement_statements=[
            RequirementStatement(
                text="The system must send email notifications",
                source_path="README.md",
                line=3,
                keywords=["system", "send", "email", "notifications"],
            )
        ],
    )
    implemented = ImplementedIntent(
        analyzed_file_count=2,
        file_text_blobs={
            "app/auth/jwt_service.py": (
                "JWT authentication token service validate_token generate_token user login"
            ),
            "app/notify/mailer.py": "send_email notification service smtp mailer",
        },
    )

    results = SemanticSimilarityReasoner().reason(documented, implemented)
    by_claim = {result.claim_text: result for result in results}

    assert by_claim["User authentication with JWT tokens"].best_match_file == "app/auth/jwt_service.py"
    assert by_claim["The system must send email notifications"].best_match_file == "app/notify/mailer.py"
    for result in results:
        assert 0.0 <= result.similarity_score <= 1.0


def test_reason_returns_empty_list_when_no_claims():
    documented = DocumentedIntent()
    implemented = ImplementedIntent(
        analyzed_file_count=1, file_text_blobs={"app/x.py": "some text"}
    )
    assert SemanticSimilarityReasoner().reason(documented, implemented) == []


def test_reason_returns_empty_list_when_no_implemented_files():
    documented = DocumentedIntent(declared_features=["Some feature"])
    implemented = ImplementedIntent(analyzed_file_count=0, file_text_blobs={})
    assert SemanticSimilarityReasoner().reason(documented, implemented) == []


def test_reason_no_match_yields_zero_score_and_no_file():
    documented = DocumentedIntent(declared_features=["Quantum teleportation module"])
    implemented = ImplementedIntent(
        analyzed_file_count=1, file_text_blobs={"app/x.py": "basic arithmetic addition"}
    )
    results = SemanticSimilarityReasoner().reason(documented, implemented)
    assert len(results) == 1
    assert results[0].best_match_file is None
    assert results[0].similarity_score == 0.0
