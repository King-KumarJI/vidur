"""
VIDUR Core - Specs
Submodule: Storage
Purpose: MongoDB-backed persistence and retrieval for Specs telemetry
(Personal / Computer / Environmental metrics) and manual deadline
entries, scoped to a project's own isolated database (Article 21) via
`app.db.mongodb.client.get_project_database` - the same
project-isolation + db pattern `app.memory.record_store` establishes.

Also owns this module's feature-flag gate
(MAJOR_IOT_ENVIRONMENTAL_ANALYTICS, Article 41-44) and the
missing-metric contract from CLAUDE.md's Specs Module spec: any metric
absent from an ingestion payload is stored as `status: "missing"`,
never fabricated or defaulted from a prior reading. Unlike the
multi-stage analysis pipelines (Inspection Engine, AI Reasoning, ...),
Specs ingestion has no analysis stages to orchestrate, so this store
owns its own flag/isolation guarantees directly rather than delegating
to a separate engine.py, matching the module scope as specified.
"""

import itertools
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pymongo.errors import PyMongoError

from app.config.feature_flags import FeatureFlag, FeatureFlagRegistry, feature_flags
from app.config.logging_config import get_logger
from app.core.inspection_engine.models import utc_now
from app.core.project_isolation import project_scope, validate_project_id_format
from app.core.specs.enums import MetricStatus
from app.core.specs.exceptions import (
    InvalidSpecsPayloadError,
    SpecsDisabledError,
    SpecsPersistenceError,
)
from app.core.specs.models import (
    CalendarSnapshot,
    ComputerMetrics,
    Deadline,
    EnvironmentalMetrics,
    MetricReading,
    PersonalMetrics,
    SpecsSnapshot,
)
from app.db.mongodb.client import get_project_database

logger = get_logger("specs.storage")

#: Name of the per-project MongoDB collection that stores ingested
#: Specs telemetry snapshots (one document per ingestion cycle).
SNAPSHOTS_COLLECTION_NAME = "specs_snapshots"

#: Name of the per-project MongoDB collection that stores manual
#: deadline entries.
DEADLINES_COLLECTION_NAME = "specs_deadlines"

#: Process-wide strictly-increasing counter backing `_sequence`. Wall
#: clock `recorded_at` can tie between two ingestions taken in quick
#: succession, and on some platforms `time.monotonic_ns()` itself has
#: coarse resolution (tens of milliseconds) and can also tie between
#: back-to-back calls - so neither is safe as a tiebreaker on its own.
#: `next()` on an `itertools.count()` is a single atomic C-level
#: operation under the GIL and hands out a distinct integer per call,
#: so it can never tie between two ingestions, making "most recent" in
#: get_current_snapshot always well-defined.
_sequence_counter = itertools.count()

_PERSONAL_UNITS = {
    "last_session_duration_minutes": "minutes",
    "sleep_hours": "hours",
    "caffeine_intake_mg": "mg",
    "typing_speed_cpm": "chars_per_minute",
    "mouse_activity_rate": "events_per_minute",
    "break_frequency_per_hour": "breaks_per_hour",
}
_COMPUTER_UNITS = {
    "cpu_usage_percent": "percent",
    "ram_usage_percent": "percent",
    "disk_io_kbps": "kbps",
    "internet_latency_ms": "ms",
}
_ENVIRONMENTAL_UNITS = {
    "temperature_celsius": "celsius",
    "humidity_percent": "percent",
    "ambient_light_lux": "lux",
    "noise_level_db": "db",
}


def _reading(value: Optional[float], unit: str, source: Optional[str] = None) -> MetricReading:
    if value is None:
        return MetricReading.missing(unit=unit, source=source)
    return MetricReading.present(value=value, unit=unit, source=source)


def _build_personal(payload: Optional[Dict[str, Any]]) -> PersonalMetrics:
    payload = payload or {}
    return PersonalMetrics(
        **{field_name: _reading(payload.get(field_name), unit) for field_name, unit in _PERSONAL_UNITS.items()}
    )


def _build_computer(payload: Optional[Dict[str, Any]]) -> ComputerMetrics:
    payload = payload or {}
    return ComputerMetrics(
        **{field_name: _reading(payload.get(field_name), unit) for field_name, unit in _COMPUTER_UNITS.items()}
    )


def _build_environmental(payload: Optional[Dict[str, Any]]) -> EnvironmentalMetrics:
    payload = payload or {}
    source = payload.get("source")
    return EnvironmentalMetrics(
        **{
            field_name: _reading(payload.get(field_name), unit, source=source)
            for field_name, unit in _ENVIRONMENTAL_UNITS.items()
        }
    )


def _reading_from_document(data: Dict[str, Any]) -> MetricReading:
    return MetricReading(
        status=MetricStatus(data["status"]),
        value=data.get("value"),
        unit=data.get("unit"),
        source=data.get("source"),
    )


def _personal_from_document(data: Dict[str, Any]) -> PersonalMetrics:
    return PersonalMetrics(**{field_name: _reading_from_document(data[field_name]) for field_name in _PERSONAL_UNITS})


def _computer_from_document(data: Dict[str, Any]) -> ComputerMetrics:
    return ComputerMetrics(**{field_name: _reading_from_document(data[field_name]) for field_name in _COMPUTER_UNITS})


def _environmental_from_document(data: Dict[str, Any]) -> EnvironmentalMetrics:
    return EnvironmentalMetrics(
        **{field_name: _reading_from_document(data[field_name]) for field_name in _ENVIRONMENTAL_UNITS}
    )


def _snapshot_to_document(snapshot: SpecsSnapshot) -> Dict[str, Any]:
    document = snapshot.to_dict()
    document["_id"] = uuid.uuid4().hex
    document["recorded_at"] = snapshot.recorded_at
    # `_sequence` is a monotonic tiebreaker, storage-internal only -
    # never exposed on SpecsSnapshot - so "most recent" ordering in
    # get_current_snapshot is always well-defined even when
    # `recorded_at` ties. See `_sequence_counter` for why this must be
    # a counter rather than a clock reading.
    document["_sequence"] = next(_sequence_counter)
    return document


def _document_to_snapshot(document: Dict[str, Any]) -> SpecsSnapshot:
    return SpecsSnapshot(
        project_id=document["project_id"],
        recorded_at=document["recorded_at"],
        personal=_personal_from_document(document["personal"]),
        computer=_computer_from_document(document["computer"]),
        environmental=_environmental_from_document(document["environmental"]),
    )


def _deadline_to_document(deadline: Deadline) -> Dict[str, Any]:
    return {
        "_id": deadline.deadline_id,
        "project_id": deadline.project_id,
        "title": deadline.title,
        "due_at": deadline.due_at,
        "created_at": deadline.created_at,
        "notes": deadline.notes,
    }


def _deadline_from_document(document: Dict[str, Any]) -> Deadline:
    return Deadline(
        deadline_id=document["_id"],
        project_id=document["project_id"],
        title=document["title"],
        due_at=document["due_at"],
        created_at=document["created_at"],
        notes=document.get("notes"),
    )


class SpecsStorage:
    """Project-isolated persistence for Specs telemetry snapshots and
    manual deadline entries. Enforces the
    MAJOR_IOT_ENVIRONMENTAL_ANALYTICS feature flag and Article 21
    (Absolute Project Isolation) on every public operation."""

    def __init__(
        self,
        database_provider: Optional[Callable[[str], Any]] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
    ) -> None:
        self._database_provider = database_provider or get_project_database
        self._feature_flags = feature_flag_registry or feature_flags

    def _snapshots_collection(self, project_id: str) -> Any:
        return self._database_provider(project_id)[SNAPSHOTS_COLLECTION_NAME]

    def _deadlines_collection(self, project_id: str) -> Any:
        return self._database_provider(project_id)[DEADLINES_COLLECTION_NAME]

    async def ingest(
        self,
        project_id: str,
        personal: Optional[Dict[str, Any]] = None,
        computer: Optional[Dict[str, Any]] = None,
        environmental: Optional[Dict[str, Any]] = None,
    ) -> SpecsSnapshot:
        """Store one ingestion cycle from the local agent.

        Any of the three sections, or any individual field within a
        supplied section, may be absent - each absent metric is stored
        as `status: "missing"`, never fabricated. Raises
        SpecsDisabledError if MAJOR_IOT_ENVIRONMENTAL_ANALYTICS is
        disabled, InvalidProjectIdError if `project_id` fails format
        validation, and SpecsPersistenceError if the write fails.
        """
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        snapshot = SpecsSnapshot(
            project_id=normalized_project_id,
            recorded_at=utc_now(),
            personal=_build_personal(personal),
            computer=_build_computer(computer),
            environmental=_build_environmental(environmental),
        )

        logger.info("Ingesting specs snapshot for project_id=%s", normalized_project_id)

        with project_scope(normalized_project_id):
            collection = self._snapshots_collection(normalized_project_id)
            try:
                await collection.insert_one(_snapshot_to_document(snapshot))
            except PyMongoError as exc:
                logger.error(
                    "Failed to persist specs snapshot for project_id=%s: %s",
                    normalized_project_id,
                    exc,
                )
                raise SpecsPersistenceError(
                    f"Failed to persist specs snapshot for project '{normalized_project_id}': {exc}"
                ) from exc

        logger.info("Ingested specs snapshot for project_id=%s", normalized_project_id)
        return snapshot

    async def get_current_snapshot(self, project_id: str) -> SpecsSnapshot:
        """Return the most recently ingested SpecsSnapshot for
        `project_id`. If nothing has been ingested yet, returns a
        snapshot with every metric explicitly marked missing rather
        than fabricating values or raising an error."""
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        with project_scope(normalized_project_id):
            collection = self._snapshots_collection(normalized_project_id)
            try:
                document = await collection.find_one(
                    {"project_id": normalized_project_id},
                    sort=[("recorded_at", -1), ("_sequence", -1)],
                )
            except PyMongoError as exc:
                logger.error(
                    "Failed to load current specs snapshot for project_id=%s: %s",
                    normalized_project_id,
                    exc,
                )
                raise SpecsPersistenceError(
                    f"Failed to load current specs snapshot for project "
                    f"'{normalized_project_id}': {exc}"
                ) from exc

        if document is None:
            return SpecsSnapshot(
                project_id=normalized_project_id,
                recorded_at=utc_now(),
                personal=_build_personal(None),
                computer=_build_computer(None),
                environmental=_build_environmental(None),
            )

        return _document_to_snapshot(document)

    async def add_deadline(
        self,
        project_id: str,
        title: str,
        due_at: datetime,
        notes: Optional[str] = None,
    ) -> Deadline:
        """Persist a manual deadline entry (CLAUDE.md Specs Module:
        Calendar - upcoming deadlines are manual entry only)."""
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)
        if not title or not title.strip():
            raise InvalidSpecsPayloadError("title must be a non-empty string")

        deadline = Deadline(
            deadline_id=uuid.uuid4().hex,
            project_id=normalized_project_id,
            title=title.strip(),
            due_at=due_at,
            created_at=utc_now(),
            notes=notes,
        )

        with project_scope(normalized_project_id):
            collection = self._deadlines_collection(normalized_project_id)
            try:
                await collection.insert_one(_deadline_to_document(deadline))
            except PyMongoError as exc:
                logger.error(
                    "Failed to persist deadline for project_id=%s: %s", normalized_project_id, exc
                )
                raise SpecsPersistenceError(
                    f"Failed to persist deadline for project '{normalized_project_id}': {exc}"
                ) from exc

        return deadline

    async def list_deadlines(self, project_id: str) -> List[Deadline]:
        """Return `project_id`'s manual deadline entries, soonest due
        first."""
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        with project_scope(normalized_project_id):
            collection = self._deadlines_collection(normalized_project_id)
            try:
                cursor = collection.find({"project_id": normalized_project_id}).sort("due_at", 1)
                documents = await cursor.to_list(length=None)
            except PyMongoError as exc:
                logger.error(
                    "Failed to list deadlines for project_id=%s: %s", normalized_project_id, exc
                )
                raise SpecsPersistenceError(
                    f"Failed to list deadlines for project '{normalized_project_id}': {exc}"
                ) from exc

        return [_deadline_from_document(document) for document in documents]

    async def get_calendar(self, project_id: str) -> CalendarSnapshot:
        """Return the real-time day/time plus `project_id`'s upcoming
        (not yet due) deadlines, soonest first (CLAUDE.md Specs
        Module: Calendar - time of day and day of week are computed,
        real-time)."""
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        now = utc_now()
        all_deadlines = await self.list_deadlines(normalized_project_id)
        upcoming_deadlines = [deadline for deadline in all_deadlines if deadline.due_at >= now]

        return CalendarSnapshot(
            project_id=normalized_project_id,
            current_time=now,
            day_of_week=now.strftime("%A"),
            upcoming_deadlines=upcoming_deadlines,
        )

    def _require_enabled(self) -> None:
        if not self._feature_flags.is_enabled(FeatureFlag.MAJOR_IOT_ENVIRONMENTAL_ANALYTICS):
            raise SpecsDisabledError(
                "Specs access was requested but the MAJOR_IOT_ENVIRONMENTAL_ANALYTICS "
                "feature flag is disabled."
            )
