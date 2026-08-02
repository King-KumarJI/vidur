"""Unit tests for app.core.specs.success_score (CLAUDE.md Specs Module:
Success Score), verified against the documented formula's exact
arithmetic, not just approximate bounds."""

from datetime import datetime, timedelta, timezone

from app.core.specs.models import SessionRecord
from app.core.specs.success_score import compute_success_score

_BASE_TIME = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)


def _session(
    duration_minutes: float = 30.0,
    breaks_per_hour=None,
    avg_typing_speed_cpm=None,
    typing_speed_stdev=None,
    avg_mouse_activity_rate=None,
    mouse_activity_stdev=None,
) -> SessionRecord:
    return SessionRecord(
        project_id="demo-project",
        started_at=_BASE_TIME,
        ended_at=_BASE_TIME + timedelta(minutes=duration_minutes),
        duration_minutes=duration_minutes,
        snapshot_count=5,
        break_count=0,
        breaks_per_hour=breaks_per_hour,
        avg_typing_speed_cpm=avg_typing_speed_cpm,
        typing_speed_stdev=typing_speed_stdev,
        avg_mouse_activity_rate=avg_mouse_activity_rate,
        mouse_activity_stdev=mouse_activity_stdev,
    )


def test_no_signal_available_returns_none_not_fabricated():
    score, basis = compute_success_score(_session(), historical_sessions=[])
    assert score is None
    assert "rather than fabricated" in basis


def test_duration_only_component_matches_formula():
    historical = [_session(duration_minutes=30.0)]
    session = _session(duration_minutes=33.0)  # ratio 1.1 -> deviation 0.1 -> score 90
    score, basis = compute_success_score(session, historical)
    assert score == 90.0
    assert "duration-closeness" in basis


def test_break_frequency_peaks_at_ideal_rate():
    ideal_score, _ = compute_success_score(_session(breaks_per_hour=2.0), historical_sessions=[])
    assert ideal_score == 100.0


def test_break_frequency_zero_is_not_ideal_but_not_zero_score():
    score, _ = compute_success_score(_session(breaks_per_hour=0.0), historical_sessions=[])
    assert score == 20.0


def test_break_frequency_excessive_scores_zero():
    score, _ = compute_success_score(_session(breaks_per_hour=6.0), historical_sessions=[])
    assert score == 0.0


def test_activity_consistency_from_single_signal():
    # mean=50, stdev=5 -> cv=0.1 -> score 90
    score, basis = compute_success_score(
        _session(avg_typing_speed_cpm=50.0, typing_speed_stdev=5.0), historical_sessions=[]
    )
    assert score == 90.0
    assert "activity-consistency" in basis


def test_all_three_components_weighted_and_averaged():
    historical = [_session(duration_minutes=30.0)]
    session = _session(
        duration_minutes=33.0,  # score_A = 90
        avg_typing_speed_cpm=50.0,
        typing_speed_stdev=5.0,  # score_B = 90 (single signal)
        breaks_per_hour=2.0,  # score_C = 100
    )
    score, basis = compute_success_score(session, historical)
    # 0.40*90 + 0.35*90 + 0.25*100 = 92.5
    assert score == 92.5
    assert "all 3 signals" in basis


def test_missing_component_reweights_remaining_to_sum_to_one():
    # Only break-frequency available: weight should renormalize to 1.0,
    # not stay at 0.25 of an otherwise-zero score.
    score, basis = compute_success_score(_session(breaks_per_hour=2.0), historical_sessions=[])
    assert score == 100.0
    assert "reweighted" in basis


def test_scoring_uses_only_sessions_passed_in_not_future_ones():
    # The caller is responsible for only passing sessions that preceded
    # this one; verify the function itself has no ordering opinion -
    # it simply averages whatever historical_sessions it is given.
    historical = [_session(duration_minutes=10.0), _session(duration_minutes=50.0)]
    session = _session(duration_minutes=30.0)  # mean historical = 30 -> ratio 1.0 -> score 100
    score, _ = compute_success_score(session, historical)
    assert score == 100.0
