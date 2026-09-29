"""
When a publish destination is due. Pure, and shared: the admin panel announces
the next run from here and the publish job decides what to start from here, so
what the panel says is what the job does.
"""

from datetime import UTC, date, datetime, time, timedelta

from utils.database.models.publish import PublishFrequency


def _at_hour(local: datetime, hour: int) -> datetime:
    """
    That day at that hour, in the same zone.

    On the day the clocks go forward the hour may not exist, and asking for it
    gives a moment that is really the hour before or after. The run then fires
    at the wrong time once a year, or twice on the day they go back. Where the
    hour is missing we take the next one that exists; where it happens twice we
    take the first, which 'fold=0' already does.
    """
    zone = local.tzinfo
    for offset in range(3):
        due = local.replace(
            hour=(hour + offset) % 24, minute=0, second=0, microsecond=0, fold=0
        )
        # An hour the clocks skipped comes back as a different one.
        if due.astimezone(UTC).astimezone(zone).hour == due.hour:
            return due
    return local.replace(hour=hour, minute=0, second=0, microsecond=0, fold=0)


def _due_on(day: date) -> datetime:
    # The hour is worked out per day, because whether it exists depends on
    # the day: 02:00 is missing on the morning the clocks go forward and
    # back the morning after.
    return _at_hour(datetime.combine(day, time(), tzinfo=UTC), 3)


def _week_anchor(day: date, forward: bool) -> date:
    """Monday on/after `day` if forward, Monday on/before `day` if not."""
    if forward:
        return day + timedelta(days=(7 - day.weekday()) % 7)
    return day - timedelta(days=day.weekday())


def _step(frequency: PublishFrequency, day: date, forward: bool) -> date:
    """One period on from `day`, in the given direction."""
    if frequency == "daily":
        return day + timedelta(days=1 if forward else -1)
    if frequency == "weekly":
        return day + timedelta(days=7 if forward else -7)
    if forward:
        # The 28th of any month plus four days is always the next month.
        return (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return (day - timedelta(days=1)).replace(day=1)


def _occurrence(
    frequency: PublishFrequency, local: datetime, forward: bool
) -> datetime | None:
    """The occurrence on/after `local` if forward, on/before it if not."""
    if frequency not in ("daily", "weekly", "monthly"):
        return None

    day = local.date()
    if frequency == "weekly":
        day = _week_anchor(day, forward)
    elif frequency == "monthly":
        day = day.replace(day=1)

    if (_due_on(day) <= local) == forward:
        day = _step(frequency, day, forward)

    return _due_on(day).astimezone(UTC)


def next_run_at(frequency: PublishFrequency, after: datetime) -> datetime | None:
    """
    The next moment the run is due, in UTC. Weekly means Monday, monthly means
    the first of the month. The execution time is fixed at 03:00 UTC so the
    admin only has one setting to understand: publication frequency.

    Always a future moment. Whether an occurrence already went by unrun is
    what previous_run_at is for.
    """
    return _occurrence(frequency, after.astimezone(UTC), forward=True)


def previous_run_at(frequency: PublishFrequency, at: datetime) -> datetime | None:
    """
    The most recent moment the run was due, at or before 'at', in UTC. The
    counterpart of next_run_at: a destination whose last run started before
    this moment has an occurrence it has not run yet.
    """
    return _occurrence(frequency, at.astimezone(UTC), forward=False)
