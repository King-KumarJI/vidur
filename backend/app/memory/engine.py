"""
VIDUR - Memory
Submodule: Engine
Purpose: Orchestrates persistence and recall of VIDUR's own analysis
history - one MemoryRecord per completed Inspection Engine / AI
Reasoning / NLP / ML Prediction / Deep Learning Vision run - through
the MongoDB-backed MemoryRecordStore and the ChromaDB-backed
MemorySemanticIndex. Enforces the MINOR_PROJECT_MEMORY feature flag
and Article 21 (Absolute Project Isolation) by requiring and binding a
valid Project ID for the duration of every operation.

This is Minor-Project baseline infrastructure (Article 41-44 gates
only Major/advanced capabilities behind a default-disabled flag);
MINOR_PROJECT_MEMORY ships enabled by default, matching every other
MINOR_* flag.

Scope (explicit, user-directed): persistent storage and recall of
VIDUR's own analysis history and health-score trends over time - not
conversational/chat memory.
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.config.feature_flags import FeatureFlag, FeatureFlagRegistry, feature_flags
from app.config.logging_config import get_logger
from app.core.ai_reasoning.models import ReasoningReport
from app.core.deep_learning_vision.models import VisualComparisonReport
from app.core.inspection_engine.models import InspectionReport, utc_now
from app.core.ml_prediction.models import MLPredictionReport
from app.core.nlp.models import NLPReport
from app.core.project_isolation import project_scope, validate_project_id_format
from app.core.project_isolation.exceptions import ProjectIsolationError
from app.memory.enums import MemoryRecordType
from app.memory.exceptions import InvalidMemoryQueryError, MemoryDisabledError, MemoryModuleError
from app.memory.models import MemoryRecallMatch, MemoryRecord
from app.memory.record_store import MemoryRecordStore
from app.memory.record_summarizer import RecordSummarizer
from app.memory.semantic_index import MemorySemanticIndex

logger = get_logger("memory.engine")


class MemoryEngine:
    """Top-level orchestrator for recording and recalling VIDUR's own
    analysis history, one project at a time."""

    def __init__(
        self,
        record_summarizer: Optional[RecordSummarizer] = None,
        record_store: Optional[MemoryRecordStore] = None,
        semantic_index: Optional[MemorySemanticIndex] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
    ) -> None:
        self._record_summarizer = record_summarizer or RecordSummarizer()
        self._record_store = record_store or MemoryRecordStore()
        self._semantic_index = semantic_index or MemorySemanticIndex()
        self._feature_flags = feature_flag_registry or feature_flags

    async def record_inspection(self, report: InspectionReport) -> MemoryRecord:
        """Persist a completed InspectionReport into `report`'s own
        project's analysis history."""
        return await self._record(
            project_id=report.project_id,
            record_type=MemoryRecordType.INSPECTION,
            summary=self._record_summarizer.summarize_inspection(report),
            payload=report.to_dict(),
            health_score=self._record_summarizer.health_score_for_inspection(report),
        )

    async def record_reasoning(self, report: ReasoningReport) -> MemoryRecord:
        """Persist a completed ReasoningReport into `report`'s own
        project's analysis history."""
        return await self._record(
            project_id=report.project_id,
            record_type=MemoryRecordType.AI_REASONING,
            summary=self._record_summarizer.summarize_reasoning(report),
            payload=report.to_dict(),
            health_score=self._record_summarizer.health_score_for_reasoning(report),
        )

    async def record_nlp(self, report: NLPReport) -> MemoryRecord:
        """Persist a completed NLPReport into `report`'s own project's
        analysis history."""
        return await self._record(
            project_id=report.project_id,
            record_type=MemoryRecordType.NLP,
            summary=self._record_summarizer.summarize_nlp(report),
            payload=report.to_dict(),
            health_score=self._record_summarizer.health_score_for_nlp(report),
        )

    async def record_ml_prediction(self, report: MLPredictionReport) -> MemoryRecord:
        """Persist a completed MLPredictionReport into `report`'s own
        project's analysis history."""
        return await self._record(
            project_id=report.project_id,
            record_type=MemoryRecordType.ML_PREDICTION,
            summary=self._record_summarizer.summarize_ml_prediction(report),
            payload=report.to_dict(),
            health_score=self._record_summarizer.health_score_for_ml_prediction(report),
        )

    async def record_visual_comparison(self, report: VisualComparisonReport) -> MemoryRecord:
        """Persist a completed VisualComparisonReport into `report`'s
        own project's analysis history."""
        return await self._record(
            project_id=report.project_id,
            record_type=MemoryRecordType.VISUAL_REGRESSION,
            summary=self._record_summarizer.summarize_visual_comparison(report),
            payload=report.to_dict(),
            health_score=self._record_summarizer.health_score_for_visual_comparison(report),
        )

    async def recall(
        self,
        project_id: str,
        query_text: str,
        top_k: int = 5,
        record_type: Optional[MemoryRecordType] = None,
    ) -> List[MemoryRecallMatch]:
        """Semantically recall `project_id`'s past analysis records
        most relevant to `query_text`, highest similarity first,
        optionally restricted to a single `record_type`.

        Raises MemoryDisabledError if MINOR_PROJECT_MEMORY is
        disabled, InvalidProjectIdError if `project_id` fails format
        validation, InvalidMemoryQueryError if `query_text` is empty,
        and MemoryModuleError wrapping any other unexpected failure.
        """
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)
        if not query_text or not query_text.strip():
            raise InvalidMemoryQueryError("query_text must be a non-empty string")

        logger.info("Memory recall started for project_id=%s", normalized_project_id)

        with project_scope(normalized_project_id):
            try:
                matches = self._semantic_index.query(
                    normalized_project_id, query_text, top_k=top_k, record_type=record_type
                )
                records = (
                    await self._record_store.get_by_ids(
                        normalized_project_id, [match.record_id for match in matches]
                    )
                    if matches
                    else []
                )
            except (MemoryModuleError, ProjectIsolationError):
                raise
            except Exception as exc:  # recall must never crash the caller
                logger.error(
                    "Memory recall failed for project_id=%s: %s", normalized_project_id, exc
                )
                raise MemoryModuleError(
                    f"Memory recall failed for project '{normalized_project_id}': {exc}"
                ) from exc

        records_by_id = {record.record_id: record for record in records}
        results = [
            MemoryRecallMatch(record=records_by_id[match.record_id], similarity_score=match.similarity_score)
            for match in matches
            if match.record_id in records_by_id
        ]

        logger.info(
            "Memory recall completed for project_id=%s matches=%d",
            normalized_project_id,
            len(results),
        )
        return results

    async def history(
        self,
        project_id: str,
        record_type: Optional[MemoryRecordType] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryRecord]:
        """Return `project_id`'s stored analysis history, most
        recently recorded first, optionally filtered to a single
        `record_type` and capped at `limit`."""
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        with project_scope(normalized_project_id):
            try:
                return await self._record_store.list_records(
                    normalized_project_id, record_type=record_type, limit=limit
                )
            except (MemoryModuleError, ProjectIsolationError):
                raise
            except Exception as exc:
                logger.error(
                    "Failed to load memory history for project_id=%s: %s",
                    normalized_project_id,
                    exc,
                )
                raise MemoryModuleError(
                    f"Failed to load memory history for project '{normalized_project_id}': {exc}"
                ) from exc

    async def health_score_trend(
        self,
        project_id: str,
        record_types: Optional[List[MemoryRecordType]] = None,
        limit: Optional[int] = None,
    ) -> List[float]:
        """Return `project_id`'s recorded health-score history, oldest
        first - directly usable as the `historical_health_scores`
        argument to MLPredictionEngine.run's QualityTrendPredictor."""
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        with project_scope(normalized_project_id):
            try:
                return await self._record_store.health_score_history(
                    normalized_project_id, record_types=record_types, limit=limit
                )
            except (MemoryModuleError, ProjectIsolationError):
                raise
            except Exception as exc:
                logger.error(
                    "Failed to load health score trend for project_id=%s: %s",
                    normalized_project_id,
                    exc,
                )
                raise MemoryModuleError(
                    f"Failed to load health score trend for project '{normalized_project_id}': {exc}"
                ) from exc

    async def quality_trend_training_data(
        self,
        project_id: str,
        limit: Optional[int] = None,
    ) -> List[Tuple[float, int]]:
        """Return `project_id`'s recorded (health_score, finding_count)
        history, oldest first - directly usable as the matched
        `historical_health_scores`/`historical_finding_counts` input
        to MLPredictionEngine.run's scikit-learn-backed
        QualityTrendPredictor."""
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        with project_scope(normalized_project_id):
            try:
                return await self._record_store.quality_trend_training_data(
                    normalized_project_id, limit=limit
                )
            except (MemoryModuleError, ProjectIsolationError):
                raise
            except Exception as exc:
                logger.error(
                    "Failed to load quality trend training data for project_id=%s: %s",
                    normalized_project_id,
                    exc,
                )
                raise MemoryModuleError(
                    f"Failed to load quality trend training data for project "
                    f"'{normalized_project_id}': {exc}"
                ) from exc

    async def _record(
        self,
        project_id: str,
        record_type: MemoryRecordType,
        summary: str,
        payload: Dict[str, Any],
        health_score: Optional[float],
    ) -> MemoryRecord:
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        record = MemoryRecord(
            record_id=uuid.uuid4().hex,
            project_id=normalized_project_id,
            record_type=record_type,
            recorded_at=utc_now(),
            summary=summary,
            payload=payload,
            health_score=health_score,
        )

        logger.info(
            "Recording %s memory for project_id=%s", record_type.value, normalized_project_id
        )

        with project_scope(normalized_project_id):
            try:
                saved = await self._record_store.save(record)
                self._semantic_index.index(saved)
            except (MemoryModuleError, ProjectIsolationError):
                raise
            except Exception as exc:  # recording must never crash the caller's own run
                logger.error(
                    "Failed to record %s memory for project_id=%s: %s",
                    record_type.value,
                    normalized_project_id,
                    exc,
                )
                raise MemoryModuleError(
                    f"Failed to record {record_type.value} memory for project "
                    f"'{normalized_project_id}': {exc}"
                ) from exc

        logger.info(
            "Recorded %s memory record_id=%s for project_id=%s",
            record_type.value,
            saved.record_id,
            normalized_project_id,
        )
        return saved

    def _require_enabled(self) -> None:
        if not self._feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_MEMORY):
            raise MemoryDisabledError(
                "Memory access was requested but the MINOR_PROJECT_MEMORY "
                "feature flag is disabled."
            )
