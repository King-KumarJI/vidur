"""
VIDUR Core - AI Reasoning
Submodule: LLM Recommendation Engine
Purpose: Turn the deterministic outputs of the AI Reasoning pipeline
(issue-correlation groups, dependency-impact assessments, debugging
hypotheses, and drift insight) into a prioritized, human-readable
Recommendation list using a real local LLM via Ollama, per the
CLAUDE.md "Real AI/ML/DL/NLP Upgrade" amendment's AI Reasoning clause.

This is additive to, not a replacement for, RecommendationEngine's
rule-based logic (Article 10-11): `AIReasoningEngine` falls back to
`RecommendationEngine` automatically whenever this engine raises
OllamaUnavailableError or OllamaResponseParsingError.
"""

import json
from typing import Any, List, Optional

from app.config.logging_config import get_logger
from app.core.ai_reasoning.enums import InsightCategory, RecommendationPriority
from app.core.ai_reasoning.exceptions import OllamaResponseParsingError
from app.core.ai_reasoning.models import (
    DebuggingHypothesis,
    DependencyImpactAssessment,
    DriftInsight,
    IssueCorrelationGroup,
    Recommendation,
)
from app.core.ai_reasoning.ollama_client import OllamaClient

logger = get_logger("ai_reasoning.llm_recommendation_engine")

_SYSTEM_PROMPT = (
    "You are the AI Reasoning module of VIDUR, an Intelligent Software "
    "Project Watchdog. You are given the structured output of a "
    "static-analysis pipeline for one project's inspection run: "
    "correlated issue groups, dependency blast-radius assessments, "
    "debugging hypotheses, and a drift insight. Turn this into a "
    "prioritized list of actionable, human-readable recommendations "
    "for the developer. Never invent findings that are not present in "
    "the supplied data, and never claim certainty the data does not "
    "support. Respond with ONLY a single JSON object of exactly this "
    'shape: {"recommendations": [{"priority": '
    '"low|medium|high|critical", "category": '
    '"issue_correlation|dependency_impact|debugging_assistance|'
    'drift_significance", "title": "string", "description": '
    '"string", "supporting_finding_codes": ["string"], '
    '"affected_files": ["string"]}]}. Do not include any text outside '
    "that JSON object. Return an empty \"recommendations\" list if "
    "there is nothing actionable in the supplied data."
)

_VALID_PRIORITIES = {priority.value for priority in RecommendationPriority}
_VALID_CATEGORIES = {category.value for category in InsightCategory}


class LLMRecommendationEngine:
    """Builds a Recommendation list from reasoning-stage output via a
    local Ollama LLM call."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None) -> None:
        self._ollama_client = ollama_client or OllamaClient()

    def build(
        self,
        correlation_groups: List[IssueCorrelationGroup],
        dependency_assessments: List[DependencyImpactAssessment],
        debugging_hypotheses: List[DebuggingHypothesis],
        drift_insight: Optional[DriftInsight],
    ) -> List[Recommendation]:
        """Return a prioritized Recommendation list produced by the
        local LLM reasoning over the supplied reasoning-stage output.

        Raises OllamaUnavailableError (via the underlying
        OllamaClient) if Ollama cannot be reached, and
        OllamaResponseParsingError if it responds but no valid
        recommendation list could be parsed out of its response. Both
        are subclasses of AIReasoningError; `AIReasoningEngine` catches
        both and falls back to `RecommendationEngine`.
        """
        if not correlation_groups and not dependency_assessments and not debugging_hypotheses and drift_insight is None:
            return []

        user_prompt = json.dumps(
            {
                "correlation_groups": [group.to_dict() for group in correlation_groups],
                "dependency_assessments": [
                    assessment.to_dict() for assessment in dependency_assessments
                ],
                "debugging_hypotheses": [
                    hypothesis.to_dict() for hypothesis in debugging_hypotheses
                ],
                "drift_insight": drift_insight.to_dict() if drift_insight else None,
            },
            default=str,
        )

        content = self._ollama_client.chat_json(_SYSTEM_PROMPT, user_prompt)
        recommendations = self._parse(content)
        recommendations.sort(
            key=lambda rec: (-rec.priority.weight, rec.category.value, rec.title)
        )
        return recommendations

    @staticmethod
    def _parse(content: str) -> List[Recommendation]:
        try:
            body = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise OllamaResponseParsingError(f"Ollama response was not valid JSON: {exc}") from exc

        if isinstance(body, list):
            raw_items: Any = body
        elif isinstance(body, dict):
            raw_items = body.get("recommendations")
            if raw_items is None:
                raise OllamaResponseParsingError(
                    "Ollama response JSON had no 'recommendations' key."
                )
            if not isinstance(raw_items, list):
                raise OllamaResponseParsingError(
                    "Ollama response JSON's 'recommendations' key was not a list."
                )
        else:
            raise OllamaResponseParsingError(
                "Ollama response JSON was neither a list nor an object with a "
                "'recommendations' key."
            )

        if not raw_items:
            return []

        recommendations = [
            recommendation
            for recommendation in (
                LLMRecommendationEngine._parse_item(item) for item in raw_items
            )
            if recommendation is not None
        ]
        if not recommendations:
            raise OllamaResponseParsingError(
                "Ollama returned recommendation items but none of them were valid."
            )
        return recommendations

    @staticmethod
    def _parse_item(item: Any) -> Optional[Recommendation]:
        if not isinstance(item, dict):
            logger.warning("Skipping non-object recommendation item from Ollama: %r", item)
            return None

        priority_raw = str(item.get("priority", "")).strip().lower()
        category_raw = str(item.get("category", "")).strip().lower()
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()

        if priority_raw not in _VALID_PRIORITIES:
            logger.warning("Skipping recommendation with invalid priority %r from Ollama", priority_raw)
            return None
        if category_raw not in _VALID_CATEGORIES:
            logger.warning("Skipping recommendation with invalid category %r from Ollama", category_raw)
            return None
        if not title or not description:
            logger.warning("Skipping recommendation with missing title/description from Ollama")
            return None

        supporting = item.get("supporting_finding_codes", [])
        affected = item.get("affected_files", [])

        return Recommendation(
            priority=RecommendationPriority(priority_raw),
            category=InsightCategory(category_raw),
            title=title,
            description=description,
            supporting_finding_codes=(
                [str(code) for code in supporting] if isinstance(supporting, list) else []
            ),
            affected_files=(
                [str(path) for path in affected] if isinstance(affected, list) else []
            ),
        )
