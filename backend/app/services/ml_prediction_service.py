"""
VIDUR Services
Submodule: ML Prediction Service
Purpose: Orchestration logic for the ML Prediction module's routes.
`MLPredictionEngine.run` requires a completed `InspectionReport` (and
optionally a paired `ReasoningReport`) as input, so this service runs
a fresh inspection (and, unless disabled by the caller, reasoning)
before predicting, fetches the project's recorded (health-score,
finding-count) training history from `MemoryEngine` to train
`QualityTrendPredictor`'s scikit-learn model, and persists the
resulting `MLPredictionReport` back into project memory.
"""

from typing import Optional

from fastapi.concurrency import run_in_threadpool

from app.config.feature_flags import FeatureFlag, feature_flags
from app.core.ml_prediction.engine import MLPredictionEngine
from app.core.ml_prediction.exceptions import MLPredictionDisabledError
from app.core.ml_prediction.models import MLPredictionReport
from app.memory.engine import MemoryEngine
from app.services.ai_reasoning_service import AIReasoningService
from app.services.inspection_service import InspectionService


class MLPredictionService:
    """Orchestrates inspection, optional reasoning, historical
    health-score lookup, ML prediction, and persistence of the
    prediction report into project memory."""

    def __init__(
        self,
        engine: Optional[MLPredictionEngine] = None,
        inspection_service: Optional[InspectionService] = None,
        ai_reasoning_service: Optional[AIReasoningService] = None,
        memory_engine: Optional[MemoryEngine] = None,
    ) -> None:
        self._engine = engine or MLPredictionEngine()
        self._inspection_service = inspection_service or InspectionService()
        self._ai_reasoning_service = ai_reasoning_service or AIReasoningService()
        self._memory_engine = memory_engine or MemoryEngine()

    async def run(self, project_id: str, root_path: str, include_reasoning: bool = True) -> MLPredictionReport:
        if not feature_flags.is_enabled(FeatureFlag.MAJOR_ML_RISK_PREDICTION):
            raise MLPredictionDisabledError(
                "ML prediction was requested but the MAJOR_ML_RISK_PREDICTION "
                "feature flag is disabled."
            )

        reasoning_report = None
        if include_reasoning:
            inspection_report, reasoning_report = await self._ai_reasoning_service.run(project_id, root_path)
        else:
            inspection_report = await self._inspection_service.run(project_id, root_path)

        historical_health_scores = None
        historical_finding_counts = None
        if feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_MEMORY):
            training_data = await self._memory_engine.quality_trend_training_data(project_id)
            historical_health_scores = [point[0] for point in training_data]
            historical_finding_counts = [point[1] for point in training_data]

        report = await run_in_threadpool(
            self._engine.run,
            project_id,
            inspection_report,
            reasoning_report,
            historical_health_scores,
            historical_finding_counts,
        )

        if feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_MEMORY):
            await self._memory_engine.record_ml_prediction(report)

        return report
