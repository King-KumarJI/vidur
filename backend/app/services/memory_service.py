"""
VIDUR Services
Submodule: Memory Service
Purpose: Orchestration logic for the Memory module's read routes
(semantic recall, history, health-score trend). Thin pass-through to
`MemoryEngine`, plus request-level `record_type` string -> enum
validation shared by every route that accepts one.
"""

from typing import List, Optional

from app.memory.engine import MemoryEngine
from app.memory.enums import MemoryRecordType
from app.memory.exceptions import InvalidMemoryQueryError
from app.memory.models import MemoryRecallMatch, MemoryRecord


def _parse_record_type(value: Optional[str]) -> Optional[MemoryRecordType]:
    if value is None:
        return None
    try:
        return MemoryRecordType(value)
    except ValueError as exc:
        valid_values = ", ".join(member.value for member in MemoryRecordType)
        raise InvalidMemoryQueryError(
            f"record_type must be one of: {valid_values}. Received: {value!r}"
        ) from exc


class MemoryService:
    """Orchestrates semantic recall and historical lookups over a
    project's recorded analysis history."""

    def __init__(self, engine: Optional[MemoryEngine] = None) -> None:
        self._engine = engine or MemoryEngine()

    async def recall(
        self, project_id: str, query_text: str, top_k: int, record_type: Optional[str]
    ) -> List[MemoryRecallMatch]:
        return await self._engine.recall(
            project_id, query_text, top_k=top_k, record_type=_parse_record_type(record_type)
        )

    async def history(
        self, project_id: str, record_type: Optional[str], limit: Optional[int]
    ) -> List[MemoryRecord]:
        return await self._engine.history(
            project_id, record_type=_parse_record_type(record_type), limit=limit
        )

    async def health_score_trend(
        self, project_id: str, record_types: Optional[List[str]], limit: Optional[int]
    ) -> List[float]:
        parsed_types = (
            [_parse_record_type(value) for value in record_types] if record_types else None
        )
        return await self._engine.health_score_trend(project_id, record_types=parsed_types, limit=limit)
