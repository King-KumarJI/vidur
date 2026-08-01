"""
VIDUR - Memory
Submodule: Models
Purpose: Plain, JSON-serializable data structures for the Memory
module: a single stored analysis-history entry (MemoryRecord), a raw
semantic-search hit before hydration (MemorySemanticMatch), and a
hydrated semantic recall result pairing a full MemoryRecord with its
similarity score (MemoryRecallMatch).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from app.memory.enums import MemoryRecordType


@dataclass(frozen=True)
class MemoryRecord:
    """One persisted unit of VIDUR's own analysis history: the
    project-isolated, timestamped record of a single completed
    Inspection Engine / AI Reasoning / NLP / ML Prediction / Deep
    Learning Vision run, carrying the run's full report payload plus a
    short human-readable summary used for semantic recall.

    `payload` is always the originating report's own `to_dict()`
    output, kept as an opaque, already-JSON-safe blob rather than
    modeled field-by-field here - the Memory module stores and
    retrieves analysis history, it does not reinterpret it (each
    report's own model classes remain the single source of truth for
    its shape)."""

    record_id: str
    project_id: str
    record_type: MemoryRecordType
    recorded_at: datetime
    summary: str
    payload: Dict[str, Any]
    health_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "project_id": self.project_id,
            "record_type": self.record_type.value,
            "recorded_at": self.recorded_at.isoformat(),
            "summary": self.summary,
            "payload": self.payload,
            "health_score": self.health_score,
        }


@dataclass(frozen=True)
class MemorySemanticMatch:
    """One raw hit returned by the ChromaDB semantic index for a
    recall query: just enough to look the full record up in the
    MongoDB record store (the index is a search accelerator, not the
    source of truth for record content)."""

    record_id: str
    similarity_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {"record_id": self.record_id, "similarity_score": self.similarity_score}


@dataclass(frozen=True)
class MemoryRecallMatch:
    """A semantic recall result: a fully hydrated MemoryRecord paired
    with the similarity score of the query that surfaced it, highest
    similarity first (per MemoryEngine.recall)."""

    record: MemoryRecord
    similarity_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "similarity_score": self.similarity_score,
        }
