"""
VIDUR Services
Submodule: AI Reasoning Service
Purpose: Orchestration logic for the AI Reasoning module's routes.
`AIReasoningEngine.run` requires a completed `InspectionReport` as its
input, so this service runs a fresh inspection (via
`InspectionService`, which also persists it) before reasoning over it,
and persists the resulting `ReasoningReport` through `MemoryEngine`.
"""

from typing import Optional, Tuple

from fastapi.concurrency import run_in_threadpool

from app.config.feature_flags import FeatureFlag, feature_flags
from app.core.ai_reasoning.engine import AIReasoningEngine
from app.core.ai_reasoning.models import ReasoningReport
from app.core.inspection_engine.models import InspectionReport
from app.memory.engine import MemoryEngine
from app.services.inspection_service import InspectionService


class AIReasoningService:
    """Orchestrates a fresh inspection followed by AI reasoning, and
    persistence of the reasoning report into project memory."""

    def __init__(
        self,
        engine: Optional[AIReasoningEngine] = None,
        inspection_service: Optional[InspectionService] = None,
        memory_engine: Optional[MemoryEngine] = None,
    ) -> None:
        self._engine = engine or AIReasoningEngine()
        self._inspection_service = inspection_service or InspectionService()
        self._memory_engine = memory_engine or MemoryEngine()

    async def run(self, project_id: str, root_path: str) -> Tuple[InspectionReport, ReasoningReport]:
        inspection_report = await self._inspection_service.run(project_id, root_path)

        reasoning_report = await run_in_threadpool(self._engine.run, project_id, inspection_report)

        if feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_MEMORY):
            await self._memory_engine.record_reasoning(reasoning_report)

        return inspection_report, reasoning_report
