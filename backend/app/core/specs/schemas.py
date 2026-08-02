"""
VIDUR Core - Specs
Submodule: Schemas
Purpose: Request/response shapes for the Specs module's ingestion and
query routes. Ingestion request fields are optional at every level -
any section, or any individual field within a supplied section, that
the caller omits is stored as `status: "missing"` by `SpecsStorage`,
never fabricated or defaulted (CLAUDE.md Specs Module: Missing-sensor
handling). Response schemas mirror `app.core.specs.models` dataclasses'
`to_dict()` output field-for-field. Ships behind the
`MAJOR_IOT_ENVIRONMENTAL_ANALYTICS` feature flag (Article 41-44),
disabled by default.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PersonalMetricsIngestRequest(BaseModel):
    """Personal activity metrics for one ingestion cycle. All fields
    optional; typing_speed_cpm/mouse_activity_rate are aggregate rates
    only (CLAUDE.md Specs Module: Personal)."""

    model_config = ConfigDict(extra="forbid")

    last_session_duration_minutes: Optional[float] = Field(default=None, ge=0)
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)
    caffeine_intake_mg: Optional[float] = Field(default=None, ge=0)
    typing_speed_cpm: Optional[float] = Field(default=None, ge=0)
    mouse_activity_rate: Optional[float] = Field(default=None, ge=0)
    break_frequency_per_hour: Optional[float] = Field(default=None, ge=0)


class ComputerMetricsIngestRequest(BaseModel):
    """Computer resource metrics for one ingestion cycle, as collected
    by the local agent via psutil (CLAUDE.md Specs Module: Computer)."""

    model_config = ConfigDict(extra="forbid")

    cpu_usage_percent: Optional[float] = Field(default=None, ge=0, le=100)
    ram_usage_percent: Optional[float] = Field(default=None, ge=0, le=100)
    disk_io_kbps: Optional[float] = Field(default=None, ge=0)
    internet_latency_ms: Optional[float] = Field(default=None, ge=0)


class EnvironmentalMetricsIngestRequest(BaseModel):
    """Environmental sensor metrics for one ingestion cycle. `source`
    records whether this cycle's readings came from real hardware or
    the simulation fallback (CLAUDE.md Specs Module: Environmental)."""

    model_config = ConfigDict(extra="forbid")

    temperature_celsius: Optional[float] = None
    humidity_percent: Optional[float] = Field(default=None, ge=0, le=100)
    ambient_light_lux: Optional[float] = Field(default=None, ge=0)
    noise_level_db: Optional[float] = Field(default=None, ge=0)
    source: Optional[Literal["hardware", "simulation"]] = None


class SpecsIngestRequest(BaseModel):
    """Partial ingestion payload from the local agent. Any of the
    three sections may be omitted entirely; within a supplied section,
    any individual field may be omitted - both cases are stored as
    `status: "missing"`, never fabricated."""

    model_config = ConfigDict(extra="forbid")

    personal: Optional[PersonalMetricsIngestRequest] = None
    computer: Optional[ComputerMetricsIngestRequest] = None
    environmental: Optional[EnvironmentalMetricsIngestRequest] = None


class MetricReadingResponse(BaseModel):
    """Mirrors `MetricReading.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    status: str
    value: Optional[float] = None
    unit: Optional[str] = None
    source: Optional[str] = None


class PersonalMetricsResponse(BaseModel):
    """Mirrors `PersonalMetrics.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    last_session_duration_minutes: MetricReadingResponse
    sleep_hours: MetricReadingResponse
    caffeine_intake_mg: MetricReadingResponse
    typing_speed_cpm: MetricReadingResponse
    mouse_activity_rate: MetricReadingResponse
    break_frequency_per_hour: MetricReadingResponse


class ComputerMetricsResponse(BaseModel):
    """Mirrors `ComputerMetrics.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    cpu_usage_percent: MetricReadingResponse
    ram_usage_percent: MetricReadingResponse
    disk_io_kbps: MetricReadingResponse
    internet_latency_ms: MetricReadingResponse


class EnvironmentalMetricsResponse(BaseModel):
    """Mirrors `EnvironmentalMetrics.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    temperature_celsius: MetricReadingResponse
    humidity_percent: MetricReadingResponse
    ambient_light_lux: MetricReadingResponse
    noise_level_db: MetricReadingResponse


class SpecsSnapshotResponse(BaseModel):
    """Mirrors `SpecsSnapshot.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    recorded_at: str
    personal: PersonalMetricsResponse
    computer: ComputerMetricsResponse
    environmental: EnvironmentalMetricsResponse


class DeadlineCreateRequest(BaseModel):
    """Request to add a manual deadline entry (CLAUDE.md Specs Module:
    Calendar - upcoming deadlines are manual entry only in VIDUR)."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    due_at: datetime
    notes: Optional[str] = None


class DeadlineResponse(BaseModel):
    """Mirrors `Deadline.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    deadline_id: str
    project_id: str
    title: str
    due_at: str
    created_at: str
    notes: Optional[str] = None


class CalendarResponse(BaseModel):
    """Mirrors `CalendarSnapshot.to_dict()`."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    current_time: str
    day_of_week: str
    upcoming_deadlines: List[DeadlineResponse]
