"""
VIDUR Services
Submodule: Inspection Service
Purpose: Orchestration logic for the Inspection Engine module's
routes. Runs `InspectionEngine` (blocking file I/O, so off the event
loop via `run_in_threadpool`), automatically feeding in the project's
most recently recorded snapshot as the drift-detection baseline and
persisting the resulting report through `MemoryEngine` - closing the
loop the Inspection Engine's own docstrings deferred to "the future
Memory module" (see `InspectionSnapshot`).
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi.concurrency import run_in_threadpool

from app.config.feature_flags import FeatureFlag, feature_flags
from app.core.inspection_engine.engine import InspectionEngine
from app.core.inspection_engine.models import FileRecord, InspectionReport, InspectionSnapshot
from app.memory.engine import MemoryEngine
from app.memory.enums import MemoryRecordType


def _deserialize_snapshot(data: Optional[Dict[str, Any]]) -> Optional[InspectionSnapshot]:
    """Reconstruct an `InspectionSnapshot` from the `snapshot` field of
    a previously recorded `InspectionReport.to_dict()` payload."""
    if not data:
        return None
    files = {path: FileRecord(**record) for path, record in data["files"].items()}
    return InspectionSnapshot(
        project_id=data["project_id"],
        root_path=data["root_path"],
        generated_at=datetime.fromisoformat(data["generated_at"]),
        files=files,
    )


class InspectionService:
    """Orchestrates a full inspection run, its drift baseline, and its
    persistence into project memory."""

    def __init__(
        self,
        engine: Optional[InspectionEngine] = None,
        memory_engine: Optional[MemoryEngine] = None,
    ) -> None:
        self._engine = engine or InspectionEngine()
        self._memory_engine = memory_engine or MemoryEngine()

    async def run(self, project_id: str, root_path: str) -> InspectionReport:
        previous_snapshot = await self._latest_snapshot(project_id)

        report = await run_in_threadpool(self._engine.run, project_id, root_path, previous_snapshot)

        if feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_MEMORY):
            await self._memory_engine.record_inspection(report)

        return report

    async def _latest_snapshot(self, project_id: str) -> Optional[InspectionSnapshot]:
        if not feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_MEMORY):
            return None
        records = await self._memory_engine.history(
            project_id, record_type=MemoryRecordType.INSPECTION, limit=1
        )
        if not records:
            return None
        return _deserialize_snapshot(records[0].payload.get("snapshot"))
