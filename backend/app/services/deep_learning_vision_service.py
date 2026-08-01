"""
VIDUR Services
Submodule: Deep Learning Vision Service
Purpose: Orchestration logic for the Deep Learning Vision module's
routes. Converts caller-supplied request schemas into
`app.core.deep_learning_vision.models` dataclasses (this module is
analysis-only and never captures screenshots itself - the caller
supplies both snapshots directly), runs `DeepLearningVisionEngine`,
and persists the resulting report through `MemoryEngine`.
"""

from typing import Optional

from fastapi.concurrency import run_in_threadpool

from app.config.feature_flags import FeatureFlag, feature_flags
from app.core.deep_learning_vision.engine import DeepLearningVisionEngine
from app.core.deep_learning_vision.models import (
    BoundingBox,
    LayoutElement,
    LayoutSnapshot,
    PixelImage,
    VisualComparisonReport,
    VisualSnapshot,
)
from app.core.inspection_engine.models import utc_now
from app.memory.engine import MemoryEngine
from app.schemas.deep_learning_vision_schemas import VisualSnapshotInput


def _build_snapshot(project_id: str, snapshot_input: VisualSnapshotInput) -> VisualSnapshot:
    image = None
    if snapshot_input.image is not None:
        image = PixelImage(
            width=snapshot_input.image.width,
            height=snapshot_input.image.height,
            channels=snapshot_input.image.channels,
            pixels=tuple(snapshot_input.image.pixels),
        )

    layout = None
    if snapshot_input.layout is not None:
        layout = LayoutSnapshot(
            elements=[
                LayoutElement(
                    element_id=element.element_id,
                    tag=element.tag,
                    bounds=BoundingBox(
                        x=element.bounds.x,
                        y=element.bounds.y,
                        width=element.bounds.width,
                        height=element.bounds.height,
                    ),
                    text=element.text,
                )
                for element in snapshot_input.layout.elements
            ]
        )

    return VisualSnapshot(
        project_id=project_id,
        label=snapshot_input.label,
        captured_at=snapshot_input.captured_at or utc_now(),
        image=image,
        layout=layout,
    )


class DeepLearningVisionService:
    """Orchestrates a visual comparison run and its persistence into
    project memory."""

    def __init__(
        self,
        engine: Optional[DeepLearningVisionEngine] = None,
        memory_engine: Optional[MemoryEngine] = None,
    ) -> None:
        self._engine = engine or DeepLearningVisionEngine()
        self._memory_engine = memory_engine or MemoryEngine()

    async def run(
        self,
        project_id: str,
        baseline: VisualSnapshotInput,
        current: VisualSnapshotInput,
        canvas_width: Optional[int] = None,
        canvas_height: Optional[int] = None,
    ) -> VisualComparisonReport:
        baseline_snapshot = _build_snapshot(project_id, baseline)
        current_snapshot = _build_snapshot(project_id, current)

        report = await run_in_threadpool(
            self._engine.run,
            project_id,
            baseline_snapshot,
            current_snapshot,
            canvas_width,
            canvas_height,
        )

        if feature_flags.is_enabled(FeatureFlag.MINOR_PROJECT_MEMORY):
            await self._memory_engine.record_visual_comparison(report)

        return report
