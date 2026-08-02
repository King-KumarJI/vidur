"""Unit tests for app.core.specs.session (CLAUDE.md Specs Module:
Session derivation)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.specs.models import (
    ComputerMetrics,
    EnvironmentalMetrics,
    MetricReading,
    PersonalMetrics,
    SpecsSnapshot,
)
from app.core.specs.session import classify_activity, derive_sessions

_BASE_TIME = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)  # a Monday
_MISSING = MetricReading.missing()


def _snapshot(
    offset_minutes: float,
    typing: Optional[float] = None,
    mouse: Optional[float] = None,
    project_id: str = "demo-project",
) -> SpecsSnapshot:
    typing_reading = MetricReading.present(typing) if typing is not None else _MISSING
    mouse_reading = MetricReading.present(mouse) if mouse is not None else _MISSING
    return SpecsSnapshot(
        project_id=project_id,
        recorded_at=_BASE_TIME + timedelta(minutes=offset_minutes),
        personal=PersonalMetrics(
            last_session_duration_minutes=_MISSING,
            sleep_hours=_MISSING,
            caffeine_intake_mg=_MISSING,
            typing_speed_cpm=typing_reading,
            mouse_activity_rate=mouse_reading,
            break_frequency_per_hour=_MISSING,
        ),
        computer=ComputerMetrics(_MISSING, _MISSING, _MISSING, _MISSING),
        environmental=EnvironmentalMetrics(_MISSING, _MISSING, _MISSING, _MISSING),
    )


def test_classify_activity_active_inactive_unknown():
    assert classify_activity(_snapshot(0, typing=30.0)) == "active"
    assert classify_activity(_snapshot(0, mouse=10.0)) == "active"
    assert classify_activity(_snapshot(0, typing=0.0, mouse=0.0)) == "inactive"
    assert classify_activity(_snapshot(0)) == "unknown"


def test_continuous_active_snapshots_form_one_session():
    snapshots = [_snapshot(offset, typing=40.0) for offset in (0, 5, 10, 15, 20)]
    sessions = derive_sessions(snapshots)

    assert len(sessions) == 1
    session = sessions[0]
    assert session.duration_minutes == 20.0
    assert session.snapshot_count == 5
    assert session.break_count == 0


def test_gap_exceeding_threshold_splits_into_two_sessions():
    first_cluster = [_snapshot(offset, typing=40.0) for offset in (0, 5, 10)]
    second_cluster = [_snapshot(offset, typing=40.0) for offset in (60, 65, 70)]
    sessions = derive_sessions(first_cluster + second_cluster)

    assert len(sessions) == 2
    assert sessions[0].duration_minutes == 10.0
    assert sessions[1].duration_minutes == 10.0


def test_inactive_stretch_within_session_counts_as_one_break():
    snapshots = [
        _snapshot(0, typing=40.0),
        _snapshot(5, typing=30.0),
        _snapshot(10, typing=0.0, mouse=0.0),
        _snapshot(15, typing=35.0),
        _snapshot(20, typing=25.0),
    ]
    sessions = derive_sessions(snapshots)

    assert len(sessions) == 1
    session = sessions[0]
    assert session.duration_minutes == 20.0
    assert session.break_count == 1
    assert session.breaks_per_hour == 3.0


def test_unknown_snapshot_does_not_end_session_or_count_as_break():
    snapshots = [
        _snapshot(0, typing=40.0),
        _snapshot(5, typing=30.0),
        _snapshot(10),  # unknown: both fields missing
        _snapshot(15, typing=35.0),
        _snapshot(20, typing=25.0),
    ]
    sessions = derive_sessions(snapshots)

    assert len(sessions) == 1
    assert sessions[0].snapshot_count == 5
    assert sessions[0].break_count == 0


def test_run_with_no_activity_signal_produces_no_session():
    all_inactive = [_snapshot(offset, typing=0.0, mouse=0.0) for offset in (0, 5, 10)]
    all_unknown = [_snapshot(offset) for offset in (100, 105, 110)]

    assert derive_sessions(all_inactive) == []
    assert derive_sessions(all_unknown) == []


def test_single_snapshot_run_is_not_a_session():
    sessions = derive_sessions([_snapshot(0, typing=40.0)])
    assert sessions == []


def test_empty_snapshot_list_returns_no_sessions():
    assert derive_sessions([]) == []


def test_activity_aggregates_computed_from_present_values_only():
    snapshots = [
        _snapshot(0, typing=20.0, mouse=5.0),
        _snapshot(5, typing=40.0),  # mouse missing this cycle
        _snapshot(10, typing=60.0, mouse=15.0),
    ]
    sessions = derive_sessions(snapshots)

    assert len(sessions) == 1
    session = sessions[0]
    assert session.avg_typing_speed_cpm == 40.0
    assert session.avg_mouse_activity_rate == 10.0
