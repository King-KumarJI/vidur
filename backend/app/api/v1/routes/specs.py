"""
VIDUR API Layer
Module: Specs
Purpose: Routes for Specs telemetry ingestion/retrieval (Personal /
Computer / Environmental metrics) and manual deadline/calendar entries,
scoped to the active Project ID bound by `ProjectIsolationMiddleware`.
Ships behind the `MAJOR_IOT_ENVIRONMENTAL_ANALYTICS` feature flag
(Article 41-44), disabled by default - the routes always exist and
compile, but `SpecsStorage` raises `SpecsDisabledError` (mapped to HTTP
403 by `app.api.v1.error_handlers`) until the flag is enabled.

No ML prediction and no local agent live here (out of scope for this
module, per CLAUDE.md's Specs Module section) - just ingestion and
storage.
"""

from typing import List

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_project_id, get_specs_storage
from app.core.specs.schemas import (
    CalendarResponse,
    DeadlineCreateRequest,
    DeadlineResponse,
    SpecsIngestRequest,
    SpecsSnapshotResponse,
)
from app.core.specs.storage import SpecsStorage

router = APIRouter(prefix="/specs", tags=["Specs"])


@router.post("/ingest", response_model=SpecsSnapshotResponse, summary="Ingest a Specs telemetry cycle")
async def ingest_specs(
    body: SpecsIngestRequest,
    project_id: str = Depends(get_project_id),
    storage: SpecsStorage = Depends(get_specs_storage),
) -> SpecsSnapshotResponse:
    snapshot = await storage.ingest(
        project_id,
        personal=body.personal.model_dump() if body.personal is not None else None,
        computer=body.computer.model_dump() if body.computer is not None else None,
        environmental=body.environmental.model_dump() if body.environmental is not None else None,
    )
    return SpecsSnapshotResponse.model_validate(snapshot.to_dict())


@router.get("/current", response_model=SpecsSnapshotResponse, summary="Get the current Specs snapshot")
async def get_current_snapshot(
    project_id: str = Depends(get_project_id),
    storage: SpecsStorage = Depends(get_specs_storage),
) -> SpecsSnapshotResponse:
    snapshot = await storage.get_current_snapshot(project_id)
    return SpecsSnapshotResponse.model_validate(snapshot.to_dict())


@router.post("/deadlines", response_model=DeadlineResponse, summary="Add a manual deadline entry")
async def add_deadline(
    body: DeadlineCreateRequest,
    project_id: str = Depends(get_project_id),
    storage: SpecsStorage = Depends(get_specs_storage),
) -> DeadlineResponse:
    deadline = await storage.add_deadline(project_id, body.title, body.due_at, notes=body.notes)
    return DeadlineResponse.model_validate(deadline.to_dict())


@router.get("/deadlines", response_model=List[DeadlineResponse], summary="List manual deadline entries")
async def list_deadlines(
    project_id: str = Depends(get_project_id),
    storage: SpecsStorage = Depends(get_specs_storage),
) -> List[DeadlineResponse]:
    deadlines = await storage.list_deadlines(project_id)
    return [DeadlineResponse.model_validate(deadline.to_dict()) for deadline in deadlines]


@router.get("/calendar", response_model=CalendarResponse, summary="Get real-time calendar and upcoming deadlines")
async def get_calendar(
    project_id: str = Depends(get_project_id),
    storage: SpecsStorage = Depends(get_specs_storage),
) -> CalendarResponse:
    calendar = await storage.get_calendar(project_id)
    return CalendarResponse.model_validate(calendar.to_dict())
