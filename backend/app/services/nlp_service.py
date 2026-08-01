"""
VIDUR Services
Submodule: NLP Service
Purpose: Orchestration logic for the NLP module's routes. Runs
`NLPEngine` directly over a project root (blocking file I/O, so off
the event loop via `run_in_threadpool`) and persists the resulting
report through `MemoryEngine`.
"""

from typing import Optional

from fastapi.concurrency import run_in_threadpool

from app.config.feature_flags import FeatureFlag, feature_flags
from app.core.nlp.engine import NLPEngine
from app.core.nlp.models import NLPReport
from app.memory.engine import MemoryEngine


class NLPService:
    """Orchestrates a full NLP analysis run and its persistence into
    project memory."""

    def __init__(
        self,
        engine: Optional[NLPEngine] = None,
        memory_engine: Optional[MemoryEngine] = None,
    ) -> None:
        self._engine = engine or NLPEngine()
        self._memory_engine = memory_engine or MemoryEngine()

    async def run(self, project_id: str, root_path: str) -> NLPReport:
        report = await run_in_threadpool(self._engine.run, project_id, root_path)

        if feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_MEMORY):
            await self._memory_engine.record_nlp(report)

        return report
