"""
VIDUR Core - Specs
Submodule: Session Derivation
Purpose: Reconstruct coding sessions from the historical stream of
ingested Specs snapshots (CLAUDE.md Specs Module: Session derivation).
No explicit session-boundary event exists in VIDUR - a session is
inferred by walking time-ordered snapshots and grouping the ones close
enough together in time to plausibly be one sitting.

Algorithm (deterministic, documented here because CLAUDE.md's rule is
necessarily a prose approximation and this is the concrete reading it
resolves to):

1. Classify every snapshot's Personal activity signal as ACTIVE
   (typing_speed_cpm > 0 or mouse_activity_rate > 0, either present),
   INACTIVE (both fields present and both zero), or UNKNOWN (both
   fields missing - CLAUDE.md: "a missing personal-activity field in
   some snapshots means unknown, not no activity - don't let it break
   the walk").
2. Split the full snapshot stream into raw contiguous runs wherever the
   gap between two consecutive snapshots exceeds
   `ingestion_interval_minutes + idle_gap_minutes` - this is the
   literal "gap larger than the threshold ends the session" rule, and
   it alone determines run boundaries (activity does not).
3. A raw run only qualifies as a session if it contains at least one
   ACTIVE snapshot and at least 2 snapshots (a session needs a
   measurable duration). A run with no activity signal at all - all
   INACTIVE/UNKNOWN - is discarded, which is the literal "a run with no
   activity signal ... ends the session" rule read as "such a run is
   never promoted to a session" rather than "trims mid-run". UNKNOWN
   snapshots never disqualify a run by themselves, since they carry no
   evidence either way.
4. Within a qualifying session, each maximal contiguous stretch of
   INACTIVE snapshots is one "break" (CLAUDE.md Personal: break
   frequency "derived from activity gaps") - UNKNOWN snapshots neither
   start nor extend a break stretch, they are simply skipped over.
5. Session duration = last snapshot's timestamp minus first snapshot's
   timestamp within the run, exactly as CLAUDE.md specifies.
"""

import statistics
from datetime import timedelta
from typing import List, Optional

from app.core.specs.enums import MetricStatus
from app.core.specs.models import SessionRecord, SpecsSnapshot

DEFAULT_INGESTION_INTERVAL_MINUTES = 5.0
DEFAULT_IDLE_GAP_MINUTES = 10.0

ACTIVE = "active"
INACTIVE = "inactive"
UNKNOWN = "unknown"


def classify_activity(snapshot: SpecsSnapshot) -> str:
    """Classify one snapshot's Personal activity signal as ACTIVE,
    INACTIVE, or UNKNOWN. Exposed publicly (not just used internally by
    `derive_sessions`) so `predictor.py` can apply the same
    classification to the last-hour feature window."""
    typing = snapshot.personal.typing_speed_cpm
    mouse = snapshot.personal.mouse_activity_rate
    typing_known = typing.status == MetricStatus.PRESENT
    mouse_known = mouse.status == MetricStatus.PRESENT

    if not typing_known and not mouse_known:
        return UNKNOWN

    typing_active = typing_known and (typing.value or 0.0) > 0.0
    mouse_active = mouse_known and (mouse.value or 0.0) > 0.0
    return ACTIVE if (typing_active or mouse_active) else INACTIVE


def _split_into_raw_runs(
    snapshots: List[SpecsSnapshot], max_gap: timedelta
) -> List[List[SpecsSnapshot]]:
    runs: List[List[SpecsSnapshot]] = []
    current: List[SpecsSnapshot] = []
    previous_time = None

    for snapshot in snapshots:
        if previous_time is not None and (snapshot.recorded_at - previous_time) > max_gap:
            if current:
                runs.append(current)
            current = []
        current.append(snapshot)
        previous_time = snapshot.recorded_at

    if current:
        runs.append(current)
    return runs


def _count_breaks(statuses: List[str]) -> int:
    break_count = 0
    previous_was_inactive = False
    for status in statuses:
        if status == INACTIVE:
            if not previous_was_inactive:
                break_count += 1
            previous_was_inactive = True
        elif status == ACTIVE:
            previous_was_inactive = False
        # UNKNOWN leaves previous_was_inactive untouched: it neither
        # extends nor resets an in-progress inactive stretch.
    return break_count


def _mean_and_stdev(values: List[float]) -> "tuple[Optional[float], Optional[float]]":
    if not values:
        return None, None
    mean = statistics.fmean(values)
    stdev = statistics.stdev(values) if len(values) >= 2 else None
    return mean, stdev


def _build_session_record(run: List[SpecsSnapshot]) -> SessionRecord:
    statuses = [classify_activity(snapshot) for snapshot in run]
    started_at = run[0].recorded_at
    ended_at = run[-1].recorded_at
    duration_minutes = (ended_at - started_at).total_seconds() / 60.0
    break_count = _count_breaks(statuses)
    breaks_per_hour = (break_count / (duration_minutes / 60.0)) if duration_minutes > 0 else None

    typing_values = [
        snapshot.personal.typing_speed_cpm.value
        for snapshot in run
        if snapshot.personal.typing_speed_cpm.status == MetricStatus.PRESENT
        and snapshot.personal.typing_speed_cpm.value is not None
    ]
    mouse_values = [
        snapshot.personal.mouse_activity_rate.value
        for snapshot in run
        if snapshot.personal.mouse_activity_rate.status == MetricStatus.PRESENT
        and snapshot.personal.mouse_activity_rate.value is not None
    ]
    avg_typing, typing_stdev = _mean_and_stdev(typing_values)
    avg_mouse, mouse_stdev = _mean_and_stdev(mouse_values)

    return SessionRecord(
        project_id=run[0].project_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_minutes=round(duration_minutes, 2),
        snapshot_count=len(run),
        break_count=break_count,
        breaks_per_hour=round(breaks_per_hour, 4) if breaks_per_hour is not None else None,
        avg_typing_speed_cpm=avg_typing,
        typing_speed_stdev=typing_stdev,
        avg_mouse_activity_rate=avg_mouse,
        mouse_activity_stdev=mouse_stdev,
    )


def derive_sessions(
    snapshots: List[SpecsSnapshot],
    ingestion_interval_minutes: float = DEFAULT_INGESTION_INTERVAL_MINUTES,
    idle_gap_minutes: float = DEFAULT_IDLE_GAP_MINUTES,
) -> List[SessionRecord]:
    """Reconstruct sessions from `snapshots` (must already be time-
    ordered, oldest first - `SpecsStorage.list_snapshots`'s contract).
    Returns sessions oldest-first, each unscored (`success_score` is
    None until `success_score.compute_success_score` fills it in)."""
    if not snapshots:
        return []

    max_gap = timedelta(minutes=ingestion_interval_minutes + idle_gap_minutes)
    sessions: List[SessionRecord] = []
    for run in _split_into_raw_runs(snapshots, max_gap):
        if len(run) < 2:
            continue
        statuses = [classify_activity(snapshot) for snapshot in run]
        if ACTIVE not in statuses:
            continue
        sessions.append(_build_session_record(run))

    return sessions
