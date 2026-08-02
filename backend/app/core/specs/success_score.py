"""
VIDUR Core - Specs
Submodule: Success Score
Purpose: Compute the 0-100 per-session Success Score (CLAUDE.md Specs
Module: Success Score) from whichever session-level signals are
actually present, reweighting over what's available rather than
failing on a missing one.

Exact formula (documented here, and mirrored in the development
tracker's design notes, so it is inspectable later):

Three components, each independently scored 0-100 and independently
optional depending on data availability:

  A. Duration closeness (weight 0.40) - how close the session's
     duration is to the mean duration of the sessions that preceded it
     (not "longer is better"). Requires at least one prior session.
         ratio = duration_minutes / historical_mean_duration_minutes
         deviation = abs(1 - ratio), clamped to [0, 1]
         score_A = 100 * (1 - deviation)

  B. Activity consistency (weight 0.35) - low variance in typing/mouse
     rate during the session, measured via each signal's coefficient
     of variation (stdev / mean) where the signal was present on at
     least 2 snapshots in the session. Averaged across whichever of
     typing/mouse are available.
         cv = stdev / mean  (undefined, so excluded, if mean == 0)
         score_signal = 100 * (1 - clamp(cv, 0, 1))
         score_B = mean(score_signal for each available signal)

  C. Break-frequency health (weight 0.25) - peaks at a healthy
     breaks/hour rate, not zero, not excessive. Requires a defined
     breaks_per_hour (i.e. duration_minutes > 0).
         score_C = clamp(100 - 40 * abs(breaks_per_hour - 2.0), 0, 100)
     (2.0 breaks/hour - one short break roughly every 30 minutes - is
     the assumed healthy peak; the 40-point-per-break-per-hour penalty
     means 0 breaks/hour scores 20/100 - low, but not zero, matching
     "not zero" - and >= 4.5 breaks/hour scores 0.)

Final score = weighted average of whichever components are available,
with their weights renormalized to sum to 1. If none of the three
components can be computed (first-ever session with no typing/mouse
data at all), no score is fabricated - the function returns None with
an explanatory basis string instead (CLAUDE.md: never fabricate a
score/confidence that has no support).
"""

from typing import List, Optional, Tuple

from app.core.specs.models import SessionRecord

DURATION_CLOSENESS_WEIGHT = 0.40
ACTIVITY_CONSISTENCY_WEIGHT = 0.35
BREAK_HEALTH_WEIGHT = 0.25

IDEAL_BREAKS_PER_HOUR = 2.0
BREAK_HEALTH_PENALTY_PER_UNIT = 40.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _duration_closeness_score(session: SessionRecord, historical_sessions: List[SessionRecord]) -> Optional[float]:
    if not historical_sessions:
        return None
    historical_mean = sum(s.duration_minutes for s in historical_sessions) / len(historical_sessions)
    if historical_mean <= 0:
        return None
    ratio = session.duration_minutes / historical_mean
    deviation = _clamp(abs(1.0 - ratio), 0.0, 1.0)
    return 100.0 * (1.0 - deviation)


def _consistency_component(mean: Optional[float], stdev: Optional[float]) -> Optional[float]:
    if mean is None or stdev is None or mean <= 0:
        return None
    coefficient_of_variation = _clamp(stdev / mean, 0.0, 1.0)
    return 100.0 * (1.0 - coefficient_of_variation)


def _activity_consistency_score(session: SessionRecord) -> Optional[float]:
    signal_scores = [
        score
        for score in (
            _consistency_component(session.avg_typing_speed_cpm, session.typing_speed_stdev),
            _consistency_component(session.avg_mouse_activity_rate, session.mouse_activity_stdev),
        )
        if score is not None
    ]
    if not signal_scores:
        return None
    return sum(signal_scores) / len(signal_scores)


def _break_health_score(session: SessionRecord) -> Optional[float]:
    if session.breaks_per_hour is None:
        return None
    penalty = BREAK_HEALTH_PENALTY_PER_UNIT * abs(session.breaks_per_hour - IDEAL_BREAKS_PER_HOUR)
    return _clamp(100.0 - penalty, 0.0, 100.0)


def compute_success_score(
    session: SessionRecord,
    historical_sessions: List[SessionRecord],
) -> Tuple[Optional[float], str]:
    """Return `(score, basis)` for `session`, scored only against
    `historical_sessions` that preceded it (never against sessions that
    happened afterward, to avoid look-ahead bias). `score` is None, with
    `basis` explaining why, when no component signal is available at
    all."""
    components: List[Tuple[float, float, str]] = []

    duration_score = _duration_closeness_score(session, historical_sessions)
    if duration_score is not None:
        components.append((DURATION_CLOSENESS_WEIGHT, duration_score, "duration-closeness"))

    consistency_score = _activity_consistency_score(session)
    if consistency_score is not None:
        components.append((ACTIVITY_CONSISTENCY_WEIGHT, consistency_score, "activity-consistency"))

    break_score = _break_health_score(session)
    if break_score is not None:
        components.append((BREAK_HEALTH_WEIGHT, break_score, "break-frequency-health"))

    if not components:
        return None, (
            "No scoring signal was available (no prior session to compare duration "
            "against, and no typing/mouse activity or break data on this session) - "
            "Success Score was left unscored rather than fabricated."
        )

    total_weight = sum(weight for weight, _, _ in components)
    score = sum(weight * value for weight, value, _ in components) / total_weight
    used = ", ".join(name for _, _, name in components)
    basis = (
        f"Scored from {len(components)} of 3 available signal(s) ({used}), "
        f"reweighted to sum to 1.0 since the remaining signal(s) were unavailable."
        if len(components) < 3
        else f"Scored from all 3 signals ({used})."
    )
    return round(score, 2), basis
