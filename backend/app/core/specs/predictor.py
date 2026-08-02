"""
VIDUR Core - Specs
Submodule: ML Prediction Engine
Purpose: Produce the four required Specs prediction outputs (CLAUDE.md
Specs Module: ML Prediction Engine) from a project's accumulated Specs
snapshot history: upcoming-session likelihood + predicted outcome,
last-session summary, last-5-session average Success Score, and a
Mon-Sun zero-filled weekly coding-time breakdown.

Ships behind the MAJOR_PREDICTIVE_DASHBOARDS feature flag (Article
41-44), disabled by default. Trains periodically in the sense that
every call re-derives sessions and their Success Scores from whatever
history now exists in `SpecsStorage` (no separately persisted model -
there is nothing here that benefits from a stale cached fit); predicts
live using the last-hour window of ingested snapshots as its input
features, per CLAUDE.md. Cold start (little or no history) is expected
and always reported honestly via `ConfidenceLevel`/explanatory text,
never fabricated.
"""

import statistics
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from app.config.feature_flags import FeatureFlag, FeatureFlagRegistry, feature_flags
from app.config.logging_config import get_logger
from app.core.inspection_engine.models import utc_now
from app.core.project_isolation import project_scope, validate_project_id_format
from app.core.specs.enums import ConfidenceLevel
from app.core.specs.exceptions import SpecsPredictionDisabledError
from app.core.specs.models import (
    LastSessionSummary,
    RecentSessionsComparison,
    SessionRecord,
    SpecsPredictionReport,
    SpecsSnapshot,
    UpcomingSessionPrediction,
    WeeklyCodingTime,
    WeeklyPoint,
)
from app.core.specs.session import (
    DEFAULT_IDLE_GAP_MINUTES,
    DEFAULT_INGESTION_INTERVAL_MINUTES,
    ACTIVE,
    classify_activity,
    derive_sessions,
)
from app.core.specs.storage import SpecsStorage
from app.core.specs.success_score import compute_success_score

logger = get_logger("specs.predictor")

#: How many of the most recent sessions the "last-5-session comparison"
#: and the upcoming-session outcome estimate draw from (CLAUDE.md: "the
#: 5 most recent sessions").
RECENT_SESSION_WINDOW = 5

#: Session-count thresholds for honestly reported confidence tiers on
#: the upcoming-session prediction. More history -> more confidence,
#: but this is always a plain statistical estimate over derived
#: sessions, never a claim of a separately trained model.
_MEDIUM_CONFIDENCE_SESSION_COUNT = 5
_HIGH_CONFIDENCE_SESSION_COUNT = 20

#: A historical session "matches" the current moment if it started on
#: the same day of week and within this many hours of the current
#: time-of-day - used as the historical half of the upcoming-session
#: likelihood estimate.
_TIME_BUCKET_HOURS = 2.0

#: Weight given to the recent-activity-signal component vs. the
#: historical time-of-day/day-of-week match component when both are
#: available.
_ACTIVITY_COMPONENT_WEIGHT = 0.6
_HISTORICAL_COMPONENT_WEIGHT = 0.4


def _hour_of_day(moment: datetime) -> float:
    return moment.hour + moment.minute / 60.0 + moment.second / 3600.0


def _time_bucket_matches(session_start: datetime, now: datetime) -> bool:
    if session_start.weekday() != now.weekday():
        return False
    diff = abs(_hour_of_day(session_start) - _hour_of_day(now))
    diff = min(diff, 24.0 - diff)
    return diff <= _TIME_BUCKET_HOURS


def _confidence_for_session_count(session_count: int) -> ConfidenceLevel:
    if session_count <= 0:
        return ConfidenceLevel.NONE
    if session_count < _MEDIUM_CONFIDENCE_SESSION_COUNT:
        return ConfidenceLevel.LOW
    if session_count < _HIGH_CONFIDENCE_SESSION_COUNT:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.HIGH


def _mean(values: List[float]) -> Optional[float]:
    return statistics.fmean(values) if values else None


class SpecsPredictionEngine:
    """Top-level orchestrator for a single Specs ML Prediction run over
    one project's snapshot history."""

    def __init__(
        self,
        storage: Optional[SpecsStorage] = None,
        feature_flag_registry: Optional[FeatureFlagRegistry] = None,
        ingestion_interval_minutes: float = DEFAULT_INGESTION_INTERVAL_MINUTES,
        idle_gap_minutes: float = DEFAULT_IDLE_GAP_MINUTES,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._storage = storage or SpecsStorage()
        self._feature_flags = feature_flag_registry or feature_flags
        self._ingestion_interval_minutes = ingestion_interval_minutes
        self._idle_gap_minutes = idle_gap_minutes
        self._clock = clock or utc_now

    async def predict(self, project_id: str) -> SpecsPredictionReport:
        """Run the full Specs ML Prediction Engine for `project_id`.

        Raises SpecsPredictionDisabledError if MAJOR_PREDICTIVE_DASHBOARDS
        is disabled, and propagates SpecsDisabledError (from the
        underlying `SpecsStorage`) if MAJOR_IOT_ENVIRONMENTAL_ANALYTICS
        is disabled - both flags gate real telemetry to predict from.
        """
        self._require_enabled()
        normalized_project_id = validate_project_id_format(project_id)

        logger.info("Specs prediction started for project_id=%s", normalized_project_id)

        with project_scope(normalized_project_id):
            snapshots = await self._storage.list_snapshots(normalized_project_id)

        now = self._clock()
        sessions = derive_sessions(
            snapshots,
            ingestion_interval_minutes=self._ingestion_interval_minutes,
            idle_gap_minutes=self._idle_gap_minutes,
        )
        scored_sessions = self._score_sessions(sessions)

        report = SpecsPredictionReport(
            project_id=normalized_project_id,
            generated_at=now,
            upcoming_session=self._predict_upcoming_session(snapshots, scored_sessions, now),
            last_session=self._last_session_summary(scored_sessions),
            recent_sessions=self._recent_sessions_comparison(scored_sessions),
            weekly_coding_time=self._weekly_coding_time(normalized_project_id, scored_sessions, now),
        )

        logger.info(
            "Specs prediction completed for project_id=%s sessions_derived=%d",
            normalized_project_id,
            len(scored_sessions),
        )
        return report

    @staticmethod
    def _score_sessions(sessions: List[SessionRecord]) -> List[SessionRecord]:
        """Score every derived session against only the sessions that
        preceded it, so no session's score is influenced by data that
        did not yet exist when it happened."""
        scored: List[SessionRecord] = []
        for index, session in enumerate(sessions):
            score, basis = compute_success_score(session, scored[:index])
            scored.append(replace(session, success_score=score, success_score_basis=basis))
        return scored

    def _predict_upcoming_session(
        self,
        snapshots: List[SpecsSnapshot],
        sessions: List[SessionRecord],
        now: datetime,
    ) -> UpcomingSessionPrediction:
        last_hour_snapshots = [s for s in snapshots if s.recorded_at >= now - timedelta(hours=1)]
        has_recent_telemetry = bool(last_hour_snapshots)
        activity_signal = any(classify_activity(s) == ACTIVE for s in last_hour_snapshots)

        if not sessions:
            if not has_recent_telemetry:
                likelihood = 20.0
                basis = (
                    "No historical sessions have been derived yet and no telemetry was "
                    "ingested in the last hour; this is a low-confidence baseline "
                    "heuristic, not a trained-model prediction."
                )
            else:
                likelihood = 70.0 if activity_signal else 30.0
                basis = (
                    "No historical sessions have been derived yet, so the likelihood is "
                    "based only on whether the last-hour telemetry window shows an "
                    "active typing/mouse signal - not a trained-model prediction."
                )
            return UpcomingSessionPrediction(
                likelihood_score=likelihood,
                predicted_duration_minutes=None,
                predicted_success_score=None,
                confidence=ConfidenceLevel.NONE,
                basis=basis,
            )

        activity_component = 100.0 if activity_signal else (15.0 if has_recent_telemetry else 0.0)
        matching = sum(1 for session in sessions if _time_bucket_matches(session.started_at, now))
        historical_component = 100.0 * matching / len(sessions)
        likelihood = round(
            _ACTIVITY_COMPONENT_WEIGHT * activity_component
            + _HISTORICAL_COMPONENT_WEIGHT * historical_component,
            1,
        )

        recent = sessions[-RECENT_SESSION_WINDOW:]
        predicted_duration = _mean([s.duration_minutes for s in recent])
        predicted_success = _mean([s.success_score for s in recent if s.success_score is not None])

        confidence = _confidence_for_session_count(len(sessions))
        basis = (
            f"Statistical estimate from {len(sessions)} derived historical session(s): "
            f"{matching} started around this day-of-week/time-of-day, and the last-hour "
            f"telemetry window {'shows' if activity_signal else 'does not show'} an "
            f"active signal. Predicted duration/success score are the mean of the "
            f"{len(recent)} most recent session(s)."
        )
        return UpcomingSessionPrediction(
            likelihood_score=likelihood,
            predicted_duration_minutes=(
                round(predicted_duration, 2) if predicted_duration is not None else None
            ),
            predicted_success_score=(
                round(predicted_success, 2) if predicted_success is not None else None
            ),
            confidence=confidence,
            basis=basis,
        )

    @staticmethod
    def _last_session_summary(sessions: List[SessionRecord]) -> LastSessionSummary:
        if not sessions:
            return LastSessionSummary(
                has_session=False,
                started_at=None,
                ended_at=None,
                duration_minutes=None,
                success_score=None,
                success_score_basis=None,
                message="No sessions have been recorded yet.",
            )

        last = sessions[-1]
        message = (
            f"Last session ran {last.duration_minutes:.1f} minute(s)"
            + (
                f" with a Success Score of {last.success_score:.1f}."
                if last.success_score is not None
                else " (Success Score unavailable - see success_score_basis)."
            )
        )
        return LastSessionSummary(
            has_session=True,
            started_at=last.started_at,
            ended_at=last.ended_at,
            duration_minutes=last.duration_minutes,
            success_score=last.success_score,
            success_score_basis=last.success_score_basis,
            message=message,
        )

    @staticmethod
    def _recent_sessions_comparison(sessions: List[SessionRecord]) -> RecentSessionsComparison:
        recent = sessions[-RECENT_SESSION_WINDOW:]
        scores = [s.success_score for s in recent if s.success_score is not None]
        average = _mean(scores)

        if not recent:
            message = "No sessions have been recorded yet."
        elif not scores:
            message = f"{len(recent)} recent session(s) considered, but none have a computed Success Score yet."
        elif len(recent) < RECENT_SESSION_WINDOW:
            message = f"Average of {len(scores)} session(s) - fewer than {RECENT_SESSION_WINDOW} exist so far."
        else:
            message = f"Average of the {len(scores)} most recent sessions."

        return RecentSessionsComparison(
            sessions_considered=len(recent),
            success_scores=[round(score, 2) for score in scores],
            average_success_score=round(average, 2) if average is not None else None,
            message=message,
        )

    @staticmethod
    def _weekly_coding_time(
        project_id: str,
        sessions: List[SessionRecord],
        now: datetime,
    ) -> WeeklyCodingTime:
        week_start = now.date() - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)

        by_day = {week_start + timedelta(days=offset): [] for offset in range(7)}
        for session in sessions:
            session_date = session.started_at.date()
            if session_date in by_day:
                by_day[session_date].append(session)

        points = [
            WeeklyPoint(
                day_of_week=day.strftime("%A"),
                date=day,
                total_minutes=round(sum(s.duration_minutes for s in day_sessions), 2),
                session_count=len(day_sessions),
            )
            for day, day_sessions in sorted(by_day.items())
        ]

        return WeeklyCodingTime(
            project_id=project_id,
            week_start=week_start,
            week_end=week_end,
            points=points,
        )

    def _require_enabled(self) -> None:
        if not self._feature_flags.is_enabled(FeatureFlag.MAJOR_PREDICTIVE_DASHBOARDS):
            raise SpecsPredictionDisabledError(
                "Specs prediction was requested but the MAJOR_PREDICTIVE_DASHBOARDS "
                "feature flag is disabled."
            )
