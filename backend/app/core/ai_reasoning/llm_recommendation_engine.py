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

Large inspection runs (100+ findings) are sent to the LLM in multiple
smaller batches rather than one call, per a live-Playwright-confirmed
reproduction: a single call carrying a ~39KB, ~10K-token prompt over a
112-finding run consistently exceeded the local 8B model's 8192-token
context window, causing Ollama to silently truncate its input. The
model still returned genuinely well-formed JSON (so this never
surfaced as a parse error) but of the wrong shape (e.g. `{"reasoning":
"..."}` or `{"file_paths": [...], "summary": "..."}` instead of the
required `{"recommendations": [...]}`), because the truncated context
had dropped some or all of the schema instructions. Raising Ollama's
`num_ctx`/`num_predict` alone did not fix this in reproduction (the
model still ignored the schema at that input scale, and took longer)
- only reducing how much the model has to reason about per call did,
hence batching rather than a larger context window.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

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

_BATCH_NOTE = (
    " NOTE: this call carries only one batch of a larger inspection "
    "run's correlation groups / dependency assessments / debugging "
    "hypotheses - other batches contain additional items not shown "
    "here. Do not claim this batch is the complete set of findings for "
    "the project."
)

#: When the combined JSON-serialized size of correlation groups,
#: dependency assessments, and debugging hypotheses exceeds this many
#: characters, the request is split into multiple smaller Ollama calls
#: whose recommendations are merged, instead of one call whose input
#: risks exceeding the local model's context window (see module
#: docstring for the reproduced failure mode this avoids).
CHUNKING_THRESHOLD_CHARS = 6000

#: Target maximum JSON-serialized character size per batch once
#: chunking is triggered - chosen to keep each batch's prompt
#: comfortably inside an 8K-token-context local model even alongside
#: the system prompt and a generous response budget.
BATCH_TARGET_CHARS = 4000

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

        batches = self._make_batches(
            correlation_groups, dependency_assessments, debugging_hypotheses, drift_insight
        )
        multi_batch = len(batches) > 1
        if multi_batch:
            logger.info(
                "AI reasoning LLM prompt split into %d batches (large inspection run).",
                len(batches),
            )

        recommendations: List[Recommendation] = []
        for batch_payload in batches:
            system_prompt = _SYSTEM_PROMPT + _BATCH_NOTE if multi_batch else _SYSTEM_PROMPT
            user_prompt = json.dumps(batch_payload, default=str)
            content = self._ollama_client.chat_json(system_prompt, user_prompt)
            recommendations.extend(self._parse(content))

        recommendations.sort(
            key=lambda rec: (-rec.priority.weight, rec.category.value, rec.title)
        )
        return recommendations

    @staticmethod
    def _batch_payload(
        correlation_groups: List[IssueCorrelationGroup],
        dependency_assessments: List[DependencyImpactAssessment],
        debugging_hypotheses: List[DebuggingHypothesis],
        drift_insight: Optional[DriftInsight],
    ) -> Dict[str, Any]:
        return {
            "correlation_groups": [group.to_dict() for group in correlation_groups],
            "dependency_assessments": [
                assessment.to_dict() for assessment in dependency_assessments
            ],
            "debugging_hypotheses": [
                hypothesis.to_dict() for hypothesis in debugging_hypotheses
            ],
            "drift_insight": drift_insight.to_dict() if drift_insight else None,
        }

    @classmethod
    def _make_batches(
        cls,
        correlation_groups: List[IssueCorrelationGroup],
        dependency_assessments: List[DependencyImpactAssessment],
        debugging_hypotheses: List[DebuggingHypothesis],
        drift_insight: Optional[DriftInsight],
    ) -> List[Dict[str, Any]]:
        """Split reasoning-stage output into one or more batch payloads
        small enough to stay well inside the local model's context
        window. `drift_insight` (a single small object) is attached
        only to the first batch - it never needs splitting, and
        repeating it across every batch would risk the same
        drift-based recommendation being independently generated (and
        left undeduplicated) more than once."""
        tagged: List[Tuple[str, Any]] = (
            [("correlation_group", group) for group in correlation_groups]
            + [("dependency_assessment", assessment) for assessment in dependency_assessments]
            + [("debugging_hypothesis", hypothesis) for hypothesis in debugging_hypotheses]
        )
        sizes = [len(json.dumps(item.to_dict(), default=str)) for _, item in tagged]

        if sum(sizes) <= CHUNKING_THRESHOLD_CHARS:
            return [
                cls._batch_payload(
                    correlation_groups, dependency_assessments, debugging_hypotheses, drift_insight
                )
            ]

        item_batches: List[List[Tuple[str, Any]]] = []
        current: List[Tuple[str, Any]] = []
        current_chars = 0
        for (kind, item), item_chars in zip(tagged, sizes):
            if current and current_chars + item_chars > BATCH_TARGET_CHARS:
                item_batches.append(current)
                current = []
                current_chars = 0
            current.append((kind, item))
            current_chars += item_chars
        if current:
            item_batches.append(current)

        payloads: List[Dict[str, Any]] = []
        for index, item_batch in enumerate(item_batches):
            payloads.append(
                cls._batch_payload(
                    correlation_groups=[item for kind, item in item_batch if kind == "correlation_group"],
                    dependency_assessments=[
                        item for kind, item in item_batch if kind == "dependency_assessment"
                    ],
                    debugging_hypotheses=[
                        item for kind, item in item_batch if kind == "debugging_hypothesis"
                    ],
                    drift_insight=drift_insight if index == 0 else None,
                )
            )
        return payloads

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
