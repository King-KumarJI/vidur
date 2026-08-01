"""
VIDUR - Memory
Submodule: Semantic Index
Purpose: ChromaDB-backed semantic recall over MemoryRecord summaries,
scoped to a project's own isolated vector collection (Article 21) via
`app.db.chromadb.client.get_project_collection`. The index only ever
stores a record's `record_id`, `summary` text, and light metadata - it
is a search accelerator, never the source of truth for record content
(the MongoDB-backed MemoryRecordStore owns that).

The collection handle is obtained through an injectable
`collection_provider` (defaulting to the real `get_project_collection`)
so this index can be exercised in unit tests against a fake, in-memory
collection without a live ChromaDB server, matching the same
dependency-injection pattern used by `MemoryRecordStore`.
"""

from typing import Any, Callable, List, Optional

from app.config.logging_config import get_logger
from app.db.chromadb.client import get_project_collection
from app.memory.enums import MemoryRecordType
from app.memory.exceptions import MemoryPersistenceError
from app.memory.models import MemoryRecord, MemorySemanticMatch

logger = get_logger("memory.semantic_index")

#: Cosine distances from ChromaDB's default embedding space are
#: bounded to [0, 2]; clamp before converting to a [0, 1] similarity
#: score so an unusually distant match still yields a sane score.
_MAX_COSINE_DISTANCE = 2.0


class MemorySemanticIndex:
    """Project-isolated semantic search over MemoryRecord summaries."""

    def __init__(self, collection_provider: Optional[Callable[[str], Any]] = None) -> None:
        self._collection_provider = collection_provider or get_project_collection

    def index(self, record: MemoryRecord) -> None:
        """Index (or re-index) `record`'s summary text for semantic
        recall. Upserts by `record_id`, so re-recording the same
        record is idempotent rather than creating a duplicate entry."""
        collection = self._collection_provider(record.project_id)
        try:
            collection.upsert(
                ids=[record.record_id],
                documents=[record.summary],
                metadatas=[
                    {
                        "project_id": record.project_id,
                        "record_type": record.record_type.value,
                        "recorded_at": record.recorded_at.isoformat(),
                    }
                ],
            )
        except Exception as exc:  # chromadb raises varied exception types
            logger.error(
                "Failed to index memory record %s for project_id=%s: %s",
                record.record_id,
                record.project_id,
                exc,
            )
            raise MemoryPersistenceError(
                f"Failed to index memory record '{record.record_id}' "
                f"for project '{record.project_id}': {exc}"
            ) from exc

    def query(
        self,
        project_id: str,
        query_text: str,
        top_k: int = 5,
        record_type: Optional[MemoryRecordType] = None,
    ) -> List[MemorySemanticMatch]:
        """Return up to `top_k` past records whose summary is most
        semantically similar to `query_text`, highest similarity
        first, optionally restricted to a single `record_type`."""
        collection = self._collection_provider(project_id)
        where = {"record_type": record_type.value} if record_type is not None else None

        try:
            result = collection.query(query_texts=[query_text], n_results=top_k, where=where)
        except Exception as exc:  # chromadb raises varied exception types
            logger.error("Semantic recall query failed for project_id=%s: %s", project_id, exc)
            raise MemoryPersistenceError(
                f"Semantic recall query failed for project '{project_id}': {exc}"
            ) from exc

        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        matches = []
        for record_id, distance in zip(ids, distances):
            clamped_distance = max(0.0, min(distance, _MAX_COSINE_DISTANCE))
            similarity_score = round(1.0 - (clamped_distance / _MAX_COSINE_DISTANCE), 4)
            matches.append(MemorySemanticMatch(record_id=record_id, similarity_score=similarity_score))
        return matches
