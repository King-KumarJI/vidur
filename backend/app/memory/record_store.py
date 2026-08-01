"""
VIDUR - Memory
Submodule: Record Store
Purpose: MongoDB-backed persistence for MemoryRecord analysis history,
scoped to a project's own isolated database (Article 21) via
`app.db.mongodb.client.get_project_database`. Owns the mapping between
MemoryRecord and its MongoDB document shape; MemoryRecord.to_dict()
itself stays JSON-safe/isoformat, matching every other report model in
the codebase, while documents stored here keep `recorded_at` as a
native datetime so MongoDB can sort and range-query it correctly.

The database handle is obtained through an injectable
`database_provider` (defaulting to the real `get_project_database`) so
this store can be exercised in unit tests against a fake, in-memory
collection without a live MongoDB server - the same dependency-
injection pattern every prior module's engine uses for its analyzer
components.
"""

from typing import Any, Callable, Dict, List, Optional

from pymongo.errors import PyMongoError

from app.config.logging_config import get_logger
from app.db.mongodb.client import get_project_database
from app.memory.enums import MemoryRecordType
from app.memory.exceptions import MemoryPersistenceError
from app.memory.models import MemoryRecord

logger = get_logger("memory.record_store")

#: Name of the per-project MongoDB collection that stores memory records.
COLLECTION_NAME = "memory_records"


def _to_document(record: MemoryRecord) -> Dict[str, Any]:
    return {
        "_id": record.record_id,
        "project_id": record.project_id,
        "record_type": record.record_type.value,
        "recorded_at": record.recorded_at,
        "summary": record.summary,
        "payload": record.payload,
        "health_score": record.health_score,
    }


def _from_document(document: Dict[str, Any]) -> MemoryRecord:
    return MemoryRecord(
        record_id=document["_id"],
        project_id=document["project_id"],
        record_type=MemoryRecordType(document["record_type"]),
        recorded_at=document["recorded_at"],
        summary=document["summary"],
        payload=document["payload"],
        health_score=document.get("health_score"),
    )


class MemoryRecordStore:
    """Project-isolated CRUD/query access to persisted MemoryRecords."""

    def __init__(self, database_provider: Optional[Callable[[str], Any]] = None) -> None:
        self._database_provider = database_provider or get_project_database

    def _collection(self, project_id: str) -> Any:
        return self._database_provider(project_id)[COLLECTION_NAME]

    async def save(self, record: MemoryRecord) -> MemoryRecord:
        """Persist `record`, upserting by `record_id` so a retried
        call is idempotent rather than creating a duplicate."""
        collection = self._collection(record.project_id)
        try:
            await collection.replace_one(
                {"_id": record.record_id}, _to_document(record), upsert=True
            )
        except PyMongoError as exc:
            logger.error(
                "Failed to persist memory record %s for project_id=%s: %s",
                record.record_id,
                record.project_id,
                exc,
            )
            raise MemoryPersistenceError(
                f"Failed to persist memory record '{record.record_id}' "
                f"for project '{record.project_id}': {exc}"
            ) from exc
        return record

    async def list_records(
        self,
        project_id: str,
        record_type: Optional[MemoryRecordType] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryRecord]:
        """Return records for `project_id`, most recently recorded
        first, optionally filtered to a single `record_type` and
        capped at `limit`."""
        collection = self._collection(project_id)
        query: Dict[str, Any] = {"project_id": project_id}
        if record_type is not None:
            query["record_type"] = record_type.value

        try:
            cursor = collection.find(query).sort("recorded_at", -1)
            if limit is not None:
                cursor = cursor.limit(limit)
            documents = await cursor.to_list(length=limit)
        except PyMongoError as exc:
            logger.error("Failed to list memory records for project_id=%s: %s", project_id, exc)
            raise MemoryPersistenceError(
                f"Failed to list memory records for project '{project_id}': {exc}"
            ) from exc

        return [_from_document(document) for document in documents]

    async def get_by_ids(self, project_id: str, record_ids: List[str]) -> List[MemoryRecord]:
        """Return the subset of `record_ids` that belong to
        `project_id` and still exist in the store."""
        if not record_ids:
            return []

        collection = self._collection(project_id)
        try:
            cursor = collection.find({"project_id": project_id, "_id": {"$in": list(record_ids)}})
            documents = await cursor.to_list(length=len(record_ids))
        except PyMongoError as exc:
            logger.error(
                "Failed to fetch memory records by id for project_id=%s: %s", project_id, exc
            )
            raise MemoryPersistenceError(
                f"Failed to fetch memory records by id for project '{project_id}': {exc}"
            ) from exc

        return [_from_document(document) for document in documents]

    async def health_score_history(
        self,
        project_id: str,
        record_types: Optional[List[MemoryRecordType]] = None,
        limit: Optional[int] = None,
    ) -> List[float]:
        """Return the health scores of `project_id`'s past runs,
        oldest first, for use as `historical_health_scores` input to
        MLPredictionEngine's QualityTrendPredictor. Only records that
        carry a health score are included."""
        collection = self._collection(project_id)
        query: Dict[str, Any] = {"project_id": project_id, "health_score": {"$ne": None}}
        if record_types:
            query["record_type"] = {"$in": [record_type.value for record_type in record_types]}

        try:
            cursor = collection.find(query).sort("recorded_at", 1)
            if limit is not None:
                cursor = cursor.limit(limit)
            documents = await cursor.to_list(length=limit)
        except PyMongoError as exc:
            logger.error(
                "Failed to load health score history for project_id=%s: %s", project_id, exc
            )
            raise MemoryPersistenceError(
                f"Failed to load health score history for project '{project_id}': {exc}"
            ) from exc

        return [document["health_score"] for document in documents]
