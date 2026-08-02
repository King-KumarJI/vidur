"""
VIDUR Core - Specs
Submodule: Models
Purpose: Plain, JSON-serializable data structures for the Specs module
- Personal / Computer / Environmental telemetry snapshots, manual
Calendar deadline entries, and the ML Prediction Engine's derived
sessions and four required prediction outputs (CLAUDE.md Specs Module:
ML Prediction Engine). Every metric is wrapped in a MetricReading
carrying an explicit MetricStatus, so a missing sensor or manual input
is always reported as `status: "missing"`, never fabricated or
silently defaulted (CLAUDE.md Specs Module: Missing-sensor handling).
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.core.specs.enums import ConfidenceLevel, MetricStatus


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


@dataclass(frozen=True)
class SessionRecord:
    """One reconstructed coding session (CLAUDE.md Specs Module:
    Session derivation) - a contiguous run of ingested snapshots
    spanning `started_at` to `ended_at`, with the aggregate activity
    signals `success_score.py` needs to score it and `predictor.py`
    needs to summarize/compare it. `success_score`/`success_score_basis`
    start unset (a session is derived before it is scored) and are
    filled in by replacing the frozen instance once a score exists."""

    project_id: str
    started_at: datetime
    ended_at: datetime
    duration_minutes: float
    snapshot_count: int
    break_count: int
    breaks_per_hour: Optional[float]
    avg_typing_speed_cpm: Optional[float]
    typing_speed_stdev: Optional[float]
    avg_mouse_activity_rate: Optional[float]
    mouse_activity_stdev: Optional[float]
    success_score: Optional[float] = None
    success_score_basis: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "snapshot_count": self.snapshot_count,
            "break_count": self.break_count,
            "breaks_per_hour": self.breaks_per_hour,
            "avg_typing_speed_cpm": self.avg_typing_speed_cpm,
            "typing_speed_stdev": self.typing_speed_stdev,
            "avg_mouse_activity_rate": self.avg_mouse_activity_rate,
            "mouse_activity_stdev": self.mouse_activity_stdev,
            "success_score": self.success_score,
            "success_score_basis": self.success_score_basis,
        }


@dataclass(frozen=True)
class UpcomingSessionPrediction:
    """Required output 1 (CLAUDE.md ML Prediction Engine): likelihood a
    session starts now, plus the predicted outcome (duration/success
    score) if one does."""

    likelihood_score: float
    predicted_duration_minutes: Optional[float]
    predicted_success_score: Optional[float]
    confidence: ConfidenceLevel
    basis: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "likelihood_score": self.likelihood_score,
            "predicted_duration_minutes": self.predicted_duration_minutes,
            "predicted_success_score": self.predicted_success_score,
            "confidence": self.confidence.value,
            "basis": self.basis,
        }


@dataclass(frozen=True)
class LastSessionSummary:
    """Required output 2 (CLAUDE.md ML Prediction Engine): the most
    recent session's duration and computed Success Score."""

    has_session: bool
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_minutes: Optional[float]
    success_score: Optional[float]
    success_score_basis: Optional[str]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_session": self.has_session,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes": self.duration_minutes,
            "success_score": self.success_score,
            "success_score_basis": self.success_score_basis,
            "message": self.message,
        }


@dataclass(frozen=True)
class RecentSessionsComparison:
    """Required output 3 (CLAUDE.md ML Prediction Engine): average
    Success Score across the up-to-5 most recent sessions. Cold start
    (fewer than 5) averages over however many exist and says so
    explicitly rather than padding with fabricated sessions."""

    sessions_considered: int
    success_scores: List[float]
    average_success_score: Optional[float]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sessions_considered": self.sessions_considered,
            "success_scores": self.success_scores,
            "average_success_score": self.average_success_score,
            "message": self.message,
        }


@dataclass(frozen=True)
class WeeklyPoint:
    """One day's aggregated coding time within a Mon-Sun weekly
    breakdown. A day with no session still gets an explicit point with
    `total_minutes: 0.0` - never omitted or interpolated (CLAUDE.md ML
    Prediction Engine: Weekly zero-fill)."""

    day_of_week: str
    date: date
    total_minutes: float
    session_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day_of_week": self.day_of_week,
            "date": self.date.isoformat(),
            "total_minutes": self.total_minutes,
            "session_count": self.session_count,
        }


@dataclass(frozen=True)
class WeeklyCodingTime:
    """Required output 4 (CLAUDE.md ML Prediction Engine): a Mon-Sun
    weekly coding-time breakdown that always emits exactly 7 points."""

    project_id: str
    week_start: date
    week_end: date
    points: List[WeeklyPoint]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "points": [point.to_dict() for point in self.points],
        }


@dataclass(frozen=True)
class SpecsPredictionReport:
    """Combined report bundling all four ML Prediction Engine outputs
    for a single project, as returned by `GET /specs/prediction`."""

    project_id: str
    generated_at: datetime
    upcoming_session: UpcomingSessionPrediction
    last_session: LastSessionSummary
    recent_sessions: RecentSessionsComparison
    weekly_coding_time: WeeklyCodingTime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "generated_at": self.generated_at.isoformat(),
            "upcoming_session": self.upcoming_session.to_dict(),
            "last_session": self.last_session.to_dict(),
            "recent_sessions": self.recent_sessions.to_dict(),
            "weekly_coding_time": self.weekly_coding_time.to_dict(),
        }
