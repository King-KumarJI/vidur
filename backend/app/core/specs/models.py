"""
VIDUR Core - Specs
Submodule: Models
Purpose: Plain, JSON-serializable data structures for the Specs module
- Personal / Computer / Environmental telemetry snapshots, and manual
Calendar deadline entries. Every metric is wrapped in a MetricReading
carrying an explicit MetricStatus, so a missing sensor or manual input
is always reported as `status: "missing"`, never fabricated or
silently defaulted (CLAUDE.md Specs Module: Missing-sensor handling).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.specs.enums import MetricStatus


@dataclass(frozen=True)
class MetricReading:
    """A single metric value paired with an explicit presence status."""

    status: MetricStatus
    value: Optional[float] = None
    unit: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
        }

    @staticmethod
    def present(value: float, unit: Optional[str] = None, source: Optional[str] = None) -> "MetricReading":
        return MetricReading(status=MetricStatus.PRESENT, value=value, unit=unit, source=source)

    @staticmethod
    def missing(unit: Optional[str] = None, source: Optional[str] = None) -> "MetricReading":
        return MetricReading(status=MetricStatus.MISSING, value=None, unit=unit, source=source)


@dataclass(frozen=True)
class PersonalMetrics:
    """Personal activity metrics for one ingestion cycle (CLAUDE.md
    Specs Module: Personal). typing_speed_cpm and mouse_activity_rate
    are aggregate rates only, never continuous key content or mouse
    coordinate logging."""

    last_session_duration_minutes: MetricReading
    sleep_hours: MetricReading
    caffeine_intake_mg: MetricReading
    typing_speed_cpm: MetricReading
    mouse_activity_rate: MetricReading
    break_frequency_per_hour: MetricReading

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_session_duration_minutes": self.last_session_duration_minutes.to_dict(),
            "sleep_hours": self.sleep_hours.to_dict(),
            "caffeine_intake_mg": self.caffeine_intake_mg.to_dict(),
            "typing_speed_cpm": self.typing_speed_cpm.to_dict(),
            "mouse_activity_rate": self.mouse_activity_rate.to_dict(),
            "break_frequency_per_hour": self.break_frequency_per_hour.to_dict(),
        }


@dataclass(frozen=True)
class ComputerMetrics:
    """Computer resource metrics for one ingestion cycle, collected via
    psutil in the local agent (CLAUDE.md Specs Module: Computer)."""

    cpu_usage_percent: MetricReading
    ram_usage_percent: MetricReading
    disk_io_kbps: MetricReading
    internet_latency_ms: MetricReading

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_usage_percent": self.cpu_usage_percent.to_dict(),
            "ram_usage_percent": self.ram_usage_percent.to_dict(),
            "disk_io_kbps": self.disk_io_kbps.to_dict(),
            "internet_latency_ms": self.internet_latency_ms.to_dict(),
        }


@dataclass(frozen=True)
class EnvironmentalMetrics:
    """Environmental sensor metrics for one ingestion cycle, via
    ESP32/Arduino with simulation fallback (CLAUDE.md Specs Module:
    Environmental). Each reading's `source` records whether it came
    from real hardware or the simulation fallback."""

    temperature_celsius: MetricReading
    humidity_percent: MetricReading
    ambient_light_lux: MetricReading
    noise_level_db: MetricReading

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature_celsius": self.temperature_celsius.to_dict(),
            "humidity_percent": self.humidity_percent.to_dict(),
            "ambient_light_lux": self.ambient_light_lux.to_dict(),
            "noise_level_db": self.noise_level_db.to_dict(),
        }


@dataclass(frozen=True)
class SpecsSnapshot:
    """One full ingestion cycle - or the current-snapshot read of the
    most recent one - combining all three telemetry categories for a
    single project."""

    project_id: str
    recorded_at: datetime
    personal: PersonalMetrics
    computer: ComputerMetrics
    environmental: EnvironmentalMetrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "recorded_at": self.recorded_at.isoformat(),
            "personal": self.personal.to_dict(),
            "computer": self.computer.to_dict(),
            "environmental": self.environmental.to_dict(),
        }


@dataclass(frozen=True)
class Deadline:
    """A manually entered upcoming deadline (CLAUDE.md Specs Module:
    Calendar - upcoming deadlines are manual entry only in VIDUR)."""

    deadline_id: str
    project_id: str
    title: str
    due_at: datetime
    created_at: datetime
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deadline_id": self.deadline_id,
            "project_id": self.project_id,
            "title": self.title,
            "due_at": self.due_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CalendarSnapshot:
    """Real-time computed time-of-day/day-of-week plus the project's
    upcoming (not yet due) deadlines, soonest first."""

    project_id: str
    current_time: datetime
    day_of_week: str
    upcoming_deadlines: List[Deadline] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "current_time": self.current_time.isoformat(),
            "day_of_week": self.day_of_week,
            "upcoming_deadlines": [deadline.to_dict() for deadline in self.upcoming_deadlines],
        }
